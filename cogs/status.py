import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

# --- PHASE 2 HIERARCHY DATA ---
REALM_DATA = {
    "The Bound (Mortal)": {"ki_cap": 100, "stat_cap": 100, "afk_rate": 5},
    "Third-Rate Warrior": {"ki_cap": 1000, "stat_cap": 300, "afk_rate": 15},
    "Second-Rate Warrior": {"ki_cap": 3000, "stat_cap": 600, "afk_rate": 40}
}

class StatusView(discord.ui.View):
    def __init__(self, bot, target, get_db):
        super().__init__(timeout=30)
        self.bot = bot
        self.target = target
        self.get_db = get_db

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.gray)
    async def refresh_button(self, interaction: discord.Interaction):
        # We redirect the refresh button to trigger the main stats logic 
        # so it recalculates AFK gains on every click.
        cog = self.bot.get_cog('Status')
        await cog.stats(interaction, self.target)

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    # --- AFK CALCULATION ENGINE ---
    def process_afk_gains(self, user_data):
        u_id, bg, rank, stage, ki, mastery, last_ref, hp, vit = user_data
        
        now = datetime.datetime.now()
        last_ref_dt = datetime.datetime.fromisoformat(last_ref)
        hours_passed = (now - last_ref_dt).total_seconds() / 3600
        
        realm_info = REALM_DATA.get(rank, REALM_DATA["The Bound (Mortal)"])
        
        # 1. AFK Ki Gains
        ki_gained = int(realm_info["afk_rate"] * hours_passed)
        # 2. Offline Mastery (0.1% per hour)
        mastery_gained = 0.1 * hours_passed
        
        # 3. Hermit Perk: 5% HP/Vit regen per hour while offline
        if bg == "Hermit":
            regen_mult = 0.05 * hours_passed
            hp = min(realm_info["stat_cap"], hp + (realm_info["stat_cap"] * regen_mult))
            vit = min(realm_info["stat_cap"], vit + (realm_info["stat_cap"] * regen_mult))

        new_ki = min(realm_info["ki_cap"], ki + ki_gained)
        new_mastery = min(100.0, mastery + mastery_gained)

        # 4. Stage Logic (Divide Ki Cap into 4 Stages)
        quarter = realm_info["ki_cap"] / 4
        if new_ki >= realm_info["ki_cap"]: new_stage = "Peak"
        elif new_ki >= quarter * 3: new_stage = "Late"
        elif new_ki >= quarter * 2: new_stage = "Middle"
        else: new_stage = "Initial"

        return new_ki, new_mastery, new_stage, hp, vit, now

    @commands.hybrid_command(name="stats", description="View progress and claim AFK gains.")
    async def stats(self, ctx_or_inter, member: discord.Member = None):
        target = member or (ctx_or_inter.user if isinstance(ctx_or_inter, discord.Interaction) else ctx_or_inter.author)
        
        conn = self.get_db()
        c = conn.cursor()
        
        # Fetch Phase 2 Columns
        row = c.execute("""
            SELECT user_id, background, rank, stage, ki, mastery, last_refresh, hp, vitality, taels, item_id 
            FROM users WHERE user_id=?
        """, (target.id,)).fetchone()

        if not row:
            msg = "❌ Path not found."
            if isinstance(ctx_or_inter, discord.Interaction):
                return await ctx_or_inter.response.send_message(msg, ephemeral=True)
            return await ctx_or_inter.send(msg)

        # Process AFK Gains
        new_ki, new_mastery, new_stage, new_hp, new_vit, now = self.process_afk_gains(row[:9])
        
        # Update DB with new gains and current timestamp
        c.execute("""
            UPDATE users SET ki=?, mastery=?, stage=?, hp=?, vitality=?, last_refresh=? 
            WHERE user_id=?
        """, (new_ki, round(new_mastery, 2), new_stage, new_hp, new_vit, now.isoformat(), target.id))
        conn.commit()
        
        # Refresh variables for display
        u_id, bg, rank, stage, ki, mastery, last_ref, hp, vit, taels, item = row
        realm_info = REALM_DATA.get(rank, REALM_DATA["The Bound (Mortal)"])

        embed = discord.Embed(title=f"📜 Status: {target.name}", color=0x700000)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Realm", value=f"**{rank}**\n({new_stage} Stage)", inline=True)
        embed.add_field(name="Background", value=bg, inline=True)
        
        embed.add_field(name="Vital Statistics", 
                        value=f"🩸 HP: {int(new_hp)}/{realm_info['stat_cap']}\n❤️ Vit: {int(new_vit)}/{realm_info['stat_cap']}", 
                        inline=True)
        
        embed.add_field(name="Cultivation", 
                        value=f"✨ Ki: {new_ki}/{realm_info['ki_cap']}\n📖 Mastery: {round(new_mastery, 2)}%", 
                        inline=True)
        
        embed.add_field(name="Resources", value=f"💰 Taels: {taels}\n📦 Item: {item}", inline=False)
        
        embed.set_footer(text=f"Last Meditated: {now.strftime('%H:%M:%S')}")
        
        view = StatusView(self.bot, target, self.get_db) if target.id == (ctx_or_inter.user.id if isinstance(ctx_or_inter, discord.Interaction) else ctx_or_inter.author.id) else None
        
        if isinstance(ctx_or_inter, discord.Interaction):
            if ctx_or_inter.response.is_done():
                await ctx_or_inter.edit_original_response(embed=embed, view=view)
            else:
                await ctx_or_inter.response.send_message(embed=embed, view=view)
        else:
            await ctx_or_inter.send(embed=embed, view=view)
        conn.close()

async def setup(bot):
    await bot.add_cog(Status(bot))
