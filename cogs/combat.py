import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import datetime

# --- COMBAT UI ENGINE (MASTER SCALE) ---
class CombatView(discord.ui.View):
    def __init__(self, bot, player_data, enemy_data, db_func):
        super().__init__(timeout=180) # Robust timeout for deep duels
        self.bot = bot
        self.get_db = db_func
        # Data structure: [id, hp, vit, ki, mastery, tech, rank, c_mastery, taels]
        self.player = list(player_data) 
        self.enemy = enemy_data 
        
        # We now store the STARTING max HP to calculate percentage bars properly
        self.p_max_hp = self.player[1]
        self.e_max_hp = enemy_data['hp']
        
        self.log = "The battle lines are drawn."
        self.turn = 1

    def get_player_stats(self):
        # Stats based calculation
        _, hp, vit, ki, mastery, tech, rank, c_mastery, taels = self.player
        atk_map = {"The Bound (Mortal)": 8, "Third-Rate Warrior": 25, "Second-Rate Warrior": 50, "First-Rate Warrior": 120}
        base_atk = atk_map.get(rank, 10)
        
        dodge = 0.18 if tech == "Flowing Cloud Steps" else 0.05
        def_mod = 0.75 if tech == "Golden Bell Shield" else 1.0
        return base_atk, dodge, def_mod

    def generate_bar(self, current, total, filled_emoji, empty_emoji="⬛"):
        """Always returns a 10-segment bar, regardless of scale."""
        if total <= 0: return "⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛"
        percentage = max(0, min(current / total, 1))
        filled = int(percentage * 10)
        return f"{filled_emoji * filled}{empty_emoji * (10 - filled)}"

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"⚔️ Duel vs {self.enemy['name']}", color=0x700000)
        
        # --- Percentage-Based Scaling ---
        p_hp_str = self.generate_bar(self.player[1], self.p_max_hp, "🟥")
        e_hp_str = self.generate_bar(self.enemy['hp'], self.e_max_hp, "🟧")
        
        embed.add_field(name=f"👤 Player (HP: {int(self.player[1])})", value=f"`{p_hp_str}`", inline=False)
        embed.add_field(name=f"👹 Foe (HP: {int(self.enemy['hp'])})", value=f"`{e_hp_str}`", inline=False)
        
        # Compact Log
        embed.add_field(name="📜 Combat Log", value=f"```ml\n{self.log}\n```", inline=False)
        embed.set_footer(text=f"Turn: {self.turn} | Ki: {self.player[3]} | Technique Bonus: {self.player[4]}%")

        # --- sticky Check: End-of-Battle Lockout ---
        if self.player[1] <= 0 or self.enemy['hp'] <= 0:
            # gray out every button instantly
            for child in self.children:
                child.disabled = True
            # edit original to show grayed out state
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop() # stop the view listener
            # proceed to results
            return await self.handle_end(interaction)

        # Normal fight update
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.edit_original_response(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            # Recovery if interaction token expires
            await interaction.channel.send(content=f"{interaction.user.mention}, the battle rages on!", embed=embed, view=self)

    async def handle_end(self, interaction):
        conn = self.get_db()
        c = conn.cursor()
        
        if self.player[1] <= 0:
            # Defeat logic
            tael_loss = int(self.player[8] * 0.10)
            debuff_time = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            
            c.execute("UPDATE users SET hp=20, vitality=20, taels=taels-?, meridian_damage=? WHERE user_id=?", 
                      (tael_loss, debuff_time, self.player[0]))
            
            msg = f"💀 **Defeat.** You lost {tael_loss} Taels and your meridians are torn."
        else:
            # Victory logic (rewards scale with player level)
            reward = random.randint(40, 90)
            c_exp = 5.0 # increased combat mastery for high level players
            c.execute("UPDATE users SET hp=?, vitality=?, taels=taels+?, combat_mastery=combat_mastery+? WHERE user_id=?", 
                      (int(self.player[1]), int(self.player[2]), reward, c_exp, self.player[0]))
            
            msg = f"🏆 **Victory!** Gained {reward} Taels and {c_exp} Combat Mastery."

        conn.commit()
        conn.close()
        # Followup message provides clarity that battle has concluded
        await interaction.followup.send(content=f"{interaction.user.mention}\n{msg}")

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def strike(self, interaction: discord.Interaction, button: discord.ui.Button):
        base_atk, dodge, def_mod = self.get_player_stats()
        
        p_dmg = random.randint(base_atk, base_atk + 25)
        self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
        self.log = f"Turn {self.turn}: You hit for {p_dmg}."
        
        if self.enemy['hp'] > 0:
            if random.random() < dodge:
                self.log += f"\nTurn {self.turn}: You evaded the counter!"
            else:
                e_dmg = int(random.randint(self.enemy['atk']-5, self.enemy['atk']+5) * def_mod)
                self.player[1] = max(0, self.player[1] - e_dmg)
                self.log += f"\nTurn {self.turn}: Enemy hits for {e_dmg}."
        
        self.turn += 1
        await self.update_embed(interaction)

    @discord.ui.button(label="Technique", style=discord.ButtonStyle.primary, emoji="🌀")
    async def technique(self, interaction: discord.Interaction, button: discord.ui.Button):
        base_atk, dodge, def_mod = self.get_player_stats()
        
        if self.player[3] < 15: # slightly higher cost for dynamic scaling
            return await interaction.response.send_message("❌ Your Ki is too low!", ephemeral=True)
            
        self.player[3] -= 15
        multiplier = 1 + (self.player[4] / 100)
        p_dmg = int(random.randint(base_atk + 20, base_atk + 60) * multiplier)
        
        self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
        self.log = f"Turn {self.turn}: You unleash your technique for {p_dmg}!"
        
        if self.enemy['hp'] > 0:
            e_dmg = int(self.enemy['atk'] * def_mod)
            self.player[1] = max(0, self.player[1] - e_dmg)
            self.log += f"\nTurn {self.turn}: Enemy counters you for {e_dmg}."

        self.turn += 1
        await self.update_embed(interaction)

class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="hunt", description="Venture out to find spirit beasts to fight.")
    async def hunt(self, ctx):
        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send("🧘 You cannot hunt while in deep meditation!", ephemeral=True)

        conn = self.get_db()
        c = conn.cursor()
        user = c.execute("""SELECT user_id, hp, vitality, ki, mastery, active_tech, rank, 
                            combat_mastery, taels, meridian_damage FROM users WHERE user_id=?""", 
                            (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("❌ Use `!start` first.")
        
        if user[9]:
            try:
                end_time = datetime.datetime.fromisoformat(user[9])
                if datetime.datetime.now() < end_time:
                    diff = end_time - datetime.datetime.now()
                    return await ctx.send(f"❌ Your meridians are damaged! Wait **{int(diff.total_seconds() // 60)}m**.")
            except: pass

        if "Mortal" in user[6]:
            return await ctx.send("❌ The hunting grounds are too dangerous for a Mortal. Reach **Third-Rate Warrior** first.")

        # --- DYNAMIC ENEMY SCALING ---
        rank = user[6]
        if "First-Rate" in rank:
            enemies = [{'name': 'Corrupted Elder', 'hp': 500, 'atk': 90, 'spd': 15}]
        elif "Second-Rate" in rank:
            enemies = [{'name': 'Shadow Tiger', 'hp': 220, 'atk': 40, 'spd': 12}]
        elif "Third-Rate" in rank:
            enemies = [{'name': 'Spirit Wolf', 'hp': 90, 'atk': 15, 'spd': 5}]
        else:
            return await ctx.send("❌ Mortals cannot survive the hunt.")

        target = random.choice(enemies)
        
        view = CombatView(self.bot, user[:9], target, self.get_db)
        embed = discord.Embed(title="👹 A foe draws near!", description="Prepare yourself for martial conflict.", color=0x700000)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Combat(bot))
