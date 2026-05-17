import discord
from discord.ext import commands
import traceback
import config

print("[DEBUG] errors.py: Loading Error Handler cog...")

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] ErrorHandler cog initialized")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        print(f"[DEBUG] errors.on_command_error: Command {ctx.command} raised {type(error).__name__}")

        # Ignore command not found errors (silent)
        if isinstance(error, commands.CommandNotFound):
            return

        # Handle cooldown errors
        if isinstance(error, commands.CommandOnCooldown):
            msg = config.MSG_COOLDOWN.format(seconds=round(error.retry_after))
            await ctx.send(msg, ephemeral=True)
            return

        # Handle missing required arguments
        if isinstance(error, commands.MissingRequiredArgument):
            msg = config.MSG_MISSING_ARGUMENT.format(param=error.param.name)
            await ctx.send(msg, ephemeral=True)
            return

        # Handle check failures (already handled by the check itself)
        if isinstance(error, commands.CheckFailure):
            # Checks usually send their own message, so we don't send another
            return

        # Handle any other error (log it and notify user)
        print(f"[ERROR] Unhandled error in command {ctx.command}: {error}")
        traceback.print_exc()

        # Log to file using main.py's function
        from main import log_error_to_file
        log_error_to_file(f"Unhandled error in {ctx.command}: {error}\n{traceback.format_exc()}")

        # Send generic error message to user
        await ctx.send("⚠️ An unexpected error occurred. The bot owner has been notified.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
    print("[DEBUG] errors.py: Setup complete")