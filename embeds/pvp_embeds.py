"""
embeds/pvp_embeds.py - Embed designs for PvP cog
Contains all embed builders for sparring challenges, combat, and results.

This file handles:
- Spar challenge embed (when someone is challenged)
- Spar start embed (battle begins)
- Spar combat update embed (HP bars, combat log, turn indicator)
- Spar result embed (victory/defeat with bet payout)
- Cooldown error embed
- Invalid opponent error embeds
"""

import discord
from backend.helpers import format_embed_color

print("[DEBUG] pvp_embeds.py: Loading PvP embeds...")


# ==========================================
# HEALTH BAR GENERATOR
# ==========================================

def generate_health_bar(current: int, max_hp: int) -> str:
    """
    Generate a visual health bar using red and black squares.
    
    Args:
        current: Current HP value
        max_hp: Maximum HP value
        
    Returns:
        str: Health bar string (e.g., "🟥🟥🟥🟥🟥🟥⬛⬛⬛⬛")
    """
    ratio = max(0.0, min(current / max_hp, 1.0))
    filled = int(ratio * 10)
    return "🟥" * filled + "⬛" * (10 - filled)


# ==========================================
# SPAR CHALLENGE EMBED
# ==========================================

def spar_challenge_embed(
    challenger_name: str,
    opponent_mention: str,
    bet_amount: int = 0
) -> discord.Embed:
    """
    Build the embed sent when someone is challenged to a spar.
    
    Args:
        challenger_name: Name of the person issuing the challenge
        opponent_mention: Mention string of the opponent
        bet_amount: Amount of Taels bet (0 if no bet)
        
    Returns:
        discord.Embed: Formatted challenge embed
    """
    description = f"{opponent_mention}, **{challenger_name}** challenges you to a spar!"
    
    if bet_amount > 0:
        description += f"\n\n💰 **Bet:** {bet_amount} Taels (winner takes all)"
    
    embed = discord.Embed(
        title="⚔️ Spar Challenge",
        description=description,
        color=format_embed_color("gold")
    )
    embed.set_footer(text="You have 60 seconds to accept or decline.")
    
    return embed


# ==========================================
# SPAR START EMBED
# ==========================================

def spar_start_embed(
    challenger: discord.Member,
    opponent: discord.Member,
    bet_amount: int = 0,
    first_turn: discord.Member = None
) -> discord.Embed:
    """
    Build the embed shown when a spar begins.
    
    Args:
        challenger: The player who initiated the spar
        opponent: The player who accepted
        bet_amount: Amount of Taels bet
        first_turn: Who goes first (defaults to challenger)
        
    Returns:
        discord.Embed: Formatted spar start embed
    """
    first = first_turn or challenger
    
    embed = discord.Embed(
        title="⚔️ Spar Started!",
        description=f"{challenger.mention} vs {opponent.mention}\n**{first.display_name}** goes first.",
        color=format_embed_color("main")
    )
    
    if bet_amount > 0:
        embed.add_field(
            name="💰 Bet",
            value=f"{bet_amount} Taels (winner takes all)",
            inline=False
        )
    
    embed.set_footer(text="Use the buttons below to fight!")
    
    return embed


# ==========================================
# SPAR COMBAT UPDATE EMBED
# ==========================================

def spar_combat_embed(
    challenger: discord.Member,
    opponent: discord.Member,
    challenger_hp: int,
    opponent_hp: int,
    challenger_max_hp: int,
    opponent_max_hp: int,
    combat_log: str,
    turn: str,
    current_player: discord.Member
) -> discord.Embed:
    """
    Build the combat update embed during a spar.
    
    Shows HP bars for both players, combat log, and turn indicator.
    
    Args:
        challenger: The player who initiated
        opponent: The opponent
        challenger_hp: Challenger's current HP
        opponent_hp: Opponent's current HP
        challenger_max_hp: Challenger's max HP
        opponent_max_hp: Opponent's max HP
        combat_log: Description of the last action
        turn: Whose turn it is ("challenger" or "opponent")
        current_player: The player who should act now
        
    Returns:
        discord.Embed: Formatted combat embed
    """
    # Generate health bars
    challenger_bar = generate_health_bar(challenger_hp, challenger_max_hp)
    opponent_bar = generate_health_bar(opponent_hp, opponent_max_hp)
    
    # Determine turn indicator
    turn_indicator = f"🟢 **{current_player.display_name}'s turn**" if challenger_hp > 0 and opponent_hp > 0 else ""
    
    embed = discord.Embed(
        title=f"⚔️ Spar: {challenger.display_name} vs {opponent.display_name}",
        description=turn_indicator if turn_indicator else None,
        color=format_embed_color("main")
    )
    
    # Challenger HP
    embed.add_field(
        name=f"👤 {challenger.display_name}",
        value=f"❤️ HP: {max(0, challenger_hp)}/{challenger_max_hp}\n`{challenger_bar}`",
        inline=True
    )
    
    # Opponent HP
    embed.add_field(
        name=f"👤 {opponent.display_name}",
        value=f"❤️ HP: {max(0, opponent_hp)}/{opponent_max_hp}\n`{opponent_bar}`",
        inline=True
    )
    
    # Combat log
    embed.add_field(
        name="📜 Combat Log",
        value=f"```ml\n{combat_log}\n```",
        inline=False
    )
    
    return embed


# ==========================================
# SPAR RESULT EMBED
# ==========================================

def spar_result_embed(
    winner: discord.Member,
    loser: discord.Member,
    combat_log: str,
    bet_amount: int = 0,
    winner_taels_gained: int = 0
) -> discord.Embed:
    """
    Build the embed shown when a spar ends.
    
    Args:
        winner: The winner of the spar
        loser: The loser of the spar
        combat_log: Final combat log
        bet_amount: Amount that was bet
        winner_taels_gained: How many Taels the winner gained (0 if no bet)
        
    Returns:
        discord.Embed: Formatted result embed
    """
    description = f"**{winner.display_name}** defeated **{loser.display_name}**!\n\n{combat_log}"
    
    if bet_amount > 0 and winner_taels_gained > 0:
        description += f"\n\n💰 **{winner.display_name}** won **{winner_taels_gained} Taels**!"
    
    # Winner gets green, loser gets red/black
    color = format_embed_color("win") if winner else format_embed_color("lose")
    
    embed = discord.Embed(
        title="⚔️ Spar Finished",
        description=description,
        color=color
    )
    
    return embed


# ==========================================
# SPAR COOLDOWN EMBED
# ==========================================

def spar_cooldown_embed(remaining_seconds: int) -> discord.Embed:
    """
    Build the embed shown when a user tries to spar while on cooldown.
    
    Args:
        remaining_seconds: Seconds remaining on cooldown
        
    Returns:
        discord.Embed: Formatted cooldown embed
    """
    if remaining_seconds >= 60:
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        time_text = f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes} minutes"
    else:
        time_text = f"{remaining_seconds} seconds"
    
    embed = discord.Embed(
        title="⏳ Spar Cooldown",
        description=f"You must wait **{time_text}** before sparring again.",
        color=format_embed_color("orange")
    )
    
    return embed


# ==========================================
# ERROR EMBEDS
# ==========================================

def cannot_spar_self_embed() -> discord.Embed:
    """Error for trying to spar with yourself."""
    embed = discord.Embed(
        title="❌ Cannot Spar",
        description="You cannot spar with yourself. Find a worthy opponent!",
        color=format_embed_color("error")
    )
    return embed


def cannot_spar_bot_embed() -> discord.Embed:
    """Error for trying to spar with a bot."""
    embed = discord.Embed(
        title="❌ Cannot Spar",
        description="You cannot spar with a bot. Challenge a real cultivator!",
        color=format_embed_color("error")
    )
    return embed


def rank_required_embed(required_rank: str = "Third-Rate Warrior") -> discord.Embed:
    """Error for insufficient rank to spar."""
    embed = discord.Embed(
        title="❌ Rank Required",
        description=f"You must be at least **{required_rank}** to spar.",
        color=format_embed_color("error")
    )
    return embed


def already_meditating_embed(player_name: str = None) -> discord.Embed:
    """Error for trying to spar while meditating."""
    if player_name:
        description = f"**{player_name}** is meditating and cannot spar right now."
    else:
        description = "You are meditating. Use `!cancel` to stop before sparring."
    
    embed = discord.Embed(
        title="🧘 Meditation Interrupted",
        description=description,
        color=format_embed_color("error")
    )
    return embed


def already_in_combat_embed(player_name: str = None) -> discord.Embed:
    """Error for trying to spar while already in combat (hunting)."""
    if player_name:
        description = f"**{player_name}** is already in combat and cannot spar right now."
    else:
        description = "You are already in combat! Finish your hunt first."
    
    embed = discord.Embed(
        title="⚔️ Already in Combat",
        description=description,
        color=format_embed_color("error")
    )
    return embed


def insufficient_taels_embed(current_taels: int, required_bet: int) -> discord.Embed:
    """Error for not having enough Taels to cover the bet."""
    embed = discord.Embed(
        title="❌ Insufficient Taels",
        description=f"You need **{required_bet} Taels** to make this bet.\n💰 Current Taels: {current_taels}",
        color=format_embed_color("error")
    )
    return embed


def opponent_insufficient_taels_embed(opponent_name: str, required_bet: int) -> discord.Embed:
    """Error when opponent doesn't have enough Taels to accept the bet."""
    embed = discord.Embed(
        title="❌ Bet Declined",
        description=f"{opponent_name} doesn't have enough Taels to accept the bet ({required_bet} required).",
        color=format_embed_color("error")
    )
    return embed


def min_bet_required_embed(min_bet: int = 10) -> discord.Embed:
    """Error for bet below minimum."""
    embed = discord.Embed(
        title="❌ Bet Too Low",
        description=f"Minimum bet is **{min_bet} Taels**.",
        color=format_embed_color("error")
    )
    return embed


def bet_cannot_be_negative_embed() -> discord.Embed:
    """Error for negative bet amount."""
    embed = discord.Embed(
        title="❌ Invalid Bet",
        description="Bet amount cannot be negative.",
        color=format_embed_color("error")
    )
    return embed


def challenger_not_registered_embed() -> discord.Embed:
    """Error when challenger isn't registered."""
    embed = discord.Embed(
        title="❌ Not Registered",
        description="You must register with `!start` before sparring.",
        color=format_embed_color("error")
    )
    return embed


def opponent_not_registered_embed(opponent_name: str) -> discord.Embed:
    """Error when opponent isn't registered."""
    embed = discord.Embed(
        title="❌ Opponent Not Registered",
        description=f"{opponent_name} has not begun their journey yet.",
        color=format_embed_color("error")
    )
    return embed


def feature_disabled_embed() -> discord.Embed:
    """Error when PvP feature is disabled."""
    embed = discord.Embed(
        title="❌ Feature Disabled",
        description="Sparring is currently disabled by an administrator.",
        color=format_embed_color("error")
    )
    return embed


def challenge_expired_embed() -> discord.Embed:
    """Message shown when challenge times out."""
    embed = discord.Embed(
        title="⏳ Challenge Expired",
        description="The spar challenge has timed out. No one was hurt.",
        color=format_embed_color("orange")
    )
    return embed


print("[DEBUG] pvp_embeds.py: PvP embeds loaded successfully")