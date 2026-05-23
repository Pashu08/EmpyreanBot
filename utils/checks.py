import datetime
import functools
from discord.ext import commands
from utils import db as db_utils
import config

print("[DEBUG] checks.py: Loading command guards...")

# ==========================================
# HELPER: Get setting from database (MongoDB version)
# ==========================================
async def _get_setting(bot, key, default=None):
    """Get a setting from bot_settings collection."""
    try:
        return await bot.db.get_bot_setting(key, default)
    except:
        return default

# ==========================================
# 1. REGISTERED CHECK
# ==========================================
def registered():
    """Command guard: rejects if player hasn't used !start."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.registered: Checking user {ctx.author.id}")
        if not await db_utils.user_exists(ctx.bot.db, ctx.author.id):
            msg = await _get_setting(ctx.bot, "msg_not_registered", config.MSG_NOT_REGISTERED)
            await ctx.send(msg, ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 2. NOT MEDITATING
# ==========================================
def not_meditating():
    """Rejects if player is in active meditation."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.not_meditating: Checking user {ctx.author.id}")
        if hasattr(ctx.bot, 'is_meditating') and ctx.author.id in ctx.bot.is_meditating:
            msg = await _get_setting(ctx.bot, "msg_already_meditating", config.MSG_ALREADY_MEDITATING)
            await ctx.send(msg, ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 3. MERIDIANS INTACT
# ==========================================
def meridians_intact():
    """Rejects if player has damaged meridians."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.meridians_intact: Checking user {ctx.author.id}")
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if user and user.get('meridian_damage'):
            try:
                exp = datetime.datetime.fromisoformat(user['meridian_damage'])
                if datetime.datetime.now() < exp:
                    diff = exp - datetime.datetime.now()
                    minutes = int(diff.total_seconds() // 60)
                    msg = await _get_setting(ctx.bot, "msg_meridian_damage", config.MSG_MERIDIAN_DAMAGE)
                    await ctx.send(msg.format(minutes=minutes), ephemeral=True)
                    return False
            except (ValueError, TypeError):
                pass
        return True
    return commands.check(predicate)

# ==========================================
# 4. NOT IN COMBAT
# ==========================================
def not_in_combat():
    """Rejects if player is currently in a hunt (has CombatView open)."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.not_in_combat: Checking user {ctx.author.id}")
        if hasattr(ctx.bot, 'active_combats') and ctx.author.id in ctx.bot.active_combats:
            await ctx.send("❌ You are already in combat! Finish your current fight first.", ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 5. COOLDOWN CHECK (from bot_settings)
# ==========================================
def cooldown_check(command_name):
    """Reads cooldown from bot_settings collection instead of hardcoded."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.cooldown_check: Checking {command_name} for user {ctx.author.id}")
        cooldown_key = f"cooldown_{command_name}"
        seconds = await _get_setting(ctx.bot, cooldown_key, None)
        if seconds is None:
            return True
        if not hasattr(ctx.bot, 'command_cooldowns'):
            ctx.bot.command_cooldowns = {}
        user_key = f"{command_name}_{ctx.author.id}"
        last_used = ctx.bot.command_cooldowns.get(user_key, 0)
        now = datetime.datetime.now().timestamp()
        if now - last_used < seconds:
            remaining = int(seconds - (now - last_used))
            msg = await _get_setting(ctx.bot, "msg_cooldown", config.MSG_COOLDOWN)
            await ctx.send(msg.format(seconds=remaining), ephemeral=True)
            return False
        ctx.bot.command_cooldowns[user_key] = now
        return True
    return commands.check(predicate)

# ==========================================
# 6. HAS ENOUGH KI
# ==========================================
def has_enough_ki(amount):
    """Checks if player has at least 'amount' Ki."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.has_enough_ki: Need {amount} for user {ctx.author.id}")
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if not user:
            msg = await _get_setting(ctx.bot, "msg_not_registered", config.MSG_NOT_REGISTERED)
            await ctx.send(msg, ephemeral=True)
            return False
        current_ki = user.get('ki', 0)
        if current_ki < amount:
            msg = await _get_setting(ctx.bot, "msg_no_ki", config.MSG_NO_KI)
            await ctx.send(msg.format(required=amount), ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 7. HAS ENOUGH VITALITY
# ==========================================
def has_enough_vitality(amount):
    """Checks if player has at least 'amount' Vitality."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.has_enough_vitality: Need {amount} for user {ctx.author.id}")
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if not user:
            msg = await _get_setting(ctx.bot, "msg_not_registered", config.MSG_NOT_REGISTERED)
            await ctx.send(msg, ephemeral=True)
            return False
        current_vit = user.get('vitality', 0)
        if current_vit < amount:
            msg = await _get_setting(ctx.bot, "msg_no_vitality", config.MSG_NO_VITALITY)
            await ctx.send(msg.format(required=amount), ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 8. MINIMUM RANK
# ==========================================
def min_rank(required_rank):
    """Checks if player's rank is at least the required rank."""
    rank_order = [
        "The Bound (Mortal)",
        "Third-Rate Warrior",
        "Second-Rate Warrior",
        "First-Rate Warrior",
        "Peak Master"
    ]
    async def predicate(ctx):
        print(f"[DEBUG] checks.min_rank: Need {required_rank} for user {ctx.author.id}")
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if not user:
            msg = await _get_setting(ctx.bot, "msg_not_registered", config.MSG_NOT_REGISTERED)
            await ctx.send(msg, ephemeral=True)
            return False
        current_rank = user.get('rank', "The Bound (Mortal)")
        if rank_order.index(current_rank) < rank_order.index(required_rank):
            await ctx.send(f"❌ You need to be at least **{required_rank}** to use this command.", ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 9. NOT BANNED
# ==========================================
def not_banned():
    """Checks if user is not in the banned_users collection."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.not_banned: Checking user {ctx.author.id}")
        if await db_utils.is_user_banned(ctx.bot.db, ctx.author.id):
            await ctx.send("❌ You are banned from using this bot.", ephemeral=True)
            return False
        return True
    return commands.check(predicate)

# ==========================================
# 10. PER-USER COOLDOWN (database backed, survives restart)
# ==========================================
def cooldown_per_user(command_name, seconds):
    """Per-user cooldown stored in database (survives bot restart)."""
    async def predicate(ctx):
        print(f"[DEBUG] checks.cooldown_per_user: Checking {command_name} for user {ctx.author.id}")
        user_key = f"{command_name}_{ctx.author.id}"
        now = datetime.datetime.now()

        # Get existing cooldown
        last_used = await ctx.bot.db.get_user_cooldown(user_key)

        if last_used:
            elapsed = (now - last_used).total_seconds()
            if elapsed < seconds:
                remaining = int(seconds - elapsed)
                msg = await _get_setting(ctx.bot, "msg_cooldown", config.MSG_COOLDOWN)
                await ctx.send(msg.format(seconds=remaining), ephemeral=True)
                return False

        # Set new cooldown
        await ctx.bot.db.set_user_cooldown(user_key)
        return True
    return commands.check(predicate)

print("[DEBUG] checks.py: Command guards loaded successfully")