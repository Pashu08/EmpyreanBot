"""
embeds/actions_embeds.py - Embed designs for Actions cog
Contains all embed builders for work, observe, comprehend, and choice events.
"""

import discord
from backend.helpers import format_embed_color

print("[DEBUG] actions_embeds.py: Loading action embeds...")


# ==========================================
# FLAVOR TEXTS (moved from actions.py)
# ==========================================

WORK_FLAVORS = [
    "You spent the day transporting heavy iron ore through muddy mountain roads.",
    "You guarded a merchant caravan traveling between remote villages.",
    "You helped repair damaged homes after a fierce storm swept through the region.",
    "You carried water and supplies for wandering martial artists.",
    "You gathered medicinal herbs near the forest outskirts.",
    "You assisted blacksmiths in forging crude weapons for local guards.",
    "You chopped firewood beside a freezing mountain settlement.",
    "You helped merchants unload expensive cargo beneath careful supervision.",
]

OBSERVE_FLAVORS = [
    "You sat beneath a silent tree and listened to the rhythm of your breathing.",
    "You observed flowing water and felt your thoughts gradually settle.",
    "You meditated quietly as cold mountain winds brushed past your robes.",
    "You watched the rain strike ancient stone paths deep in thought.",
    "You focused on the circulation of Ki flowing within your body.",
    "You studied the movements of distant martial practitioners from afar.",
    "You sat in silence beneath the moon, calming your restless mind.",
    "You listened carefully to the natural flow of the world around you.",
]


# ==========================================
# WORK EMBED
# ==========================================

def work_embed(
    flavor_text: str,
    mastery_msg: str,
    event_text: str,
    event_changes: list,
    milestone_msg: str,
    final_taels_gain: int,
    new_vit: int,
    max_vit: int,
    mastery_gain: float,
    new_mastery: float,
    daily_bonus: bool,
    new_taels: int
) -> discord.Embed:
    """
    Build the embed for the !work command.
    
    Args:
        flavor_text: Random work description
        mastery_msg: Laborer mastery gain message (if any)
        event_text: Random event description (if any)
        event_changes: List of stat changes from event
        milestone_msg: Mastery milestone reward message (if any)
        final_taels_gain: Taels earned from work
        new_vit: Current Vitality after work
        max_vit: Maximum Vitality for current rank
        mastery_gain: Mastery gained (if any)
        new_mastery: Total mastery after gain
        daily_bonus: Whether daily bonus was applied
        new_taels: Total Taels after work
        
    Returns:
        discord.Embed: Formatted work result embed
    """
    embed = discord.Embed(
        title="⚒️ Murim Labor",
        color=format_embed_color("main"),
        description=flavor_text
    )

    if mastery_msg:
        embed.description += mastery_msg
    if event_text:
        embed.description += f"\n\n🌿 {event_text}"
        if event_changes:
            embed.description += f"\n*{', '.join(event_changes)}*"
    if milestone_msg:
        embed.description += f"\n\n🏆 **Milestone Reached!**\n{milestone_msg}"

    bonus_text = " **(Daily Bonus Active!)**" if daily_bonus else ""
    embed.add_field(name="Earned", value=f"💰 **+{final_taels_gain}** Taels{bonus_text}", inline=True)
    embed.add_field(name="Vitality", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
    
    if mastery_gain > 0:
        embed.add_field(
            name="Mastery",
            value=f"📖 **+{mastery_gain}%** (Total: {new_mastery:.1f}%)",
            inline=True
        )

    embed.set_footer(text=f"Current Wealth: {new_taels} Taels")
    return embed


# ==========================================
# OBSERVE EMBED
# ==========================================

def observe_embed(
    flavor_text: str,
    mastery_msg: str,
    event_text: str,
    event_changes: list,
    milestone_msg: str,
    ki_gain: int,
    new_vit: int,
    max_vit: int,
    mastery_gain: float,
    new_mastery: float,
    daily_bonus: bool,
    new_ki: int,
    ki_cap: int
) -> discord.Embed:
    """
    Build the embed for the !observe command.
    
    Args:
        flavor_text: Random observe description
        mastery_msg: Martial Insight mastery gain message
        event_text: Random event description (if any)
        event_changes: List of stat changes from event
        milestone_msg: Mastery milestone reward message (if any)
        ki_gain: Ki gained from observing
        new_vit: Current Vitality after observe
        max_vit: Maximum Vitality for current rank
        mastery_gain: Mastery gained (if any)
        new_mastery: Total mastery after gain
        daily_bonus: Whether daily bonus was applied
        new_ki: Current Ki after observe
        ki_cap: Maximum Ki for current rank
        
    Returns:
        discord.Embed: Formatted observe result embed
    """
    embed = discord.Embed(
        title="👁️ Observation",
        color=format_embed_color("teal"),
        description=flavor_text
    )

    if mastery_msg:
        embed.description += mastery_msg
    if event_text:
        embed.description += f"\n\n🌿 {event_text}"
        if event_changes:
            embed.description += f"\n*{', '.join(event_changes)}*"
    if milestone_msg:
        embed.description += f"\n\n🏆 **Milestone Reached!**\n{milestone_msg}"

    bonus_text = " **(Daily Bonus Active!)**" if daily_bonus else ""
    embed.add_field(name="Ki Refined", value=f"✨ **+{ki_gain}** Ki{bonus_text}", inline=True)
    embed.add_field(name="Vitality", value=f"❤️ **{new_vit}**/{max_vit}", inline=True)
    
    if mastery_gain > 0:
        embed.add_field(
            name="Mastery",
            value=f"📖 **+{mastery_gain}%** (Total: {new_mastery:.1f}%)",
            inline=True
        )

    embed.set_footer(text=f"Current Ki: {new_ki}/{ki_cap}")
    return embed


# ==========================================
# COMPREHEND EMBED
# ==========================================

def comprehend_embed(
    tech_name: str,
    event_text: str,
    event_changes: list,
    milestone_msg: str,
    actual_gain: float,
    new_mastery: float,
    new_vit: int,
    max_vit: int
) -> discord.Embed:
    """
    Build the embed for the !comprehend command.
    
    Args:
        tech_name: Name of the technique being studied
        event_text: Random event description (if any)
        event_changes: List of stat changes from event
        milestone_msg: Mastery milestone reward message (if any)
        actual_gain: Actual mastery percentage gained
        new_mastery: Total mastery after gain
        new_vit: Current Vitality after comprehend
        max_vit: Maximum Vitality for current rank
        
    Returns:
        discord.Embed: Formatted comprehend result embed
    """
    embed = discord.Embed(
        title="🧠 Martial Comprehension",
        color=format_embed_color("gold")
    )
    embed.description = (
        f"You isolated yourself from worldly distractions and focused entirely "
        f"on the principles of **{tech_name}**.\n\n"
        f"Fragments of understanding slowly surfaced within your mind."
    )

    if event_text:
        embed.description += f"\n\n🌿 {event_text}"
        if event_changes:
            embed.description += f"\n*{', '.join(event_changes)}*"
    if milestone_msg:
        embed.description += f"\n\n🏆 **Milestone Reached!**\n{milestone_msg}"

    embed.add_field(name="Mastery Gained", value=f"📖 **+{actual_gain}%**", inline=True)
    embed.add_field(name="Total Mastery", value=f"📊 **{new_mastery:.1f}%** / 100%", inline=True)
    embed.set_footer(text=f"Vitality Remaining: {new_vit}/{max_vit}")

    return embed


# ==========================================
# CHOICE EVENT EMBED
# ==========================================

def choice_event_embed(title: str, description: str) -> discord.Embed:
    """
    Build the embed for a random choice event.
    
    Args:
        title: Event title (e.g., "🏮 A Wandering Master")
        description: Event description text
        
    Returns:
        discord.Embed: Formatted choice event embed
    """
    return discord.Embed(
        title=title,
        description=description,
        color=format_embed_color("gold")
    )


# ==========================================
# EVENT OUTCOME EMBED
# ==========================================

def event_outcome_embed(result: str) -> discord.Embed:
    """
    Build the embed for a choice event outcome.
    
    Args:
        result: Outcome description text
        
    Returns:
        discord.Embed: Formatted outcome embed
    """
    return discord.Embed(
        title="✨ Event Outcome",
        description=result,
        color=format_embed_color("gold")
    )


# ==========================================
# MILESTONE SUCCESS EMBED
# ==========================================

def milestone_success_embed(target_minor: str, bonuses: dict) -> discord.Embed:
    """
    Build the embed for a minor breakthrough success.
    
    Args:
        target_minor: Name of the minor realm reached (Early, Middle, Late, Peak)
        bonuses: Dictionary containing ki_gain, tech_damage, major_bt_chance
        
    Returns:
        discord.Embed: Formatted success embed
    """
    embed = discord.Embed(
        title="✅ MINOR BREAKTHROUGH SUCCESS",
        description=f"You have reached the **{target_minor}** minor realm!\n\n"
                    f"📈 **Permanent Bonuses Gained:**\n"
                    f"• Ki Gain: +{bonuses.get('ki_gain', 0)}%\n"
                    f"• Technique Damage: +{bonuses.get('tech_damage', 0)}%\n"
                    f"• Major BT Chance: +{bonuses.get('major_bt_chance', 0)}%",
        color=format_embed_color("win")
    )
    return embed


def milestone_failure_embed(target_minor: str, ki_percent: int, taels_lost: int, cooldown_minutes: int) -> discord.Embed:
    """
    Build the embed for a minor breakthrough failure.
    
    Args:
        target_minor: Name of the minor realm that was attempted
        ki_percent: Percentage of Ki lost
        taels_lost: Taels lost (0 if none)
        cooldown_minutes: Minutes to wait before next attempt
        
    Returns:
        discord.Embed: Formatted failure embed
    """
    description = f"You failed to reach **{target_minor}** minor realm.\n\n"
    description += f"❌ Lost {ki_percent}% of your Ki\n"
    if taels_lost > 0:
        description += f"❌ Lost {taels_lost} Taels\n"
    description += f"⏳ You cannot attempt another minor breakthrough for {cooldown_minutes} minutes."

    embed = discord.Embed(
        title="💀 MINOR BREAKTHROUGH FAILED",
        description=description,
        color=format_embed_color("lose")
    )
    return embed


# ==========================================
# COOLDOWN EMBED
# ==========================================

def cooldown_embed(remaining: int) -> discord.Embed:
    """
    Build the embed for a cooldown error message.
    
    Args:
        remaining: Seconds remaining on cooldown
        
    Returns:
        discord.Embed: Formatted cooldown embed
    """
    return discord.Embed(
        title="⏳ Cooldown",
        description=f"Please wait **{remaining} seconds** before using this command again.",
        color=format_embed_color("error")
    )


print("[DEBUG] actions_embeds.py: Action embeds loaded successfully")