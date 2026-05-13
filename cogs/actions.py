import discord
from discord.ext import commands
from discord import app_commands
import random

class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ==========================================
        # WORK FLAVOR TEXTS
        # ==========================================
        self.work_events = [
            "You spent the day transporting heavy iron ore through muddy mountain roads.",
            "You guarded a merchant caravan traveling between remote villages.",
            "You helped repair damaged homes after a fierce storm swept through the region.",
            "You carried water and supplies for wandering martial artists.",
            "You gathered medicinal herbs near the forest outskirts.",
            "You assisted blacksmiths in forging crude weapons for local guards.",
            "You chopped firewood beside a freezing mountain settlement.",
            "You helped merchants unload expensive cargo beneath careful supervision.",
        ]

        # ==========================================
        # OBSERVE FLAVOR TEXTS
        # ==========================================
        self.observe_events = [
            "You sat beneath a silent tree and listened to the rhythm of your breathing.",
            "You observed flowing water and felt your thoughts gradually settle.",
            "You meditated quietly as cold mountain winds brushed past your robes.",
            "You watched the rain strike ancient stone paths deep in thought.",
            "You focused on the circulation of Ki flowing within your body.",
            "You studied the movements of distant martial practitioners from afar.",
            "You sat in silence beneath the moon, calming your restless mind.",
            "You listened carefully to the natural flow of the world around you.",
        ]

        # ==========================================
        # RARE ATMOSPHERIC EVENTS
        # ==========================================
        self.rare_events = [
            "⚠️ A wandering old man briefly glanced at you before disappearing into the crowd.",
            "📜 You noticed strange markings carved into a weathered stone wall.",
            "🌫️ For a brief moment, the surrounding air felt strangely heavy.",
            "👁️ You felt as though someone powerful was observing you from afar.",
            "🩸 You discovered traces of a recent battle hidden deep within the forest.",
        ]

    # ==========================================
    # RANK STAT HELPER
    # ==========================================
    def get_rank_stats(self, rank):
        if "Second-Rate" in rank:
            return 600, 3000
        elif "Third-Rate" in rank:
            return 300, 1000
        else:
            return 100, 100

    # ==========================================
    # RANDOM RARE EVENT
    # ==========================================
    def get_rare_event(self):
        if random.random() <= 0.05:
            return random.choice(self.rare_events)
        return None

    # ==========================================
    # HYBRID COMMAND: WORK
    # ==========================================
    @commands.hybrid_command(name="work", description="Perform labor within the Murim world for Taels.")
    @app_commands.checks.cooldown(1, 5.0)
    async def work(self, ctx):

        user_id = ctx.author.id

        cursor = await self.bot.db.execute(
            """
            SELECT vitality, taels, rank, background, mastery, active_tech
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        )

        user = await cursor.fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        vit, taels, rank, bg, mastery, tech = user

        max_vit, _ = self.get_rank_stats(rank)

        if vit < 10:
            return await ctx.send(
                f"❌ Your exhausted body refuses to continue. ({vit}/{max_vit} Vitality)",
                ephemeral=True
            )

        # Reward Scaling
        base_gain = random.randint(5, 15)

        if "Third-Rate" in rank:
            base_gain += 5
        elif "Second-Rate" in rank:
            base_gain += 10

        new_vit = max(0, vit - 10)
        new_taels = taels + base_gain

        # Mastery Gain
        mastery_msg = ""
        new_mastery = mastery

        if bg == "Laborer" and tech != "None" and mastery < 100:
            if random.random() <= 0.10:
                mastery_gain = 0.5
                new_mastery = min(100.0, mastery + mastery_gain)

                mastery_msg = (
                    f"\n✨ **Laborer's Insight:** "
                    f"Your hardships refined your understanding of **{tech}**. "
                    f"(+0.5% Mastery)"
                )

        # Rare Event
        rare_event = self.get_rare_event()

        # Database Update
        await self.bot.db.execute(
            """
            UPDATE users
            SET vitality=?, taels=?, mastery=?
            WHERE user_id=?
            """,
            (new_vit, new_taels, new_mastery, user_id)
        )

        await self.bot.db.commit()

        # Embed
        embed = discord.Embed(
            title="⚒️ Murim Labor",
            color=0x700000
        )

        embed.description = random.choice(self.work_events)

        if mastery_msg:
            embed.description += mastery_msg

        if rare_event:
            embed.description += f"\n\n{rare_event}"

        embed.add_field(
            name="Earned",
            value=f"💰 **+{base_gain}** Taels",
            inline=True
        )

        embed.add_field(
            name="Vitality",
            value=f"❤️ **{new_vit}**/{max_vit}",
            inline=True
        )

        embed.set_footer(
            text=f"Current Wealth: {new_taels} Taels"
        )

        await ctx.send(embed=embed)

    # ==========================================
    # HYBRID COMMAND: OBSERVE
    # ==========================================
    @commands.hybrid_command(name="observe", description="Observe the world and refine your Ki.")
    @app_commands.checks.cooldown(1, 5.0)
    async def observe(self, ctx):

        user_id = ctx.author.id

        cursor = await self.bot.db.execute(
            """
            SELECT vitality, ki, rank, mastery, active_tech
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        )

        user = await cursor.fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        vit, ki, rank, mastery, tech = user

        max_vit, ki_cap = self.get_rank_stats(rank)

        if vit < 10:
            return await ctx.send(
                f"❌ Your weary mind cannot focus clearly enough. ({vit}/{max_vit} Vitality)",
                ephemeral=True
            )

        ki_gain = random.randint(3, 8)

        if "Third-Rate" in rank:
            ki_gain += 2
        elif "Second-Rate" in rank:
            ki_gain += 4

        new_vit = max(0, vit - 10)
        new_ki = min(ki_cap, ki + ki_gain)

        # Mastery Gain
        mastery_msg = ""
        new_mastery = mastery

        if tech != "None" and mastery < 100:
            mastery_gain = round(random.uniform(0.5, 1.5), 2)
            new_mastery = min(100.0, mastery + mastery_gain)

            mastery_msg = (
                f"\n📖 **Martial Insight:** "
                f"+{mastery_gain}% Mastery in **{tech}**"
            )

        # Rare Event
        rare_event = self.get_rare_event()

        # Database Update
        await self.bot.db.execute(
            """
            UPDATE users
            SET vitality=?, ki=?, mastery=?
            WHERE user_id=?
            """,
            (new_vit, new_ki, new_mastery, user_id)
        )

        await self.bot.db.commit()

        # Embed
        embed = discord.Embed(
            title="👁️ Observation",
            color=0x00AABB
        )

        embed.description = random.choice(self.observe_events)

        if mastery_msg:
            embed.description += mastery_msg

        if rare_event:
            embed.description += f"\n\n{rare_event}"

        embed.add_field(
            name="Ki Refined",
            value=f"✨ **+{ki_gain}** Ki",
            inline=True
        )

        embed.add_field(
            name="Vitality",
            value=f"❤️ **{new_vit}**/{max_vit}",
            inline=True
        )

        embed.set_footer(
            text=f"Current Ki: {new_ki}/{ki_cap}"
        )

        await ctx.send(embed=embed)
    # ==========================================
    # HYBRID COMMAND: COMPREHEND
    # ==========================================
    @commands.hybrid_command(
        name="comprehend",
        description="Deeply study your martial technique."
    )
    @commands.cooldown(1, 1800, commands.BucketType.user)  # ✅ FIXED COOLDOWN
    async def comprehend(self, ctx):

        user_id = ctx.author.id

        cursor = await self.bot.db.execute(
            """
            SELECT vitality, active_tech, mastery, rank
            FROM users
            WHERE user_id=?
            """,
            (user_id,)
        )

        user = await cursor.fetchone()

        if not user:
            return await ctx.send("❌ Use `!start` first.", ephemeral=True)

        vit, tech, mastery, rank = user

        if tech == "None":
            return await ctx.send(
                "❌ You possess no martial technique to comprehend.",
                ephemeral=True
            )

        if vit < 40:
            return await ctx.send(
                f"❌ Your mind lacks the strength required for deep comprehension. "
                f"(Need 40 Vitality, currently {vit})",
                ephemeral=True
            )

        # ✅ NEW: mastery cap check FIRST
        if mastery >= 100:
            return await ctx.send(
                "🧠 Your understanding has already reached its peak.",
                ephemeral=True
            )

        gain = round(random.uniform(5.0, 10.0), 2)

        new_vit = max(0, vit - 40)
        new_mastery = min(100.0, mastery + gain)

        actual_gain = round(new_mastery - mastery, 2)  # ✅ FIX DISPLAY

        rare_event = self.get_rare_event()

        # Database Update
        await self.bot.db.execute(
            """
            UPDATE users
            SET vitality=?, mastery=?
            WHERE user_id=?
            """,
            (new_vit, new_mastery, user_id)
        )

        await self.bot.db.commit()

        embed = discord.Embed(
            title="🧠 Martial Comprehension",
            color=0xFFD700
        )

        embed.description = (
            f"You isolated yourself from worldly distractions and focused entirely "
            f"on the principles of **{tech}**.\n\n"
            f"Fragments of understanding slowly surfaced within your mind."
        )

        if rare_event:
            embed.description += f"\n\n{rare_event}"

        embed.add_field(
            name="Mastery Gained",
            value=f"📖 **+{actual_gain}%**",  # ✅ FIXED
            inline=True
        )

        embed.add_field(
            name="Total Mastery",
            value=f"📊 **{new_mastery}%** / 100%",
            inline=True
        )

        embed.set_footer(
            text=f"Vitality Remaining: {new_vit}"
        )

        await ctx.send(embed=embed)

    # ==========================================
    # COOLDOWN ERROR HANDLER
    # ==========================================
    @work.error
    @observe.error
    @comprehend.error
    async def action_error(self, ctx, error):

        if isinstance(error, (commands.CommandOnCooldown, app_commands.CommandOnCooldown)):

            await ctx.send(
                f"⏳ **Steady your breathing.** "
                f"Wait {error.retry_after:.1f}s before acting again.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Actions(bot))