"""
backend/pavilion_helpers.py - Helper functions and UI views for Pavilion cog

This module handles:
- PavilionSelect class (dropdown menu for technique selection)
- PavilionView class (main view with dropdown and confirm button)
- Technique data validation and requirements checking
- Hidden technique checking (for future expansion)
"""

import discord
from discord.ui import Select, View, Button
from typing import List, Dict, Any, Optional, Tuple

from backend.helpers import format_embed_color
from backend.constants import TECHNIQUES
from embeds.pavilion_embeds import (
    technique_inspect_embed,
    get_family_data,
    get_technique_type_emoji
)

print("[DEBUG] pavilion_helpers.py: Loading pavilion helpers...")


# ==========================================
# TECHNIQUE HELPER FUNCTIONS
# ==========================================

def get_all_techniques() -> List[Tuple[str, Dict]]:
    """
    Get all techniques from constants.
    
    Returns:
        List of tuples (technique_name, technique_data)
    """
    return list(TECHNIQUES.items())


def get_technique_data(tech_name: str) -> Optional[Dict]:
    """
    Get data for a specific technique.
    
    Args:
        tech_name: Name of the technique
        
    Returns:
        Technique data dict, or None if not found
    """
    return TECHNIQUES.get(tech_name)


def get_techniques_by_family(family: str) -> List[Tuple[str, Dict]]:
    """
    Get all techniques belonging to a specific family.
    
    Args:
        family: Family name (Orthodox, Unorthodox, Demonic)
        
    Returns:
        List of tuples (technique_name, technique_data)
    """
    result = []
    for name, data in TECHNIQUES.items():
        if data.get("family") == family:
            result.append((name, data))
    return result


def get_available_techniques_for_rank(rank: str) -> List[str]:
    """
    Get all techniques that a user of a given rank can learn.
    
    Args:
        rank: User's cultivation rank
        
    Returns:
        List of technique names that are available
    """
    available = []
    
    # Rank hierarchy for comparison
    rank_levels = {
        "The Bound (Mortal)": 0,
        "Third-Rate Warrior": 1,
        "Second-Rate Warrior": 2,
        "First-Rate Warrior": 3,
        "Peak Master": 4
    }
    
    user_level = rank_levels.get(rank, 0)
    
    for tech_name, tech_data in TECHNIQUES.items():
        required_rank = tech_data.get("rank_required", "The Bound (Mortal)")
        required_level = rank_levels.get(required_rank, 0)
        
        if user_level >= required_level:
            available.append(tech_name)
    
    return available


def meets_rank_requirement(rank: str, required_rank: str) -> bool:
    """
    Check if a user's rank meets the requirement for a technique.
    
    Args:
        rank: User's current rank
        required_rank: Required rank for the technique
        
    Returns:
        True if user meets requirement, False otherwise
    """
    rank_levels = {
        "The Bound (Mortal)": 0,
        "Third-Rate Warrior": 1,
        "Second-Rate Warrior": 2,
        "First-Rate Warrior": 3,
        "Peak Master": 4
    }
    
    user_level = rank_levels.get(rank, 0)
    required_level = rank_levels.get(required_rank, 0)
    
    return user_level >= required_level


def validate_technique_exists(tech_name: str) -> bool:
    """
    Check if a technique exists in the constants.
    
    Args:
        tech_name: Name of the technique to check
        
    Returns:
        True if technique exists, False otherwise
    """
    return tech_name in TECHNIQUES


# ==========================================
# PAVILION SELECT DROPDOWN
# ==========================================

class PavilionSelect(Select):
    """
    Dropdown menu for selecting a technique to inspect.
    
    Shows all available techniques with emojis and descriptions.
    When selected, displays the technique details and enables the confirm button.
    """
    
    def __init__(self, member_id: int, available_techs: List[str]):
        """
        Initialize the Pavilion dropdown.
        
        Args:
            member_id: Discord user ID (to verify interaction)
            available_techs: List of technique names available to this user
        """
        self.member_id = member_id
        self.available_techs = available_techs
        
        options = []
        for tech_name in available_techs:
            tech_data = TECHNIQUES.get(tech_name, {})
            emoji = tech_data.get("emoji", "📜")
            tech_type = tech_data.get("type", "Technique")
            description = tech_data.get("description", "A martial technique")[:50]
            
            options.append(
                discord.SelectOption(
                    label=tech_name,
                    description=f"{tech_type} - {description}",
                    emoji=emoji
                )
            )
        
        super().__init__(
            placeholder="📖 Select a scroll to examine...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """
        Handle dropdown selection.
        
        When a technique is selected, displays an inspection embed
        and enables the confirm button.
        """
        # Verify this is the right user
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "❌ This enlightenment is not meant for you.",
                ephemeral=True
            )
            return
        
        # Get selected technique
        selected_tech = self.values[0]
        view: PavilionView = self.view
        view.selected_tech = selected_tech
        
        # Get technique data
        tech_data = TECHNIQUES.get(selected_tech, {})
        
        # Get user rank from view (stored when view was created)
        user_rank = view.user_rank
        meets_req = meets_rank_requirement(user_rank, tech_data.get("rank_required", "The Bound (Mortal)"))
        
        # Build inspection embed
        embed = technique_inspect_embed(
            tech_name=selected_tech,
            tech_data=tech_data,
            user_rank=user_rank,
            meets_requirements=meets_req
        )
        
        # Enable confirm button only if requirements are met
        view.confirm_btn.disabled = not meets_req
        if not meets_req:
            view.confirm_btn.label = "❌ Path Blocked"
            view.confirm_btn.style = discord.ButtonStyle.secondary
        else:
            view.confirm_btn.label = "✅ Begin Training"
            view.confirm_btn.style = discord.ButtonStyle.success
        
        await interaction.response.edit_message(embed=embed, view=view)


# ==========================================
# PAVILION VIEW (Main view with dropdown + confirm)
# ==========================================

class PavilionView(View):
    """
    Main Pavilion view containing technique dropdown and confirm button.
    
    This view is attached to the Pavilion menu and allows users to
    browse techniques, inspect them, and select one to learn.
    """
    
    def __init__(
        self,
        ctx,
        member_id: int,
        bot,
        available_techs: List[str],
        user_rank: str
    ):
        """
        Initialize the Pavilion view.
        
        Args:
            ctx: Command context
            member_id: Discord user ID
            bot: Bot instance
            available_techs: List of technique names user can learn
            user_rank: User's current cultivation rank
        """
        super().__init__(timeout=120)  # 2 minute timeout
        self.ctx = ctx
        self.member_id = member_id
        self.bot = bot
        self.selected_tech = None
        self.user_rank = user_rank
        
        # Add technique selector dropdown
        self.add_item(PavilionSelect(member_id, available_techs))
        
        # Add confirm button (disabled until a technique is selected)
        self.confirm_btn = Button(
            label="📜 Select a technique first",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.confirm_btn.callback = self.confirm_selection
        self.add_item(self.confirm_btn)
    
    async def confirm_selection(self, interaction: discord.Interaction):
        """
        Handle confirm button click.
        
        Sets the selected technique as the user's active technique
        and saves to database.
        """
        # Verify user
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "❌ This path is not yours to walk.",
                ephemeral=True
            )
            return
        
        # Check if technique was selected
        if not self.selected_tech:
            await interaction.response.send_message(
                "❌ Please select a scroll from the menu first.",
                ephemeral=True
            )
            return
        
        # Verify technique still exists
        if not validate_technique_exists(self.selected_tech):
            await interaction.response.send_message(
                "❌ This technique is no longer available.",
                ephemeral=True
            )
            return
        
        db = self.bot.db
        user_id = self.member_id
        
        # Double-check user doesn't already have a technique
        user = await db.users.find_one({"user_id": user_id})
        if user and user.get("active_tech") != "None":
            await interaction.response.send_message(
                "❌ You already have a technique. Use `!reset_technique` first.",
                ephemeral=True
            )
            return
        
        # Update user's active technique
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"active_tech": self.selected_tech, "mastery": 0.0}}
        )
        
        # Get technique data for the success message
        tech_data = TECHNIQUES.get(self.selected_tech, {})
        family_data = get_family_data(tech_data.get("family", "Unorthodox"))
        type_emoji = get_technique_type_emoji(tech_data.get("type", "Technique"))
        
        # Create success embed
        from embeds.pavilion_embeds import reset_success_embed  # Avoid circular import
        # Actually we'll make a dedicated success embed here
        embed = discord.Embed(
            title="✨ Path Bound",
            description=(
                f"{type_emoji} You have committed your soul to the **{self.selected_tech}**.\n"
                f"{family_data['emoji']} *{tech_data.get('description', 'A martial technique')}*\n\n"
                "Your journey begins. Use `!observe` or `!comprehend` to train."
            ),
            color=format_embed_color("win")
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def on_timeout(self):
        """
        Handle view timeout - disable all children and show expired message.
        """
        for child in self.children:
            child.disabled = True
        
        # Try to edit the original message to show it expired
        if hasattr(self, 'message'):
            try:
                embed = discord.Embed(
                    title="⏳ Pavilion Menu Expired",
                    description="The sacred scrolls have been sealed. Type `!pavilion` to open them again.",
                    color=format_embed_color("error")
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass


# ==========================================
# RESET CONFIRMATION VIEW
# ==========================================

class ResetConfirmView(View):
    """
    View for confirming technique reset with buttons.
    """
    
    def __init__(
        self,
        member_id: int,
        bot,
        tech_name: str,
        mastery: float,
        reset_cost: int,
        current_taels: int
    ):
        """
        Initialize the reset confirmation view.
        
        Args:
            member_id: Discord user ID
            bot: Bot instance
            tech_name: Name of technique being abandoned
            mastery: Current mastery percentage
            reset_cost: Taels cost to reset
            current_taels: User's current Taels
        """
        super().__init__(timeout=60)
        self.member_id = member_id
        self.bot = bot
        self.tech_name = tech_name
        self.mastery = mastery
        self.reset_cost = reset_cost
        self.current_taels = current_taels
        self.confirmed = False
    
    @discord.ui.button(label="✅ Confirm (500 Taels)", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        """Confirm reset - deduct Taels and remove technique."""
        if interaction.user.id != self.member_id:
            await interaction.response.send_message("❌ This is not your command.", ephemeral=True)
            return
        
        db = self.bot.db
        user_id = self.member_id
        
        # Deduct Taels and reset technique
        new_taels = self.current_taels - self.reset_cost
        
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"active_tech": "None", "mastery": 0.0, "taels": new_taels}}
        )
        
        from embeds.pavilion_embeds import reset_success_embed
        embed = reset_success_embed(
            old_tech=self.tech_name,
            lost_mastery=self.mastery,
            cost=self.reset_cost,
            new_taels=new_taels
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.confirmed = True
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        """Cancel reset - do nothing."""
        if interaction.user.id != self.member_id:
            await interaction.response.send_message("❌ This is not your command.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Reset Cancelled",
            description="Your technique remains unchanged.",
            color=format_embed_color("error")
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def on_timeout(self):
        """Handle timeout - disable buttons and show timeout message."""
        for child in self.children:
            child.disabled = True
        
        if hasattr(self, 'message'):
            try:
                embed = discord.Embed(
                    title="⏳ Reset Confirmation Expired",
                    description="No changes were made to your technique.",
                    color=format_embed_color("error")
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass


print("[DEBUG] pavilion_helpers.py: Pavilion helpers loaded successfully")