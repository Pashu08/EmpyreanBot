class ErrorHandler(commands.Cog):
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Wait **{error.retry_after:.1f}s**.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`.", ephemeral=True)
        elif isinstance(error, commands.CheckFailure):
            pass  # checks already send their own messages
        elif isinstance(error, commands.CommandNotFound):
            pass  # silent — no spam
        else:
            print(f"[ERROR] {ctx.command}: {error}")
            raise error