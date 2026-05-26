"""
backend/core_helpers.py - Core helper functions and UI views for character creation

This module handles:
- StartMenu class (interactive button view for background selection)
- Character creation logic (database insertion)
- Tutorial DM sending to new players

All database operations for character creation are handled here.
"""

import discord
import datetime
from backend.helpers import format_embed_color
from backend.db import is_user_banned, get_bot_setting, add_item
from backend.constants import BACKGROUNDS
from embeds.core_embeds import character_success_embed, tutorial_embed, already_registered_embed
import config

print("[DEBUG] core_helpers.py: Loading core helpers...")


# ==========================================
# START MENU VIEW (Background Selection Buttons)
# ==========================================

class StartMenu(discord.ui.View):
    """
    Interactive view for character creation background selection.
    
    Provides three buttons:
    - Laborer (⚒️) - Gains Taels easily, chance for mastery from work
    - Outcast (🌑) - Access to Shady Dealer in Bazaar
    - Hermit (🌿) - Faster HP/Vitality regeneration
    
    The view times out after 60 seconds if no interaction.
    """
    
    def __init__(self, user_id: int, bot):
        """
        Initialize the start menu view.
        
        Args:
            user_id: Discord user ID of the player creating a character
            bot: Bot instance for database access and user lookup
        """
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bot = bot

    async def handle_start(self, interaction: discord.Interaction, background_name: str):
        """
        Handle the character creation process for a chosen background.
        
        This method:
        1. Verifies the interaction is from the correct user
        2. Checks if user is banned
        3. Checks if feature is enabled
        4. Checks if user already has a character
        5. Creates the user document in the database
        6. Adds the starting item to inventory
        7. Sends success message and tutorial
        
        Args:
            interaction: The discord interaction from button click
            background_name: The chosen background (Laborer, Outcast, or Hermit)
        """
        print(f"[DEBUG] StartMenu.handle_start: User {interaction.user.id} chose {background_name}")

        # ========== STEP 1: Verify user identity ==========
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This destiny is not yours to claim.",
                ephemeral=True
            )
            return

        db = self.bot.db

        # ========== STEP 2: Check if user is banned ==========
        if await is_user_banned(db, interaction.user.id):
            await interaction.response.send_message(
                config.MSG_BANNED,
                ephemeral=True
            )
            return

        # ========== STEP 3: Check if feature is enabled ==========
        enabled = await get_bot_setting(db, "toggle_core", True)
        if not enabled:
            await interaction.response.send_message(
                config.MSG_FEATURE_DISABLED.format(feature="Character Creation"),
                ephemeral=True
            )
            return

        # ========== STEP 4: Check if user already exists ==========
        existing = await db.users.find_one({"user_id": interaction.user.id})
        if existing:
            embed = already_registered_embed()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ========== STEP 5: Get background data ==========
        bg_data = BACKGROUNDS.get(background_name, {})
        item_name = bg_data.get("item", "Torn Page")
        now = datetime.datetime.now().isoformat()

        # ========== STEP 6: Insert new user into database ==========
        await db.users.insert_one({
            "user_id": interaction.user.id,
            "background": background_name,
            "rank": "The Bound (Mortal)",
            "rank_id": 0,
            "item_id": item_name,
            "taels": 0,
            "ki": 0,
            "vitality": config.START_VITALITY,
            "hp": config.START_HP,
            "stage": "Initial",
            "last_refresh": now,
            "mastery": 0.0,
            "active_tech": "None",
            "boss_flags": "",
            "profession": "None",
            "prof_rank": "Apprentice",
            "prof_xp": 0,
            "prof_req_xp": 1000,
            "combat_mastery": 0.0,
            "meridian_damage": None,
            "daily_work_date": None,
            "daily_observe_date": None,
            "mastery_flags": None,
            "teaching_bonus_dodge": 0,
            "teaching_bonus_crit": 0,
            "teaching_bonus_dmg_reduction": 0,
            "teaching_bonus_regen": 0,
            "daily_give_date": None,
            "daily_give_count": 0,
            "hidden_techs_unlocked": None,
            "heartbeat_dm": 1,
            "minor_realm": "Initial",
            "minor_breakthrough_bonus_ki": 0,
            "minor_breakthrough_bonus_damage": 0,
            "minor_breakthrough_bonus_bt": 0,
        })

        # ========== STEP 7: Add starting item to inventory ==========
        # bound=True means the item cannot be sold or traded
        await add_item(db, interaction.user.id, item_name, 1, bound=True)

        print(f"[DEBUG] StartMenu.handle_start: Character created for {interaction.user.id} with item {item_name}")

        # ========== STEP 8: Send success embed ==========
        success_embed = character_success_embed(background_name, item_name)
        await interaction.response.edit_message(content=None, embed=success_embed, view=None)

        # ========== STEP 9: Send tutorial popup ==========
        await self._send_tutorial(interaction.user, interaction)
        
        # Stop the view to prevent further interactions
        self.stop()

    async def _send_tutorial(self, user: discord.User, interaction: discord.Interaction):
        """
        Send a tutorial message to the new player.
        
        Tries to send as a DM first. If DMs are disabled, sends as an
        ephemeral message in the channel instead.
        
        Args:
            user: The discord user to send the tutorial to
            interaction: The original interaction for fallback messaging
        """
        embed = tutorial_embed()
        
        try:
            await user.send(embed=embed)
            print(f"[DEBUG] StartMenu._send_tutorial: DM sent to {user.id}")
        except discord.Forbidden:
            # User has DMs disabled - send in channel as ephemeral
            await interaction.followup.send(embed=embed, ephemeral=True)
            print(f"[DEBUG] StartMenu._send_tutorial: DM failed, sent in channel for {user.id}")

    # ==========================================
    # BUTTON: LABORER
    # ==========================================
    
    @discord.ui.button(label="Laborer", style=discord.ButtonStyle.green, emoji="⚒️")
    async def laborer(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Laborer background button.
        
        Perks:
        - 15% lower Ki requirement for breakthrough
        - 10% chance of Mastery gain from !work
        - Starting item: Torn Page (mutates to Jade Scripture)
        """
        await self.handle_start(interaction, "Laborer")

    # ==========================================
    # BUTTON: OUTCAST
    # ==========================================
    
    @discord.ui.button(label="Outcast", style=discord.ButtonStyle.grey, emoji="🌑")
    async def outcast(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Outcast background button.
        
        Perks:
        - Unlocks Shady Dealer stall in the Bazaar
        - Access to forbidden items and techniques
        - Starting item: Black Coin (mutates to Shadow Seal)
        """
        await self.handle_start(interaction, "Outcast")

    # ==========================================
    # BUTTON: HERMIT
    # ==========================================
    
    @discord.ui.button(label="Hermit", style=discord.ButtonStyle.blurple, emoji="🌿")
    async def hermit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Hermit background button.
        
        Perks:
        - +15% HP/Vitality AFK regen rate
        - +10 Vitality/Ki from meditation (!recover)
        - Starting item: Glowing Fruit (mutates to Verdant Bone)
        """
        await self.handle_start(interaction, "Hermit")


# ==========================================
# HELPER: Check if feature is enabled
# ==========================================

async def is_core_enabled(bot) -> bool:
    """
    Check if the core feature (character creation) is enabled.
    
    Args:
        bot: Bot instance for database access
        
    Returns:
        bool: True if enabled, False otherwise
    """
    return await get_bot_setting(bot.db, "toggle_core", True)


# ==========================================
# HELPER: Get background details
# ==========================================

def get_background_details(background_name: str) -> dict:
    """
    Get the details of a specific background.
    
    Args:
        background_name: Name of the background (Laborer, Outcast, Hermit)
        
    Returns:
        dict: Background data from constants, or empty dict if not found
    """
    return BACKGROUNDS.get(background_name, {})


def get_all_backgrounds() -> dict:
    """
    Get all available backgrounds with their details.
    
    Returns:
        dict: All backgrounds from constants
    """
    return BACKGROUNDS


print("[DEBUG] core_helpers.py: Core helpers loaded successfully")