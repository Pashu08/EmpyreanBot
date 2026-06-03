"""
commands/actions.py - Command logic for Actions cog
Contains all command implementations (work, observe, comprehend).
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
from backend.helpers import get_max_stats, roll_random_event, calculate_stage_from_ki
from backend.db import get_bot_setting, get_user_stat, update_user_stat, is_user_banned, set_user_cooldown, get_user_cooldown
from backend.cultivation_helpers import get_minor_realm_from_ki, get_next_minor_realm, get_ki_required_for_minor_realm
from backend.actions_data import (
    WORK_VIT_COST,
    WORK_BASE_GAIN_MIN,
    WORK_BASE_GAIN_MAX,
    WORK_RANK_BONUS,
    OBSERVE_VIT_COST,
    OBSERVE_BASE_KI_MIN,
    OBSERVE_BASE_KI_MAX,
    OBSERVE_RANK_BONUS,
    COMPREHEND_VIT_COST,
    COMPREHEND_COOLDOWN_SECONDS,
    COMPREHEND_GAIN_MIN,
    COMPREHEND_GAIN_MAX,
    LABORER_MASTERY_CHANCE,
    LABORER_MASTERY_GAIN,
    MARTIAL_INSIGHT_MIN,
    MARTIAL_INSIGHT_MAX,
    CHOICE_EVENT_CHANCE,
    RANDOM_EVENT_CHANCE
)
from embeds.actions_embeds import (
    WORK_FLAVORS,
    OBSERVE_FLAVORS,
    work_embed,
    observe_embed,
    comprehend_embed,
    choice_event_embed,
    event_outcome_embed,
    cooldown_embed
)
import config

print("[DEBUG] commands/actions.py: Loading Actions commands...")

# ==========================================
# HELPER: Check if user is admin (for debug bypass)
# ==========================================
async def is_admin(bot, user_id: int) -> bool:
    """Check if user has admin permissions."""
    from backend.constants import PERMANENT_GOD
    from backend.permissions import has_permission
    
    if user_id == PERMANENT_GOD:
        return True
    if await has_permission(bot, user_id, "system"):
        return True
    return False

class ChoiceEventView(discord.ui.View):
    """View for choice-based random events with actual stat changes."""

    def __init__(self, ctx, event_data, user_id, user_data):
        super().__init__(timeout=90)
        self.ctx = ctx
        self.event_data = event_data
        self.user_id = user_id
        self.user_data = user_data
        self.choices = event_data["choices"]

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
                return await interaction.response.send_message(
                    "❌ This event is not for you.", 
                    ephemeral=True
                )
            
            choice = self.choices[key]
            result_text = choice["result"]
            
            # Apply actual stat changes based on choice
            db = self.ctx.bot.db
            user_id = self.user_id
            
            if "+20 Ki" in result_text:
                current_ki = self.user_data.get("ki", 0)
                max_ki = get_max_stats(self.user_data.get("rank", "The Bound (Mortal)"))["ki_cap"]
                new_ki = min(max_ki, current_ki + 20)
                await update_user_stat(db, user_id, "ki", new_ki)
            elif "+5 Combat Mastery" in result_text:
                current_cm = self.user_data.get("combat_mastery", 0)
                await update_user_stat(db, user_id, "combat_mastery", current_cm + 5)
            elif "-10 Vitality" in result_text:
                current_vit = self.user_data.get("vitality", 0)
                new_vit = max(0, current_vit - 10)
                await update_user_stat(db, user_id, "vitality", new_vit)
            elif "+15 Mastery" in result_text:
                current_mastery = self.user_data.get("mastery", 0.0)
                new_mastery = min(100.0, current_mastery + 15)
                await update_user_stat(db, user_id, "mastery", new_mastery)
            elif "+10 Ki" in result_text:
                current_ki = self.user_data.get("ki", 0)
                max_ki = get_max_stats(self.user_data.get("rank", "The Bound (Mortal)"))["ki_cap"]
                new_ki = min(max_ki, current_ki + 10)
                await update_user_stat(db, user_id, "ki", new_ki)
            elif "+5 Vitality" in result_text:
                current_vit = self.user_data.get("vitality", 0)
                max_vit = get_max_stats(self.user_data.get("rank", "The Bound (Mortal)"))["max_vit"]
                new_vit = min(max_vit, current_vit + 5)
                await update_user_stat(db, user_id, "vitality", new_vit)
            elif "+20 Taels" in result_text:
                current_taels = self.user_data.get("taels", 0)
                await update_user_stat(db, user_id, "taels", current_taels + 20)
            elif "+30 Taels" in result_text:
                current_taels = self.user_data.get("taels", 0)
                await update_user_stat(db, user_id, "taels", current_taels + 30)
            elif "+10 Combat Mastery" in result_text:
                current_cm = self.user_data.get("combat_mastery", 0)
                await update_user_stat(db, user_id, "combat_mastery", current_cm + 10)
            
            embed = event_outcome_embed(result_text)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        return callback

class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Actions cog initialized")

    # ==========================================
    # HELPER: Check feature toggle
    # ==========================================
    async def _actions_enabled(self, ctx):
        enabled = await get_bot_setting(self.bot.db, "toggle_actions", True)
        if not enabled:
            await ctx.send(
                config.MSG_FEATURE_DISABLED.format(feature="Actions"), 
                ephemeral=True
            )
        return enabled

    # ==========================================
    # HELPER: Check if command is toggled off
    # ==========================================
    async def _is_command_enabled(self, ctx, command_name: str) -> bool:
        """Check if specific command is enabled via !toggle_cmd."""
        enabled = await get_bot_setting(self.bot.db, f"cmd_{command_name}", True)
        if not enabled:
            await ctx.send(f"❌ Command `{command_name}` is currently disabled by an administrator.", ephemeral=True)
        return enabled

    # ==========================================
    # HELPER: Check maintenance mode
    # ==========================================
    async def _check_maintenance(self, ctx) -> bool:
        """Check if bot is in maintenance mode."""
        maintenance = await get_bot_setting(self.bot.db, "maintenance_mode", False)
        if maintenance:
            is_admin_user = await is_admin(self.bot, ctx.author.id)
            if not is_admin_user:
                await ctx.send("🔧 Bot is under maintenance. Please try again later.", ephemeral=True)
                return True
        return False

    # ==========================================
    # HELPER: Debug log
    # ==========================================
    async def _debug_log(self, ctx, message: str):
        """Log debug info if debug mode is enabled."""
        debug_mode = await get_bot_setting(self.bot.db, "debug_mode", False)
        if debug_mode:
            print(f"[DEBUG] {ctx.command.name if ctx.command else 'Unknown'}: {message}")

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
    # HELPER: Check if Ki gain is blocked by minor realm cap
    # ==========================================
    async def _is_ki_gain_blocked(self, user_id, rank, current_ki, max_ki, minor_realm):
        current_minor = minor_realm
        if current_minor == "Peak":
            return False, None, 0
        next_minor = get_next_minor_realm(current_minor)
        if not next_minor:
            return False, None, 0
        required_ki = get_ki_required_for_minor_realm(next_minor, max_ki)
        if current_ki >= required_ki:
            return True, next_minor, required_ki
        return False, None, 0

    # ==========================================
    # HELPER: Process mastery milestone rewards
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
    # HELPER: Random choice event
    # ==========================================
    async def _maybe_choice_event(self, ctx, user_id, user_data):
        if random.random() > CHOICE_EVENT_CHANCE:
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
    # COMMAND: WORK
    # ==========================================
    @commands.hybrid_command(name="work", description="Perform labor within the Murim world for Taels.")
    @app_commands.checks.cooldown(1, 5.0)
    async def work(self, ctx):
        print(f"[DEBUG] actions.work: Called by {ctx.author.id}")

        if not await self._is_command_enabled(ctx, "work"):
            return
        if await self._check_maintenance(ctx):
            return
        if not await self._actions_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        await self._debug_log(ctx, "Starting work command")

        user_id = ctx.author.id
        db = self.bot.db

        user = await db.fetch_user(user_id)
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        vit = user.get("vitality", 0)
        taels = user.get("taels", 0)
        rank = user.get("rank", "The Bound (Mortal)")
        bg = user.get("background", "")
        mastery = user.get("mastery", 0.0)
        tech = user.get("active_tech", "None")
        minor_realm = user.get("minor_realm", "Initial")

        max_stats = get_max_stats(rank)
        max_vit = max_stats["max_vit"]
        max_ki = max_stats["ki_cap"]

        if vit < WORK_VIT_COST:
            return await ctx.send(config.MSG_NO_VITALITY.format(required=WORK_VIT_COST), ephemeral=True)

        daily_bonus, _ = await self._check_daily_bonus(user_id, "work")
        multiplier = 2 if daily_bonus else 1

        base_gain = random.randint(WORK_BASE_GAIN_MIN, WORK_BASE_GAIN_MAX)
        for rank_name, bonus in WORK_RANK_BONUS.items():
            if rank_name in rank:
                base_gain += bonus
                break

        final_taels_gain = base_gain * multiplier
        new_vit = vit - WORK_VIT_COST
        new_taels = taels + final_taels_gain

        mastery_gain = 0
        new_mastery = mastery
        mastery_msg = ""
        if bg == "Laborer" and tech != "None" and mastery < 100:
            if random.random() <= LABORER_MASTERY_CHANCE:
                mastery_gain = LABORER_MASTERY_GAIN
                new_mastery = min(100.0, mastery + mastery_gain)
                mastery_msg = f"\n✨ **Laborer's Insight:** +{mastery_gain}% Mastery in **{tech}**"

        ki_before = user.get("ki", 0)
        hp_before = user.get("hp", 0)

        choice_event = await self._maybe_choice_event(ctx, user_id, user)
        if choice_event:
            embed = choice_event_embed(choice_event["title"], choice_event["description"])
            view = ChoiceEventView(ctx, choice_event, user_id, user)
            await ctx.send(embed=embed, view=view)
            return

        event_text = None
        event_effects = {}
        event_changes = []
        if random.random() <= RANDOM_EVENT_CHANCE:
            event_text, event_effects = roll_random_event()
            update_data = {}
            if "ki" in event_effects:
                new_ki = min(max_ki, ki_before + event_effects["ki"])
                update_data["ki"] = new_ki
                event_changes.append(f"✨ {event_effects['ki']:+} Ki")
            if "taels" in event_effects:
                new_taels += event_effects["taels"]
                event_changes.append(f"💰 {event_effects['taels']:+} Taels")
            if "vit" in event_effects:
                new_vit = max(0, new_vit + event_effects["vit"])
                event_changes.append(f"❤️ {event_effects['vit']:+} Vitality")
            if "hp" in event_effects:
                new_hp = min(max_stats["max_hp"], hp_before + event_effects["hp"])
                update_data["hp"] = new_hp
                event_changes.append(f"🩸 {event_effects['hp']:+} HP")
            if "mastery" in event_effects:
                new_mastery = min(100.0, new_mastery + event_effects["mastery"])
                event_changes.append(f"📖 {event_effects['mastery']:+}% Mastery")
            if "combat_mastery" in event_effects:
                new_cm = user.get("combat_mastery", 0) + event_effects["combat_mastery"]
                update_data["combat_mastery"] = new_cm
                event_changes.append(f"⚔️ {event_effects['combat_mastery']:+} Combat Mastery")

            if update_data:
                await db.update_user(user_id, update_data)

        await db.update_user(user_id, {
            "vitality": new_vit,
            "taels": new_taels,
            "mastery": new_mastery
        })

        new_ki = await get_user_stat(self.bot.db, user_id, "ki") or 0
        await self._update_stage(user_id, rank, new_ki)

        milestone_msg = await self._process_mastery_milestones(ctx, user_id, tech, mastery, new_mastery)

        embed = work_embed(
            flavor_text=random.choice(WORK_FLAVORS),
            mastery_msg=mastery_msg,
            event_text=event_text,
            event_changes=event_changes,
            milestone_msg=milestone_msg,
            final_taels_gain=final_taels_gain,
            new_vit=new_vit,
            max_vit=max_vit,
            mastery_gain=mastery_gain,
            new_mastery=new_mastery,
            daily_bonus=daily_bonus,
            new_taels=new_taels
        )
        await ctx.send(embed=embed)

    # ==========================================
    # COMMAND: OBSERVE
    # ==========================================
    @commands.hybrid_command(name="observe", description="Observe the world and refine your Ki.")
    @app_commands.checks.cooldown(1, 5.0)
    async def observe(self, ctx):
        print(f"[DEBUG] actions.observe: Called by {ctx.author.id}")

        if not await self._is_command_enabled(ctx, "observe"):
            return
        if await self._check_maintenance(ctx):
            return
        if not await self._actions_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        await self._debug_log(ctx, "Starting observe command")

        user_id = ctx.author.id
        db = self.bot.db

        user = await db.fetch_user(user_id)
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        vit = user.get("vitality", 0)
        ki = user.get("ki", 0)
        rank = user.get("rank", "The Bound (Mortal)")
        mastery = user.get("mastery", 0.0)
        tech = user.get("active_tech", "None")
        minor_realm = user.get("minor_realm", "Initial")

        max_stats = get_max_stats(rank)
        max_vit = max_stats["max_vit"]
        max_ki = max_stats["ki_cap"]

        if vit < OBSERVE_VIT_COST:
            return await ctx.send(config.MSG_NO_VITALITY.format(required=OBSERVE_VIT_COST), ephemeral=True)

        # Ki cap check for minor realms
        blocked, next_realm, required_ki = await self._is_ki_gain_blocked(user_id, rank, ki, max_ki, minor_realm)
        if blocked:
            return await ctx.send(
                f"❌ Your Ki has reached the threshold for **{next_realm}** realm.\n"
                f"Use `!breakthrough` to advance before gaining more Ki.\n"
                f"(Current Ki: {ki} / Required: {required_ki})",
                ephemeral=True
            )

        daily_bonus, _ = await self._check_daily_bonus(user_id, "observe")
        multiplier = 2 if daily_bonus else 1

        ki_gain = random.randint(OBSERVE_BASE_KI_MIN, OBSERVE_BASE_KI_MAX)
        for rank_name, bonus in OBSERVE_RANK_BONUS.items():
            if rank_name in rank:
                ki_gain += bonus
                break
        ki_gain = ki_gain * multiplier

        new_vit = vit - OBSERVE_VIT_COST
        new_ki = min(max_ki, ki + ki_gain)

        mastery_gain = 0
        new_mastery = mastery
        mastery_msg = ""
        if tech != "None" and mastery < 100:
            mastery_gain = round(random.uniform(MARTIAL_INSIGHT_MIN, MARTIAL_INSIGHT_MAX), 2)
            new_mastery = min(100.0, mastery + mastery_gain)
            mastery_msg = f"\n📖 **Martial Insight:** +{mastery_gain}% Mastery in **{tech}**"

        hp_before = user.get("hp", 0)

        choice_event = await self._maybe_choice_event(ctx, user_id, user)
        if choice_event:
            embed = choice_event_embed(choice_event["title"], choice_event["description"])
            view = ChoiceEventView(ctx, choice_event, user_id, user)
            await ctx.send(embed=embed, view=view)
            return

        event_text = None
        event_effects = {}
        event_changes = []
        if random.random() <= RANDOM_EVENT_CHANCE:
            event_text, event_effects = roll_random_event()
            if "ki" in event_effects:
                new_ki = min(max_ki, new_ki + event_effects["ki"])
                event_changes.append(f"✨ {event_effects['ki']:+} Ki")
            if "vit" in event_effects:
                new_vit = max(0, new_vit + event_effects["vit"])
                event_changes.append(f"❤️ {event_effects['vit']:+} Vitality")
            if "hp" in event_effects:
                new_hp = min(max_stats["max_hp"], hp_before + event_effects["hp"])
                await db.update_user(user_id, {"hp": new_hp})
                event_changes.append(f"🩸 {event_effects['hp']:+} HP")
            if "mastery" in event_effects:
                new_mastery = min(100.0, new_mastery + event_effects["mastery"])
                event_changes.append(f"📖 {event_effects['mastery']:+}% Mastery")

        await db.update_user(user_id, {
            "vitality": new_vit,
            "ki": new_ki,
            "mastery": new_mastery
        })

        await self._update_stage(user_id, rank, new_ki)

        milestone_msg = await self._process_mastery_milestones(ctx, user_id, tech, mastery, new_mastery)

        embed = observe_embed(
            flavor_text=random.choice(OBSERVE_FLAVORS),
            mastery_msg=mastery_msg,
            event_text=event_text,
            event_changes=event_changes,
            milestone_msg=milestone_msg,
            ki_gain=ki_gain,
            new_vit=new_vit,
            max_vit=max_vit,
            mastery_gain=mastery_gain,
            new_mastery=new_mastery,
            daily_bonus=daily_bonus,
            new_ki=new_ki,
            ki_cap=max_ki
        )
        await ctx.send(embed=embed)

    # ==========================================
    # COMMAND: COMPREHEND
    # ==========================================
    @commands.hybrid_command(name="comprehend", description="Deeply study your martial technique.")
    async def comprehend(self, ctx):
        print(f"[DEBUG] actions.comprehend: Called by {ctx.author.id}")

        if not await self._is_command_enabled(ctx, "comprehend"):
            return
        if await self._check_maintenance(ctx):
            return
        if not await self._actions_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        await self._debug_log(ctx, "Starting comprehend command")

        user_id = ctx.author.id
        db = self.bot.db

        user = await db.fetch_user(user_id)
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        vit = user.get("vitality", 0)
        tech = user.get("active_tech", "None")
        mastery = user.get("mastery", 0.0)
        rank = user.get("rank", "The Bound (Mortal)")

        max_stats = get_max_stats(rank)
        max_vit = max_stats["max_vit"]

        if tech == "None":
            return await ctx.send("❌ You possess no martial technique to comprehend.", ephemeral=True)

        # Database-backed cooldown
        cooldown_key = f"comprehend_{user_id}"
        cooldown_seconds = await get_bot_setting(self.bot.db, "cooldown_comprehend", COMPREHEND_COOLDOWN_SECONDS)
        
        last_used = await get_user_cooldown(self.bot.db, cooldown_key)
        if last_used:
            elapsed = (datetime.datetime.now() - last_used).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                await self._debug_log(ctx, f"Comprehend on cooldown: {remaining}s remaining")
                await ctx.send(embed=cooldown_embed(remaining), ephemeral=True)
                return

        if vit < COMPREHEND_VIT_COST:
            return await ctx.send(config.MSG_NO_VITALITY.format(required=COMPREHEND_VIT_COST), ephemeral=True)

        if mastery >= 100:
            return await ctx.send("🧠 Your understanding has already reached its peak.", ephemeral=True)

        gain = round(random.uniform(COMPREHEND_GAIN_MIN, COMPREHEND_GAIN_MAX), 2)
        new_vit = vit - COMPREHEND_VIT_COST
        new_mastery = min(100.0, mastery + gain)
        actual_gain = round(new_mastery - mastery, 2)

        await set_user_cooldown(db, cooldown_key)

        await self._debug_log(ctx, f"Gained {actual_gain}% mastery, new mastery: {new_mastery}%")

        choice_event = await self._maybe_choice_event(ctx, user_id, user)
        if choice_event:
            embed = choice_event_embed(choice_event["title"], choice_event["description"])
            view = ChoiceEventView(ctx, choice_event, user_id, user)
            await ctx.send(embed=embed, view=view)
            return

        event_text = None
        event_effects = {}
        event_changes = []
        if random.random() <= RANDOM_EVENT_CHANCE:
            event_text, event_effects = roll_random_event()
            if "vit" in event_effects:
                new_vit = max(0, new_vit + event_effects["vit"])
                event_changes.append(f"❤️ {event_effects['vit']:+} Vitality")

        await db.update_user(user_id, {
            "vitality": new_vit,
            "mastery": new_mastery
        })

        milestone_msg = await self._process_mastery_milestones(ctx, user_id, tech, mastery, new_mastery)

        embed = comprehend_embed(
            tech_name=tech,
            event_text=event_text,
            event_changes=event_changes,
            milestone_msg=milestone_msg,
            actual_gain=actual_gain,
            new_mastery=new_mastery,
            new_vit=new_vit,
            max_vit=max_vit
        )
        await ctx.send(embed=embed)

    # ==========================================
    # COOLDOWN ERROR HANDLER
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
    print("[DEBUG] commands/actions.py: Setup complete")
