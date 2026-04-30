import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

# ==========================================
# UI COMPONENTS: STATUS VIEW & REFRESH
# ==========================================
class StatusView(discord.ui.View):
    def __init__(self, bot, target, get_db):
        super().__init__(timeout=30)
        self.bot = bot
        self.target = target
        self.get_db = get_db

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.gray)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # FIXED: Added 'button' argument to stop the TypeError crash
        await interaction.response.defer()
        
        cog = self.bot.get_cog('Status')
        if cog:
            await cog.stats(interaction, self.target)

# ==========================================
# CORE COG: STATUS, AFK ENGINE & INVENTORY
# ==========================================
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
        u_id, bg, rank, stage, ki, mastery, last_ref, hp, vit, active_tech, profession = user_data
        
        now = datetime.datetime.now()
        if not last_ref:
            return ki, mastery, stage, hp, vit, now

        last_ref_dt = datetime.datetime.fromisoformat(last_ref)
        hours_passed = (now - last_ref_dt).total_seconds() / 3600
        
        rates = {
            "The Bound (Mortal)": 10,
            "Third-Rate Warrior": 25,
            "Second-Rate Warrior": 60
        }
        base_rate = rates.get(rank, 10)
        
        ki_gained = int(base_rate * hours_passed)
        mastery_mult = 1.15 if profession == "Instructor" else 1.0
        mastery_gained = (0.1 * hours_passed) * mastery_mult
        
        if bg == "Hermit":
            regen_mult = 0.05 * hours_passed
            hp += (hp * regen_mult)
            vit += (vit * regen_mult)

        caps = {"The Bound (Mortal)": 100, "Third-Rate Warrior": 1000, "Second-Rate Warrior": 3000}
        ki_cap = caps.get(rank, 7500)

        new_ki = min(ki_cap, ki + ki_gained)
        new_mastery = min(100.0, mastery + mastery_gained)

        quarter = ki_cap / 4
        if new_ki >= ki_cap: new_stage = "Peak"
        elif new_ki >= quarter * 3: new_stage = "Late"
        elif new_ki >= quarter * 2: new_stage = "Middle"
        else: new_stage = "Initial"

        return new_ki, new_mastery, new_stage, hp, vit, now

    # ==========================================
    # HYBRID COMMAND: !stats
    # ==========================================
    @commands.hybrid_command(name="stats", description="View progress and claim AFK gains.")
    async def stats(self, ctx_or_inter, member: discord.Member = None):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        author = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        target = member or author
        
        conn = self.get_db()
        c = conn.cursor()
        
        row = c.execute("""
            SELECT user_id, background, rank, stage, ki, mastery, last_refresh, hp, vitality, active_tech, profession, taels, item_id 
            FROM users WHERE user_id=?
        """, (target.id,)).fetchone()

        if not row:
            msg = "❌ Path not found. Use `!start` first."
            if is_interaction:
                if not ctx_or_inter.response.is_done():
                    return await ctx_or_inter.response.send_message(msg, ephemeral=True)
                return
            return await ctx_or_inter.send(msg)

        u_id, bg, rank, stage, ki, mastery, last_ref, hp, vit, active_tech, profession, taels, item = row
        new_ki, new_mastery, new_stage, new_hp, new_vit, now = self.process_afk_gains(row[:11])
        
        c.execute("""
            UPDATE users SET ki=?, mastery=?, stage=?, hp=?, vitality=?, last_refresh=? 
            WHERE user_id=?
        """, (new_ki, round(new_mastery, 2), new_stage, new_hp, new_vit, now.isoformat(), target.id))
        conn.commit()
        
        embed = discord.Embed(title=f"📜 Status: {target.name}", color=0x700000)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        prof_display = f"🎓 {profession}" if profession != "None" else "None"
        bg_emoji = "🌿" if bg == "Hermit" else "⚒️" if bg == "Laborer" else "🌑"
        
        embed.add_field(name="Identity", value=f"**Realm:** {rank}\n**Stage:** {new_stage}\n**Path:** {bg_emoji} {bg}\n**Profession:** {prof_display}", inline=False)
        embed.add_field(name="Vital Statistics", value=f"🩸 **HP:** {int(new_hp)}\n❤️ **Vit:** {int(new_vit)}", inline=True)
        
        m_bar = self.progress_bar(new_mastery)
        embed.add_field(name="Cultivation", value=f"✨ **Ki:** {new_ki}\n📖 **Mastery:** {round(new_mastery, 2)}%\n{m_bar}", inline=True)
        
        tech_val = f"📜 {active_tech}" if active_tech != "None" else "No technique selected."
        embed.add_field(name="Current Study", value=tech_val, inline=False)
        
        # INVENTORY REMOVED FROM HERE AS REQUESTED
        embed.set_footer(text=f"Last Sync: {now.strftime('%H:%M:%S')}")
        
        view = StatusView(self.bot, target, self.get_db) if target.id == author.id else None
        
        if is_interaction:
            await ctx_or_inter.edit_original_response(embed=embed, view=view)
        else:
            await ctx_or_inter.send(embed=embed, view=view)
        conn.close()

    # ==========================================
    # NEW HYBRID COMMAND: !inventory
    # ==========================================
    @commands.hybrid_command(name="inventory", description="View your currency and stored items.")
    async def inventory(self, ctx):
        conn = self.get_db()
        c = conn.cursor()
        
        row = c.execute("SELECT taels, item_id FROM users WHERE user_id=?", (ctx.author.id,)).fetchone()
        conn.close()

        if not row:
            return await ctx.send("❌ You haven't started your journey yet.", ephemeral=True)

        taels, item_string = row
        
        # Format the item list
        if not item_string or item_string == "None":
            items_display = "*Your pockets are empty.*"
        else:
            # Splits the comma-separated string into a bulleted list
            items_display = "\n".join([f"• {i.strip()}" for i in item_string.split(",")])

        embed = discord.Embed(title=f"🎒 Inventory: {ctx.author.name}", color=0x2c3e50)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        embed.add_field(name="Wealth", value=f"💰 **Taels:** {taels}", inline=False)
        embed.add_field(name="Possessions", value=items_display, inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
