import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import datetime

# --- COMBAT UI ENGINE ---
class CombatView(discord.ui.View):
    def __init__(self, bot, player_data, enemy_data, db_func):
        super().__init__(timeout=120)
        self.bot = bot
        self.get_db = db_func
        # Data: [id, hp, vit, ki, mastery, tech, rank, c_mastery, taels]
        self.player = list(player_data) 
        self.enemy = enemy_data 
        self.log = "⚔️ The battle begins!"
        self.turn = 1

    def get_player_stats(self):
        # Stats calculation for damage and avoidance
        _, hp, vit, ki, mastery, tech, rank, c_mastery, taels = self.player
        
        # Base ATK scaling by Rank
        atk_map = {"The Bound (Mortal)": 5, "Third-Rate Warrior": 15, "Second-Rate Warrior": 35}
        base_atk = atk_map.get(rank, 10)
        
        # Technique Modifiers
        dodge = 0.15 if tech == "Flowing Cloud Steps" else 0.05
        def_mod = 0.80 if tech == "Golden Bell Shield" else 1.0
        
        return base_atk, dodge, def_mod

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"⚔️ Battle: vs {self.enemy['name']}", color=0x700000)
        
        # Visual Health Bars (5-segment)
        p_hp_bar = "🔴" * int(self.player[1]/20) + "⚪" * (5 - int(self.player[1]/20))
        e_hp_bar = "🟠" * int(self.enemy['hp']/20) + "⚪" * (5 - int(self.enemy['hp']/20))
        
        embed.add_field(name=f"👤 You (HP: {self.player[1]})", value=p_hp_bar, inline=True)
        embed.add_field(name=f"👹 {self.enemy['name']} (HP: {self.enemy['hp']})", value=e_hp_bar, inline=True)
        
        embed.description = f"**Turn {self.turn}**\n>>> {self.log}"
        
        if self.player[1] <= 0 or self.enemy['hp'] <= 0:
            self.stop()
            await self.handle_end(interaction)
        else:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.edit_original_response(embed=embed, view=self)

    async def handle_end(self, interaction):
        conn = self.get_db()
        c = conn.cursor()
        
        if self.player[1] <= 0:
            # Defeat: 10% Tael loss + Damaged Meridians
            tael_loss = int(self.player[8] * 0.10)
            new_taels = self.player[8] - tael_loss
            debuff_time = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            
            c.execute("UPDATE users SET hp=20, vitality=20, taels=?, meridian_damage=? WHERE user_id=?", 
                      (new_taels, debuff_time, self.player[0]))
            
            result_embed = discord.Embed(title="💀 Defeated", color=0x000000)
            result_embed.description = f"You have fallen in battle. Your meridians are damaged, and you lost **{tael_loss} Taels**."
        else:
            # Victory: Taels + Combat Mastery XP
            reward = random.randint(20, 50)
            c_exp = 2.5
            c.execute("UPDATE users SET hp=?, vitality=?, taels=taels+?, combat_mastery=combat_mastery+? WHERE user_id=?", 
                      (self.player[1], self.player[2], reward, c_exp, self.player[0]))
            
            result_embed = discord.Embed(title="🏆 Victory!", color=0x00FF00)
            result_embed.description = f"You stood victorious! Harvested **{reward} Taels** and gained **{c_exp} Combat Mastery**."

        conn.commit()
        conn.close()
        await interaction.followup.send(embed=result_embed)

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def strike(self, interaction: discord.Interaction, button: discord.ui.Button):
        atk, dodge, def_mod = self.get_player_stats()
        
        p_dmg = random.randint(atk-2, atk+5)
        self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
        self.log = f"You strike for **{p_dmg}** damage."
        
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
            return await interaction.response.send_message("❌ Your Ki is depleted!", ephemeral=True)
            
        self.player[3] -= 10
        # Mastery Multiplier (100% Mastery = 2x Damage)
        multiplier = 1 + (mastery / 100)
        p_dmg = int(random.randint(atk+5, atk+10) * multiplier)
        
        self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
        self.log = f"You unleash your technique! Dealing **{p_dmg}** damage."
        
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
        # Lockout check for active meditation
        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send("❌ You cannot hunt while in deep meditation!", ephemeral=True)

        conn = self.get_db()
        c = conn.cursor()
        
        user = c.execute("""SELECT user_id, hp, vitality, ki, mastery, active_tech, rank, 
                            combat_mastery, taels, meridian_damage FROM users WHERE user_id=?""", 
                            (ctx.author.id,)).fetchone()
        
        if not user: 
            return await ctx.send("❌ You must `!start` your journey first.")
        
        # Check for Damaged Meridians debuff
        if user[9]:
            try:
                end_time = datetime.datetime.fromisoformat(user[9])
                if datetime.datetime.now() < end_time:
                    diff = end_time - datetime.datetime.now()
                    return await ctx.send(f"❌ Your meridians are damaged! You cannot fight for another **{int(diff.total_seconds() // 60)}m**.")
            except: pass

        if "Mortal" in user[6]:
            return await ctx.send("❌ The hunting grounds are too dangerous for a Mortal. Reach **Third-Rate Warrior** first.")

        # Enemy selection logic
        enemies = [
            {'name': 'Spirit Wolf', 'hp': 80, 'atk': 10, 'spd': 5},
            {'name': 'Shadow Panther', 'hp': 120, 'atk': 18, 'spd': 12},
            {'name': 'Rogue Cultivator', 'hp': 100, 'atk': 15, 'spd': 10}
        ]
        target = random.choice(enemies)
        
        view = CombatView(self.bot, user[:9], target, self.get_db)
        embed = discord.Embed(title=f"👹 Encounter: {target['name']}", 
                              description="A beast lunges from the tall grass! Draw your weapon.", 
                              color=0x700000)
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Combat(bot))
