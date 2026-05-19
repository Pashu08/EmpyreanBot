import discord
from discord.ext import commands
import random
import asyncio
import datetime
from utils.helpers import get_max_stats, format_embed_color, get_breakthrough_ki_required, get_next_rank
from utils.db import get_bot_setting, is_user_banned, get_user_stat, update_user_stat
from utils.constants import RANKS, ITEM_MUTATIONS
import config

print("[DEBUG] cultivation.py: Loading Cultivation cog...")

# ==========================================
# BREAKTHROUGH UI (ASYNC VERSION)
# ==========================================
class BreakthroughView(discord.ui.View):
    def __init__(self, bot, user_id, user_rank, user_bg):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.user_rank = user_rank
        self.user_bg = user_bg
        self.stage = 1
        self.success_count = 0

        self.prompts = [
            {
                "text": "🌀 **Stage 1: The Gathering**\nYour Ki is swirling violently within your dantian. It feels like molten lead. How do you stabilize the flow?",
                "choices": ["Force it down", "Circulate slowly", "Let it overflow"]
            },
            {
                "text": "🔥 **Stage 2: The Core Heat**\nYour veins begin to glow. The heat is becoming unbearable. Your vision blurs. What is your next move?",
                "choices": ["Focus on breathing", "Ice the spirit", "Endure the pain"]
            },
            {
                "text": "⚡ **Stage 3: The Final Wall**\nYou see the bottleneck. A massive wall of shadow blocking your path to the next rank. Smash it!",
                "choices": ["All-out strike", "Look for a crack", "Pray for luck"]
            }
        ]
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        current_choices = self.prompts[self.stage - 1]["choices"]
        for i, choice in enumerate(current_choices):
            btn = discord.ui.Button(label=choice, style=discord.ButtonStyle.secondary, custom_id=str(i))
            btn.callback = self.button_callback
            self.add_item(btn)

    async def button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This is not your tribulation.", ephemeral=True)

        # 50% chance to succeed on each choice (kept as is – design choice)
        if random.random() > 0.5:
            self.success_count += 1

        if self.stage < 3:
            self.stage += 1
            self.update_buttons()
            embed = discord.Embed(
                title="⚔️ Breakthrough in Progress",
                description=self.prompts[self.stage - 1]["text"],
                color=format_embed_color("main")
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.finish_breakthrough(interaction)

    async def finish_breakthrough(self, interaction):
        db = self.bot.db
        print(f"[DEBUG] cultivation.finish_breakthrough: User {self.user_id}, success_count={self.success_count}")

        if self.success_count >= 2:  # Success
            # Get current user data
            current_rank = self.user_rank
            current_item = await get_user_stat(db, self.user_id, "item_id") or "Torn Page"

            # Get next rank using helper
            new_rank = get_next_rank(current_rank)

            # Get target rank stats for new caps
            target_stats = get_max_stats(new_rank)
            new_hp_cap = target_stats["max_hp"]
            new_vit_cap = target_stats["max_vit"]
            new_ki_cap = target_stats["ki_cap"]

            # Item mutation
            new_item = ITEM_MUTATIONS.get(current_item, current_item)

            # Get rank_id (index in RANKS list)
            new_rank_id = RANKS.index(new_rank) if new_rank in RANKS else 0

            # Update user
            await db.execute("""
                UPDATE users SET
                    rank = ?, rank_id = ?, stage = 'Initial',
                    item_id = ?, ki = 0,
                    hp = ?, vitality = ?
                WHERE user_id = ?
            """, (new_rank, new_rank_id, new_item, new_hp_cap, new_vit_cap, self.user_id))
            await db.commit()

            print(f"[DEBUG] cultivation.finish_breakthrough: {self.user_id} advanced to {new_rank}")

            result_embed = discord.Embed(
                title="🎊 REALM ASCENSION SUCCESS",
                description=(
                    f"You have reached the **{new_rank}**!\n"
                    f"Your item has evolved into: **{new_item}**.\n\n"
                    f"📈 **Stat Growth:**\n"
                    f"Max HP: **{new_hp_cap}**\n"
                    f"Max Vitality: **{new_vit_cap}**\n"
                    f"Ki Cap: **{new_ki_cap}**"
                ),
                color=format_embed_color("win")
            )
        else:  # Failure
            # Lose 100 Ki
            current_ki = await get_user_stat(db, self.user_id, "ki") or 0
            new_ki = max(0, current_ki - 100)
            await update_user_stat(db, self.user_id, "ki", new_ki)

            # Add meridian damage (10 minutes)
            debuff_time = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            await update_user_stat(db, self.user_id, "meridian_damage", debuff_time)

            print(f"[DEBUG] cultivation.finish_breakthrough: {self.user_id} failed, lost 100 Ki, meridians damaged")

            result_embed = discord.Embed(
                title="💀 BREAKTHROUGH FAILED",
                description="The energy backfired. Your meridians are damaged and you lost 100 Ki.",
                color=format_embed_color("lose")
            )

        await interaction.response.edit_message(embed=result_embed, view=None)
        self.stop()

# ==========================================
# MAIN COG
# ==========================================
class Cultivation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Cultivation cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_cultivation", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Cultivation"), ephemeral=True)
        return enabled

    @commands.hybrid_command(name="breakthrough", aliases=["bt"], description="Attempt to reach a higher Major Realm")
    async def breakthrough(self, ctx):
        print(f"[DEBUG] cultivation.breakthrough: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        # Fetch user data
        async with db.execute(
            "SELECT ki, rank, background, stage, mastery FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            user = await cursor.fetchone()

        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        ki, rank, bg, stage, mastery = user

        print(f"[DEBUG] cultivation.breakthrough: User {user_id} - Rank={rank}, Stage={stage}, Ki={ki}, Mastery={mastery}")

        # Get breakthrough Ki requirement using helper
        base_req = get_breakthrough_ki_required(rank, bg)

        # Stage check: Must be at PEAK
        if stage != "Peak":
            return await ctx.send(
                f"❌ You are currently in the **{stage}** stage. You must reach the **Peak** of your current realm first.",
                ephemeral=True
            )

        # Ki check
        if ki < base_req:
            return await ctx.send(
                f"❌ Your foundation is insufficient. You need **{base_req} Ki** for this ascension.",
                ephemeral=True
            )

        # Mastery check for Mortal rank
        if "Mortal" in rank and (mastery is None or mastery < 50.0):
            return await ctx.send(
                "❌ To advance beyond the Mortal realm, you must master at least **50%** of a technique at the **Pavilion of Hidden Scrolls**.",
                ephemeral=True
            )

        # Check if already at max rank (Peak Master)
        if rank == "Peak Master":
            return await ctx.send(
                "❌ You have already reached the peak of martial arts. There is no higher realm to ascend to.",
                ephemeral=True
            )

        # Create breakthrough view
        view = BreakthroughView(self.bot, user_id, rank, bg)
        embed = discord.Embed(
            title="⚔️ Realm Ascension Initiation",
            description=view.prompts[0]["text"],
            color=format_embed_color("main")
        )

        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
    print("[DEBUG] cultivation.py: Setup complete")