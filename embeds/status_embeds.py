"""
embeds/status_embeds.py - Embed designs for Status cog
"""

import discord
from backend.helpers import format_embed_color

print("[DEBUG] status_embeds.py: Loading status embeds...")


def afk_no_gains_embed() -> discord.Embed:
    """Embed shown when user has no AFK gains."""
    return discord.Embed(
        title="🧘 AFK Status",
        description="You have no AFK gains to claim. Try using `!observe` or `!work` to start your journey!",
        color=format_embed_color("main")
    )


def afk_gains_embed(time_str: str, ki_gain: int, mastery_gain: float) -> discord.Embed:
    """Embed shown when user returns from AFK with gains."""
    embed = discord.Embed(
        title="🌙 Welcome Back!",
        description=f"You were away for **{time_str}**.\n\n"
                   f"✨ **Ki Gained:** +{ki_gain}\n"
                   f"📖 **Mastery Gained:** +{mastery_gain:.1f}%",
        color=format_embed_color("teal")
    )
    embed.set_footer(text="Use `!stats` to see your full progress.")
    return embed


def stats_embed(
    target: discord.Member,
    rank: str,
    stage: str,
    bg_emoji: str,
    bg: str,
    taels: int,
    hp: int,
    max_hp: int,
    vitality: int,
    max_vit: int,
    meridian_status: str,
    ki: int,
    ki_cap: int,
    ki_bar: str,
    mastery: float,
    mastery_bar: str,
    combat_mastery: int
) -> discord.Embed:
    """Main stats embed showing cultivation progress."""
    embed = discord.Embed(
        title=f"📜 Status: {target.name}",
        color=format_embed_color("main")
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    embed.add_field(
        name="Identity",
        value=f"**Realm:** {rank} ({stage})\n**Path:** {bg_emoji} {bg}",
        inline=False
    )
    embed.add_field(
        name="💰 Wealth",
        value=f"{taels} Taels",
        inline=True
    )
    embed.add_field(
        name="Vital Statistics",
        value=f"🩸 **HP:** {hp}/{max_hp}\n❤️ **Vit:** {vitality}/{max_vit}\n🧠 **Meridians:** {meridian_status}",
        inline=True
    )
    embed.add_field(
        name="Cultivation",
        value=f"✨ **Ki:** {ki}/{ki_cap}\n`{ki_bar}`\n📖 **Mastery:** {mastery:.1f}%\n`{mastery_bar}`\n⚔️ **Combat Mastery:** {combat_mastery}",
        inline=True
    )
    
    embed.set_footer(text="Use `!profile` for detailed character sheet. Use `!afk` to check AFK gains.")
    return embed


print("[DEBUG] status_embeds.py: Status embeds loaded successfully")