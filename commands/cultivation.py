"""
commands/cultivation.py - Command logic for Cultivation cog
"""

import discord
from discord.ext import commands
import asyncio
import datetime
import random
from typing import Optional

from backend.db import (
    get_bot_setting, is_user_banned, get_user_stat, 
    update_user_stat, has_item, remove_item, get_user_cooldown
)
from backend.helpers import get_max_stats, get_next_rank
from backend.cultivation_helpers import (
    MINOR_REALMS,
    MINOR_REALM_KI_REQUIREMENTS,
    MINOR_BREAKTHROUGH_CHANCES,
    MINOR_COOLDOWN_MINUTES,
    MAJOR_COOLDOWN_MINUTES,
    get_minor_realm_from_ki,
    get_next_minor_realm,
    get_ki_required_for_minor_realm,
    get_minor_breakthrough_chance,
    get_major_breakthrough_chance,
    apply_minor_success,
    apply_minor_failure,
    apply_major_success,
    apply_major_failure,
    get_major_stage,
    calculate_stage_success,
    finalize_major_breakthrough
)

from embeds.cultivation_embeds import (
    minor_breakthrough_confirm_embed,
    minor_breakthrough_success_embed,
    minor_breakthrough_failure_embed,
    major_breakthrough_confirm_embed,
    major_stage_embed,
    major_breakthrough_success_embed,
    major_breakthrough_failure_embed,
    breakthrough_status_embed,
    breakthrough_cooldown_embed
)

import config

print("[DEBUG] commands/cultivation.py: Loading Cultivation commands...")

class MajorBreakthroughView(discord.ui.View):
    """Interactive view for major breakthrough stages."""

    def __init__(self, bot, user_id: int, user_rank: str, user_bg: str, user_item: str):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = user_id
        self.user_rank = user_rank
        self.user_bg = user_bg
        self.user_item = user_item
        self.stage_index = 0
        self.stage_results = []
        self.stage_effects = []
        self.next_stage_boost = False
        self.final_chance_boost = False

        self.update_buttons()

    def update_buttons(self):
        """Update buttons for current stage."""
        self.clear_items()

        stage_data = get_major_stage(self.stage_index)
        choices = stage_data["choices"]

        for i, choice in enumerate(choices):
            btn = discord.ui.Button(
                label=choice["text"],
                style=discord.ButtonStyle.primary,
                custom_id=str(i)
            )
            btn.callback = self.make_callback(i)
            self.add_item(btn)

    def make_callback(self, choice_index: int):
        """Create callback for a specific choice."""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message(
                    "❌ This tribulation is not yours.", ephemeral=True
                )

            await self.process_stage(interaction, choice_index)

        return callback

    async def process_stage(self, interaction: discord.Interaction, choice_index: int):
        """Process a breakthrough stage."""

        # Calculate success for this stage
        success, chance, effects = calculate_stage_success(
            self.stage_index, choice_index, self.next_stage_boost
        )

        self.stage_results.append(success)
        self.stage_effects.append(effects)

        # Update boosts for next stage
        if effects.get("next_stage_boost"):
            self.next_stage_boost = True
        if effects.get("final_chance_boost"):
            self.final_chance_boost = True

        # Move to next stage or finish
        self.stage_index += 1

        if self.stage_index < 3:
            # Next stage
            self.update_buttons()
            stage_data = get_major_stage(self.stage_index)

            embed = major_stage_embed(
                stage=self.stage_index + 1,
                stage_name=stage_data["name"],
                description=stage_data["description"],
                choices=[(c["text"], c["base_success"]) for c in stage_data["choices"]]
            )

            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Breakthrough complete
            await self.finish_breakthrough(interaction)

    async def finish_breakthrough(self, interaction: discord.Interaction):
        """Finalize the major breakthrough."""

        db = self.bot.db

        # Check if all stages succeeded
        all_succeeded = all(self.stage_results)

        # Apply final chance boost if earned
        if self.final_chance_boost and not all_succeeded:
            # Extra 20% chance to succeed even with failures
            if random.randint(1, 100) <= 20:
                all_succeeded = True

        if all_succeeded:
            # Major success
            result = await apply_major_success(
                db, self.user_id, self.user_rank, self.user_item
            )

            # Apply double rewards if earned
            double_rewards = any(effects.get("double_rewards", False) for effects in self.stage_effects)
            if double_rewards:
                await add_item(db, self.user_id, result["new_item"], 1, bound=True)
                result["double_reward"] = True

            embed = major_breakthrough_success_embed(
                new_rank=result["new_rank"],
                new_item=result["new_item"],
                new_hp_cap=result["new_hp_cap"],
                new_vit_cap=result["new_vit_cap"],
                new_ki_cap=result["new_ki_cap"]
            )

            if result.get("double_reward"):
                embed.add_field(name="🎁 Double Reward!", value="You received an extra copy of your evolved item!", inline=False)

            # Set cooldown
            cooldown_key = f"breakthrough_major_{self.user_id}"
            now = datetime.datetime.now().isoformat()
            await db.user_cooldowns.update_one(
                {"cooldown_key": cooldown_key},
                {"$set": {"last_used": now}},
                upsert=True
            )

        else:
            # Major failure
            ki_loss, tael_loss, meridian_minutes = await apply_major_failure(db, self.user_id)

            embed = major_breakthrough_failure_embed(
                ki_percent_lost=ki_loss,
                taels_lost=tael_loss,
                meridian_minutes=meridian_minutes,
                cooldown_minutes=MAJOR_COOLDOWN_MINUTES
            )

            # Set cooldown
            cooldown_key = f"breakthrough_major_{self.user_id}"
            now = datetime.datetime.now().isoformat()
            await db.user_cooldowns.update_one(
                {"cooldown_key": cooldown_key},
                {"$set": {"last_used": now}},
                upsert=True
            )

        # Disable all buttons
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    async def on_timeout(self):
        """Handle timeout."""
        for child in self.children:
            child.disabled = True

        if hasattr(self, 'message'):
            try:
                embed = discord.Embed(
                    title="⏳ Breakthrough Cancelled",
                    description="The tribulation has ended due to inactivity.",
                    color=0xE74C3C
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass

class Cultivation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Cultivation cog initialized")

    async def _is_feature_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_cultivation", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Cultivation"), ephemeral=True)
        return enabled

    async def _check_cooldown(self, user_id, bt_type):
        """Check if user is on breakthrough cooldown."""
        cooldown_key = f"breakthrough_{bt_type}_{user_id}"
        last_used = await get_user_cooldown(self.bot.db, cooldown_key)

        if not last_used:
            return False, 0

        minutes = MAJOR_COOLDOWN_MINUTES if bt_type == "major" else MINOR_COOLDOWN_MINUTES
        now = datetime.datetime.now()
        elapsed = (now - last_used).total_seconds() / 60

        if elapsed < minutes:
            remaining = int((minutes - elapsed) * 60)
            return True, remaining

        return False, 0

    # ==========================================
    # COMMAND: BREAKTHROUGH
    # ==========================================

    @commands.hybrid_command(name="breakthrough", aliases=["bt"])
    async def breakthrough(self, ctx):
        """Attempt a breakthrough to the next minor or major realm."""

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        # Fetch user data
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        ki = user.get("ki", 0)
        rank = user.get("rank", "The Bound (Mortal)")
        bg = user.get("background", "")
        minor_realm = user.get("minor_realm", "Initial")
        mastery = user.get("mastery", 0.0)
        taels = user.get("taels", 0)

        max_stats = get_max_stats(rank)
        max_ki = max_stats["ki_cap"]

        # Get current minor realm from Ki (for consistency)
        correct_minor = get_minor_realm_from_ki(ki, max_ki)
        if correct_minor != minor_realm:
            await update_user_stat(db, user_id, "minor_realm", correct_minor)
            minor_realm = correct_minor

        # Check if at Peak -> attempt major breakthrough
        if minor_realm == "Peak":
            await self._attempt_major_breakthrough(ctx, user_id, rank, bg, ki, max_ki, mastery, taels)
        else:
            await self._attempt_minor_breakthrough(ctx, user_id, rank, bg, minor_realm, ki, max_ki, taels)

    async def _attempt_minor_breakthrough(self, ctx, user_id, rank, bg, current_minor, ki, max_ki, taels):
        """Handle minor breakthrough attempt."""

        next_minor = get_next_minor_realm(current_minor)
        if not next_minor:
            return await ctx.send("❌ You are already at the peak of your realm. Attempt a major breakthrough!", ephemeral=True)

        # Calculate required Ki
        required_ki = get_ki_required_for_minor_realm(next_minor, max_ki)

        # Check Ki requirement
        if ki < required_ki:
            return await ctx.send(
                f"❌ You need **{required_ki} Ki** to attempt {next_minor} minor realm. (You have {ki})",
                ephemeral=True
            )

        # Check cooldown
        on_cooldown, remaining = await self._check_cooldown(user_id, "minor")
        if on_cooldown:
            minutes = remaining // 60
            seconds = remaining % 60
            embed = breakthrough_cooldown_embed(minutes, seconds, is_major=False)
            return await ctx.send(embed=embed, ephemeral=True)

        # Check for Breakthrough Pill
        has_bt_pill = await has_item(self.bot.db, user_id, "Breakthrough Pill")

        # Calculate success chance
        success_chance = await get_minor_breakthrough_chance(
            self.bot.db, user_id, rank, next_minor, ki, required_ki, has_bt_pill
        )

        # Send confirmation embed
        embed = minor_breakthrough_confirm_embed(
            current_minor=current_minor,
            target_minor=next_minor,
            required_ki=required_ki,
            current_ki=ki,
            max_ki=max_ki,
            success_chance=success_chance,
            has_pill=has_bt_pill
        )

        await ctx.send(embed=embed)

        # Wait for confirmation
        def check(m):
            return m.author == ctx.author and m.content.lower() in ["yes", "y", "no", "n"]

        try:
            msg = await self.bot.wait_for("message", timeout=30, check=check)
            if msg.content.lower() not in ["yes", "y"]:
                return await ctx.send("❌ Breakthrough cancelled.", ephemeral=True)
        except asyncio.TimeoutError:
            return await ctx.send("⏳ Breakthrough cancelled (timeout).", ephemeral=True)

        # Perform breakthrough roll
        roll = random.randint(1, 100)
        success = roll <= success_chance

        if success:
            # Consume pill if used
            if has_bt_pill:
                await remove_item(self.bot.db, user_id, "Breakthrough Pill", 1)

            # Apply success
            bonuses = await apply_minor_success(self.bot.db, user_id, next_minor)

            embed = minor_breakthrough_success_embed(
                target_minor=next_minor,
                ki_bonus=bonuses["ki_gain"],
                damage_bonus=bonuses["tech_damage"],
                bt_bonus=bonuses["major_bt_chance"]
            )
            await ctx.send(embed=embed)
        else:
            # Apply failure
            ki_lost, taels_lost = await apply_minor_failure(self.bot.db, user_id, next_minor)

            embed = minor_breakthrough_failure_embed(
                target_minor=next_minor,
                ki_percent_lost=ki_lost,
                taels_lost=taels_lost,
                cooldown_minutes=MINOR_COOLDOWN_MINUTES
            )
            await ctx.send(embed=embed)

        # Set cooldown
        cooldown_key = f"breakthrough_minor_{user_id}"
        now = datetime.datetime.now().isoformat()
        await self.bot.db.user_cooldowns.update_one(
            {"cooldown_key": cooldown_key},
            {"$set": {"last_used": now}},
            upsert=True
        )

    async def _attempt_major_breakthrough(self, ctx, user_id, rank, bg, ki, max_ki, mastery, taels):
        """Handle major breakthrough attempt."""

        if rank == "Peak Master":
            return await ctx.send("❌ You have already reached the peak of martial arts. There is no higher realm.", ephemeral=True)

        next_rank = get_next_rank(rank)
        required_ki = max_ki  # FIXED: was int(max_ki * 1.5)

        # Check Ki requirement
        if ki < required_ki:
            return await ctx.send(
                f"❌ You need **{required_ki} Ki** to attempt a major breakthrough. (You have {ki})",
                ephemeral=True
            )

        # Check mastery requirement for Mortal rank
        if "Mortal" in rank and mastery < 50:
            return await ctx.send(
                "❌ To advance beyond the Mortal realm, you must master at least **50%** of a technique at the Pavilion.",
                ephemeral=True
            )

        # Check cooldown
        on_cooldown, remaining = await self._check_cooldown(user_id, "major")
        if on_cooldown:
            minutes = remaining // 60
            seconds = remaining % 60
            embed = breakthrough_cooldown_embed(minutes, seconds, is_major=True)
            return await ctx.send(embed=embed, ephemeral=True)

        # Check for Breakthrough Pill
        has_bt_pill = await has_item(self.bot.db, user_id, "Breakthrough Pill")

        # Calculate success chance
        success_chance = await get_major_breakthrough_chance(
            self.bot.db, user_id, rank, ki, required_ki, has_bt_pill
        )

        # Send confirmation embed
        embed = major_breakthrough_confirm_embed(
            current_rank=rank,
            next_rank=next_rank,
            required_ki=required_ki,
            current_ki=ki,
            max_ki=max_ki,
            success_chance=success_chance,
            has_pill=has_bt_pill,
            current_mastery=mastery
        )

        await ctx.send(embed=embed)

        # Wait for confirmation
        def check(m):
            return m.author == ctx.author and m.content.lower() in ["yes", "y", "no", "n"]

        try:
            msg = await self.bot.wait_for("message", timeout=30, check=check)
            if msg.content.lower() not in ["yes", "y"]:
                return await ctx.send("❌ Breakthrough cancelled.", ephemeral=True)
        except asyncio.TimeoutError:
            return await ctx.send("⏳ Breakthrough cancelled (timeout).", ephemeral=True)

        # Consume pill if used
        if has_bt_pill:
            await remove_item(self.bot.db, user_id, "Breakthrough Pill", 1)

        # Get user's current item
        user = await self.bot.db.users.find_one({"user_id": user_id})
        current_item = user.get("item_id", "Torn Page")

        # Start the breakthrough view
        view = MajorBreakthroughView(self.bot, user_id, rank, bg, current_item)
        stage_data = get_major_stage(0)

        embed = major_stage_embed(
            stage=1,
            stage_name=stage_data["name"],
            description=stage_data["description"],
            choices=[(c["text"], c["base_success"]) for c in stage_data["choices"]]
        )

        message = await ctx.send(embed=embed, view=view)
        view.message = message

    # ==========================================
    # COMMAND: BREAKTHROUGH STATUS
    # ==========================================

    @commands.hybrid_command(name="breakthrough_status", aliases=["btst"])
    async def breakthrough_status(self, ctx):
        """Check breakthrough progress and requirements."""

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        user = await db.users.find_one({"user_id": user_id})
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        rank = user.get("rank", "The Bound (Mortal)")
        minor_realm = user.get("minor_realm", "Initial")
        ki = user.get("ki", 0)
        mastery = user.get("mastery", 0.0)
        bonus_ki = user.get("minor_breakthrough_bonus_ki", 0)
        bonus_damage = user.get("minor_breakthrough_bonus_damage", 0)
        bonus_bt = user.get("minor_breakthrough_bonus_bt", 0)

        max_stats = get_max_stats(rank)
        max_ki = max_stats["ki_cap"]

        # Correct minor realm if needed
        correct_realm = get_minor_realm_from_ki(ki, max_ki)
        if correct_realm != minor_realm:
            minor_realm = correct_realm

        # Prepare next breakthrough info
        next_breakthrough = None

        if minor_realm != "Peak":
            next_minor = get_next_minor_realm(minor_realm)
            required_ki = get_ki_required_for_minor_realm(next_minor, max_ki)
            required_pct = MINOR_REALM_KI_REQUIREMENTS.get(next_minor, 50)

            next_breakthrough = {
                "title": "Next Minor Breakthrough",
                "description": f"Target: **{next_minor}**\nKi Needed: {required_ki}/{max_ki} ({required_pct}%)"
            }
        elif rank != "Peak Master":
            required_ki = max_ki  # FIXED: was int(max_ki * 1.5)
            next_breakthrough = {
                "title": "Next Major Breakthrough",
                "description": f"Target: **{get_next_rank(rank)}**\nKi Needed: {required_ki}/{max_ki} (100%)\n"
                              f"Mastery Required: 50% {'✅' if mastery >= 50 else '❌'}"
            }

        embed = breakthrough_status_embed(
            rank=rank,
            minor_realm=minor_realm,
            ki=ki,
            max_ki=max_ki,
            mastery=mastery,
            bonus_ki=bonus_ki,
            bonus_damage=bonus_damage,
            bonus_bt=bonus_bt,
            next_breakthrough_info=next_breakthrough
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
    print("[DEBUG] commands/cultivation.py: Setup complete")
