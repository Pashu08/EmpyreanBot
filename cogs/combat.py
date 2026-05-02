import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import datetime

# --- COMBAT UI ENGINE (STABLE + PREMIUM UI) ---
class CombatView(discord.ui.View):
    def __init__(self, bot, author_id, player_data, enemy_data, db_func, color):
        super().__init__(timeout=180)
        self.bot = bot
        self.author_id = author_id
        self.get_db = db_func
        self.lock = asyncio.Lock()
        self.ended = False
        
        # Data: [id, hp, vit, ki, mastery, tech, rank, c_mastery, taels]
        self.player = list(player_data) 
        self.enemy = enemy_data.copy()
        
        self.p_max_hp = max(1, int(self.player[1] or 100))
        self.e_max_hp = max(1, int(self.enemy['hp'] or 100))
        self.color = color
        self.log = f"The {enemy_data['name']} blocks your path!"
        self.turn = 1

        # --- DYNAMIC BUTTON LOGIC ---
        tech_name = self.player[5]
        if tech_name and tech_name != "None":
            self.technique_btn.label = tech_name 
        else:
            self.technique_btn.disabled = True
            self.technique_btn.label = "No Technique"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """TheDesigner's Security: Only allow the hunt starter to click."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your fight.", ephemeral=True)
            return False
        if self.ended:
            return False
        return True

    def get_bar(self, current, max_val, color_emoji):
        percentage = max(0, min(current / max_val, 1))
        filled = int(percentage * 10)
        return color_emoji * filled + "⬛" * (10 - filled)

    async def update_embed(self, interaction: discord.Interaction):
        if self.player[1] <= 0 or self.enemy['hp'] <= 0:
            self.ended = True
            for child in self.children: child.disabled = True
            await self.handle_end(interaction)
            return

        embed = discord.Embed(title=f"⚔️ Martial Encounter: {self.enemy['name']}", color=self.color)
        p_bar = self.get_bar(self.player[1], self.p_max_hp, "🟥")
        e_bar = self.get_bar(self.enemy['hp'], self.e_max_hp, "🟧")
        
        embed.add_field(name=f"👤 You (HP: {int(self.player[1])})", value=f"`{p_bar}`", inline=False)
        embed.add_field(name=f"👹 {self.enemy['name']} (HP: {int(self.enemy['hp'])})", value=f"`{e_bar}`", inline=False)
        embed.add_field(name="📜 Combat Log", value=f"```ml\n{self.log}\n```", inline=False)
        embed.set_footer(text=f"Turn: {self.turn} | Ki: {self.player[3]} | Mastery: {self.player[4]}%")

        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.edit_original_response(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            pass

    async def handle_end(self, interaction):
        try:
            with self.get_db() as conn:
                c = conn.cursor()
                if self.player[1] <= 0:
                    tael_loss = int((self.player[8] or 0) * 0.10)
                    debuff = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
                    c.execute("UPDATE users SET hp=20, vitality=20, taels=max(taels-?, 0), meridian_damage=? WHERE user_id=?", 
                              (tael_loss, debuff, self.player[0]))
                    
                    final_embed = discord.Embed(title="💀 DEFEATED", color=0x000000)
                    final_embed.description = f"**{self.enemy['name']}** has overwhelmed you.\n\n❌ Lost **{tael_loss}** Taels.\n⚠️ Meridians Damaged (10m)."
                else:
                    reward = random.randint(50, 100)
                    c.execute("UPDATE users SET hp=?, vitality=?, taels=taels+?, combat_mastery=combat_mastery+5.0 WHERE user_id=?", 
                              (int(self.player[1]), int(self.player[2]), reward, self.player[0]))
                    
                    final_embed = discord.Embed(title="🏆 VICTORY", color=0x00FF00)
                    final_embed.description = f"The **{self.enemy['name']}** falls!\n\n💰 Harvested: **{reward} Taels**\n⚔️ Gained: **5.0 Combat Mastery**"
                conn.commit()
        except sqlite3.Error as e:
            print(f"DB Error: {e}")

        await interaction.edit_original_response(embed=final_embed, view=None)
        self.stop()

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def strike(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            if self.ended: return
            
            atk_map = {"The Bound (Mortal)": 8, "Third-Rate Warrior": 25, "Second-Rate Warrior": 60, "First-Rate Warrior": 150}
            base_atk = atk_map.get(self.player[6], 10)
            
            p_dmg = random.randint(base_atk, base_atk + 20)
            self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
            self.log = f"Turn {self.turn}: You strike for {p_dmg}."
            
            if self.enemy['hp'] > 0:
                e_dmg = random.randint(max(1, self.enemy['atk']-5), self.enemy['atk']+5)
                self.player[1] = max(0, self.player[1] - e_dmg)
                self.log += f"\nTurn {self.turn}: {self.enemy['name']} hits for {e_dmg}."
                
            self.turn += 1
            await self.update_embed(interaction)

    @discord.ui.button(label="Technique", style=discord.ButtonStyle.primary, emoji="🌀")
    async def technique_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            if self.ended: return
            if self.player[3] < 15:
                return await interaction.response.send_message("❌ Ki exhausted!", ephemeral=True)
                
            self.player[3] -= 15
            atk_map = {"The Bound (Mortal)": 15, "Third-Rate Warrior": 50, "Second-Rate Warrior": 120, "First-Rate Warrior": 300}
            base_atk = atk_map.get(self.player[6], 20)
            
            p_dmg = int(random.randint(base_atk, base_atk + 50) * (1 + (self.player[4] or 0) / 100))
            self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
            self.log = f"Turn {self.turn}: [{self.player[5]}] unleashed for {p_dmg}!"
            
            if self.enemy['hp'] > 0:
                e_dmg = self.enemy['atk']
                self.player[1] = max(0, self.player[1] - e_dmg)
                self.log += f"\nTurn {self.turn}: {self.enemy['name']} counters for {e_dmg}."

            self.turn += 1
            await self.update_embed(interaction)

class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        # Uses the config path from TheDesigner's main.py if available
        path = getattr(self.bot.config, 'DB_PATH', 'murim.db') if hasattr(self.bot, 'config') else 'murim.db'
        return sqlite3.connect(path, timeout=30)

    @commands.hybrid_command(name="hunt")
    async def hunt(self, ctx):
        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send("🧘 Meditation requires stillness.", ephemeral=True)

        with self.get_db() as conn:
            c = conn.cursor()
            user = c.execute("""SELECT user_id, 
                                       COALESCE(hp, 100), 
                                       COALESCE(vitality, 100), 
                                       COALESCE(ki, 0), 
                                       COALESCE(mastery, 0), 
                                       COALESCE(active_tech, 'None'), 
                                       COALESCE(rank, 'The Bound (Mortal)'), 
                                       COALESCE(combat_mastery, 0), 
                                       COALESCE(taels, 0), 
                                       meridian_damage 
                                FROM users WHERE user_id=?""", (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("❌ Use `!start`.")
        if user[9]:
            try:
                end = datetime.datetime.fromisoformat(user[9])
                if datetime.datetime.now() < end:
                    return await ctx.send("❌ Your meridians are damaged.", ephemeral=True)
            except: pass

        rank = user[6]
        if "First-Rate" in rank: target, color = {'name': 'Corrupted Elder', 'hp': 600, 'atk': 95}, 0x992d22 
        elif "Second-Rate" in rank: target, color = {'name': 'Shadow Tiger', 'hp': 250, 'atk': 45}, 0xe67e22 
        elif "Third-Rate" in rank: target, color = {'name': 'Spirit Wolf', 'hp': 100, 'atk': 15}, 0x2ecc71 
        else: return await ctx.send("❌ Mortals cannot hunt spirit beasts.")

        view = CombatView(self.bot, ctx.author.id, user[:9], target, self.get_db, color)
        embed = discord.Embed(title=f"⚔️ Encounter: {target['name']}", description="Steel your heart.", color=color)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Combat(bot))
