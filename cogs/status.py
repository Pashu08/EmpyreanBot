import discord
from discord.ext import commands
import sqlite3

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect('murim.db')

    @commands.hybrid_command(name="stats", description="View your progress or another player's status.")
    async def stats(self, ctx, member: discord.Member = None):
        """Displays progress. Usage: !stats or !stats @user"""
        # If no member is mentioned, target is the person who typed the command
        target = member or ctx.author
        
        conn = self.get_db()
        c = conn.cursor()
        
        user = c.execute("""
            SELECT background, rank, taels, ki, vitality, hp, item_id 
            FROM users WHERE user_id=?
        """, (target.id,)).fetchone()
        conn.close()

        if not user:
            msg = "❌ You haven't started yet." if target == ctx.author else f"❌ {target.name} hasn't started their journey yet."
            return await ctx.send(msg)

        bg, rank, taels, ki, vit, hp, item = user

        # --- DYNAMIC CAP LOGIC ---
        # If they are Third-Rate, their cap is 300. Otherwise, it's 100.
        cap = 300 if "Third-Rate" in rank else 100

        embed = discord.Embed(title=f"📜 Status: {target.name}", color=0x700000)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Section 1: Identity & Rank
        embed.add_field(name="Background", value=bg, inline=True)
        embed.add_field(name="Current Rank", value=f"**{rank}**", inline=True)
        
        # Section 2: Vital Statistics (Using the Dynamic Cap)
        embed.add_field(name="HP", value=f"🩸 {hp}/{cap}", inline=True)
        embed.add_field(name="Vitality", value=f"❤️ {vit}/{cap}", inline=True)
        
        # Section 3: Progress & Wealth
        embed.add_field(name="Ki", value=f"✨ {ki}/100", inline=True)
        embed.add_field(name="Taels", value=f"💰 {taels}", inline=True)
        
        # Section 4: Items
        embed.add_field(name="Innate Item", value=f"📦 {item}", inline=False)
        
        footer_text = "Focus your spirit." if target == ctx.author else f"Observing {target.name}'s foundation..."
        embed.set_footer(text=footer_text)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
