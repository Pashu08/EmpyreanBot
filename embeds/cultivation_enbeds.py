"""
embeds/cultivation_embeds.py - Embed designs for Cultivation cog
"""

import discord
from backend.helpers import format_embed_color
from typing import Optional, Dict, List, Tuple

print("[DEBUG] cultivation_embeds.py: Loading cultivation embeds...")


# ==========================================
# MINOR BREAKTHROUGH EMBEDS
# ==========================================

def minor_breakthrough_confirm_embed(
    current_minor: str,
    target_minor: str,
    required_ki: int,
    current_ki: int,
    max_ki: int,
    success_chance: int,
    has_pill: bool,
    pill_bonus: int = 15
) -> discord.Embed:
    """Embed shown before minor breakthrough attempt."""
    
    # Progress bar for Ki
    ki_percent = int((current_ki / max_ki) * 100)
    filled = int(ki_percent / 10)
    ki_bar = "🟩" * filled + "⬛" * (10 - filled)
    
    pill_text = "✅ Available (+15%)" if has_pill else "❌ Not available"
    
    embed = discord.Embed(
        title="⚔️ Minor Breakthrough Attempt",
        description=f"Attempt to reach **{target_minor}** minor realm.",
        color=format_embed_color("main")
    )
    
    embed.add_field(
        name="📊 Current Progress",
        value=f"Current: **{current_minor}** → Next: **{target_minor}**\n"
              f"Ki: `{ki_bar}` {ki_percent}% ({current_ki}/{max_ki})",
        inline=False
    )
    
    embed.add_field(
        name="✨ Success Chance",
        value=f"**{success_chance}%**\n💊 Breakthrough Pill: {pill_text}",
        inline=True
    )
    
    embed.add_field(
        name="💰 Failure Penalty",
        value=f"• Lose {_get_failure_ki_penalty(target_minor)}% Ki\n"
              f"• Lose {_get_failure_taels_penalty(target_minor)} Taels",
        inline=True
    )
    
    embed.set_footer(text="Type 'yes' to begin your breakthrough, 'no' to cancel")
    return embed


def minor_breakthrough_success_embed(
    target_minor: str,
    ki_bonus: int,
    damage_bonus: int,
    bt_bonus: int
) -> discord.Embed:
    """Embed shown on successful minor breakthrough."""
    
    embed = discord.Embed(
        title="✅ MINOR BREAKTHROUGH SUCCESS",
        description=f"You have reached the **{target_minor}** minor realm!",
        color=format_embed_color("win")
    )
    
    embed.add_field(
        name="📈 Permanent Bonuses Gained",
        value=f"• ✨ Ki Gain: **+{ki_bonus}%**\n"
              f"• ⚔️ Technique Damage: **+{damage_bonus}%**\n"
              f"• 🌀 Major BT Chance: **+{bt_bonus}%**",
        inline=False
    )
    
    return embed


def minor_breakthrough_failure_embed(
    target_minor: str,
    ki_percent_lost: int,
    taels_lost: int,
    cooldown_minutes: int
) -> discord.Embed:
    """Embed shown on failed minor breakthrough."""
    
    embed = discord.Embed(
        title="💀 MINOR BREAKTHROUGH FAILED",
        description=f"You failed to reach **{target_minor}** minor realm.",
        color=format_embed_color("lose")
    )
    
    penalty_text = f"❌ Lost {ki_percent_lost}% of your Ki\n"
    if taels_lost > 0:
        penalty_text += f"❌ Lost {taels_lost} Taels\n"
    penalty_text += f"⏳ You cannot attempt another minor breakthrough for {cooldown_minutes} minutes."
    
    embed.description = penalty_text
    return embed


# ==========================================
# MAJOR BREAKTHROUGH EMBEDS
# ==========================================

def major_breakthrough_confirm_embed(
    current_rank: str,
    next_rank: str,
    required_ki: int,
    current_ki: int,
    max_ki: int,
    success_chance: int,
    has_pill: bool,
    mastery_required: int = 50,
    current_mastery: float = 0
) -> discord.Embed:
    """Embed shown before major breakthrough attempt."""
    
    # Ki progress bar
    ki_percent = int((current_ki / max_ki) * 100)
    filled = int(ki_percent / 10)
    ki_bar = "🟩" * filled + "⬛" * (10 - filled)
    
    # Mastery requirement check
    mastery_met = current_mastery >= mastery_required
    mastery_status = "✅" if mastery_met else f"❌ ({current_mastery:.1f}%/{mastery_required}%)"
    
    pill_text = "✅ Available (+15%)" if has_pill else "❌ Not available"
    
    embed = discord.Embed(
        title="⚔️ MAJOR BREAKTHROUGH ATTEMPT",
        description=f"Attempt to ascend from **{current_rank}** to **{next_rank}**.",
        color=format_embed_color("main")
    )
    
    embed.add_field(
        name="📊 Requirements",
        value=f"Ki: `{ki_bar}` {ki_percent}% ({current_ki}/{max_ki})\n"
              f"📖 Mastery: {mastery_status}",
        inline=False
    )
    
    embed.add_field(
        name="✨ Success Chance",
        value=f"**{success_chance}%**\n💊 Breakthrough Pill: {pill_text}",
        inline=True
    )
    
    embed.add_field(
        name="💰 Failure Penalty",
        value=f"• Lose 30% Ki\n• Lose 100 Taels\n• Meridians damaged (15 min)",
        inline=True
    )
    
    embed.set_footer(text="Type 'yes' to begin your tribulation, 'no' to cancel")
    return embed


def major_stage_embed(
    stage: int,
    stage_name: str,
    description: str,
    choices: List[Tuple[str, int]],
    total_stages: int = 3
) -> discord.Embed:
    """Embed for each stage of major breakthrough tribulation."""
    
    # Progress bar for stages
    filled = stage - 1
    progress_bar = "🟩" * filled + "⬜" * (total_stages - filled)
    
    embed = discord.Embed(
        title=f"⚔️ Realm Ascension: Stage {stage}/{total_stages}",
        description=f"`{progress_bar}`\n\n**{stage_name}**\n{description}",
        color=format_embed_color("main")
    )
    
    # Add choices with success rates
    choices_text = ""
    for i, (choice_text, success_rate) in enumerate(choices, 1):
        choices_text += f"**{i}.** {choice_text} *(+{success_rate}% success)*\n"
    
    embed.add_field(name="📜 Choose Your Path", value=choices_text, inline=False)
    embed.set_footer(text="Click a button below to make your choice")
    
    return embed


def major_breakthrough_success_embed(
    new_rank: str,
    new_item: str,
    new_hp_cap: int,
    new_vit_cap: int,
    new_ki_cap: int
) -> discord.Embed:
    """Embed shown on successful major breakthrough."""
    
    embed = discord.Embed(
        title="🎊 REALM ASCENSION SUCCESS",
        description=f"You have reached the **{new_rank}**!",
        color=format_embed_color("win")
    )
    
    embed.add_field(
        name="📦 Item Evolution",
        value=f"Your item has evolved into: **{new_item}**",
        inline=False
    )
    
    embed.add_field(
        name="📈 Stat Growth",
        value=f"🩸 Max HP: **{new_hp_cap}**\n"
              f"❤️ Max Vitality: **{new_vit_cap}**\n"
              f"✨ Ki Cap: **{new_ki_cap}**",
        inline=False
    )
    
    return embed


def major_breakthrough_failure_embed(
    ki_percent_lost: int,
    taels_lost: int,
    meridian_minutes: int,
    cooldown_minutes: int
) -> discord.Embed:
    """Embed shown on failed major breakthrough."""
    
    embed = discord.Embed(
        title="💀 BREAKTHROUGH FAILED",
        description=(
            f"The energy backfired.\n\n"
            f"❌ Lost {ki_percent_lost}% of your Ki\n"
            f"❌ Lost {taels_lost} Taels\n"
            f"⚠️ Meridians damaged for {meridian_minutes} minutes\n"
            f"⏳ You cannot attempt another major breakthrough for {cooldown_minutes} minutes."
        ),
        color=format_embed_color("lose")
    )
    
    return embed


# ==========================================
# BREAKTHROUGH STATUS EMBED
# ==========================================

def breakthrough_status_embed(
    rank: str,
    minor_realm: str,
    ki: int,
    max_ki: int,
    mastery: float,
    bonus_ki: int,
    bonus_damage: int,
    bonus_bt: int,
    next_breakthrough_info: Optional[Dict] = None
) -> discord.Embed:
    """Embed showing breakthrough status and requirements."""
    
    # Ki progress bar
    ki_percent = int((ki / max_ki) * 100)
    filled = int(ki_percent / 10)
    ki_bar = "🟩" * filled + "⬛" * (10 - filled)
    
    embed = discord.Embed(
        title="📈 Breakthrough Status",
        description=f"**Realm:** {rank}\n**Minor Realm:** {minor_realm}",
        color=format_embed_color("teal")
    )
    
    embed.add_field(
        name="✨ Cultivation Progress",
        value=f"Ki: `{ki_bar}` {ki_percent}% ({ki}/{max_ki})\n"
              f"📖 Technique Mastery: {mastery:.1f}%",
        inline=False
    )
    
    if next_breakthrough_info:
        embed.add_field(
            name=next_breakthrough_info["title"],
            value=next_breakthrough_info["description"],
            inline=False
        )
    
    embed.add_field(
        name="📊 Permanent Bonuses",
        value=f"✨ Ki Gain: **+{bonus_ki}%**\n"
              f"⚔️ Technique Damage: **+{bonus_damage}%**\n"
              f"🌀 Major BT Chance: **+{bonus_bt}%**",
        inline=False
    )
    
    embed.set_footer(text="Use !breakthrough to attempt ascension")
    return embed


def breakthrough_cooldown_embed(minutes_left: int, seconds_left: int, is_major: bool) -> discord.Embed:
    """Embed shown when breakthrough is on cooldown."""
    
    bt_type = "major" if is_major else "minor"
    time_str = f"{minutes_left}m {seconds_left}s" if minutes_left > 0 else f"{seconds_left}s"
    
    embed = discord.Embed(
        title="⏳ Breakthrough Cooldown",
        description=f"You must wait **{time_str}** before attempting another {bt_type} breakthrough.",
        color=format_embed_color("orange")
    )
    
    return embed


# ==========================================
# HELPER FUNCTIONS FOR PENALTIES
# ==========================================

def _get_failure_ki_penalty(target_minor: str) -> int:
    """Get Ki loss percentage for failed minor breakthrough."""
    penalties = {"Early": 10, "Middle": 15, "Late": 20, "Peak": 25}
    return penalties.get(target_minor, 15)


def _get_failure_taels_penalty(target_minor: str) -> int:
    """Get Taels loss for failed minor breakthrough."""
    penalties = {"Early": 0, "Middle": 20, "Late": 30, "Peak": 50}
    return penalties.get(target_minor, 20)


print("[DEBUG] cultivation_embeds.py: Cultivation embeds loaded successfully")