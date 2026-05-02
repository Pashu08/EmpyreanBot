import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import datetime

# --- COMBAT UI ENGINE ---
class CombatView(discord.ui.View):
    def __init__(self, bot, player_data, enemy_data, db_func):
        super().__init__(timeout=180) # Longer timeout for stable battles
        self.bot = bot
        self.get_db = db_func
        # Data: [id, hp, vit, ki, mastery, tech, rank, c_mastery, taels]
        self.player = list(player_data) 
        self.enemy = enemy_data 
        self.log = "The battle begins! Prepare your soul."
        self.turn = 1

    def get_player_stats(self):
        _, hp, vit, ki, mastery, tech, rank, c_mastery, taels = self.player
        
        # Base ATK scaling
        atk_map = {"The Bound (Mortal)": 8, "Third-Rate Warrior": 20, "Second-Rate Warrior": 45}
        base_atk = atk_map.get(rank, 10)
        
        dodge = 0.18 if tech == "Flowing Cloud Steps" else 0.05
        def_mod = 0.75 if tech == "Golden Bell Shield" else 1.0
        
        return base_atk, dodge, def_mod

    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"⚔️ Battlefield: vs {self.enemy['name']}", color=0x700000)
        
        # Visual Health Bars (Fixed with int() to remove decimals)
        p_hp_bar = "🟥" * int(self.player[1]/20) + "⬛" * (5 - int(self.player[1]/20))
        e_hp_bar = "🟧" * int(self.enemy['hp']/20) + "⬛" * (5 - int(self.enemy['hp']/20))
        
        embed.add_field(name=f"👤 You (HP: {int(self.player[1])})", value=p_hp_bar, inline=True)
        embed.add_field(name=f"👹 Enemy (HP: {int(self.enemy['hp'])})", value=e_hp_bar, inline=True)
        
        # Clean Combat Log
        embed.add_field(name="📜 Battle Record", value=f"```ml\n{self.log}\n```", inline=False)
        embed.set_footer(text=f"Turn: {self.turn} | Ki: {self.player[3]} | Mastery Bonus: {self.player[4]}%")

        # CRASH PREVENTION LOGIC
        try:
            if self.player[1] <= 0 or self.enemy['hp'] <= 0:
                self.stop()
                await self.handle_end(interaction)
            else:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.edit_original_response(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            # Safe recovery if interaction expires
            await interaction.channel.send(content=f"{interaction.user.mention}, the battle continues!", embed=embed, view=self)

    async def handle_end(self, interaction):
        conn = self.get_db()
        c = conn.cursor()
        
        if self.player[1] <= 0:
            tael_loss = int(self.player[8] * 0.10)
            new_taels = self.player[8] - tael_loss
            debuff_time = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            
            c.execute("UPDATE users SET hp=20, vitality=20, taels=?, meridian_damage=? WHERE user_id=?", 
                      (new_taels, debuff_time, self.player[0]))
            
            result_embed = discord.Embed(title="💀 DEFEATED", color=0x000000)
            result_embed.description = f"You fell in battle. Your meridians are damaged and you lost **{tael_loss} Taels**."
        else:
            reward = random.randint(30, 70)
            c_exp = 3.5
            c.execute("UPDATE users SET hp=?, vitality=?, taels=taels+?, combat_mastery=combat_mastery+? WHERE user_id=?", 
                      (int(self.player[1]), int(self.player[2]), reward, c_exp, self.player[0]))
            
            result_embed = discord.Embed(title="🏆 VICTORIOUS", color=0x00FF00)
            result_embed.description = f"You vanquished the beast!\nHarvested: **{reward} Taels**\nGained: **{c_exp} Combat Mastery**"

        conn.commit()
        conn.close()
        # Using followup ensures we avoid the "Unknown Webhook" 404
        await interaction.followup.send(embed=result_embed)

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def strike(self, interaction: discord.Interaction, button: discord.ui.Button):
        atk, dodge, def_mod = self.get_player_stats()
        p_dmg = random.randint(atk-2, atk+5)
        self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
        self.log = f"Turn {self.turn}: You strike for {p_dmg} damage."
        
        if self.enemy['hp'] > 0:
            if random.random() < dodge:
                self.log += f"\nTurn {self.turn}: You dodged the counter-attack!"
            else:
                e_dmg = int(random.randint(self.enemy['atk']-2, self.enemy['atk']+2) * def_mod)
                self.player[1] = max(0, self.player[1] - e_dmg)
                self.log += f"\nTurn {self.turn}: Enemy hits you for {e_dmg} damage."
        
        self.turn += 1
        await self.update_embed(interaction)

    @discord.ui.button(label="Technique", style=discord.ButtonStyle.primary, emoji="🌀")
    async def technique(self, interaction: discord.Interaction, button: discord.ui.Button):
        atk, dodge, def_mod = self.get_player_stats()
        if self.player[3] < 10:
            return await interaction.response.send_message("❌ Not enough Ki!", ephemeral=True)
            
        self.player[3] -= 10
        multiplier = 1 + (self.player[4] / 100)
        p_dmg = int(random.randint(atk+8, atk+15) * multiplier)
        
        self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
        self.log = f"Turn {self.turn}: You unleash your technique for {p_dmg} damage!"
        
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

    @commands.hybrid_command(name="hunt", description="Venture into the wild to find spirit beasts.")
    async def hunt(self, ctx):
        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send("🧘 You cannot fight while in deep meditation!", ephemeral=True)

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
            return await ctx.send("❌ Mortals cannot survive the hunting grounds. Reach **Third-Rate Warrior** first.")

        enemies = [
            {'name': 'Spirit Wolf', 'hp': 80, 'atk': 12, 'spd': 5},
            {'name': 'Rogue Cultivator', 'hp': 100, 'atk': 18, 'spd': 10},
            {'name': 'Shadow Panther', 'hp': 120, 'atk': 22, 'spd': 12}
        ]
        target = random.choice(enemies)
        
        view = CombatView(self.bot, user[:9], target, self.get_db)
        embed = discord.Embed(title=f"👺 Encounter: {target['name']}", 
                              description="A threat emerges! Steel your heart.", 
                              color=0x700000)
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Combat(bot))
