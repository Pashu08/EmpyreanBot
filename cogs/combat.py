import discord
from discord.ext import commands
import random
import asyncio
import datetime
from utils.helpers import format_embed_color, has_meridian_damage
from utils.db import get_bot_setting, is_user_banned, get_user_stat, update_user_stat, add_item, remove_item
from utils.constants import ENEMIES, SHOP_ITEMS, TECHNIQUES
import config

print("[DEBUG] combat.py: Loading Combat cog...")

# ==========================================
# ENEMY RARIY SYSTEM (5 tiers)
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
# LEADERBOARD VIEW
# ==========================================
class LeaderboardView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.mode = "total_hunts"

    async def get_leaderboard_embed(self, mode):
        db = self.bot.db
        collection = db.users
        
        if mode == "total_hunts":
            sort_field = "hunt_total"
            sort_order = -1
            title = "🏆 Most Hunts (Lifetime)"
            value_field = "hunt_total"
        elif mode == "highest_damage":
            sort_field = "hunt_damage_max"
            sort_order = -1
            title = "💥 Highest Single Hit Damage"
            value_field = "hunt_damage_max"
        elif mode == "fastest_kill":
            sort_field = "hunt_fastest_turns"
            sort_order = 1
            title = "⚡ Fastest Kill (least turns)"
            value_field = "hunt_fastest_turns"
        elif mode == "elite_kills":
            sort_field = "hunt_elite_kills"
            sort_order = -1
            title = "👑 Elite & Boss Kills"
            value_field = "hunt_elite_kills"
        else:
            sort_field = "hunt_taels_earned"
            sort_order = -1
            title = "💰 Total Taels from Hunting"
            value_field = "hunt_taels_earned"

        cursor = collection.find({value_field: {"$gt": 0}}).sort(sort_field, sort_order).limit(10)
        rows = await cursor.to_list(length=10)

        embed = discord.Embed(title=title, color=format_embed_color("main"))
        if not rows:
            embed.description = "No data yet. Go hunt!"
        else:
            desc = ""
            for i, doc in enumerate(rows, 1):
                uid = doc.get("user_id")
                val = doc.get(value_field, 0)
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
    def __init__(self, bot, author_id, player_data, enemy_data, rarity, color, pre_hunt_stats):
        super().__init__(timeout=180)
        self.bot = bot
        self.author_id = author_id
        self.rarity = rarity
        self.color = color
        self.lock = asyncio.Lock()
        self.ended = False
        self.pre_hunt_stats = pre_hunt_stats

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
        user_id = self.player[0]

        # RESTORE original HP and Vitality (no permanent loss)
        original = self.pre_hunt_stats[user_id]
        await update_user_stat(db, user_id, "hp", original["hp"])
        await update_user_stat(db, user_id, "vitality", original["vitality"])

        if self.player[1] <= 0:  # Defeat
            tael_loss = max(1, int(self.player[8] * 0.10))
            new_taels = max(0, self.player[8] - tael_loss)
            await update_user_stat(db, user_id, "taels", new_taels)
            debuff = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            await update_user_stat(db, user_id, "meridian_damage", debuff)
            embed = discord.Embed(
                title="💀 DEFEATED",
                description=f"You fell to **{self.enemy['name']}**.\n❌ Lost **{tael_loss}** Taels.\nMeridians damaged for 10 minutes.",
                color=format_embed_color("lose")
            )
        else:  # Victory
            base_reward = random.randint(50, 150)
            mult = self.rarity["reward_mult"]
            if self.daily_hunts_today < 3:
                mult *= 2
            cm_bonus = 1 + (self.player[7] * 0.005)
            final_reward = int(base_reward * mult * cm_bonus)

            new_taels = self.player[8] + final_reward
            await update_user_stat(db, user_id, "taels", new_taels)

            new_cm = self.player[7] + 2.0
            await update_user_stat(db, user_id, "combat_mastery", new_cm)

            # Update hunt stats using MongoDB
            await db.users.update_one(
                {"user_id": user_id},
                {"$inc": {
                    "hunt_total": 1,
                    "hunt_taels_earned": final_reward,
                    "hunt_damage_max": self.last_damage,
                    "hunt_elite_kills": 1 if self.rarity["name"] in ("Elite","Master","Grandmaster","Mythical") else 0
                },
                "$min": {"hunt_fastest_turns": self.turn}},
                upsert=True
            )

            drop_item = None
            if random.random() < self.rarity["drop_chance"]:
                possible_items = list(SHOP_ITEMS.keys())
                drop_item = random.choice(possible_items)
                await add_item(db, user_id, drop_item, 1)

            desc = f"The **{self.enemy['name']}** falls!\n💰 Earned: **{final_reward} Taels**\n⚔️ Gained: **2.0 Combat Mastery**"
            if drop_item:
                desc += f"\n🎁 Dropped: **{drop_item}**"
            embed = discord.Embed(title="🏆 VICTORY", color=format_embed_color("win"), description=desc)

        await self.safe_edit(interaction, embed, None)
        if hasattr(self.bot, 'active_combats') and user_id in self.bot.active_combats:
            del self.bot.active_combats[user_id]
        self.stop()

    # ---------- Strike Button ----------
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

    # ---------- Technique Button ----------
    @discord.ui.button(label="Technique", style=discord.ButtonStyle.primary, emoji="🌀")
    async def technique(self, interaction, button):
        async with self.lock:
            if self.ended: return
            if self.player[3] < 15:
                await interaction.response.send_message(config.MSG_NO_KI.format(required=15), ephemeral=True)
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

    # ---------- Run Away Button ----------
    @discord.ui.button(label="Run Away", style=discord.ButtonStyle.secondary, emoji="🏃")
    async def run_away(self, interaction, button):
        async with self.lock:
            if self.ended: return
            self.ended = True
            for child in self.children:
                child.disabled = True
            db = self.bot.db
            user_id = self.player[0]
            original = self.pre_hunt_stats[user_id]
            await update_user_stat(db, user_id, "hp", original["hp"])
            await update_user_stat(db, user_id, "vitality", original["vitality"])
            tael_loss = max(1, int(self.player[8] * 0.10))
            new_taels = max(0, self.player[8] - tael_loss)
            await update_user_stat(db, user_id, "taels", new_taels)
            if not hasattr(self.bot, 'hunt_cooldowns'):
                self.bot.hunt_cooldowns = {}
            self.bot.hunt_cooldowns[user_id] = datetime.datetime.now() + datetime.timedelta(minutes=2)
            embed = discord.Embed(
                title="🏃‍♂️ You fled the battle",
                description=f"You escaped but lost **{tael_loss} Taels**.\nYou cannot hunt for 2 minutes.",
                color=format_embed_color("lose")
            )
            await self.safe_edit(interaction, embed, None)
            self.stop()

# ==========================================
# MAIN COG
# ==========================================
class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.hunt_cooldowns = {}
        print("[DEBUG] Combat cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_combat", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Combat"), ephemeral=True)
        return enabled

    @commands.hybrid_command(name="hunt", aliases=["h"])
    async def hunt(self, ctx):
        print(f"[DEBUG] combat.hunt: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        # Check run away cooldown
        if hasattr(self.bot, 'hunt_cooldowns') and user_id in self.bot.hunt_cooldowns:
            if datetime.datetime.now() < self.bot.hunt_cooldowns[user_id]:
                remaining = int((self.bot.hunt_cooldowns[user_id] - datetime.datetime.now()).total_seconds())
                embed = discord.Embed(
                    title="⏳ Escape Recovery",
                    description=f"You are still recovering from your last escape.\nPlease wait **{remaining} seconds** before hunting again.",
                    color=format_embed_color("lose")
                )
                return await ctx.send(embed=embed, ephemeral=True)
            else:
                del self.bot.hunt_cooldowns[user_id]

        if not hasattr(self.bot, 'active_combats'):
            self.bot.active_combats = {}
        if user_id in self.bot.active_combats:
            return await ctx.send("❌ You are already in combat! Finish your current fight first.", ephemeral=True)

        # Fetch player data using MongoDB
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        # Check meridian damage
        damaged, _ = has_meridian_damage(user.get("meridian_damage"))
        if damaged:
            return await ctx.send("❌ Your meridians are damaged. You cannot hunt.", ephemeral=True)

        rank = user.get("rank", "The Bound (Mortal)")
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

        # Choose rarity
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

        # Daily hunt tracking
        today = datetime.datetime.now().date().isoformat()
        daily_hunts = user.get("daily_hunts", 0)
        last_date = user.get("last_hunt_date", "")
        if last_date != today:
            daily_hunts = 0
        daily_hunts += 1
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"daily_hunts": daily_hunts, "last_hunt_date": today}}
        )

        # Save pre-hunt HP and Vitality
        pre_hunt_stats = {
            user_id: {
                "hp": user.get("hp", 100),
                "vitality": user.get("vitality", 100),
            }
        }

        self.bot.active_combats[user_id] = True

        # Convert user data to tuple format expected by CombatView
        player_tuple = (
            user_id,
            user.get("hp", 100),
            user.get("vitality", 100),
            user.get("ki", 0),
            user.get("mastery", 0.0),
            user.get("active_tech", "None"),
            rank,
            user.get("combat_mastery", 0),
            user.get("taels", 0)
        )

        view = CombatView(self.bot, user_id, player_tuple, enemy, rarity_data, color, pre_hunt_stats)
        view.daily_hunts_today = daily_hunts - 1
        embed = discord.Embed(title=f"⚔️ Encounter: {name}", description=f"Rarity: **{chosen_rarity}**", color=color)
        embed.add_field(name=f"👤 You (HP: {user.get('hp', 100)})", value=f"`{view.generate_bar(user.get('hp', 100), user.get('hp', 100))}`", inline=False)
        embed.add_field(name=f"👹 {name} (HP: {enemy_hp})", value=f"`{view.generate_bar(enemy_hp, enemy_hp)}`", inline=False)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="huntleaderboard", aliases=["hlb"])
    async def hunt_leaderboard(self, ctx):
        print(f"[DEBUG] combat.hunt_leaderboard: Called by {ctx.author.id}")
        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        view = LeaderboardView(self.bot, ctx.author.id)
        embed = await view.get_leaderboard_embed("total_hunts")
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Combat(bot))
    print("[DEBUG] combat.py: Setup complete")