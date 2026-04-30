import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

class StatusView(discord.ui.View):
    def __init__(self, bot, target, get_db):
        super().__init__(timeout=30)
        self.bot = bot
        self.target = target
        self.get_db = get_db

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.gray)
    async def refresh_button(self, interaction: discord.Interaction):
        cog = self.bot.get_cog('Status')
        await cog.stats(interaction, self.target)

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    def progress_bar(self, current, total=100, segments=10):
        ratio = max(0, min(current / total, 1))
        filled = int(ratio * segments)
        return "🟥" * filled + "⬛" * (segments - filled)

    # --- AFK CALCULATION ENGINE ---
    def process_afk_gains(self, user_data):
        # Adjusted unpacking to match the SQL query in stats()
        u_id, bg, rank, stage, ki, mastery, last_ref, hp, vit, active_tech = user_data
        
        now = datetime.datetime.now()
        # Fallback for fresh/migrated accounts with None timestamps
        if not last_ref:
            return ki, mastery, stage, hp, vit, now

        last_ref_dt = datetime.datetime.fromisoformat(last_ref)
        hours_passed = (now - last_ref_dt).total_seconds() / 3600
        
        # Phase 2 AFK Ki Rates based on Realm
        rates = {
            "The Bound (Mortal)": 5,
            "Third-Rate Warrior": 15,
            "Second-Rate Warrior": 40
        }
        base_rate = rates.get(rank, 5)
        
        # 1. AFK Ki Gains
        ki_gained = int(base_rate * hours_passed)
        
        # 2. Offline Mastery (0.1% per hour, +15% if Instructor)
        # Note: Professional bonuses will be added here once Profession logic is fully linked.
        mastery_gained = 0.1 * hours_passed
        
        # 3. Hermit Perk: 5% HP/Vit regen per hour
        if bg == "Hermit":
            regen_mult = 0.05 * hours_passed
            hp = min(hp + (hp * regen_mult), hp) # Just safety caps
            vit = min(vit + (vit * regen_mult), vit)

        # Caps logic: Ki cap depends on rank
        caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 1000, "Second-Rate Warrior": 3000}
        ki_cap = caps.get(rank, 7500)

        new_ki = min(ki_cap, ki + ki_gained)
        new_mastery = min(100.0, mastery + mastery_gained)

        # 4. Stage Logic
        quarter = ki_cap / 4
        if new_ki >= ki_cap: new_stage = "Peak"
        elif new_ki >= quarter * 3: new_stage = "Late"
        elif new_ki >= quarter * 2: new_stage = "Middle"
        else: new_stage = "Initial"

        return new_ki, new_mastery, new_stage, hp, vit, now

    @commands.hybrid_command(name="stats", description="View progress and claim AFK gains.")
    async def stats(self, ctx_or_inter, member: discord.Member = None):
        target = member or (ctx_or_inter.user if isinstance(ctx_or_inter, discord.Interaction) else ctx_or_inter.author)
        
        conn = self.get_db()
        c = conn.cursor()
        
        # Fetching all relevant Phase 2 + Profession columns
        row = c.execute("""
            SELECT user_id, background, rank, stage, ki, mastery, last_refresh, hp, vitality, active_tech, taels, item_id, profession
            FROM users WHERE user_id=?
        """, (target.id,)).fetchone()

        if not row:
            msg = "❌ Path not found. Use `/start` first."
            if isinstance(ctx_or_inter, discord.Interaction):
                return await ctx_or_inter.response.send_message(msg, ephemeral=True)
            return await ctx_or_inter.send(msg)

        # Unpacking data (matches the SELECT order above)
        u_id, bg, rank, stage, ki, mastery, last_ref, hp, vit, active_tech, taels, item, profession = row

        # Process AFK Gains (Sending first 10 elements to processor)
        new_ki, new_mastery, new_stage, new_hp, new_vit, now = self.process_afk_gains(row[:10])
        
        # Update DB
        c.execute("""
            UPDATE users SET ki=?, mastery=?, stage=?, hp=?, vitality=?, last_refresh=? 
            WHERE user_id=?
        """, (new_ki, round(new_mastery, 2), new_stage, new_hp, new_vit, now.isoformat(), target.id))
        conn.commit()
        
        # Build Embed
        embed = discord.Embed(title=f"📜 Status: {target.name}", color=0x700000)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="Identity", value=f"**Realm:** {rank}\n**Stage:** {new_stage}\n**Background:** {bg}\n**Profession:** {profession}", inline=False)
        
        # Vital Stats (Displaying current/max)
        embed.add_field(name="Vital Statistics", 
                        value=f"🩸 **HP:** {int(new_hp)}\n❤️ **Vit:** {int(new_vit)}", 
                        inline=True)
        
        # Cultivation & Mastery
        m_bar = self.progress_bar(new_mastery)
        embed.add_field(name="Cultivation", 
                        value=f"✨ **Ki:** {new_ki}\n📖 **Mastery:** {round(new_mastery, 2)}%\n{m_bar}", 
                        inline=True)
        
        # Techniques Section
        tech_val = active_tech if active_tech != "None" else "No technique selected."
        embed.add_field(name="Current Study", value=f"📜 {tech_val}", inline=False)
        
        # Innate Slots (Limit 3 as discussed)
        # Note: This will be dynamically populated once the Pavilion 'Innate' logic is coded.
        embed.add_field(name="Innate Techniques (Slots: 0/3)", value="*No passives equipped.*", inline=False)
        
        embed.add_field(name="Inventory", value=f"💰 **Taels:** {taels}\n📦 **Soul Item:** {item}", inline=False)
        
        embed.set_footer(text=f"Last Sync: {now.strftime('%H:%M:%S')}")
        
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
