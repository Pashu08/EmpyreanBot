import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import datetime

# --- COMBAT UI ---
class CombatView(discord.ui.View):
    def __init__(self, bot, player_data, enemy_data, db_func):
        super().__init__(timeout=120)
        self.bot = bot
        self.get_db = db_func
        self.player = list(player_data) # [id, hp, vit, ki, mastery, tech, rank, c_mastery, taels]
        self.enemy = enemy_data # {'name': str, 'hp': int, 'atk': int, 'spd': int}
        self.log = "⚔️ The battle begins!"
        self.turn = 1

    def get_player_stats(self):
        # Unpacking for easier math
        _, hp, vit, ki, mastery, tech, rank, c_mastery, taels = self.player
        
        # Base ATK based on Rank
        atk_map = {"The Bound (Mortal)": 5, "Third-Rate Warrior": 15, "Second-Rate Warrior": 35}
        base_atk = atk_map.get(rank, 10)
        
        # Stats influenced by Techniques
        dodge = 0.15 if tech == "Flowing Cloud Steps" else 0.05
        def_mod = 0.80 if tech == "Golden Bell Shield" else 1.0
        
        return base_atk, dodge, def_mod

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"⚔️ Battle: vs {self.enemy['name']}", color=0x700000)
        
        # Health Bars
        p_hp_bar = "🔴" * int(self.player[1]/20) + "⚪" * (5 - int(self.player[1]/20))
        e_hp_bar = "🟠" * int(self.enemy['hp']/20) + "⚪" * (5 - int(self.enemy['hp']/20))
        
        embed.add_field(name=f"👤 You (HP: {self.player[1]})", value=p_hp_bar, inline=True)
        embed.add_field(name=f"👹 {self.enemy['name']} (HP: {self.enemy['hp']})", value=e_hp_bar, inline=True)
        
        embed.description = f"**Turn {self.turn}**\n>>> {self.log}"
        
        if self.player[1] <= 0 or self.enemy['hp'] <= 0:
            self.stop()
            await self.handle_end(interaction)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def handle_end(self, interaction):
        conn = self.get_db()
        c = conn.cursor()
        
        if self.player[1] <= 0:
            # DEFEAT LOGIC
            tael_loss = int(self.player[8] * 0.10)
            new_taels = self.player[8] - tael_loss
            debuff_time = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            
            c.execute("UPDATE users SET hp=20, vitality=20, taels=?, meridian_damage=? WHERE user_id=?", 
                      (new_taels, debuff_time, self.player[0]))
            
            result_embed = discord.Embed(title="💀 Defeated", color=discord.Color.black())
            result_embed.description = f"You were overwhelmed. Your meridians are damaged, and you lost **{tael_loss} Taels**."
        else:
            # VICTORY LOGIC
            reward = random.randint(20, 50)
            c_exp = 2.5
            c.execute("UPDATE users SET hp=?, vitality=?, taels=taels+?, combat_mastery=combat_mastery+? WHERE user_id=?", 
                      (self.player[1], self.player[2], reward, c_exp, self.player[0]))
            
            result_embed = discord.Embed(title="🏆 Victory!", color=discord.Color.green())
            result_embed.description = f"The beast falls! You harvested **{reward} Taels** and gained **{c_exp} Combat Mastery**."

        conn.commit()
        conn.close()
        await interaction.followup.send(embed=result_embed)

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def strike(self, interaction: discord.Interaction, button: discord.ui.Button):
        atk, dodge, def_mod = self.get_player_stats()
        
        # Player Turn
        p_dmg = random.randint(atk-2, atk+5)
        self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
        self.log = f"You strike for **{p_dmg}** damage."
        
        # Enemy Turn (if alive)
        if self.enemy['hp'] > 0:
            if random.random() < dodge:
                self.log += f"\n💨 You dodged the enemy's counter!"
            else:
                e_dmg = int(random.randint(self.enemy['atk']-2, self.enemy['atk']+2) * def_mod)
                self.player[1] = max(0, self.player[1] - e_dmg)
                self.log += f"\n👹 The enemy hits you for **{e_dmg}** damage."
        
        self.turn += 1
        await self.update_embed(interaction)

    @discord.ui.button(label="Technique", style=discord.ButtonStyle.primary, emoji="🌀")
    async def technique(self, interaction: discord.Interaction, button: discord.ui.Button):
        atk, dodge, def_mod = self.get_player_stats()
        mastery = self.player[4]
        ki = self.player[3]
        
        if ki < 10:
            return await interaction.response.send_message("Not enough Ki!", ephemeral=True)
            
        self.player[3] -= 10 # Ki Cost
        
        # Mastery Scaling: 100% Mastery = 2x Damage
        multiplier = 1 + (mastery / 100)
        p_dmg = int(random.randint(atk+5, atk+10) * multiplier)
        
        self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
        self.log = f"You unleash your technique! Dealing **{p_dmg}** damage."
        
        # Enemy counter logic simplified for brevity
        if self.enemy['hp'] > 0:
            e_dmg = int(self.enemy['atk'] * def_mod)
            self.player[1] = max(0, self.player[1] - e_dmg)
            self.log += f"\n👹 Enemy counters for **{e_dmg}**."

        self.turn += 1
        await self.update_embed(interaction)

class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="hunt", description="Hunt spirit beasts for rewards.")
    async def hunt(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        
        # Check for Debuff
        user = c.execute("SELECT user_id, hp, vitality, ki, mastery, active_tech, rank, combat_mastery, taels, meridian_damage FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("Use `!start`.")
        
        # Debuff Check
        if user[9]:
            end_time = datetime.datetime.fromisoformat(user[9])
            if datetime.datetime.now() < end_time:
                return await ctx.send(f"❌ Your meridians are damaged! You must recover. (Ends in {int((end_time - datetime.datetime.now()).total_seconds()/60)}m)")

        if "Mortal" in user[6]:
            return await ctx.send("❌ Mortals cannot survive the hunting grounds. Reach **Third-Rate Warrior** first.")

        # Generate Enemy based on Rank
        enemies = [
            {'name': 'Spirit Wolf', 'hp': 80, 'atk': 10, 'spd': 5},
            {'name': 'Shadow Panther', 'hp': 120, 'atk': 18, 'spd': 12}
        ]
        target = random.choice(enemies)
        
        view = CombatView(self.bot, user[:9], target, self.get_db)
        embed = discord.Embed(title=f"👹 A {target['name']} appears!", description="The beast lunges from the shadows. Prepare yourself!", color=0x700000)
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Combat(bot))
