"""
commands/block.py - Channel blocking commands
Allows admins to block/unblock channels from bot commands.
"""

import discord
from discord.ext import commands
from backend.permissions import has_permission
from backend.constants import PERMANENT_GOD

print("[DEBUG] commands/block.py: Loading block commands...")


class Block(commands.Cog):
    """
    Channel blocking cog - Allows admins to block channels from bot commands.
    
    Commands:
    - !block - Block the current channel
    - !unblock - Unblock the current channel
    - !listblocks - List all blocked channels
    """
    
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] Block cog initialized")
    
    async def is_admin(self, ctx):
        """Check if user has admin permissions."""
        return ctx.author.id == PERMANENT_GOD or await has_permission(self.bot, ctx.author.id, "system")
    
    @commands.hybrid_command(
        name="block",
        description="Block this channel from using bot commands"
    )
    async def block(self, ctx):
        """
        Block the current channel from all bot commands.
        
        Usage: !block
        """
        if not await self.is_admin(ctx):
            return await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
        
        if ctx.channel.id in self.bot.blocked_channels:
            return await ctx.send(f"❌ {ctx.channel.mention} is already blocked.", ephemeral=True)
        
        self.bot.blocked_channels.add(ctx.channel.id)
        await ctx.send(f"🔒 {ctx.channel.mention} is now blocked from bot commands.")
    
    @commands.hybrid_command(
        name="unblock",
        description="Unblock this channel"
    )
    async def unblock(self, ctx):
        """
        Unblock the current channel.
        
        Usage: !unblock
        """
        if not await self.is_admin(ctx):
            return await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
        
        if ctx.channel.id not in self.bot.blocked_channels:
            return await ctx.send(f"❌ {ctx.channel.mention} is not blocked.", ephemeral=True)
        
        self.bot.blocked_channels.discard(ctx.channel.id)
        await ctx.send(f"🔓 {ctx.channel.mention} is now unblocked.")
    
    @commands.hybrid_command(
        name="listblocks",
        aliases=["blocked"],
        description="List all blocked channels"
    )
    async def listblocks(self, ctx):
        """
        List all channels currently blocked from bot commands.
        
        Usage: !listblocks or !blocked
        """
        if not await self.is_admin(ctx):
            return await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
        
        if not self.bot.blocked_channels:
            return await ctx.send("✅ No channels are currently blocked.", ephemeral=True)
        
        # Build list of blocked channels
        channels = []
        for channel_id in self.bot.blocked_channels:
            channel = self.bot.get_channel(channel_id)
            if channel:
                channels.append(f"• {channel.mention}")
            else:
                channels.append(f"• Unknown channel ({channel_id})")
        
        embed = discord.Embed(
            title="🔒 Blocked Channels",
            description="\n".join(channels),
            color=0xE74C3C
        )
        embed.set_footer(text="Use !unblock in a channel to unblock it")
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(Block(bot))
    print("[DEBUG] commands/block.py: Setup complete")