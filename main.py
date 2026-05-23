"""
main.py - Entry point for Empyrean Ascent Bot
Loads all components and starts the bot.

This file handles:
- Bot initialization
- MongoDB connection (via backend.mongodb_wrapper)
- Web dashboard (via backend.dashboard)
- Command loading from ./commands folder
- Graceful shutdown with shutdown source tracking
"""

import discord
from discord.ext import commands
import config
import os
import asyncio
import traceback
import time
import signal
import sys

# Backend imports (will be created in separate files)
from backend.mongodb_wrapper import MongoDBWrapper
from backend.dashboard import DashboardServer
from utils.logging import log_error_to_file

print("[DEBUG] main.py: Starting imports...")

# ==========================================
# BOT INTENTS
# ==========================================
# Intents define what events the bot receives from Discord
intents = discord.Intents.default()
intents.message_content = True   # Allows bot to read message content
intents.members = True           # Allows bot to track member join/leave events
print("[DEBUG] main.py: Intents configured")


# ==========================================
# MAIN BOT CLASS
# ==========================================
class MurimBot(commands.Bot):
    """
    Main bot class. Handles database connection, command loading, and shutdown.
    """
    
    def __init__(self):
        """Initialize the bot with configuration and empty state."""
        print("[DEBUG] MurimBot.__init__: Started")
        
        # Store configuration reference
        self.config = config
        
        # Database wrapper (will be initialized in setup_hook)
        self.db = None
        
        # Startup tracking
        self.startup_time = time.time()
        
        # Web dashboard server
        self.dashboard = None
        
        # Shutdown tracking
        self._shutdown_handled = False
        self.shutdown_source = None   # Will store why the bot shut down
        
        # Game state tracking (in-memory, not in database)
        self.active_combats = {}       # user_id -> True (currently in a hunt)
        self.command_cooldowns = {}    # user_id -> timestamp (manual cooldowns)
        self.is_meditating = set()     # user_id -> currently meditating

        # Initialize the parent Bot class
        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents
        )
        print("[DEBUG] MurimBot.__init__: Finished")

    async def setup_hook(self):
        """
        Called once before the bot connects to Discord.
        This is where we set up database, dashboard, and load commands.
        """
        print("[DEBUG] setup_hook: Started")
        overall_start = time.time()

        # ========== STEP 1: Validate Discord Token ==========
        if not config.TOKEN:
            print("[ERROR] No Discord token found in config/.env")
            log_error_to_file("FATAL: No Discord token found")
            self.shutdown_source = "missing_token"
            return

        # ========== STEP 2: Connect to MongoDB ==========
        print("📦 Connecting to MongoDB...")
        
        # Get MongoDB connection string from environment variables
        mongodb_uri = os.environ.get("MONGODB_URI")
        mongodb_db_name = os.environ.get("MONGODB_DB_NAME", "Empyrean-ascent")

        if not mongodb_uri:
            print("[ERROR] MONGODB_URI not set! Please set it in environment variables.")
            log_error_to_file("FATAL: MONGODB_URI not set")
            self.shutdown_source = "missing_mongodb_uri"
            return

        print(f"[DEBUG] MongoDB URI found (length: {len(mongodb_uri)})")

        # Create and connect the MongoDB wrapper
        self.db = MongoDBWrapper(mongodb_uri, mongodb_db_name)
        await self.db.connect()
        await self.db.initialize_default_settings()

        print("🔗 MongoDB Connection Established")
        print("[DEBUG] setup_hook: Database connection opened")

        # ========== STEP 3: Start Web Dashboard ==========
        if config.WEB_DASHBOARD_ENABLED:
            try:
                self.dashboard = DashboardServer(self)
                await self.dashboard.start()
                print("[DEBUG] Web dashboard started")
            except Exception as e:
                print(f"[WARN] Could not start web dashboard: {e}")
                log_error_to_file(f"Dashboard start failed: {e}")

        # ========== STEP 4: Load All Commands ==========
        print("--- Loading Empyrean Systems (Commands) ---")
        commands_loaded = 0
        commands_failed = []

        # Create commands directory if it doesn't exist
        if not os.path.exists("./commands"):
            print("[WARN] No 'commands' directory found! Creating empty commands directory.")
            os.makedirs("./commands")
            with open("./commands/__init__.py", "w") as f:
                f.write("# Commands package\n")

        # Load every .py file from the commands folder (except __init__.py)
        for filename in os.listdir("./commands"):
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    print(f"[DEBUG] setup_hook: Attempting to load commands.{filename[:-3]}")
                    await self.load_extension(f"commands.{filename[:-3]}")
                    print(f"✅ Loaded: {filename}")
                    commands_loaded += 1
                except Exception as e:
                    error_msg = f"Failed to load {filename}: {e}\n{traceback.format_exc()}"
                    print(f"❌ Error Loading {filename}: {e}")
                    log_error_to_file(error_msg)
                    commands_failed.append(filename)
                    if self.dashboard:
                        self.dashboard.set_last_error(error_msg[:200])

        # Print summary of command loading
        load_time = time.time() - overall_start
        print(f"[DEBUG] setup_hook: Loaded {commands_loaded} commands, {len(commands_failed)} failed in {load_time:.2f}s")
        if commands_failed:
            print(f"[DEBUG] setup_hook: Failed commands: {commands_failed}")

        # Store stats for dashboard
        self.commands_loaded_count = commands_loaded
        self.commands_failed_list = commands_failed
        self.startup_duration = load_time

    async def close(self):
        """
        Graceful shutdown handler.
        Called when the bot is stopping (Ctrl+C, Render signal, or crash).
        """
        print("[DEBUG] close: Graceful shutdown started")
        
        # Prevent multiple shutdown calls
        if self._shutdown_handled:
            return
        self._shutdown_handled = True

        # Log shutdown source if available
        if self.shutdown_source:
            log_error_to_file(f"Shutdown initiated by: {self.shutdown_source}")
            print(f"[DEBUG] Shutdown source: {self.shutdown_source}")

        # Stop web dashboard
        if self.dashboard:
            try:
                await self.dashboard.stop()
                print("[DEBUG] Web dashboard stopped")
            except Exception as e:
                print(f"[DEBUG] Error stopping dashboard: {e}")

        # Close database connection
        if self.db:
            try:
                await self.db.close()
                print("[DEBUG] Database connection closed")
            except Exception as e:
                print(f"[DEBUG] Error closing database: {e}")

        # Call parent class close
        await super().close()
        print("[DEBUG] close: Graceful shutdown complete")

    async def on_ready(self):
        """
        Called when the bot has successfully connected to Discord.
        This is where we announce that the bot is online.
        """
        startup_duration = time.time() - self.startup_time
        
        # Print startup banner
        print("\n--- Murim: Empyrean Ascent is Online ---")
        print(f"Logged in as: {self.user.name}")
        print(f"Startup took {startup_duration:.2f} seconds")
        print(f"Commands loaded: {len(self.cogs)}")
        print("Status: Database Sync Complete")
        print("------------------------------------------")
        print("[DEBUG] on_ready: Bot is fully ready")

        # Sync slash commands with Discord (makes /commands available)
        try:
            synced = await self.tree.sync()
            print(f"[DEBUG] Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"[WARN] Failed to sync slash commands: {e}")

        # Send startup announcement to configured channel (if any)
        if config.STARTUP_ANNOUNCE_CHANNEL_ID:
            try:
                channel = self.get_channel(config.STARTUP_ANNOUNCE_CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title="🌿 Empyrean Ascent Bot Online",
                        description=f"Bot started successfully in {startup_duration:.2f}s\nLoaded {len(self.cogs)} commands",
                        color=0x00FF00
                    )
                    await channel.send(embed=embed)
                    print("[DEBUG] Startup announcement sent to Discord")
                else:
                    print(f"[WARN] Could not find channel {config.STARTUP_ANNOUNCE_CHANNEL_ID}")
            except Exception as e:
                print(f"[WARN] Failed to send startup announcement: {e}")
                log_error_to_file(f"Startup announcement failed: {e}")


# ==========================================
# GRACEFUL SHUTDOWN HANDLER
# ==========================================
bot_instance = None

def signal_handler(signum, frame):
    """
    Handle system signals (Ctrl+C, SIGTERM from Render).
    Records the shutdown source before initiating cleanup.
    """
    # Map signal number to human-readable name
    signal_names = {
        signal.SIGINT: "SIGINT (Ctrl+C from user)",
        signal.SIGTERM: "SIGTERM (Render shutdown or system)",
    }
    signal_name = signal_names.get(signum, f"Unknown signal ({signum})")
    
    print(f"\n[DEBUG] Received shutdown signal: {signal_name}")
    
    if bot_instance:
        bot_instance.shutdown_source = signal_name
        asyncio.create_task(bot_instance.close())


# ==========================================
# RUN BOT
# ==========================================
if __name__ == "__main__":
    print("[DEBUG] main.py: Starting bot...")
    
    # Create bot instance
    bot_instance = MurimBot()
    bot = bot_instance

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal (from Render)

    try:
        # Start the bot (this blocks until the bot stops)
        bot.run(config.TOKEN)
    except KeyboardInterrupt:
        # This should be caught by signal handler, but just in case
        print("[DEBUG] Bot stopped by user (KeyboardInterrupt)")
        if bot_instance:
            bot_instance.shutdown_source = "KeyboardInterrupt (fallback)"
    except Exception as e:
        # Any other unexpected error
        print(f"[DEBUG] main.py: Fatal error: {e}")
        traceback.print_exc()
        log_error_to_file(f"FATAL: {e}\n{traceback.format_exc()}")
        if bot_instance:
            bot_instance.shutdown_source = f"unexpected_error: {type(e).__name__}"
    finally:
        print("[DEBUG] main.py: Bot shutdown complete")