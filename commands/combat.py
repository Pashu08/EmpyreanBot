"""
commands/combat.py - Command logic for Combat cog
Contains all combat-related commands and UI views.

This file handles:
- hunt command (main combat system)
- huntleaderboard command (statistics leaderboard)
- CombatView class (interactive battle UI)
- LeaderboardView class (navigation buttons for leaderboards)

Embed designs are imported from embeds.combat_embeds.
Combat helpers are imported from backend.combat_helpers.
"""

import discord
from discord.ext import commands
import random
import asyncio
import datetime
from typing import Dict, Any, Optional

# Backend imports
from backend.helpers import format_embed_color, has_meridian_damage
from backend.db import (
    get_bot_setting, is_user_banned, get_user_stat,
    update_user_stat, add_item, remove_item
)
from backend.constants import ENEMIES, SHOP_ITEMS, TECHNIQUES
from backend.combat_helpers import (
    RARITIES,
    ENEMY_NAMES,
    generate_health_bar,
    get_rank_attack,
    get_technique_attack,
    calculate_normal_damage,
    calculate_technique_damage,
    calculate_enemy_damage,
    choose_enemy_rarity,
    get_enemy_name,
    generate_enemy,
    calculate_reward,
    calculate_tael_loss,
    process_technique_effect,
    get_enemy_tier_from_player_rank
)

# Embed imports
from embeds.combat_embeds import (
    combat_embed,
    victory_embed,
    defeat_embed,
    flee_embed,
    hunt_cooldown_embed,
    encounter_start_embed,
    leaderboard_embed,
    technique_disabled_embed,
    not_enough_ki_embed,
    meridian_damage_embed,
    mortal_cannot_hunt_embed,
    already_in_combat_embed
)

import config

print("[DEBUG] commands/combat.py: Loading Combat commands...")


# ==========================================
# LEADERBOARD VIEW (Navigation Buttons)
# ==========================================

class LeaderboardView(discord.ui.View):
    """
    Interactive view for hunt leaderboards.
    Provides buttons to switch between different leaderboard categories.
    """
    
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.mode = "total_hunts"  # Default mode

    async def get_leaderboard_data(self, mode: str) -> tuple:
        """
        Fetch leaderboard data from database based on selected mode.
        
        Args:
            mode: Leaderboard mode (total_hunts, highest_damage, fastest_kill, etc.)
            
        Returns:
            tuple: (title, rows) where rows is list of (rank, user_name, value)
        """
        db = self.bot.db
        collection = db.users

        # Configure based on mode
        if mode == "total_hunts":
            sort_field = "hunt_total"
            sort_order = -1
            title = "🏆 Most Hunts (Lifetime)"
            value_field = "hunt_total"
        elif mode == "highest_damage":
            sort_field = "hunt_damage_max"
            sort_order = -1
            title = "💥 Highest Single Hit Damage"
            value_field = "hunt_damage_max"
        elif mode == "fastest_kill":
            sort_field = "hunt_fastest_turns"
            sort_order = 1  # Ascending (lower turns is better)
            title = "⚡ Fastest Kill (least turns)"
            value_field = "hunt_fastest_turns"
        elif mode == "elite_kills":
            sort_field = "hunt_elite_kills"
            sort_order = -1
            title = "👑 Elite & Boss Kills"
            value_field = "hunt_elite_kills"
        else:  # taels_earned
            sort_field = "hunt_taels_earned"
            sort_order = -1
            title = "💰 Total Taels from Hunting"
            value_field = "hunt_taels_earned"

        # Query top 10 players
        cursor = collection.find({value_field: {"$gt": 0}}).sort(sort_field, sort_order).limit(10)
        docs = await cursor.to_list(length=10)

        # Format rows
        rows = []
        for i, doc in enumerate(docs, 1):
            user_id = doc.get("user_id")
            value = doc.get(value_field, 0)
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"<@{user_id}>"
            rows.append((i, name, value))

        return title, rows

    async def get_leaderboard_embed(self, mode: str) -> discord.Embed:
        """
        Get the embed for the current leaderboard mode.
        
        Args:
            mode: Leaderboard mode to display
            
        Returns:
            discord.Embed: Formatted leaderboard embed
        """
        title, rows = await self.get_leaderboard_data(mode)
        requester = self.bot.get_user(self.user_id)
        requester_name = requester.display_name if requester else "Unknown"
        
        return leaderboard_embed(title, rows, mode, requester_name)

    async def update(self, interaction: discord.Interaction):
        """Update the leaderboard embed with current mode."""
        embed = await self.get_leaderboard_embed(self.mode)
        await interaction.response.edit_message(embed=embed, view=self)

    # ========== Button Callbacks ==========
    
    @discord.ui.button(label="🏆 Total Hunts", style=discord.ButtonStyle.secondary)
    async def btn_total(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "total_hunts"
        await self.update(interaction)

    @discord.ui.button(label="💥 Highest Damage", style=discord.ButtonStyle.secondary)
    async def btn_damage(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "highest_damage"
        await self.update(interaction)

    @discord.ui.button(label="⚡ Fastest Kill", style=discord.ButtonStyle.secondary)
    async def btn_fastest(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "fastest_kill"
        await self.update(interaction)

    @discord.ui.button(label="👑 Elite Kills", style=discord.ButtonStyle.secondary)
    async def btn_elite(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "elite_kills"
        await self.update(interaction)

    @discord.ui.button(label="💰 Taels Earned", style=discord.ButtonStyle.secondary)
    async def btn_taels(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "taels_earned"
        await self.update(interaction)


# ==========================================
# COMBAT VIEW (Battle Interface)
# ==========================================

class CombatView(discord.ui.View):
    """
    Interactive view for turn-based combat.
    Provides Strike, Technique, and Run Away buttons.
    """
    
    def __init__(
        self,
        bot,
        author_id: int,
        player_data: tuple,
        enemy_data: dict,
        rarity_data: dict,
        color: int,
        pre_hunt_stats: dict
    ):
        """
        Initialize the combat view.
        
        Args:
            bot: Bot instance
            author_id: Discord user ID of the player
            player_data: Tuple of (user_id, hp, vitality, ki, mastery, active_tech, rank, combat_mastery, taels)
            enemy_data: Dictionary with enemy name, hp, atk
            rarity_data: Rarity modifiers for this enemy
            color: Embed color for this enemy
            pre_hunt_stats: Original HP/Vitality before hunt (for restoration)
        """
        super().__init__(timeout=180)
        self.bot = bot
        self.author_id = author_id
        self.rarity_data = rarity_data
        self.color = color
        self.lock = asyncio.Lock()  # Prevent concurrent button presses
        self.ended = False
        self.pre_hunt_stats = pre_hunt_stats

        # Unpack player data
        # player_data: (user_id, hp, vitality, ki, mastery, active_tech, rank, combat_mastery, taels)
        self.player = list(player_data)
        
        # Enemy data with max HP tracking
        self.enemy = enemy_data.copy()
        self.enemy["max_hp"] = self.enemy["hp"]
        
        # Store max HP for health bar calculations
        self.player_max_hp = self.player[1]
        self.enemy_max_hp = self.enemy["hp"]

        # Combat state
        self.combat_log = "The battle lines are drawn."
        self.turn = 1
        self.daily_hunts_today = 0
        self.last_damage = 0

        # Configure technique button
        tech_name = self.player[5]
        if tech_name and tech_name != "None" and tech_name in TECHNIQUES:
            self.technique.label = tech_name
            self.tech_effect_text = TECHNIQUES[tech_name]["effect_text"]
        else:
            self.technique.disabled = True
            self.technique.label = "No Technique"
            self.tech_effect_text = "None"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original player can interact with the buttons."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This is not your fight.", ephemeral=True)
            return False
        return not self.ended

    async def safe_edit(self, interaction: discord.Interaction, embed: discord.Embed, view=None):
        """
        Safely edit the original message, handling potential errors.
        
        Args:
            interaction: The discord interaction
            embed: The embed to send
            view: The view to attach (or None to remove)
        """
        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                await interaction.edit_original_response(embed=embed, view=view)
        except (discord.NotFound, discord.HTTPException):
            pass  # Message was deleted or interaction expired

    async def update_embed(self, interaction: discord.Interaction):
        """
        Update the combat embed with current HP values and combat log.
        
        Args:
            interaction: The discord interaction
        """
        # Check if battle has ended (player or enemy died)
        if self.player[1] <= 0 or self.enemy["hp"] <= 0:
            self.ended = True
            for child in self.children:
                child.disabled = True
            await self.end_battle(interaction)
            return

        # Create and send updated embed
        embed = combat_embed(
            enemy_name=self.enemy["name"],
            color=self.color,
            player_hp=self.player[1],
            player_max_hp=self.player_max_hp,
            enemy_hp=self.enemy["hp"],
            enemy_max_hp=self.enemy_max_hp,
            combat_log=self.combat_log,
            turn=self.turn,
            ki=self.player[3],
            tech_effect_text=self.tech_effect_text
        )
        await self.safe_edit(interaction, embed, self)

    async def end_battle(self, interaction: discord.Interaction):
        """
        End the battle, calculate rewards or penalties, and clean up.
        
        Args:
            interaction: The discord interaction
        """
        db = self.bot.db
        user_id = self.player[0]

        # RESTORE original HP and Vitality (no permanent loss from combat)
        original = self.pre_hunt_stats[user_id]
        await update_user_stat(db, user_id, "hp", original["hp"])
        await update_user_stat(db, user_id, "vitality", original["vitality"])

        # ========== DEFEAT CASE ==========
        if self.player[1] <= 0:
            tael_loss = calculate_tael_loss(self.player[8])
            new_taels = max(0, self.player[8] - tael_loss)
            await update_user_stat(db, user_id, "taels", new_taels)
            
            # Apply meridian damage (10 minute debuff)
            debuff = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            await update_user_stat(db, user_id, "meridian_damage", debuff)
            
            embed = defeat_embed(self.enemy["name"], tael_loss)
            await self.safe_edit(interaction, embed, None)

        # ========== VICTORY CASE ==========
        else:
            # Calculate reward
            base_reward_range = (50, 150)
            daily_bonus = self.daily_hunts_today < 3
            final_reward = calculate_reward(
                base_reward_range=base_reward_range,
                rarity_multiplier=self.rarity_data["reward_mult"],
                daily_bonus_active=daily_bonus,
                combat_mastery=self.player[7]
            )
            
            # Update Taels
            new_taels = self.player[8] + final_reward
            await update_user_stat(db, user_id, "taels", new_taels)
            
            # Update Combat Mastery (+2 per victory)
            new_cm = self.player[7] + 2.0
            await update_user_stat(db, user_id, "combat_mastery", new_cm)
            
            # Update hunt statistics (using MongoDB inc operations)
            is_elite = self.rarity_data["name"] in ("Elite", "Master", "Grandmaster", "Mythical")
            await db.users.update_one(
                {"user_id": user_id},
                {
                    "$inc": {
                        "hunt_total": 1,
                        "hunt_taels_earned": final_reward,
                        "hunt_damage_max": self.last_damage,
                        "hunt_elite_kills": 1 if is_elite else 0
                    },
                    "$min": {"hunt_fastest_turns": self.turn}
                },
                upsert=True
            )
            
            # Check for item drop
            drop_item = None
            if random.random() < self.rarity_data["drop_chance"]:
                possible_items = list(SHOP_ITEMS.keys())
                drop_item = random.choice(possible_items)
                await add_item(db, user_id, drop_item, 1)
            
            # Check if this was a record fastest kill
            fastest_turn_record = False  # This would need to fetch current record
            
            embed = victory_embed(
                enemy_name=self.enemy["name"],
                final_reward=final_reward,
                combat_mastery_gain=2.0,
                drop_item=drop_item,
                fastest_turn_record=fastest_turn_record
            )
            await self.safe_edit(interaction, embed, None)

        # Remove from active combat tracking
        if hasattr(self.bot, 'active_combats') and user_id in self.bot.active_combats:
            del self.bot.active_combats[user_id]
        
        self.stop()

    # ========== BUTTON: STRIKE ==========
    
    @discord.ui.button(label="Strike", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def strike(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Perform a normal strike attack.
        Cost: None
        Damage: Based on rank + random variance
        """
        async with self.lock:
            if self.ended:
                return
            
            # Calculate player's attack
            base_atk = get_rank_attack(self.player[6])
            damage, is_critical = calculate_normal_damage(base_atk)
            
            # Apply damage to enemy
            self.enemy["hp"] = max(0, self.enemy["hp"] - damage)
            self.last_damage = damage
            
            # Update combat log
            crit_text = " **CRITICAL!**" if is_critical else ""
            self.combat_log = f"Turn {self.turn}: You strike for {damage}{crit_text}."
            
            # Enemy counter-attack if still alive
            if self.enemy["hp"] > 0:
                enemy_damage = calculate_enemy_damage(
                    self.enemy["atk"],
                    self.player[5]
                )
                self.player[1] = max(0, self.player[1] - enemy_damage)
                self.combat_log += f"\nTurn {self.turn}: Enemy hits for {enemy_damage}."
            
            self.turn += 1
            await self.update_embed(interaction)

    # ========== BUTTON: TECHNIQUE ==========
    
    @discord.ui.button(label="Technique", style=discord.ButtonStyle.primary, emoji="🌀")
    async def technique(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Perform a technique attack.
        Cost: 15 Ki
        Damage: Based on rank, technique attack stat, and mastery multiplier
        """
        async with self.lock:
            if self.ended:
                return
            
            # Check Ki cost
            KI_COST = 15
            if self.player[3] < KI_COST:
                embed = not_enough_ki_embed(KI_COST)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Deduct Ki cost
            self.player[3] -= KI_COST
            
            # Calculate technique damage
            tech_name = self.player[5]
            base_atk = get_technique_attack(self.player[6])
            damage, is_critical = calculate_technique_damage(
                base_atk,
                self.player[4]  # mastery percentage
            )
            
            # Apply damage to enemy
            self.enemy["hp"] = max(0, self.enemy["hp"] - damage)
            self.last_damage = damage
            
            # Process special technique effects
            effect_result = process_technique_effect(
                tech_name,
                self.player[1],
                self.player_max_hp,
                self.enemy["hp"],
                damage
            )
            
            # Apply extra damage from double strike
            if effect_result["extra_damage"] > 0:
                self.enemy["hp"] = max(0, self.enemy["hp"] - effect_result["extra_damage"])
                damage += effect_result["extra_damage"]
            
            # Apply healing from Vajra Guard Mantra
            if effect_result["heal_amount"] > 0:
                self.player[1] = min(self.player_max_hp, self.player[1] + effect_result["heal_amount"])
            
            # Update combat log
            crit_text = " **CRITICAL!**" if is_critical else ""
            self.combat_log = f"Turn {self.turn}: [{tech_name}] deals {damage}{crit_text}."
            
            if effect_result["effect_message"]:
                self.combat_log += f"\n{effect_result['effect_message']}"
            
            # Enemy counter-attack if still alive
            if self.enemy["hp"] > 0:
                enemy_damage = calculate_enemy_damage(
                    self.enemy["atk"],
                    self.player[5]
                )
                self.player[1] = max(0, self.player[1] - enemy_damage)
                self.combat_log += f"\nTurn {self.turn}: Enemy hits for {enemy_damage}."
            
            self.turn += 1
            await self.update_embed(interaction)

    # ========== BUTTON: RUN AWAY ==========
    
    @discord.ui.button(label="Run Away", style=discord.ButtonStyle.secondary, emoji="🏃")
    async def run_away(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Flee from battle.
        Penalty: Lose 10% of Taels, 2 minute hunt cooldown
        """
        async with self.lock:
            if self.ended:
                return
            
            self.ended = True
            for child in self.children:
                child.disabled = True
            
            db = self.bot.db
            user_id = self.player[0]
            
            # Restore original HP and Vitality
            original = self.pre_hunt_stats[user_id]
            await update_user_stat(db, user_id, "hp", original["hp"])
            await update_user_stat(db, user_id, "vitality", original["vitality"])
            
            # Apply Taels penalty
            tael_loss = calculate_tael_loss(self.player[8])
            new_taels = max(0, self.player[8] - tael_loss)
            await update_user_stat(db, user_id, "taels", new_taels)
            
            # Apply cooldown (2 minutes)
            if not hasattr(self.bot, 'hunt_cooldowns'):
                self.bot.hunt_cooldowns = {}
            self.bot.hunt_cooldowns[user_id] = datetime.datetime.now() + datetime.timedelta(minutes=2)
            
            # Send flee embed
            embed = flee_embed(tael_loss, cooldown_minutes=2)
            await self.safe_edit(interaction, embed, None)
            
            # Clean up
            if hasattr(self.bot, 'active_combats') and user_id in self.bot.active_combats:
                del self.bot.active_combats[user_id]
            
            self.stop()


# ==========================================
# MAIN COG
# ==========================================

class Combat(commands.Cog):
    """
    Combat cog - Handles hunting, combat, and leaderboards.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.bot.hunt_cooldowns = {}  # Track flee cooldowns
        print("[DEBUG] Combat cog initialized")

    async def _is_feature_enabled(self, ctx: commands.Context) -> bool:
        """
        Check if combat feature is enabled in bot settings.
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if enabled, False otherwise
        """
        enabled = await get_bot_setting(self.bot.db, "toggle_combat", True)
        if not enabled:
            await ctx.send(
                config.MSG_FEATURE_DISABLED.format(feature="Combat"),
                ephemeral=True
            )
        return enabled

    # ==========================================
    # COMMAND: HUNT
    # ==========================================
    
    @commands.hybrid_command(name="hunt", aliases=["h"])
    async def hunt(self, ctx: commands.Context):
        """
        Hunt spirit beasts to earn Taels and Combat Mastery.
        
        Usage: !hunt
        
        Features:
        - 5 enemy rarities: Common → Elite → Master → Grandmaster → Mythical
        - Higher rarities = better rewards but tougher enemies
        - Daily bonus: First 3 hunts give 2x rewards
        - Combat Mastery increases reward multiplier
        - Special item drops from rare enemies
        """
        print(f"[DEBUG] combat.hunt: Called by {ctx.author.id}")

        # Feature toggle check
        if not await self._is_feature_enabled(ctx):
            return
        
        # Ban check
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)

        user_id = ctx.author.id
        db = self.bot.db

        # ========== FLEE COOLDOWN CHECK ==========
        if hasattr(self.bot, 'hunt_cooldowns') and user_id in self.bot.hunt_cooldowns:
            cooldown_end = self.bot.hunt_cooldowns[user_id]
            if datetime.datetime.now() < cooldown_end:
                remaining = int((cooldown_end - datetime.datetime.now()).total_seconds())
                embed = hunt_cooldown_embed(remaining)
                return await ctx.send(embed=embed, ephemeral=True)
            else:
                del self.bot.hunt_cooldowns[user_id]

        # ========== ACTIVE COMBAT CHECK ==========
        if not hasattr(self.bot, 'active_combats'):
            self.bot.active_combats = {}
        if user_id in self.bot.active_combats:
            embed = already_in_combat_embed()
            return await ctx.send(embed=embed, ephemeral=True)

        # ========== FETCH PLAYER DATA ==========
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            return await ctx.send(config.MSG_NOT_REGISTERED, ephemeral=True)

        # ========== MERIDIAN DAMAGE CHECK ==========
        damaged, _ = has_meridian_damage(user.get("meridian_damage"))
        if damaged:
            embed = meridian_damage_embed()
            return await ctx.send(embed=embed, ephemeral=True)

        # ========== RANK CHECK (Mortals cannot hunt) ==========
        rank = user.get("rank", "The Bound (Mortal)")
        enemy_tier = get_enemy_tier_from_player_rank(rank)
        if enemy_tier is None:
            embed = mortal_cannot_hunt_embed()
            return await ctx.send(embed=embed, ephemeral=True)

        # ========== GENERATE ENEMY ==========
        enemy_data, rarity_name, rarity_data = generate_enemy(enemy_tier)
        enemy_name = enemy_data["name"]
        enemy_hp = enemy_data["hp"]
        enemy_atk = enemy_data["atk"]
        color = enemy_data["color"]

        # ========== DAILY HUNT TRACKING ==========
        today = datetime.datetime.now().date().isoformat()
        daily_hunts = user.get("daily_hunts", 0)
        last_date = user.get("last_hunt_date", "")
        
        if last_date != today:
            daily_hunts = 0
        
        daily_hunts += 1
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"daily_hunts": daily_hunts, "last_hunt_date": today}}
        )

        # ========== SAVE PRE-HUNT STATS ==========
        pre_hunt_stats = {
            user_id: {
                "hp": user.get("hp", 100),
                "vitality": user.get("vitality", 100),
            }
        }

        # Mark player as in combat
        self.bot.active_combats[user_id] = True

        # Prepare player data tuple for CombatView
        player_tuple = (
            user_id,
            user.get("hp", 100),
            user.get("vitality", 100),
            user.get("ki", 0),
            user.get("mastery", 0.0),
            user.get("active_tech", "None"),
            rank,
            user.get("combat_mastery", 0),
            user.get("taels", 0)
        )

        # Create combat view
        view = CombatView(
            self.bot,
            user_id,
            player_tuple,
            enemy_data,
            rarity_data,
            color,
            pre_hunt_stats
        )
        view.daily_hunts_today = daily_hunts - 1

        # Send encounter start embed
        embed = encounter_start_embed(
            enemy_name=enemy_name,
            rarity=rarity_name,
            color=color,
            player_hp=user.get("hp", 100),
            player_max_hp=user.get("hp", 100),
            enemy_hp=enemy_hp
        )
        await ctx.send(embed=embed, view=view)

    # ==========================================
    # COMMAND: HUNT LEADERBOARD
    # ==========================================
    
    @commands.hybrid_command(name="huntleaderboard", aliases=["hlb"])
    async def hunt_leaderboard(self, ctx: commands.Context):
        """
        View hunting statistics leaderboards.
        
        Usage: !huntleaderboard or !hlb
        
        Categories:
        - Total Hunts (lifetime)
        - Highest Single Hit Damage
        - Fastest Kill (least turns)
        - Elite & Boss Kills
        - Total Taels Earned from Hunting
        
        Use the buttons below the leaderboard to switch categories.
        """
        print(f"[DEBUG] combat.hunt_leaderboard: Called by {ctx.author.id}")
        
        # Feature toggle check
        if not await self._is_feature_enabled(ctx):
            return
        
        # Ban check
        if await is_user_banned(self.bot.db, ctx.author.id):
            return await ctx.send(config.MSG_BANNED, ephemeral=True)
        
        # Create and send leaderboard view
        view = LeaderboardView(self.bot, ctx.author.id)
        embed = await view.get_leaderboard_embed("total_hunts")
        await ctx.send(embed=embed, view=view)


# ==========================================
# SETUP FUNCTION
# ==========================================

async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(Combat(bot))
    print("[DEBUG] commands/combat.py: Setup complete")