from discord.ext import commands
from utils import db as db_utils
import functools

def registered():
    """Command guard: rejects if player hasn't used !start."""
    async def predicate(ctx):
        if not await db_utils.user_exists(ctx.bot.db, ctx.author.id):
            await ctx.send("❌ Use `!start` to begin your journey.", ephemeral=True)
            return False
        return True
    return commands.check(predicate)

def not_meditating():
    """Rejects if player is in active meditation."""
    async def predicate(ctx):
        if hasattr(ctx.bot, 'is_meditating') and ctx.author.id in ctx.bot.is_meditating:
            await ctx.send("🧘 You cannot act while in deep meditation.", ephemeral=True)
            return False
        return True
    return commands.check(predicate)

def meridians_intact():
    """Rejects if player has damaged meridians."""
    import datetime
    async def predicate(ctx):
        user = await db_utils.fetch_user(ctx.bot.db, ctx.author.id)
        if user and user.get('meridian_damage'):
            try:
                exp = datetime.datetime.fromisoformat(user['meridian_damage'])
                if datetime.datetime.now() < exp:
                    diff = exp - datetime.datetime.now()
                    await ctx.send(
                        f"❌ Your meridians are damaged. Wait **{int(diff.total_seconds()//60)}m** to recover.",
                        ephemeral=True
                    )
                    return False
            except (ValueError, TypeError):
                pass
        return True
    return commands.check(predicate)