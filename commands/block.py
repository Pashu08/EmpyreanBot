"""
commands/block.py - Channel blocking commands
Allows admins to block/unblock channels from bot commands.
Blocks are saved to database and persist across bot restarts.
"""

import discord
from discord.ext import commands
import datetime
from backend.permissions import has_permission
from backend.constants import PERMANENT_GOD

print("[DEBUG] commands/block.py: Loading block commands...")


class Block(commands.Cog):
    """
    Channel blocking cog - Allows admins to block channels from bot commands.
    
    Commands:
    - !block [reason] - Block the current channel
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
    async def block(self, ctx, *, reason: str = "No reason provided"):
        """
        Block the current channel from all bot commands.
        
        Usage: !block [reason]
        Example: !block Spam channel
        """
        if not await self.is_admin(ctx):
            return await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
        
        channel_id = ctx.channel.id
        guild_id = ctx.guild.id if ctx.guild else None
        
        # Check if already blocked
        if channel_id in self.bot.blocked_channels:
            return await ctx.send(f"❌ {ctx.channel.mention} is already blocked.", ephemeral=True)
        
        # Save to database
        try:
            await self.bot.db.blocked_channels.insert_one({
                "channel_id": channel_id,
                "guild_id": guild_id,
                "blocked_by": ctx.author.id,
                "blocked_at": datetime.datetime.now().isoformat(),
                "reason": reason
            })
        except Exception as e:
            print(f"[ERROR] Failed to save blocked channel to database: {e}")
            return await ctx.send("❌ Failed to block channel. Database error.", ephemeral=True)
        
        # Add to memory
        self.bot.blocked_channels.add(channel_id)
        
        embed = discord.Embed(
            title="🔒 Channel Blocked",
            description=f"{ctx.channel.mention} is now blocked from bot commands.",
            color=0xE74C3C
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Use !unblock in this channel to reverse this")
        
        await ctx.send(embed=embed)
    
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
        
        channel_id = ctx.channel.id
        
        # Check if not blocked
        if channel_id not in self.bot.blocked_channels:
            return await ctx.send(f"❌ {ctx.channel.mention} is not blocked.", ephemeral=True)
        
        # Remove from database
        try:
            await self.bot.db.blocked_channels.delete_one({"channel_id": channel_id})
        except Exception as e:
            print(f"[ERROR] Failed to remove blocked channel from database: {e}")
            return await ctx.send("❌ Failed to unblock channel. Database error.", ephemeral=True)
        
        # Remove from memory
        self.bot.blocked_channels.discard(channel_id)
        
        embed = discord.Embed(
            title="🔓 Channel Unblocked",
            description=f"{ctx.channel.mention} can now use bot commands again.",
            color=0x2ECC71
        )
        
        await ctx.send(embed=embed)
    
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
        
        # Fetch details from database for richer display
        blocked_info = []
        try:
            cursor = self.bot.db.blocked_channels.find({})
            async for doc in cursor:
                channel_id = doc["channel_id"]
                channel = self.bot.get_channel(channel_id)
                channel_name = channel.mention if channel else f"Unknown ({channel_id})"
                blocked_by = f"<@{doc['blocked_by']}>" if doc.get('blocked_by') else "Unknown"
                reason = doc.get('reason', 'No reason')
                blocked_at = doc.get('blocked_at', 'Unknown')[:16]
                
                blocked_info.append({
                    "name": channel_name,
                    "reason": reason,
                    "blocked_by": blocked_by,
                    "blocked_at": blocked_at
                })
        except Exception as e:
            print(f"[ERROR] Failed to fetch blocked channels from database: {e}")
            # Fallback to just channel mentions
            for channel_id in self.bot.blocked_channels:
                channel = self.bot.get_channel(channel_id)
                channel_name = channel.mention if channel else f"Unknown ({channel_id})"
                blocked_info.append({"name": channel_name, "reason": "Unknown", "blocked_by": "Unknown", "blocked_at": "Unknown"})
        
        embed = discord.Embed(
            title="🔒 Blocked Channels",
            description=f"Total blocked: {len(self.bot.blocked_channels)}",
            color=0xE74C3C
        )
        
        for info in blocked_info[:25]:  # Limit to 25 to avoid embed size limits
            embed.add_field(
                name=info["name"],
                value=f"📝 Reason: {info['reason']}\n👤 By: {info['blocked_by']}\n📅 At: {info['blocked_at']}",
                inline=False
            )
        
        if len(blocked_info) > 25:
            embed.set_footer(text=f"And {len(blocked_info) - 25} more...")
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(Block(bot))
    print("[DEBUG] commands/block.py: Setup complete")