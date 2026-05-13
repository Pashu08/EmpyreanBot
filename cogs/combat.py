import discord
from discord.ext import commands
import random
import asyncio
import datetime
from utils.constants import ENEMIES, TECHNIQUES, SHOP_ITEMS
from utils.helpers import has_meridian_damage
from utils.db import add_item

# ==========================================
# ENEMY RARITY SYSTEM (5 tiers)
# ==========================================
RARITIES = {
    "Common":    {"chance": 45, "hp_mult": 1.0, "atk_mult": 1.0, "reward_mult": 1.0, "drop_chance": 0.05},
    "Elite":     {"chance": 25, "hp_mult": 1.5, "atk_mult": 1.5, "reward_mult": 1.5, "drop_chance": 0.15},
    "Master":    {"chance": 15, "hp_mult": 2.2, "atk_mult": 2.2, "reward_mult": 2.2, "drop_chance": 0.30},
    "Grandmaster":{"chance": 10, "hp_mult": 3.0, "atk_mult": 3.0, "reward_mult": 3.0, "drop_chance": 0.50},
    "Mythical":  {"chance": 5,  "hp_mult": 4.5, "atk_mult": 4.5, "reward_mult": 4.5, "drop_chance": 0.80}
}

# Murim-style enemy names (by base rank + rarity)
ENEMY_NAMES = {
    "Third-Rate Warrior": {
        "Common": "Blood Wolf",
        "Elite": "Shadow Wolf Pack Leader",
        "Master": "Frost Wolf King",
        "Grandmaster": "Moonlight Devourer",
        "Mythical": "Fenrir, The World-Ender"
    },
    "Second-Rate Warrior": {
        "Common": "Ironhide Panther",
        "Elite": "Venomous Shadow Panther",
        "Master": "Ember Mane Panther",
        "Grandmaster": "Star-Swallowing Panther",
        "Mythical": "Asura, The Soul Reaper"
    },
    "First-Rate Warrior": {
        "Common": "Corrupted Monk",
        "Elite": "Fallen Elder",
        "Master": "Soul Devouring Monk",
        "Grandmaster": "Heaven Defier",
        "Mythical": "Primordial Demon Lord"
    },
    "Peak Master": {
        "Common": "Ancient Bloodfiend",
        "Elite": "Crimson Blood Count",
        "Master": "Scarlet King",
        "Grandmaster": "Blood Emperor",
        "Mythical": "Kami of Eternal Night"
    }
}

# ==========================================
# LEADERBOARD VIEW (buttons to cycle)
# ==========================================
class LeaderboardView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.mode = "total_hunts"

    async def get_leaderboard_embed(self, mode):
        db = self.bot.db
        if mode == "total_hunts":
            order = "hunt_total DESC"
            title = "🏆 Most Hunts (Lifetime)"
            value_col = "hunt_total"
        elif mode == "highest_damage":
            order = "hunt_damage_max DESC"
            title = "💥 Highest Single Hit Damage"
            value_col = "hunt_damage_max"
        elif mode == "fastest_kill":
            order = "hunt_fastest_turns ASC"
            title = "⚡ Fastest Kill (least turns)"
            value_col = "hunt_fastest_turns"
        elif mode == "elite_kills":
            order = "hunt_elite_kills DESC"
            title = "👑 Elite & Boss Kills"
            value_col = "hunt_elite_kills"
        else:
            order = "hunt_taels_earned DESC"
            title = "💰 Total Taels from Hunting"
            value_col = "hunt_taels_earned"

        async with db.execute(f"""
            SELECT user_id, {value_col} FROM users
            WHERE {value_col} IS NOT NULL AND {value_col} > 0
            ORDER BY {order}
            LIMIT 10
        """) as cursor:
            rows = await cursor.fetchall()

        embed = discord.Embed(title=title, color=0x700000)
        if not rows:
            embed.description = "No data yet. Go hunt!"
        else:
            desc = ""
            for i, (uid, val) in enumerate(rows, 1):
                user = self.bot.get_user(uid)
                name = user.display_name if user else f"<@{uid}>"
                if mode == "fastest_kill":
                    desc += f"{i}. {name} – **{val} turns**\n"
                else:
                    desc += f"{i}. {name} – **{val}**\n"
            embed.description = desc
        embed.set_footer(text=f"Requested by {self.bot.get_user(self.user_id).display_name}")
        return embed

    async def update(self, interaction):
        embed = await self.get_leaderboard_embed(self.mode)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏆 Total Hunts", style=discord.ButtonStyle.secondary)
    async def btn_total(self, interaction, button):
        self.mode = "total_hunts"
        await self.update(interaction)

    @discord.ui.button(label="💥 Highest Damage", style=discord.ButtonStyle.secondary)
    async def btn_damage(self, interaction, button):
        self.mode = "highest_damage"
        await self.update(interaction)

    @discord.ui.button(label="⚡ Fastest Kill", style=discord.ButtonStyle.secondary)
    async def btn_fastest(self, interaction, button):
        self.mode = "fastest_kill"
        await self.update(interaction)

    @discord.ui.button(label="👑 Elite Kills", style=discord.ButtonStyle.secondary)
    async def btn_elite(self, interaction, button):
        self.mode = "elite_kills"
        await self.update(interaction)

    @discord.ui.button(label="💰 Taels Earned", style=discord.ButtonStyle.secondary)
    async def btn_taels(self, interaction, button):
        self.mode = "taels_earned"
        await self.update(interaction)

# ==========================================
# COMBAT VIEW (the actual battle)
# ==========================================
class CombatView(discord.ui.View):
    def __init__(self, bot, author_id, player_data, enemy_data, rarity, color):
        super().__init__(timeout=180)
        self.bot = bot
        self.author_id = author_id
        self.rarity = rarity
        self.color = color
        self.lock = asyncio.Lock()
        self.ended = False

        # player_data: (user_id, hp, vitality, ki, mastery, active_tech, rank, combat_mastery, taels)
        self.player = list(player_data)
        self.enemy = enemy_data.copy()
        self.enemy["max_hp"] = self.enemy["hp"]
        self.max_hp = self.player[1]
        self.max_enemy_hp = self.enemy["hp"]

        self.log = "The battle lines are drawn."
        self.turn = 1
        self.daily_hunts_today = 0
        self.last_damage = 0

        tech_name = self.player[5]
        if tech_name and tech_name != "None" and tech_name in TECHNIQUES:
            self.technique.label = tech_name
            self.tech_effect_text = TECHNIQUES[tech_name]["effect_text"]
        else:
            self.technique.disabled = True
            self.technique.label = "No Technique"
            self.tech_effect_text = "None"

    async def interaction_check(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your fight.", ephemeral=True)
            return False
        return not self.ended

    def generate_bar(self, current, total):
        ratio = max(0, min(current / total, 1))
        filled = int(ratio * 10)
        return "🟥" * filled + "⬛" * (10 - filled)

    async def safe_edit(self, interaction, embed, view=None):
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)
        except (discord.NotFound, discord.HTTPException):
            pass

    async def update_embed(self, interaction):
        if self.player[1] <= 0 or self.enemy["hp"] <= 0:
            self.ended = True
            for child in self.children:
                child.disabled = True
            await self.end_battle(interaction)
            return

        embed = discord.Embed(title=f"⚔️ Duel vs {self.enemy['name']}", color=self.color)
        embed.add_field(name=f"👤 You (HP: {int(self.player[1])})", value=f"`{self.generate_bar(self.player[1], self.max_hp)}`", inline=False)
        embed.add_field(name=f"👹 {self.enemy['name']} (HP: {int(self.enemy['hp'])})", value=f"`{self.generate_bar(self.enemy['hp'], self.max_enemy_hp)}`", inline=False)
        embed.add_field(name="📜 Combat Log", value=f"```ml\n{self.log}\n```", inline=False)
        embed.set_footer(text=f"Turn: {self.turn} | Ki: {self.player[3]} | Technique: {self.tech_effect_text}")
        await self.safe_edit(interaction, embed, self)

    async def end_battle(self, interaction):
        db = self.bot.db
        if self.player[1] <= 0:  # Defeat
            tael_loss = max(1, int(self.player[8] * 0.10))
            new_taels = max(0, self.player[8] - tael_loss)
            debuff = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            await db.execute(
                "UPDATE users SET hp = 20, vitality = 20, ki = ?, taels = ?, meridian_damage = ? WHERE user_id = ?",
                (self.player[3], new_taels, debuff, self.player[0])
            )
            await db.commit()
            embed = discord.Embed(title="💀 DEFEATED", color=0x000000,
                                  description=f"You fell to **{self.enemy['name']}**.\n❌ Lost **{tael_loss}** Taels.\nMeridians damaged for 10 minutes.")
        else:  # Victory
            base_reward = random.randint(50, 150)
            mult = self.rarity["reward_mult"]
            if self.daily_hunts_today < 3:
                mult *= 2
            cm_bonus = 1 + (self.player[7] * 0.005)
            final_reward = int(base_reward * mult * cm_bonus)
            drop_item = None
            if random.random() < self.rarity["drop_chance"]:
                possible_items = list(SHOP_ITEMS.keys())
                drop_item = random.choice(possible_items)
                await add_item(db, self.player[0], drop_item, 1)
            await db.execute("""
                UPDATE users SET
                    hp = ?, vitality = ?, ki = ?, taels = taels + ?,
                    combat_mastery = combat_mastery + 2.0,
                    hunt_total = COALESCE(hunt_total, 0) + 1,
                    hunt_taels_earned = COALESCE(hunt_taels_earned, 0) + ?,
                    hunt_damage_max = MAX(COALESCE(hunt_damage_max, 0), ?),
                    hunt_fastest_turns = CASE WHEN COALESCE(hunt_fastest_turns, 999) > ? THEN ? ELSE hunt_fastest_turns END,
                    hunt_elite_kills = hunt_elite_kills + CASE WHEN ? IN ('Elite','Master','Grandmaster','Mythical') THEN 1 ELSE 0 END
                WHERE user_id = ?
            """, (int(self.player[1]), int(self.player[2]), self.player[3], final_reward, final_reward, self.last_damage, self.turn, self.turn, self.rarity["name"], self.player[0]))
            await db.commit()
            desc = f"The **{self.enemy['name']}** falls!\n💰 Earned: **{final_reward} Taels**\n⚔️ Gained: **2.0 Combat Mastery**"
            if drop_item:
                desc += f"\n🎁 Dropped: **{drop_item}**"
            embed = discord.Embed(title="🏆 VICTORY", color=0x00FF00, description=desc)
        await self.safe_edit(interaction, embed, None)
        self.stop()
        
    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def strike(self, interaction, button):
        async with self.lock:
            if self.ended: return
            rank_atk = {"The Bound (Mortal)": 8, "Third-Rate Warrior": 25, "Second-Rate Warrior": 60, "First-Rate Warrior": 150, "Peak Master": 250}
            base_atk = rank_atk.get(self.player[6], 10)
            dmg = random.randint(base_atk, base_atk + 25)
            crit = random.random() < 0.1
            if crit:
                dmg *= 2
                crit_text = " **CRITICAL!**"
            else:
                crit_text = ""
            self.enemy["hp"] = max(0, self.enemy["hp"] - dmg)
            self.last_damage = dmg
            self.log = f"Turn {self.turn}: You strike for {dmg}{crit_text}."

            if self.enemy["hp"] > 0:
                e_dmg = random.randint(max(1, self.enemy["atk"]-5), self.enemy["atk"]+5)
                if self.player[5] == "Golden Bell Shield":
                    e_dmg = int(e_dmg * 0.8)
                self.player[1] = max(0, self.player[1] - e_dmg)
                self.log += f"\nTurn {self.turn}: Enemy hits for {e_dmg}."
            self.turn += 1
            await self.update_embed(interaction)

    @discord.ui.button(label="Technique", style=discord.ButtonStyle.primary, emoji="🌀")
    async def technique(self, interaction, button):
        async with self.lock:
            if self.ended: return
            if self.player[3] < 15:
                await interaction.response.send_message("❌ Not enough Ki!", ephemeral=True)
                return
            self.player[3] -= 15
            tech_name = self.player[5]
            tech_atk = {"The Bound (Mortal)": 15, "Third-Rate Warrior": 50, "Second-Rate Warrior": 120, "First-Rate Warrior": 300, "Peak Master": 450}
            base_atk = tech_atk.get(self.player[6], 20)
            dmg = int(random.randint(base_atk, base_atk + 50) * (1 + (self.player[4] / 100)))
            crit = random.random() < 0.1
            if crit:
                dmg *= 2
                crit_text = " **CRITICAL!**"
            else:
                crit_text = ""
            self.enemy["hp"] = max(0, self.enemy["hp"] - dmg)
            self.last_damage = dmg
            self.log = f"Turn {self.turn}: [{tech_name}] deals {dmg}{crit_text}."

            if self.enemy["hp"] > 0:
                e_dmg = self.enemy["atk"]
                if tech_name == "Golden Bell Shield":
                    e_dmg = int(e_dmg * 0.8)
                self.player[1] = max(0, self.player[1] - e_dmg)
                self.log += f"\nTurn {self.turn}: Enemy hits for {e_dmg}."
            if tech_name == "Swift Wind Kick" and random.random() < 0.3:
                extra_dmg = random.randint(base_atk//2, base_atk)
                self.enemy["hp"] = max(0, self.enemy["hp"] - extra_dmg)
                self.log += f"\n**Double strike!** +{extra_dmg} damage!"
            self.turn += 1
            await self.update_embed(interaction)

    @discord.ui.button(label="Run Away", style=discord.ButtonStyle.secondary, emoji="🏃")
    async def run_away(self, interaction, button):
        async with self.lock:
            if self.ended: return
            self.ended = True
            for child in self.children:
                child.disabled = True
            db = self.bot.db
            tael_loss = max(1, int(self.player[8] * 0.10))
            new_taels = max(0, self.player[8] - tael_loss)
            await db.execute("UPDATE users SET taels = ? WHERE user_id = ?", (new_taels, self.player[0]))
            await db.commit()
            if not hasattr(self.bot, 'hunt_cooldowns'):
                self.bot.hunt_cooldowns = {}
            self.bot.hunt_cooldowns[self.player[0]] = datetime.datetime.now() + datetime.timedelta(minutes=2)

            embed = discord.Embed(title="🏃‍♂️ You fled the battle", color=0xFFA500,
                                  description=f"You escaped but lost **{tael_loss} Taels**.\nYou cannot hunt for 2 minutes.")
            await self.safe_edit(interaction, embed, None)
            self.stop()
            
# ==========================================
# MAIN COG
# ==========================================
class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.hunt_cooldowns = {}
        self.bot.loop.create_task(self.init_db_columns())

    async def init_db_columns(self):
        await self.bot.wait_until_ready()
        db = self.bot.db
        columns = {
            "hunt_total": "INTEGER DEFAULT 0",
            "hunt_damage_max": "INTEGER DEFAULT 0",
            "hunt_fastest_turns": "INTEGER DEFAULT 999",
            "hunt_elite_kills": "INTEGER DEFAULT 0",
            "hunt_taels_earned": "INTEGER DEFAULT 0",
            "daily_hunts": "INTEGER DEFAULT 0",
            "last_hunt_date": "TEXT"
        }
        async with db.execute("PRAGMA table_info(users)") as cur:
            existing = [row[1] for row in await cur.fetchall()]
        for col, dtype in columns.items():
            if col not in existing:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {dtype}")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        await db.commit()

    @commands.hybrid_command(name="hunt", aliases=["h"])
    async def hunt(self, ctx):
        user_id = ctx.author.id
        db = self.bot.db

        if hasattr(self.bot, 'hunt_cooldowns') and user_id in self.bot.hunt_cooldowns:
            if datetime.datetime.now() < self.bot.hunt_cooldowns[user_id]:
                remaining = (self.bot.hunt_cooldowns[user_id] - datetime.datetime.now()).seconds
                embed = discord.Embed(
                    title="⏳ Escape Recovery",
                    description=f"You are still recovering from your last escape.\nPlease wait **{remaining} seconds** before hunting again.",
                    color=0xFFA500
                )
                return await ctx.send(embed=embed, ephemeral=True)
            else:
                del self.bot.hunt_cooldowns[user_id]

        async with db.execute("""
            SELECT user_id, hp, vitality, ki, mastery, active_tech, rank, combat_mastery, taels, meridian_damage
            FROM users WHERE user_id=?
        """, (user_id,)) as cursor:
            user = await cursor.fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)
        damaged, _ = has_meridian_damage(user[9])
        if damaged:
            return await ctx.send("❌ Your meridians are damaged. You cannot hunt.", ephemeral=True)

        rank = user[6]
        if "Peak Master" in rank:
            base_tier = "Peak Master"
        elif "First-Rate" in rank:
            base_tier = "First-Rate Warrior"
        elif "Second-Rate" in rank:
            base_tier = "Second-Rate Warrior"
        elif "Third-Rate" in rank:
            base_tier = "Third-Rate Warrior"
        else:
            return await ctx.send("❌ Mortals cannot hunt spirit beasts.", ephemeral=True)

        rand = random.randint(1, 100)
        cumulative = 0
        chosen_rarity = None
        for rname, rdata in RARITIES.items():
            cumulative += rdata["chance"]
            if rand <= cumulative:
                chosen_rarity = rname
                break
        rarity_data = RARITIES[chosen_rarity].copy()
        rarity_data["name"] = chosen_rarity
        name = ENEMY_NAMES[base_tier][chosen_rarity]
        base_enemy = ENEMIES[base_tier]
        enemy_hp = int(base_enemy["hp"] * rarity_data["hp_mult"])
        enemy_atk = int(base_enemy["atk"] * rarity_data["atk_mult"])
        enemy = {"name": name, "hp": enemy_hp, "atk": enemy_atk}
        color = base_enemy["color"]

        today = datetime.datetime.now().date().isoformat()
        async with db.execute("SELECT daily_hunts, last_hunt_date FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        daily_hunts = row[0] if row and row[0] else 0
        last_date = row[1] if row and row[1] else ""
        if last_date != today:
            daily_hunts = 0
            await db.execute("UPDATE users SET daily_hunts=0, last_hunt_date=? WHERE user_id=?", (today, user_id))
        daily_hunts += 1
        await db.execute("UPDATE users SET daily_hunts=? WHERE user_id=?", (daily_hunts, user_id))
        await db.commit()

        view = CombatView(self.bot, user_id, user, enemy, rarity_data, color)
        view.daily_hunts_today = daily_hunts - 1
        embed = discord.Embed(title=f"⚔️ Encounter: {name}", description=f"Rarity: **{chosen_rarity}**", color=color)
        embed.add_field(name=f"👤 You (HP: {user[1]})", value=f"`{view.generate_bar(user[1], user[1])}`", inline=False)
        embed.add_field(name=f"👹 {name} (HP: {enemy_hp})", value=f"`{view.generate_bar(enemy_hp, enemy_hp)}`", inline=False)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="huntleaderboard", aliases=["hlb"])
    async def hunt_leaderboard(self, ctx):
        view = LeaderboardView(self.bot, ctx.author.id)
        embed = await view.get_leaderboard_embed("total_hunts")
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Combat(bot))