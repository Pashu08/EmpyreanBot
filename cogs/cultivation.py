import discord
from discord.ext import commands
import random
import asyncio
import datetime
from utils.helpers import get_max_stats, format_embed_color, get_next_rank
from utils.db import get_bot_setting, is_user_banned, get_user_stat, update_user_stat, update_item_name, add_item, has_item, remove_item, get_user_cooldown
from utils.constants import RANKS, ITEM_MUTATIONS
import config

print("[DEBUG] cultivation.py: Loading Cultivation cog...")

MINOR_BREAKTHROUGH_CHANCES = {
    "The Bound (Mortal)": {"Early": 90, "Middle": 75, "Late": 60, "Peak": 45},
    "Third-Rate Warrior": {"Early": 85, "Middle": 70, "Late": 55, "Peak": 40},
    "Second-Rate Warrior": {"Early": 80, "Middle": 65, "Late": 50, "Peak": 35},
    "First-Rate Warrior": {"Early": 75, "Middle": 60, "Late": 45, "Peak": 30},
    "Peak Master": {"Early": 70, "Middle": 55, "Late": 40, "Peak": 25},
}

MAJOR_BREAKTHROUGH_CHANCES = {
    "The Bound (Mortal)": 30,
    "Third-Rate Warrior": 25,
    "Second-Rate Warrior": 20,
    "First-Rate Warrior": 15,
}

MINOR_REALMS = ["Initial", "Early", "Middle", "Late", "Peak"]
MINOR_REALM_INDEX = {realm: i for i, realm in enumerate(MINOR_REALMS)}

MINOR_REALM_BONUSES = {
    "Early": {"ki_gain": 2, "tech_damage": 0, "major_bt_chance": 0},
    "Middle": {"ki_gain": 4, "tech_damage": 2, "major_bt_chance": 0},
    "Late": {"ki_gain": 7, "tech_damage": 4, "major_bt_chance": 0},
    "Peak": {"ki_gain": 10, "tech_damage": 6, "major_bt_chance": 5},
}

FAILURE_PENALTIES = {
    "Early": {"ki_percent": 10, "taels": 0},
    "Middle": {"ki_percent": 15, "taels": 20},
    "Late": {"ki_percent": 20, "taels": 30},
    "Peak": {"ki_percent": 25, "taels": 50},
}
MAJOR_FAILURE_PENALTY = {"ki_percent": 30, "taels": 100, "meridian_minutes": 15}

MINOR_COOLDOWN_MINUTES = 10
MAJOR_COOLDOWN_MINUTES = 30

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
                "text": "🌀 Stage 1: The Gathering\nYour Ki is swirling violently within your dantian. It feels like molten lead. How do you stabilize the flow?",
                "choices": ["Force it down", "Circulate slowly", "Let it overflow"]
            },
            {
                "text": "🔥 Stage 2: The Core Heat\nYour veins begin to glow. The heat is becoming unbearable. Your vision blurs. What is your next move?",
                "choices": ["Focus on breathing", "Ice the spirit", "Endure the pain"]
            },
            {
                "text": "⚡ Stage 3: The Final Wall\nYou see the bottleneck. A massive wall of shadow blocking your path to the next rank. Smash it!",
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

        if self.success_count >= 2:
            await self._major_success(interaction, db)
        else:
            await self._major_failure(interaction, db)

    async def _major_success(self, interaction, db):
        current_rank = self.user_rank
        current_item = await get_user_stat(db, self.user_id, "item_id") or "Torn Page"
        new_rank = get_next_rank(current_rank)
        target_stats = get_max_stats(new_rank)

        new_hp_cap = target_stats["max_hp"]
        new_vit_cap = target_stats["max_vit"]
        new_ki_cap = target_stats["ki_cap"]

        new_item = ITEM_MUTATIONS.get(current_item, current_item)

        try:
            await update_item_name(db, self.user_id, current_item, new_item)
        except Exception as e:
            print(f"[DEBUG] cultivation: Failed to update inventory item: {e}")
            await add_item(db, self.user_id, new_item, 1, bound=True)

        new_rank_id = RANKS.index(new_rank) if new_rank in RANKS else 0

        # Update user using MongoDB
        await db.users.update_one(
            {"user_id": self.user_id},
            {"$set": {
                "rank": new_rank,
                "rank_id": new_rank_id,
                "minor_realm": "Initial",
                "item_id": new_item,
                "ki": 0,
                "hp": new_hp_cap,
                "vitality": new_vit_cap
            }}
        )

        result_embed = discord.Embed(
            title="🎊 REALM ASCENSION SUCCESS",
            description=(
                f"You have reached the **{new_rank}**!\n"
                f"Your item has evolved into: **{new_item}**.\n\n"
                f"📈 Stat Growth:\n"
                f"Max HP: **{new_hp_cap}**\n"
                f"Max Vitality: **{new_vit_cap}**\n"
                f"Ki Cap: **{new_ki_cap}**"
            ),
            color=format_embed_color("win")
        )
        await interaction.response.edit_message(embed=result_embed, view=None)
        self.stop()

    async def _major_failure(self, interaction, db):
        current_ki = await get_user_stat(db, self.user_id, "ki") or 0
        penalty = MAJOR_FAILURE_PENALTY
        new_ki = max(0, int(current_ki * (100 - penalty["ki_percent"]) / 100))

        current_taels = await get_user_stat(db, self.user_id, "taels") or 0
        new_taels = max(0, current_taels - penalty["taels"])

        await update_user_stat(db, self.user_id, "ki", new_ki)
        await update_user_stat(db, self.user_id, "taels", new_taels)

        debuff_time = (datetime.datetime.now() + datetime.timedelta(minutes=penalty["meridian_minutes"])).isoformat()
        await update_user_stat(db, self.user_id, "meridian_damage", debuff_time)

        cooldown_key = f"breakthrough_major_{self.user_id}"
        now = datetime.datetime.now().isoformat()
        await db.user_cooldowns.update_one(
            {"cooldown_key": cooldown_key},
            {"$set": {"last_used": now}},
            upsert=True
        )

        result_embed = discord.Embed(
            title="💀 BREAKTHROUGH FAILED",
            description=(
                f"The energy backfired.\n"
                f"❌ Lost {penalty['ki_percent']}% of your Ki\n"
                f"❌ Lost {penalty['taels']} Taels\n"
                f"⚠️ Meridians damaged for {penalty['meridian_minutes']} minutes\n"
                f"⏳ You cannot attempt another major breakthrough for {MAJOR_COOLDOWN_MINUTES} minutes."
            ),
            color=format_embed_color("lose")
        )
        await interaction.response.edit_message(embed=result_embed, view=None)
        self.stop()

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
        cooldown_key = f"breakthrough_{bt_type}_{user_id}"
        last_used = await get_user_cooldown(self.bot.db, cooldown_key)
        if not last_used:
            return False, 0

        minutes = MAJOR_COOLDOWN_MINUTES if bt_type == "major" else MINOR_COOLDOWN_MINUTES
        elapsed = (datetime.datetime.now() - last_used).total_seconds() / 60
        if elapsed < minutes:
            remaining = int((minutes - elapsed) * 60)
            return True, remaining
        return False, 0

    async def _get_breakthrough_chance(self, user_id, rank, minor_target, is_major):
        if is_major:
            base_chance = MAJOR_BREAKTHROUGH_CHANCES.get(rank, 15)
        else:
            realm_chances = MINOR_BREAKTHROUGH_CHANCES.get(rank, MINOR_BREAKTHROUGH_CHANCES["The Bound (Mortal)"])
            base_chance = realm_chances.get(minor_target, 50)

        chance = base_chance

        bg = await get_user_stat(self.bot.db, user_id, "background") or ""
        if bg == "Laborer":
            chance += 5

        bt_bonus = await get_user_stat(self.bot.db, user_id, "minor_breakthrough_bonus_bt") or 0
        if is_major:
            chance += bt_bonus

        return min(chance, 95)

    async def _apply_minor_success(self, user_id, rank, current_minor, target_minor):
        db = self.bot.db

        await update_user_stat(db, user_id, "minor_realm", target_minor)

        bonus = MINOR_REALM_BONUSES.get(target_minor, {})
        if bonus:
            current_ki_bonus = await get_user_stat(db, user_id, "minor_breakthrough_bonus_ki") or 0
            current_damage_bonus = await get_user_stat(db, user_id, "minor_breakthrough_bonus_damage") or 0
            current_bt_bonus = await get_user_stat(db, user_id, "minor_breakthrough_bonus_bt") or 0

            await update_user_stat(db, user_id, "minor_breakthrough_bonus_ki", current_ki_bonus + bonus.get("ki_gain", 0))
            await update_user_stat(db, user_id, "minor_breakthrough_bonus_damage", current_damage_bonus + bonus.get("tech_damage", 0))
            await update_user_stat(db, user_id, "minor_breakthrough_bonus_bt", current_bt_bonus + bonus.get("major_bt_chance", 0))

    async def _apply_minor_failure(self, user_id, target_minor):
        db = self.bot.db
        penalty = FAILURE_PENALTIES.get(target_minor, {"ki_percent": 15, "taels": 20})

        current_ki = await get_user_stat(db, user_id, "ki") or 0
        new_ki = max(0, int(current_ki * (100 - penalty["ki_percent"]) / 100))
        await update_user_stat(db, user_id, "ki", new_ki)

        if penalty["taels"] > 0:
            current_taels = await get_user_stat(db, user_id, "taels") or 0
            new_taels = max(0, current_taels - penalty["taels"])
            await update_user_stat(db, user_id, "taels", new_taels)

    @commands.hybrid_command(name="breakthrough", aliases=["bt"])
    async def breakthrough(self, ctx):
        print(f"[DEBUG] cultivation.breakthrough: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        # Fetch user data using MongoDB
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        ki = user.get("ki", 0)
        rank = user.get("rank", "The Bound (Mortal)")
        bg = user.get("background", "")
        minor_realm = user.get("minor_realm", "Initial")
        mastery = user.get("mastery", 0.0)
        taels = user.get("taels", 0)

        if not minor_realm or minor_realm == "None":
            minor_realm = "Initial"
            await update_user_stat(db, user_id, "minor_realm", "Initial")

        max_ki_cap = get_max_stats(rank)["ki_cap"]

        if minor_realm == "Peak":
            await self._attempt_major_breakthrough(ctx, user_id, rank, bg, ki, max_ki_cap, mastery, taels)
        else:
            await self._attempt_minor_breakthrough(ctx, user_id, rank, bg, minor_realm, ki, max_ki_cap, taels)

    async def _attempt_minor_breakthrough(self, ctx, user_id, rank, bg, current_minor, ki, max_ki_cap, taels):
        current_index = MINOR_REALM_INDEX.get(current_minor, 0)
        if current_index >= len(MINOR_REALMS) - 1:
            return await ctx.send("❌ You are already at the peak of your realm. Attempt a major breakthrough!", ephemeral=True)

        target_minor = MINOR_REALMS[current_index + 1]

        ki_percentages = {"Early": 30, "Middle": 55, "Late": 80, "Peak": 100}
        required_percent = ki_percentages.get(target_minor, 50)
        required_ki = int(max_ki_cap * required_percent / 100)

        if ki < required_ki:
            return await ctx.send(f"❌ You need {required_ki} Ki to attempt {target_minor} minor realm. (You have {ki})", ephemeral=True)

        on_cooldown, remaining = await self._check_cooldown(user_id, "minor")
        if on_cooldown:
            return await ctx.send(f"⏳ You must wait {remaining} seconds before attempting another minor breakthrough.", ephemeral=True)

        base_chance = await self._get_breakthrough_chance(user_id, rank, target_minor, is_major=False)

        if ki > required_ki:
            extra_percent = (ki - required_ki) / required_ki * 100
            extra_bonus = min(20, int(extra_percent / 10) * 2)
            base_chance += extra_bonus

        has_pill = await has_item(self.bot.db, user_id, "Breakthrough Pill")
        pill_bonus = 15 if has_pill else 0
        final_chance = min(base_chance + pill_bonus, 95)

        if has_pill:
            pill_message = "💊 Breakthrough Pill: +15% (you have one)"
        else:
            pill_message = "💊 Breakthrough Pill: +15% (you don't have one)"

        embed = discord.Embed(
            title="⚔️ Minor Breakthrough Attempt",
            description=(
                f"Attempt to reach **{target_minor}** minor realm.\n\n"
                f"📊 Success Chance: {final_chance}%\n"
                f"💰 Cost: None (Ki will be consumed on failure)\n"
                f"{pill_message}"
            ),
            color=format_embed_color("main")
        )
        embed.add_field(name="Current Minor Realm", value=current_minor, inline=True)
        embed.add_field(name="Next Minor Realm", value=target_minor, inline=True)
        embed.add_field(name="Ki Required", value=f"{required_ki}/{max_ki_cap}", inline=True)

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.content.lower() in ["yes", "y", "no", "n"]

        try:
            msg = await self.bot.wait_for("message", timeout=30, check=check)
            if msg.content.lower() not in ["yes", "y"]:
                return await ctx.send("❌ Breakthrough cancelled.", ephemeral=True)
        except asyncio.TimeoutError:
            return await ctx.send("⏳ Breakthrough cancelled (timeout).", ephemeral=True)

        roll = random.randint(1, 100)
        success = roll <= final_chance

        if success:
            if has_pill:
                await remove_item(self.bot.db, user_id, "Breakthrough Pill", 1)

            await self._apply_minor_success(user_id, rank, current_minor, target_minor)

            embed = discord.Embed(
                title="✅ MINOR BREAKTHROUGH SUCCESS",
                description=(
                    f"You have reached the **{target_minor}** minor realm!\n\n"
                    f"📈 Permanent Bonuses Gained:\n"
                    f"• Ki Gain: +{MINOR_REALM_BONUSES.get(target_minor, {}).get('ki_gain', 0)}%\n"
                    f"• Technique Damage: +{MINOR_REALM_BONUSES.get(target_minor, {}).get('tech_damage', 0)}%\n"
                    f"• Major BT Chance: +{MINOR_REALM_BONUSES.get(target_minor, {}).get('major_bt_chance', 0)}%"
                ),
                color=format_embed_color("win")
            )
            await ctx.send(embed=embed)
        else:
            await self._apply_minor_failure(user_id, target_minor)

            penalty = FAILURE_PENALTIES.get(target_minor, {"ki_percent": 15, "taels": 20})
            embed = discord.Embed(
                title="💀 MINOR BREAKTHROUGH FAILED",
                description=(
                    f"You failed to reach **{target_minor}** minor realm.\n\n"
                    f"❌ Lost {penalty['ki_percent']}% of your Ki\n"
                    f"{'❌ Lost ' + str(penalty['taels']) + ' Taels' if penalty['taels'] > 0 else ''}\n"
                    f"⏳ You cannot attempt another minor breakthrough for {MINOR_COOLDOWN_MINUTES} minutes."
                ),
                color=format_embed_color("lose")
            )
            await ctx.send(embed=embed)

    async def _attempt_major_breakthrough(self, ctx, user_id, rank, bg, ki, max_ki_cap, mastery, taels):
        if rank == "Peak Master":
            return await ctx.send("❌ You have already reached the peak of martial arts. There is no higher realm to ascend to.", ephemeral=True)

        required_ki = int(max_ki_cap * 1.5)

        if ki < required_ki:
            return await ctx.send(f"❌ You need {required_ki} Ki to attempt a major breakthrough. (You have {ki})", ephemeral=True)

        on_cooldown, remaining = await self._check_cooldown(user_id, "major")
        if on_cooldown:
            return await ctx.send(f"⏳ You must wait {remaining} seconds before attempting another major breakthrough.", ephemeral=True)

        if "Mortal" in rank and (mastery is None or mastery < 50.0):
            return await ctx.send("❌ To advance beyond the Mortal realm, you must master at least 50% of a technique at the Pavilion of Hidden Scrolls.", ephemeral=True)

        base_chance = await self._get_breakthrough_chance(user_id, rank, None, is_major=True)

        if ki > required_ki:
            extra_percent = (ki - required_ki) / required_ki * 100
            extra_bonus = min(20, int(extra_percent / 10) * 2)
            base_chance += extra_bonus

        has_pill = await has_item(self.bot.db, user_id, "Breakthrough Pill")
        pill_bonus = 15 if has_pill else 0
        final_chance = min(base_chance + pill_bonus, 95)

        if has_pill:
            pill_message = "💊 Breakthrough Pill: +15% (you have one)"
        else:
            pill_message = "💊 Breakthrough Pill: +15% (you don't have one)"

        embed = discord.Embed(
            title="⚔️ MAJOR BREAKTHROUGH ATTEMPT",
            description=(
                f"Attempt to ascend from **{rank}** to **{get_next_rank(rank)}**.\n\n"
                f"📊 Success Chance: {final_chance}%\n"
                f"💰 Cost: None (Ki and Taels will be lost on failure)\n"
                f"{pill_message}"
            ),
            color=format_embed_color("main")
        )
        embed.add_field(name="Current Rank", value=rank, inline=True)
        embed.add_field(name="Next Rank", value=get_next_rank(rank), inline=True)
        embed.add_field(name="Ki Required", value=f"{required_ki}/{max_ki_cap}", inline=True)

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.content.lower() in ["yes", "y", "no", "n"]

        try:
            msg = await self.bot.wait_for("message", timeout=30, check=check)
            if msg.content.lower() not in ["yes", "y"]:
                return await ctx.send("❌ Breakthrough cancelled.", ephemeral=True)
        except asyncio.TimeoutError:
            return await ctx.send("⏳ Breakthrough cancelled (timeout).", ephemeral=True)

        view = BreakthroughView(self.bot, user_id, rank, bg)
        embed = discord.Embed(
            title="⚔️ Realm Ascension Initiation",
            description=view.prompts[0]["text"],
            color=format_embed_color("main")
        )
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="breakthrough_status", aliases=["btst"])
    async def breakthrough_status(self, ctx):
        print(f"[DEBUG] cultivation.breakthrough_status: Called by {ctx.author.id}")

        if not await self._is_feature_enabled(ctx):
            return
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        # Fetch user data using MongoDB
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

        if not minor_realm or minor_realm == "None":
            minor_realm = "Initial"

        max_stats = get_max_stats(rank)
        max_ki = max_stats["ki_cap"]

        current_index = MINOR_REALM_INDEX.get(minor_realm, 0)
        next_minor = MINOR_REALMS[current_index + 1] if current_index < len(MINOR_REALMS) - 1 else None

        embed = discord.Embed(
            title="📈 Breakthrough Status",
            description=f"Rank: {rank}\nMinor Realm: {minor_realm}",
            color=format_embed_color("teal")
        )

        if next_minor:
            ki_percentages = {"Early": 30, "Middle": 55, "Late": 80, "Peak": 100}
            required_percent = ki_percentages.get(next_minor, 50)
            required_ki = int(max_ki * required_percent / 100)
            embed.add_field(
                name="Next Minor Breakthrough",
                value=f"Target: {next_minor}\nKi Needed: {required_ki}/{max_ki} ({required_percent}%)",
                inline=False
            )
        elif minor_realm == "Peak" and rank != "Peak Master":
            required_ki = int(max_ki * 1.5)
            embed.add_field(
                name="Next Major Breakthrough",
                value=f"Target: {get_next_rank(rank)}\nKi Needed: {required_ki}/{max_ki} (150%)",
                inline=False
            )
        elif rank == "Peak Master" and minor_realm == "Peak":
            embed.add_field(name="Peak of Martial Arts", value="You have reached the highest realm. No further breakthroughs possible.", inline=False)

        embed.add_field(name="Current Ki", value=f"{ki}/{max_ki}", inline=True)
        embed.add_field(name="Technique Mastery", value=f"{mastery}%", inline=True)

        embed.add_field(
            name="📊 Permanent Bonuses",
            value=(
                f"✨ Ki Gain: +{bonus_ki}%\n"
                f"⚔️ Technique Damage: +{bonus_damage}%\n"
                f"🌀 Major BT Chance: +{bonus_bt}%"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Cultivation(bot))
    print("[DEBUG] cultivation.py: Setup complete")