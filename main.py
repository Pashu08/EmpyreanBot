import discord
from discord.ext import commands
import aiosqlite
import config
import os
import asyncio
import traceback
import time
import datetime
from aiohttp import web
import json
from libsql_experimental import create_client

print("[DEBUG] main.py: Starting imports...")

# ==========================================
# ERROR LOGGING TO FILE (with rotation)
# ==========================================
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB

def rotate_log_file(log_path):
    """Rotate log file if it exceeds max size."""
    if os.path.exists(log_path) and os.path.getsize(log_path) > MAX_LOG_SIZE:
        old_log = log_path.replace(".log", "_old.log")
        if os.path.exists(old_log):
            os.remove(old_log)
        os.rename(log_path, old_log)

def log_error_to_file(error_message):
    """Append error to bot_errors.log, rotate if too large."""
    log_path = "bot_errors.log"
    try:
        rotate_log_file(log_path)
        with open(log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {error_message}\n")
    except:
        pass

# ==========================================
# WEB DASHBOARD
# ==========================================
class DashboardServer:
    def __init__(self, bot):
        self.bot = bot
        self.app = None
        self.runner = None
        self.site = None
        self.start_time = datetime.datetime.now()
        self.last_error = "No errors yet"

    def set_last_error(self, error):
        self.last_error = str(error)[:500]

    async def handle_index(self, request):
        cog_count = len(self.bot.cogs)
        cog_names = list(self.bot.cogs.keys())
        uptime = datetime.datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]

        user_count = 0
        if self.bot.db:
            try:
                async with self.bot.db.execute("SELECT COUNT(*) FROM users") as cur:
                    row = await cur.fetchone()
                    user_count = row[0] if row else 0
            except:
                pass

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Empyrean Bot Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #1a1a2e; color: #eee; }}
                h1 {{ color: #00ffcc; }}
                .status {{ background: #0f3460; padding: 20px; border-radius: 10px; margin: 10px 0; }}
                .online {{ color: #00ff00; }}
                .value {{ font-weight: bold; color: #ffcc00; }}
            </style>
        </head>
        <body>
            <h1>🌿 Empyrean Ascent Bot Dashboard</h1>
            <div class="status">
                <p>🤖 Bot Status: <span class="online">ONLINE</span></p>
                <p>📦 Cogs Loaded: <span class="value">{cog_count}</span> / {len(os.listdir('./cogs')) if os.path.exists('./cogs') else 0}</p>
                <p>⏱️ Uptime: <span class="value">{uptime_str}</span></p>
                <p>👥 Registered Users: <span class="value">{user_count}</span></p>
                <p>⚠️ Last Error: <span class="value">{self.last_error}</span></p>
                <hr>
                <p>📁 Loaded Cogs: {', '.join(cog_names) if cog_names else 'None'}</p>
            </div>
            <footer>Refresh page to update | Empyrean Ascent Bot</footer>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def start(self):
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', config.WEB_DASHBOARD_PORT)
        await self.site.start()

        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"[DEBUG] Web dashboard: http://localhost:{config.WEB_DASHBOARD_PORT}")
            print(f"[DEBUG] Web dashboard: http://{local_ip}:{config.WEB_DASHBOARD_PORT}")
        except:
            print(f"[DEBUG] Web dashboard: http://localhost:{config.WEB_DASHBOARD_PORT}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()

# ==========================================
# DATABASE: SELF-HEALING AUTO-MIGRATION
# ==========================================
async def init_db():
    print("[DEBUG] init_db: Started")
    start_time = time.time()
    # Added timeout parameter to prevent database locks
    async with aiosqlite.connect("murim.db", timeout=30.0) as conn:
        c = await conn.cursor()

        # --- Users table (existing + new columns) ---
        MASTER_SCHEMA = {
            "user_id": "INTEGER PRIMARY KEY",
            "background": "TEXT",
            "rank_id": "INTEGER DEFAULT 0",
            "rank": "TEXT DEFAULT 'The Bound (Mortal)'",
            "item_id": "TEXT",
            "taels": "INTEGER DEFAULT 0",
            "ki": "INTEGER DEFAULT 0",
            "vitality": "INTEGER DEFAULT 100",
            "hp": "INTEGER DEFAULT 100",
            "stage": "TEXT DEFAULT 'Initial'",
            "last_refresh": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "mastery": "REAL DEFAULT 0.0",
            "active_tech": "TEXT DEFAULT 'None'",
            "boss_flags": "TEXT DEFAULT ''",
            "profession": "TEXT DEFAULT 'None'",
            "prof_rank": "TEXT DEFAULT 'Apprentice'",
            "prof_xp": "INTEGER DEFAULT 0",
            "prof_req_xp": "INTEGER DEFAULT 1000",
            "combat_mastery": "REAL DEFAULT 0.0",
            "meridian_damage": "TEXT",
            "daily_work_date": "TEXT",
            "daily_observe_date": "TEXT",
            "mastery_flags": "TEXT",
            "teaching_bonus_dodge": "INTEGER DEFAULT 0",
            "teaching_bonus_crit": "INTEGER DEFAULT 0",
            "teaching_bonus_dmg_reduction": "INTEGER DEFAULT 0",
            "teaching_bonus_regen": "INTEGER DEFAULT 0",
            "daily_give_date": "TEXT",
            "daily_give_count": "INTEGER DEFAULT 0",
            "hidden_techs_unlocked": "TEXT",
            # ADDED: heartbeat_dm column directly in schema
            "heartbeat_dm": "INTEGER DEFAULT 1",
            "minor_realm": "TEXT DEFAULT 'Initial'",
            "minor_breakthrough_bonus_ki": "INTEGER DEFAULT 0",
            "minor_breakthrough_bonus_damage": "INTEGER DEFAULT 0",
            "minor_breakthrough_bonus_bt": "INTEGER DEFAULT 0",
        }

        await c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        print("[DEBUG] init_db: users table ensured")

        await c.execute("PRAGMA table_info(users)")
        existing_columns_data = await c.fetchall()
        existing_columns = [info[1] for info in existing_columns_data]

        for col_name, col_type in MASTER_SCHEMA.items():
            if col_name not in existing_columns:
                try:
                    await c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    print(f"[DEBUG] init_db: Added missing column: {col_name}")
                except Exception as e:
                    if col_name != "user_id":
                        print(f"[DEBUG] init_db: Failed to add {col_name}: {e}")
                        log_error_to_file(f"init_db column add failed: {col_name} - {e}")

        # --- bot_settings table ---
        await c.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT
            )
        """)
        print("[DEBUG] init_db: bot_settings table ensured")

        # --- admin_permissions table ---
        await c.execute("""
            CREATE TABLE IF NOT EXISTS admin_permissions (
                user_id INTEGER,
                permission TEXT,
                PRIMARY KEY (user_id, permission)
            )
        """)
        print("[DEBUG] init_db: admin_permissions table ensured")

        # --- user_cooldowns table ---
        await c.execute("""
            CREATE TABLE IF NOT EXISTS user_cooldowns (
                cooldown_key TEXT PRIMARY KEY,
                last_used TIMESTAMP
            )
        """)
        print("[DEBUG] init_db: user_cooldowns table ensured")

        # --- banned_users table ---
        await c.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_at TIMESTAMP,
                banned_by INTEGER
            )
        """)
        print("[DEBUG] init_db: banned_users table ensured")

        # --- inventory table ---
        await c.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER DEFAULT 1,
                bound INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        print("[DEBUG] init_db: inventory table ensured")

        # --- Insert default bot_settings ---
        # FIXED: Added missing comma after ("toggle_core", "True")

        default_settings = [
            ("toggle_actions", "True"),
            ("actions_vit_cost_work", "10"),
            ("actions_vit_cost_observe", "10"),
            ("actions_vit_cost_comprehend", "40"),
            ("toggle_status", "True"),
            ("toggle_profile", "True"),
            ("toggle_pavilion", "True"),
            ("toggle_pvp", "True"),
            ("toggle_core", "True"),
            ("toggle_combat", "True"),
            ("toggle_mechanics", "True"),
            ("toggle_cultivation", "True"),
            ("toggle_help", "True"),
            ("toggle_shop", "True"),
            ("toggle_professions", "True"),
        ]
        for key, value in default_settings:
            await c.execute(
                "INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
                (key, value)
            )
        print("[DEBUG] init_db: Default bot_settings inserted")

        await conn.commit()
        elapsed = time.time() - start_time
        print(f"[DEBUG] init_db: Finished in {elapsed:.2f}s")

# ==========================================
# BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
print("[DEBUG] main.py: Intents configured")

class MurimBot(commands.Bot):
    def __init__(self):
        print("[DEBUG] MurimBot.__init__: Started")
        self.config = config
        self.db = None
        self.startup_time = time.time()
        self.dashboard = None
        self._shutdown_handled = False
        self.active_combats = {}
        self.command_cooldowns = {}
        # ADDED: Global meditation tracking set
        self.is_meditating = set()

        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents
        )
        print("[DEBUG] MurimBot.__init__: Finished")

    async def setup_hook(self):
        print("[DEBUG] setup_hook: Started")
        overall_start = time.time()

        if not config.TOKEN:
            print("[ERROR] No Discord token found in config/.env")
            log_error_to_file("FATAL: No Discord token found")
            return

        print("📦 Initializing Database...")
        await init_db()

        print("🔗 Opening Database Connection to Turso...")
        # FIXED: Using Turso instead of local SQLite
        self.db = create_client(
            url=config.TURSO_URL,
            auth_token=config.TURSO_AUTH_TOKEN
        )
        print("[DEBUG] setup_hook: Turso connection opened")

        if config.WEB_DASHBOARD_ENABLED:
            try:
                self.dashboard = DashboardServer(self)
                await self.dashboard.start()
                print("[DEBUG] Web dashboard started")
            except Exception as e:
                print(f"[WARN] Could not start web dashboard: {e}")
                log_error_to_file(f"Dashboard start failed: {e}")

        print("--- Loading Empyrean Systems (Cogs) ---")
        cogs_loaded = 0
        cogs_failed = []

        # Ensure cogs directory exists
        if not os.path.exists("./cogs"):
            print("[WARN] No 'cogs' directory found! Creating empty cogs directory.")
            os.makedirs("./cogs")
            # Create __init__.py to make it a proper package
            with open("./cogs/__init__.py", "w") as f:
                f.write("# Cogs package\n")

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    print(f"[DEBUG] setup_hook: Attempting to load cogs.{filename[:-3]}")
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ Loaded: {filename}")
                    cogs_loaded += 1
                except Exception as e:
                    error_msg = f"Failed to load {filename}: {e}\n{traceback.format_exc()}"
                    print(f"❌ Error Loading {filename}: {e}")
                    log_error_to_file(error_msg)
                    cogs_failed.append(filename)
                    if self.dashboard:
                        self.dashboard.set_last_error(error_msg[:200])

        load_time = time.time() - overall_start
        print(f"[DEBUG] setup_hook: Loaded {cogs_loaded} cogs, {len(cogs_failed)} failed in {load_time:.2f}s")
        if cogs_failed:
            print(f"[DEBUG] setup_hook: Failed cogs: {cogs_failed}")

        self.cogs_loaded_count = cogs_loaded
        self.cogs_failed_list = cogs_failed
        self.startup_duration = load_time

    async def close(self):
        print("[DEBUG] close: Graceful shutdown started")
        if self._shutdown_handled:
            return
        self._shutdown_handled = True

        if self.dashboard:
            try:
                await self.dashboard.stop()
                print("[DEBUG] Web dashboard stopped")
            except:
                pass

        if self.db:
            try:
                await self.db.close()
                print("[DEBUG] Database connection closed")
            except Exception as e:
                print(f"[DEBUG] Error closing database: {e}")

        await super().close()
        print("[DEBUG] close: Graceful shutdown complete")

    async def on_ready(self):
        startup_duration = time.time() - self.startup_time
        print("\n--- Murim: Empyrean Ascent is Online ---")
        print(f"Logged in as: {self.user.name}")
        print(f"Startup took {startup_duration:.2f} seconds")
        print(f"Cogs loaded: {len(self.cogs)}")
        print("Status: Database Sync Complete")
        print("------------------------------------------")
        print("[DEBUG] on_ready: Bot is fully ready")

        # Sync slash commands with Discord
        try:
            synced = await self.tree.sync()
            print(f"[DEBUG] Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"[WARN] Failed to sync slash commands: {e}")

        if config.STARTUP_ANNOUNCE_CHANNEL_ID:
            try:
                channel = self.get_channel(config.STARTUP_ANNOUNCE_CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title="🌿 Empyrean Ascent Bot Online",
                        description=f"Bot started successfully in {startup_duration:.2f}s\nLoaded {len(self.cogs)} cogs",
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
    print("\n[DEBUG] Received shutdown signal. Cleaning up...")
    if bot_instance:
        asyncio.create_task(bot_instance.close())

# ==========================================
# RUN BOT
# ==========================================
if __name__ == "__main__":
    print("[DEBUG] main.py: Starting bot...")
    bot_instance = MurimBot()
    bot = bot_instance

    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        bot.run(config.TOKEN)
    except KeyboardInterrupt:
        print("[DEBUG] Bot stopped by user")
    except Exception as e:
        print(f"[DEBUG] main.py: Fatal error: {e}")
        traceback.print_exc()
        log_error_to_file(f"FATAL: {e}\n{traceback.format_exc()}")
    finally:
        print("[DEBUG] main.py: Bot shutdown complete")