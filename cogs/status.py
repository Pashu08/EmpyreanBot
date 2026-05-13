import discord
from discord.ext import commands
from discord import app_commands
import datetime
from utils.db import fetch_user, update_user_stat
from utils.helpers import get_max_stats, calculate_stage_from_ki, has_meridian_damage
from utils.constants import AFK_KI_PER_HOUR, AFK_MASTERY_PER_HOUR

# ==========================================
# UI COMPONENTS: STATUS VIEW & REFRESH
# ==========================================
class StatusView(discord.ui.View):
    def __init__(self, bot, target):
        super().__init__(timeout=30)
        self.bot = bot
        self.target = target

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.gray)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        cog = self.bot.get_cog('Status')
        if cog:
            await cog.stats(interaction, self.target)

# ==========================================
# CORE COG: STATUS & AFK ENGINE
# ==========================================
class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def progress_bar(self, current, total=100, segments=10):
        ratio = max(0, min(current / total, 1))
        filled = int(ratio * segments)
        return "🟦" * filled + "⬜" * (segments - filled)

    async def process_afk_gains(self, user_id: int, user_data: dict):
        """Calculate offline gains and update database. Returns updated stats dict."""
        now = datetime.datetime.now()
        last_refresh = user_data.get('last_refresh')
        
        if not last_refresh:
            return user_data, now
        
        try:
            last_ref_dt = datetime.datetime.fromisoformat(last_refresh)
        except (ValueError, TypeError):
            return user_data, now
            
        hours_passed = (now - last_ref_dt).total_seconds() / 3600
        if hours_passed <= 0:
            return user_data, now
        
        rank = user_data['rank']
        background = user_data.get('background', '')
        profession = user_data.get('profession', '')
        
        # Get max stats for this rank
        max_stats = get_max_stats(rank)
        ki_cap = max_stats['ki_cap']
        vit_cap = max_stats['max_vit']
        
        # Ki gains from AFK
        ki_rate = AFK_KI_PER_HOUR.get(rank, 150)
        ki_gained = int(ki_rate * hours_passed)
        new_ki = min(ki_cap, user_data.get('ki', 0) + ki_gained)
        
        # Mastery gains from AFK
        mastery_multiplier = 1.15 if profession == "Instructor" else 1.0
        mastery_gained = AFK_MASTERY_PER_HOUR * hours_passed * mastery_multiplier
        new_mastery = min(100.0, user_data.get('mastery', 0) + mastery_gained)
        
        # HP and Vitality regen
        base_regen = ki_rate  # Same rate as Ki for HP/Vit regen
        new_hp = min(vit_cap, user_data.get('hp', 100) + int(base_regen * hours_passed))
        new_vit = min(vit_cap, user_data.get('vitality', 100) + int(base_regen * hours_passed))
        
        # Hermit bonus: 15% extra regen
        if background == "Hermit":
            hermit_bonus = int(base_regen * hours_passed * 0.15)
            new_hp = min(vit_cap, new_hp + hermit_bonus)
            new_vit = min(vit_cap, new_vit + hermit_bonus)
        
        # Calculate new stage based on Ki
        new_stage = calculate_stage_from_ki(new_ki, ki_cap)
        
        # Update the database with all new values
        db = self.bot.db
        await db.execute(
            """UPDATE users SET 
                ki = ?, 
                mastery = ?, 
                stage = ?, 
                hp = ?, 
                vitality = ?, 
                last_refresh = ? 
            WHERE user_id = ?""",
            (new_ki, round(new_mastery, 2), new_stage, new_hp, new_vit, now.isoformat(), user_id)
        )
        await db.commit()
        
        # Return updated data
        updated_data = user_data.copy()
        updated_data['ki'] = new_ki
        updated_data['mastery'] = new_mastery
        updated_data['stage'] = new_stage
        updated_data['hp'] = new_hp
        updated_data['vitality'] = new_vit
        updated_data['last_refresh'] = now.isoformat()
        
        return updated_data, now

    @commands.hybrid_command(name="stats", aliases=["st"], description="View progress and claim AFK gains.")
    async def stats(self, ctx_or_inter, member: discord.Member = None):
        is_interaction = isinstance(ctx_or_inter, discord.Interaction)
        author = ctx_or_inter.user if is_interaction else ctx_or_inter.author
        target = member or author
        
        db = self.bot.db
        
        # Fetch user data using the shared db helper
        user_data = await fetch_user(db, target.id)
        
        if not user_data:
            msg = "❌ Path not found. Use `!start` first."
            if is_interaction:
                if not ctx_or_inter.response.is_done():
                    return await ctx_or_inter.response.send_message(msg, ephemeral=True)
                return
            return await ctx_or_inter.send(msg)
        
        # Process AFK gains (this updates the database and returns new data)
        updated_data, now = await self.process_afk_gains(target.id, user_data)
        
        # Extract values for display
        rank = updated_data['rank']
        stage = updated_data['stage']
        background = updated_data.get('background', 'Unknown')
        ki = updated_data['ki']
        mastery = updated_data['mastery']
        hp = updated_data['hp']
        vitality = updated_data['vitality']
        active_tech = updated_data.get('active_tech', 'None')
        profession = updated_data.get('profession', 'None')
        taels = updated_data.get('taels', 0)
        combat_mastery = updated_data.get('combat_mastery', 0)
        meridian_damage = updated_data.get('meridian_damage')
        
        # Check meridian health
        is_damaged, minutes_left = has_meridian_damage(meridian_damage)
        meridian_status = f"⚠️ Damaged ({minutes_left}m left)" if is_damaged else "✅ Healthy"
        
        # Get max stats for progress bars
        max_stats = get_max_stats(rank)
        ki_cap = max_stats['ki_cap']
        vit_cap = max_stats['max_vit']
        
        # Build embed
        embed = discord.Embed(title=f"📜 Status: {target.name}", color=0x700000)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        bg_emoji = "🌿" if background == "Hermit" else "⚒️" if background == "Laborer" else "🌑"
        
        embed.add_field(
            name="Identity", 
            value=f"**Realm:** {rank}\n**Stage:** {stage}\n**Path:** {bg_emoji} {background}", 
            inline=False
        )
        
        embed.add_field(
            name="Vital Statistics", 
            value=f"🩸 **HP:** {int(hp)}/{vit_cap}\n❤️ **Vit:** {int(vitality)}/{vit_cap}\n🧠 **Meridians:** {meridian_status}", 
            inline=True
        )
        
        # Ki progress bar
        ki_bar = self.progress_bar(ki, ki_cap)
        mastery_bar = self.progress_bar(mastery)
        
        embed.add_field(
            name="Cultivation", 
            value=f"✨ **Ki:** {ki}/{ki_cap}\n{ki_bar}\n📖 **Mastery:** {round(mastery, 2)}%\n{mastery_bar}\n⚔️ **Combat Mastery:** {combat_mastery}", 
            inline=True
        )
        
        tech_val = f"📜 {active_tech}" if active_tech != "None" else "No technique selected."
        embed.add_field(name="Current Study", value=tech_val, inline=False)
        embed.add_field(name="💰 Wealth", value=f"{taels} Taels", inline=True)
        embed.add_field(name="⚒️ Profession", value=profession if profession != "None" else "None", inline=True)
        
        embed.set_footer(text=f"Last Sync: {now.strftime('%H:%M:%S')}")
        
        # Only show refresh button for the user viewing their own stats
        view = StatusView(self.bot, target) if target.id == author.id else None
        
        if is_interaction:
            await ctx_or_inter.edit_original_response(embed=embed, view=view)
        else:
            await ctx_or_inter.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Status(bot))