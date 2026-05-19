import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
from utils.helpers import get_max_stats, format_embed_color, roll_random_event, calculate_stage_from_ki
from utils.db import get_bot_setting, get_user_stat, update_user_stat, is_user_banned
import config

print("[DEBUG] actions.py: Loading Actions cog...")

class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Actions cog initialized")

        # ==========================================
        # WORK FLAVOR TEXTS
        # ==========================================
        self.work_flavors = [
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
        self.observe_flavors = [
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
    # HELPER: Check if a milestone reward is already claimed
    # ==========================================
    async def _has_milestone(self, user_id, technique, milestone):
        flags = await get_user_stat(self.bot.db, user_id, "mastery_flags")
        if not flags:
            return False
        return f"{technique}:{milestone}" in flags.split(",")

    async def _add_milestone(self, user_id, technique, milestone):
        flags = await get_user_stat(self.bot.db, user_id, "mastery_flags") or ""
        if flags:
            new_flags = f"{flags},{technique}:{milestone}"
        else:
            new_flags = f"{technique}:{milestone}"
        await update_user_stat(self.bot.db, user_id, "mastery_flags", new_flags)

    async def _get_teaching_bonus(self, user_id, bonus_type):
        return await get_user_stat(self.bot.db, user_id, f"teaching_bonus_{bonus_type}") or 0

    async def _add_teaching_bonus(self, user_id, bonus_type, amount=1):
        current = await self._get_teaching_bonus(user_id, bonus_type)
        new = min(10, current + amount)
        await update_user_stat(self.bot.db, user_id, f"teaching_bonus_{bonus_type}", new)
        return new

    # ==========================================
    # HELPER: Check feature toggle
    # ==========================================
    async def _actions_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_actions", True)
        if not enabled:
            await ctx.send(config.MSG_FEATURE_DISABLED.format(feature="Actions"), ephemeral=True)
        return enabled

    # ==========================================
    # HELPER: Daily bonus check
    # ==========================================
    async def _check_daily_bonus(self, user_id, action_type):
        last_date = await get_user_stat(self.bot.db, user_id, f"daily_{action_type}_date")
        today = datetime.datetime.now().date().isoformat()
        if last_date != today:
            await update_user_stat(self.bot.db, user_id, f"daily_{action_type}_date", today)
            return True, today
        return False, last_date

    # ==========================================
    # HELPER: Update stage based on Ki
    # ==========================================
    async def _update_stage(self, user_id, rank, ki):
        """Update the user's cultivation stage based on current Ki."""
        max_stats = get_max_stats(rank)
        new_stage = calculate_stage_from_ki(ki, max_stats["ki_cap"])
        current_stage = await get_user_stat(self.bot.db, user_id, "stage")
        if current_stage != new_stage:
            await update_user_stat(self.bot.db, user_id, "stage", new_stage)
            return new_stage
        return None

    # ==========================================
    # HELPER: Process mastery milestone rewards
    # ==========================================
    async def _process_mastery_milestones(self, ctx, user_id, technique, old_mastery, new_mastery):
        if technique == "None":
            return ""
        rewards = []
        milestones = [25, 50, 75, 100]

        for milestone in milestones:
            if old_mastery < milestone <= new_mastery:
                if await self._has_milestone(user_id, technique, milestone):
                    continue
                await self._add_milestone(user_id, technique, milestone)

                if milestone == 25:
                    rewards.append("🌀 You unlocked a free technique use per battle (no Ki cost)!")
                    await update_user_stat(self.bot.db, user_id, f"mastery_25_{technique}", 1)
                elif milestone == 50:
                    rewards.append("⚡ Technique cooldown reduced by 1 turn in combat!")
                    await update_user_stat(self.bot.db, user_id, f"mastery_50_{technique}", 1)
                elif milestone == 75:
                    if technique == "Flowing Cloud Steps":
                        rewards.append("💨 **Flowing Cloud Steps** – Your next strike after using this technique automatically hits!")
                        await update_user_stat(self.bot.db, user_id, "mastery_75_flowing", 1)
                    elif technique == "Swift Wind Kick":
                        rewards.append("🦶 **Swift Wind Kick** – If you kill an enemy, you get a free extra strike!")
                        await update_user_stat(self.bot.db, user_id, "mastery_75_swift", 1)
                    elif technique == "Golden Bell Shield":
                        rewards.append("🔔 **Golden Bell Shield** – You now reflect 20% of damage back to the attacker!")
                        await update_user_stat(self.bot.db, user_id, "mastery_75_golden", 1)
                    elif technique == "Vajra Guard Mantra":
                        rewards.append("🧘 **Vajra Guard Mantra** – Using this technique cleanses one debuff!")
                        await update_user_stat(self.bot.db, user_id, "mastery_75_vajra", 1)
                elif milestone == 100:
                    if technique == "Flowing Cloud Steps":
                        rewards.append("🌑 **Hidden Technique Unlocked:** Flowing Cloud Shadow Step – Teleport behind an enemy for a guaranteed critical hit!")
                        rewards.append("📖 You can now teach this technique once per day. Use `!teach @user Flowing Cloud Steps`")
                        await update_user_stat(self.bot.db, user_id, "hidden_tech_flowing", 1)
                    elif technique == "Swift Wind Kick":
                        rewards.append("🌀 **Hidden Technique Unlocked:** Swift Hurricane Kick – Hits all enemies in combat!")
                        rewards.append("📖 You can now teach this technique once per day. Use `!teach @user Swift Wind Kick`")
                        await update_user_stat(self.bot.db, user_id, "hidden_tech_swift", 1)
                    elif technique == "Golden Bell Shield":
                        rewards.append("💎 **Hidden Technique Unlocked:** Indestructible Diamond Body – Become immune to damage for 2 turns!")
                        rewards.append("📖 You can now teach this technique once per day. Use `!teach @user Golden Bell Shield`")
                        await update_user_stat(self.bot.db, user_id, "hidden_tech_golden", 1)
                    elif technique == "Vajra Guard Mantra":
                        rewards.append("♾️ **Hidden Technique Unlocked:** Vajra Body Rebirth – Fully restore HP once per battle when below 20%!")
                        rewards.append("📖 You can now teach this technique once per day. Use `!teach @user Vajra Guard Mantra`")
                        await update_user_stat(self.bot.db, user_id, "hidden_tech_vajra", 1)

        return "\n".join(rewards)

    # ==========================================
    # RANDOM CHOICE EVENT (IMPROVED)
    # ==========================================
    class ChoiceEventView(discord.ui.View):
        def __init__(self, ctx, event_data):
            # Increased timeout to 90 seconds (Issue #6)
            super().__init__(timeout=90)
            self.ctx = ctx
            self.event_data = event_data
            self.choices = event_data["choices"]

            # Dynamically create buttons with meaningful labels (Issues #7 & #8)
            for key, choice in self.choices.items():
                button = discord.ui.Button(
                    label=choice["text"],
                    style=discord.ButtonStyle.primary if key == "A" else discord.ButtonStyle.secondary,
                    custom_id=key
                )
                button.callback = self.make_callback(key)
                self.add_item(button)

        def make_callback(self, key):
            async def callback(interaction: discord.Interaction):
                if interaction.user.id != self.ctx.author.id:
                    return await interaction.response.send_message("❌ This event is not for you.", ephemeral=True)
                result = self.choices[key]["result"]
                # Send result as an embed (Issue #4)
                embed = discord.Embed(
                    title="✨ Event Outcome",
                    description=result,
                    color=format_embed_color("gold")
                )
                await interaction.response.edit_message(embed=embed, view=None)
                self.stop()
            return callback

    async def _maybe_choice_event(self, ctx):
        """5% chance to trigger a random choice event (Issue #1 - reduced from 10%)."""
        if random.random() > 0.05:  # Changed from 0.1 to 0.05
            return None

        events = [
            {
                "title": "🏮 A Wandering Master",
                "description": "An old, bearded master observes your training. He offers you a choice:",
                "choices": {
                    "A": {"text": "Ask for guidance", "result": "The master shares a breathing technique. You gain +20 Ki."},
                    "B": {"text": "Challenge him", "result": "He defeats you effortlessly but respects your courage. You gain +5 Combat Mastery."}
                }
            },
            {
                "title": "📜 Ancient Scroll",
                "description": "You find a torn scroll under a rock. Do you read it or burn it?",
                "choices": {
                    "A": {"text": "Read it", "result": "The scroll contains forbidden knowledge. You lose 10 Vitality but gain +15 Mastery."},
                    "B": {"text": "Burn it", "result": "The ashes swirl around you. You gain +10 Ki and +5 Vitality."}
                }
            },
            {
                "title": "🐺 Wounded Beast",
                "description": "A wounded spirit wolf limps toward you. What do you do?",
                "choices": {
                    "A": {"text": "Heal it", "result": "The wolf becomes your companion for the day. You gain +20 Taels from hunting."},
                    "B": {"text": "Fight it", "result": "You defeat it easily. You gain +10 Combat Mastery and +30 Taels."}
                }
            }
        ]
        return random.choice(events)

    # ==========================================
    # HYBRID COMMAND: WORK
    # ==========================================
    @commands.hybrid_command(name="work", description="Perform labor within the Murim world for Taels.")
    @app_commands.checks.cooldown(1, 5.0)
    async def work(self, ctx):
        print(f"[DEBUG] actions.work: Called by {ctx.author.id}")

        if not await self._actions_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id

        async with self.bot.db.execute(
            "SELECT vitality, taels, rank, background, mastery, active_tech FROM users WHERE user_id=?",
            (user_id,)
        ) as cursor:
            user = await cursor.fetchone()

        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        vit, taels, rank, bg, mastery, tech = user
        max_stats = get_max_stats(rank)
        max_vit = max_stats["max_vit"]

        vit_cost = await get_bot_setting(self.bot.db, "actions_vit_cost_work", 10)

        if vit < vit_cost:
            return await ctx.send(config.MSG_NO_VITALITY.format(required=vit_cost), ephemeral=True)

        daily_bonus, _ = await self._check_daily_bonus(user_id, "work")
        multiplier = 2 if daily_bonus else 1

        base_gain = random.randint(5, 15)
        if "Third-Rate" in rank:
            base_gain += 5
        elif "Second-Rate" in rank:
            base_gain += 10

        final_taels_gain = base_gain * multiplier
        new_vit = vit - vit_cost
        new_taels = taels + final_taels_gain

        mastery_gain = 0
        new_mastery = mastery
        mastery_msg = ""
        if bg == "Laborer" and tech != "None" and mastery < 100:
            if random.random() <= 0.10:
                mastery_gain = 0.5
                new_mastery = min(100.0, mastery + mastery_gain)
                mastery_msg = f"\n✨ **Laborer's Insight:** +{mastery_gain}% Mastery in **{tech}**"

        # Track changes for event display
        ki_before = await get_user_stat(self.bot.db, user_id, "ki") or 0
        hp_before = await get_user_stat(self.bot.db, user_id, "hp") or 0
        vit_before = new_vit

        # Random choice event
        choice_event = await self._maybe_choice_event(ctx)
        if choice_event:
            embed = discord.Embed(title=choice_event["title"], description=choice_event["description"], color=format_embed_color("gold"))
            view = self.ChoiceEventView(ctx, choice_event)
            await ctx.send(embed=embed, view=view)
            return

        # Random normal event
        event_text, event_effects = roll_random_event()
        event_changes = []
        if "ki" in event_effects:
            new_ki = min(max_stats["ki_cap"], ki_before + event_effects["ki"])
            await update_user_stat(self.bot.db, user_id, "ki", new_ki)
            event_changes.append(f"✨ {event_effects['ki']:+} Ki")
        if "taels" in event_effects:
            new_taels += event_effects["taels"]
            event_changes.append(f"💰 {event_effects['taels']:+} Taels")
        if "vit" in event_effects:
            new_vit = max(0, new_vit + event_effects["vit"])
            event_changes.append(f"❤️ {event_effects['vit']:+} Vitality")
        if "hp" in event_effects:
            new_hp = min(max_stats["max_hp"], hp_before + event_effects["hp"])
            await update_user_stat(self.bot.db, user_id, "hp", new_hp)
            event_changes.append(f"🩸 {event_effects['hp']:+} HP")
        if "mastery" in event_effects:
            new_mastery = min(100.0, new_mastery + event_effects["mastery"])
            event_changes.append(f"📖 {event_effects['mastery']:+}% Mastery")
        if "combat_mastery" in event_effects:
            new_cm = (await get_user_stat(self.bot.db, user_id, "combat_mastery") or 0) + event_effects["combat_mastery"]
            await update_user_stat(self.bot.db, user_id, "combat_mastery", new_cm)
            event_changes.append(f"⚔️ {event_effects['combat_mastery']:+} Combat Mastery")

        await self.bot.db.execute(
            "UPDATE users SET vitality=?, taels=?, mastery=? WHERE user_id=?",
            (new_vit, new_taels, new_mastery, user_id)
        )
        await self.bot.db.commit()

        # Update stage based on new Ki (Issue #5)
        new_ki = await get_user_stat(self.bot.db, user_id, "ki") or 0
        await self._update_stage(user_id, rank, new_ki)

        milestone_msg = await self._process_mastery_milestones(ctx, user_id, tech, mastery, new_mastery)

        embed = discord.Embed(
            title="⚒️ Murim Labor",
            color=format_embed_color("main"),
            description=random.choice(self.work_flavors)
        )

        if mastery_msg:
            embed.description += mastery_msg
        if event_text:
            embed.description += f"\n\n🌿 {event_text}"
            if event_changes:
                embed.description += f"\n*{', '.join(event_changes)}*"
        if milestone_msg:
            embed.description += f"\n\n🏆 **Milestone Reached!**\n{milestone_msg}"

        bonus_text = " **(Daily Bonus Active!)**" if daily_bonus else ""
        embed.add_field(name="Earned", value=f"💰 **+{final_taels_gain}** Taels{bonus_text}", inline=True)
        embed.add_field(name="Vitality", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
        if mastery_gain > 0:
            embed.add_field(name="Mastery", value=f"📖 **+{mastery_gain}%** (Total: {new_mastery:.1f}%)", inline=True)

        embed.set_footer(text=f"Current Wealth: {new_taels} Taels")
        await ctx.send(embed=embed)

    # ==========================================
    # HYBRID COMMAND: OBSERVE
    # ==========================================
    @commands.hybrid_command(name="observe", description="Observe the world and refine your Ki.")
    @app_commands.checks.cooldown(1, 5.0)
    async def observe(self, ctx):
        print(f"[DEBUG] actions.observe: Called by {ctx.author.id}")

        if not await self._actions_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id

        async with self.bot.db.execute(
            "SELECT vitality, ki, rank, mastery, active_tech FROM users WHERE user_id=?",
            (user_id,)
        ) as cursor:
            user = await cursor.fetchone()

        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        vit, ki, rank, mastery, tech = user
        max_stats = get_max_stats(rank)
        max_vit = max_stats["max_vit"]
        ki_cap = max_stats["ki_cap"]

        vit_cost = await get_bot_setting(self.bot.db, "actions_vit_cost_observe", 10)

        if vit < vit_cost:
            return await ctx.send(config.MSG_NO_VITALITY.format(required=vit_cost), ephemeral=True)

        daily_bonus, _ = await self._check_daily_bonus(user_id, "observe")
        multiplier = 2 if daily_bonus else 1

        ki_gain = random.randint(3, 8)
        if "Third-Rate" in rank:
            ki_gain += 2
        elif "Second-Rate" in rank:
            ki_gain += 4
        ki_gain = ki_gain * multiplier

        new_vit = vit - vit_cost
        new_ki = min(ki_cap, ki + ki_gain)

        mastery_gain = 0
        new_mastery = mastery
        mastery_msg = ""
        if tech != "None" and mastery < 100:
            mastery_gain = round(random.uniform(0.5, 1.5), 2)
            new_mastery = min(100.0, mastery + mastery_gain)
            mastery_msg = f"\n📖 **Martial Insight:** +{mastery_gain}% Mastery in **{tech}**"

        # Track changes for event display
        hp_before = await get_user_stat(self.bot.db, user_id, "hp") or 0
        vit_before = new_vit

        choice_event = await self._maybe_choice_event(ctx)
        if choice_event:
            embed = discord.Embed(title=choice_event["title"], description=choice_event["description"], color=format_embed_color("gold"))
            view = self.ChoiceEventView(ctx, choice_event)
            await ctx.send(embed=embed, view=view)
            return

        event_text, event_effects = roll_random_event()
        event_changes = []
        if "ki" in event_effects:
            new_ki = min(ki_cap, new_ki + event_effects["ki"])
            event_changes.append(f"✨ {event_effects['ki']:+} Ki")
        if "vit" in event_effects:
            new_vit = max(0, new_vit + event_effects["vit"])
            event_changes.append(f"❤️ {event_effects['vit']:+} Vitality")
        if "hp" in event_effects:
            new_hp = min(max_stats["max_hp"], hp_before + event_effects["hp"])
            await update_user_stat(self.bot.db, user_id, "hp", new_hp)
            event_changes.append(f"🩸 {event_effects['hp']:+} HP")
        if "mastery" in event_effects:
            new_mastery = min(100.0, new_mastery + event_effects["mastery"])
            event_changes.append(f"📖 {event_effects['mastery']:+}% Mastery")

        await self.bot.db.execute(
            "UPDATE users SET vitality=?, ki=?, mastery=? WHERE user_id=?",
            (new_vit, new_ki, new_mastery, user_id)
        )
        await self.bot.db.commit()

        # Update stage based on new Ki (Issue #5)
        await self._update_stage(user_id, rank, new_ki)

        milestone_msg = await self._process_mastery_milestones(ctx, user_id, tech, mastery, new_mastery)

        embed = discord.Embed(
            title="👁️ Observation",
            color=format_embed_color("teal"),
            description=random.choice(self.observe_flavors)
        )

        if mastery_msg:
            embed.description += mastery_msg
        if event_text:
            embed.description += f"\n\n🌿 {event_text}"
            if event_changes:
                embed.description += f"\n*{', '.join(event_changes)}*"
        if milestone_msg:
            embed.description += f"\n\n🏆 **Milestone Reached!**\n{milestone_msg}"

        bonus_text = " **(Daily Bonus Active!)**" if daily_bonus else ""
        embed.add_field(name="Ki Refined", value=f"✨ **+{ki_gain}** Ki{bonus_text}", inline=True)
        embed.add_field(name="Vitality", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
        if mastery_gain > 0:
            embed.add_field(name="Mastery", value=f"📖 **+{mastery_gain}%** (Total: {new_mastery:.1f}%)", inline=True)

        embed.set_footer(text=f"Current Ki: {new_ki}/{ki_cap}")
        await ctx.send(embed=embed)

    # ==========================================
    # HYBRID COMMAND: COMPREHEND
    # ==========================================
    @commands.hybrid_command(name="comprehend", description="Deeply study your martial technique.")
    async def comprehend(self, ctx):
        print(f"[DEBUG] actions.comprehend: Called by {ctx.author.id}")

        if not await self._actions_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id

        async with self.bot.db.execute(
            "SELECT vitality, active_tech, mastery, rank FROM users WHERE user_id=?",
            (user_id,)
        ) as cursor:
            user = await cursor.fetchone()

        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        vit, tech, mastery, rank = user
        max_stats = get_max_stats(rank)
        max_vit = max_stats["max_vit"]

        vit_cost = await get_bot_setting(self.bot.db, "actions_vit_cost_comprehend", 40)

        # Check technique FIRST, before any cooldown (Issue #2)
        if tech == "None":
            return await ctx.send("❌ You possess no martial technique to comprehend.", ephemeral=True)

        # Cooldown check (30 minutes) – moved here so it only applies if user has a technique
        # Using manual cooldown check instead of decorator for better control
        cooldown_key = f"comprehend_{user_id}"
        if hasattr(self.bot, 'command_cooldowns'):
            last_used = self.bot.command_cooldowns.get(cooldown_key)
            if last_used:
                elapsed = (datetime.datetime.now() - last_used).total_seconds()
                if elapsed < 1800:  # 30 minutes
                    remaining = int(1800 - elapsed)
                    await ctx.send(f"⏳ You need to wait **{remaining} seconds** before using comprehend again.", ephemeral=True)
                    return
        else:
            self.bot.command_cooldowns = {}

        if vit < vit_cost:
            return await ctx.send(config.MSG_NO_VITALITY.format(required=vit_cost), ephemeral=True)

        if mastery >= 100:
            return await ctx.send("🧠 Your understanding has already reached its peak.", ephemeral=True)

        gain = round(random.uniform(5.0, 10.0), 2)
        new_vit = vit - vit_cost
        new_mastery = min(100.0, mastery + gain)
        actual_gain = round(new_mastery - mastery, 2)

        # Store cooldown
        self.bot.command_cooldowns[cooldown_key] = datetime.datetime.now()

        choice_event = await self._maybe_choice_event(ctx)
        if choice_event:
            embed = discord.Embed(title=choice_event["title"], description=choice_event["description"], color=format_embed_color("gold"))
            view = self.ChoiceEventView(ctx, choice_event)
            await ctx.send(embed=embed, view=view)
            return

        event_text, event_effects = roll_random_event()
        event_changes = []
        if "vit" in event_effects:
            new_vit = max(0, new_vit + event_effects["vit"])
            event_changes.append(f"❤️ {event_effects['vit']:+} Vitality")

        await self.bot.db.execute(
            "UPDATE users SET vitality=?, mastery=? WHERE user_id=?",
            (new_vit, new_mastery, user_id)
        )
        await self.bot.db.commit()

        milestone_msg = await self._process_mastery_milestones(ctx, user_id, tech, mastery, new_mastery)

        embed = discord.Embed(
            title="🧠 Martial Comprehension",
            color=format_embed_color("gold")
        )
        embed.description = (
            f"You isolated yourself from worldly distractions and focused entirely "
            f"on the principles of **{tech}**.\n\n"
            f"Fragments of understanding slowly surfaced within your mind."
        )

        if event_text:
            embed.description += f"\n\n🌿 {event_text}"
            if event_changes:
                embed.description += f"\n*{', '.join(event_changes)}*"
        if milestone_msg:
            embed.description += f"\n\n🏆 **Milestone Reached!**\n{milestone_msg}"

        embed.add_field(name="Mastery Gained", value=f"📖 **+{actual_gain}%**", inline=True)
        embed.add_field(name="Total Mastery", value=f"📊 **{new_mastery:.1f}%** / 100%", inline=True)
        embed.set_footer(text=f"Vitality Remaining: {new_vit}/{max_vit}")

        await ctx.send(embed=embed)

    # ==========================================
    # COOLDOWN ERROR HANDLER (for work and observe only)
    # ==========================================
    @work.error
    @observe.error
    async def action_error(self, ctx, error):
        if isinstance(error, (commands.CommandOnCooldown, app_commands.CommandOnCooldown)):
            await ctx.send(
                f"⏳ **Steady your breathing.** "
                f"Wait {error.retry_after:.1f}s before acting again.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Actions(bot))
    print("[DEBUG] actions.py: Setup complete")