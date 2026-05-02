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
        self.color = color

        # Data: [id, hp, vit, ki, mastery, tech, rank, c_mastery, taels]
        self.player = list(player_data)
        self.enemy = enemy_data.copy()

        self.p_max_hp = max(1, int(self.player[1] or 100))
        self.e_max_hp = max(1, int(self.enemy.get("hp", 100)))

        self.log = "The battle lines are drawn."
        self.turn = 1

        # --- DYNAMIC BUTTON RESTORED ---
        tech_name = self.player[5]
        if tech_name and tech_name != "None":
            self.technique.label = tech_name 
        else:
            self.technique.disabled = True
            self.technique.label = "No Technique"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your fight.", ephemeral=True)
            return False
        if self.ended:
            return False
        return True

    def generate_bar(self, current, total, filled_emoji):
        percentage = max(0, min((current or 0) / total, 1))
        filled = int(percentage * 10)
        return f"{filled_emoji * filled}{'⬛' * (10 - filled)}"

    async def safe_edit(self, interaction: discord.Interaction, embed: discord.Embed, view=None):
        """TheDesigner's stability fix for Termux/Mobile."""
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)
        except (discord.NotFound, discord.HTTPException):
            if interaction.message:
                try: await interaction.message.edit(embed=embed, view=view)
                except: pass

    async def update_embed(self, interaction: discord.Interaction):
        if self.player[1] <= 0 or self.enemy['hp'] <= 0:
            self.ended = True
            for child in self.children: child.disabled = True
            # Transition to end state
            await self.handle_end(interaction)
            return

        embed = discord.Embed(title=f"⚔️ Duel vs {self.enemy['name']}", color=self.color)
        embed.add_field(name=f"👤 You (HP: {int(self.player[1])})", value=f"`{self.generate_bar(self.player[1], self.p_max_hp, '🟥')}`", inline=False)
        embed.add_field(name=f"👹 {self.enemy['name']} (HP: {int(self.enemy['hp'])})", value=f"`{self.generate_bar(self.enemy['hp'], self.e_max_hp, '🟧')}`", inline=False)
        embed.add_field(name="📜 Combat Log", value=f"```ml\n{self.log}\n```", inline=False)
        embed.set_footer(text=f"Turn: {self.turn} | Ki: {self.player[3]} | Mastery: {self.player[4]}%")

        await self.safe_edit(interaction, embed, self)

    async def handle_end(self, interaction):
        try:
            with self.get_db() as conn:
                c = conn.cursor()
                if self.player[1] <= 0:
                    tael_loss = max(0, int((self.player[8] or 0) * 0.10))
                    debuff = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
                    c.execute("UPDATE users SET hp=20, vitality=20, taels=max(taels-?, 0), meridian_damage=? WHERE user_id=?", (tael_loss, debuff, self.player[0]))
                    final_embed = discord.Embed(title="💀 DEFEATED", color=0x000000, description=f"You fell to **{self.enemy['name']}**.\n❌ Lost **{tael_loss}** Taels.")
                else:
                    reward = random.randint(50, 100)
                    c.execute("UPDATE users SET hp=?, vitality=?, taels=taels+?, combat_mastery=combat_mastery+5.0 WHERE user_id=?", (int(self.player[1]), int(self.player[2]), reward, self.player[0]))
                    final_embed = discord.Embed(title="🏆 VICTORY", color=0x00FF00, description=f"The **{self.enemy['name']}** falls!\n💰 Harvested: **{reward} Taels**\n⚔️ Gained: **5.0 Combat Mastery**")
                conn.commit()
        except sqlite3.Error as e:
            final_embed = discord.Embed(title="⚠️ System Error", description=f"Battle recorded, but database failed: {e}")

        # The Transformation: Replace the battle screen with results
        await self.safe_edit(interaction, final_embed, None)
        self.stop()

    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def strike(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            if self.ended: return
            atk_map = {"The Bound (Mortal)": 8, "Third-Rate Warrior": 25, "Second-Rate Warrior": 60, "First-Rate Warrior": 150, "Peak Master": 250}
            base_atk = atk_map.get(self.player[6], 10)
            
            p_dmg = random.randint(base_atk, base_atk + 25)
            self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
            self.log = f"Turn {self.turn}: You strike for {p_dmg}."
            
            if self.enemy['hp'] > 0:
                e_dmg = int(random.randint(max(1, self.enemy.get('atk', 10)-5), self.enemy.get('atk', 10)+5) * (0.75 if self.player[5] == "Golden Bell Shield" else 1.0))
                self.player[1] = max(0, self.player[1] - e_dmg)
                self.log += f"\nTurn {self.turn}: Enemy hits for {e_dmg}."
            
            self.turn += 1
            await self.update_embed(interaction)

    @discord.ui.button(label="Technique", style=discord.ButtonStyle.primary, emoji="🌀")
    async def technique(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.lock:
            if self.ended or self.player[3] < 15: 
                if not self.ended: await interaction.response.send_message("❌ Ki exhausted!", ephemeral=True)
                return
                
            self.player[3] -= 15
            atk_map = {"The Bound (Mortal)": 15, "Third-Rate Warrior": 50, "Second-Rate Warrior": 120, "First-Rate Warrior": 300, "Peak Master": 450}
            base_atk = atk_map.get(self.player[6], 20)
            
            p_dmg = int(random.randint(base_atk, base_atk + 50) * (1 + (self.player[4] or 0) / 100))
            self.enemy['hp'] = max(0, self.enemy['hp'] - p_dmg)
            self.log = f"Turn {self.turn}: [{self.player[5]}] unleashed for {p_dmg}!"
            
            if self.enemy['hp'] > 0:
                self.player[1] = max(0, self.player[1] - int(self.enemy.get('atk', 10)))
                
            self.turn += 1
            await self.update_embed(interaction)

class Combat(commands.Cog):
    def __init__(self, bot): self.bot = bot
    def get_db(self): 
        path = getattr(self.bot.config, 'DB_PATH', 'murim.db') if hasattr(self.bot, 'config') else 'murim.db'
        return sqlite3.connect(path, timeout=30)

    @commands.hybrid_command(name="hunt")
    async def hunt(self, ctx):
        if hasattr(self.bot, 'is_meditating') and ctx.author.id in self.bot.is_meditating:
            return await ctx.send("🧘 Meditation requires stillness.")

        with self.get_db() as conn:
            user = conn.execute("SELECT user_id, COALESCE(hp, 100), COALESCE(vitality, 100), COALESCE(ki, 0), COALESCE(mastery, 0), COALESCE(active_tech, 'None'), COALESCE(rank, 'The Bound (Mortal)'), COALESCE(combat_mastery, 0), COALESCE(taels, 0), meridian_damage FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        
        if not user: return await ctx.send("❌ Use `!start` first.")
        if user[9]:
            try:
                if datetime.datetime.now() < datetime.datetime.fromisoformat(user[9]):
                    return await ctx.send("❌ Your meridians are damaged.")
            except: pass

        rank = user[6]
        if "Peak Master" in rank: target, color = {'name': 'Ancient Bloodfiend', 'hp': 850, 'atk': 135}, 0x582f0e
        elif "First-Rate" in rank: target, color = {'name': 'Corrupted Elder', 'hp': 600, 'atk': 95}, 0x992d22
        elif "Second-Rate" in rank: target, color = {'name': 'Shadow Tiger', 'hp': 250, 'atk': 45}, 0xe67e22
        elif "Third-Rate" in rank: target, color = {'name': 'Spirit Wolf', 'hp': 100, 'atk': 15}, 0x2ecc71
        else: return await ctx.send("❌ Mortals cannot hunt spirit beasts.")

        view = CombatView(self.bot, ctx.author.id, user, target, self.get_db, color)
        embed = discord.Embed(title=f"⚔️ Encounter: {target['name']}", description="Steel your heart.", color=color)
        # Using a fixed 10-bar for the initial send
        embed.add_field(name=f"👤 You (HP: {int(user[1])})", value=f"`{view.generate_bar(user[1], user[1], '🟥')}`", inline=False)
        embed.add_field(name=f"👹 {target['name']} (HP: {int(target['hp'])})", value=f"`{view.generate_bar(target['hp'], target['hp'], '🟧')}`", inline=False)
        await ctx.send(embed=embed, view=view)

async def setup(bot): await bot.add_cog(Combat(bot))
