import discord
from discord.ext import commands
import traceback
import config

# Import error logging function from main
from main import log_error_to_file

print("[DEBUG] errors.py: Loading Error Handler cog...")

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] ErrorHandler cog initialized")

    async def _send_to_log_channel(self, error_message, ctx, error):
        """Send error details to the configured log channel."""
        if not config.ERROR_LOG_CHANNEL_ID:
            return

        channel = self.bot.get_channel(config.ERROR_LOG_CHANNEL_ID)
        if not channel:
            print(f"[DEBUG] errors: Could not find channel {config.ERROR_LOG_CHANNEL_ID}")
            return

        embed = discord.Embed(
            title="❌ Error Occurred",
            description=f"```py\n{error_message[:1900]}\n```",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Command", value=f"`{ctx.command}`" if ctx.command else "Unknown", inline=True)
        embed.add_field(name="User", value=f"{ctx.author} ({ctx.author.id})", inline=True)
        embed.add_field(name="Channel", value=f"{ctx.channel.mention}", inline=True)

        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[DEBUG] errors: Failed to send error to log channel: {e}")

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

        # Log to file
        log_error_to_file(f"Unhandled error in {ctx.command}: {error}\n{traceback.format_exc()}")

        # Send to Discord log channel (if configured)
        error_details = f"{type(error).__name__}: {error}\n{traceback.format_exc()}"
        await self._send_to_log_channel(error_details[:2000], ctx, error)

        # Send generic error message to user
        await ctx.send(config.MSG_GENERIC_ERROR, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
    print("[DEBUG] errors.py: Setup complete")