import discord
from discord.ext import commands
import config
import os
import asyncio
import traceback
import time
import datetime
from aiohttp import web
import json
from motor.motor_asyncio import AsyncIOMotorClient

print("[DEBUG] main.py: Starting imports...")

# ==========================================
# ERROR LOGGING TO FILE (with rotation)
# ==========================================
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB

def rotate_log_file(log_path):
    if os.path.exists(log_path) and os.path.getsize(log_path) > MAX_LOG_SIZE:
        old_log = log_path.replace(".log", "_old.log")
        if os.path.exists(old_log):
            os.remove(old_log)
        os.rename(log_path, old_log)

def log_error_to_file(error_message):
    log_path = "bot_errors.log"
    try:
        rotate_log_file(log_path)
        with open(log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {error_message}\n")
    except:
        pass

# ==========================================
# MONGODB DATABASE WRAPPER (FIXED INDEXES)
# ==========================================
class MongoDBWrapper:
    def __init__(self, uri, db_name):
        self.client = None
        self.db = None
        self.uri = uri
        self.db_name = db_name

        # Collections
        self.users = None
        self.bot_settings = None
        self.admin_permissions = None
        self.user_cooldowns = None
        self.banned_users = None
        self.inventory = None
        self.admin_logs = None
        self.admins = None

    async def connect(self):
        if not self.uri:
            raise ValueError("MONGODB_URI not set")

        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client[self.db_name]

        # Initialize collections
        self.users = self.db.users
        self.bot_settings = self.db.bot_settings
        self.admin_permissions = self.db.admin_permissions
        self.user_cooldowns = self.db.user_cooldowns
        self.banned_users = self.db.banned_users
        self.inventory = self.db.inventory
        self.admin_logs = self.db.admin_logs
        self.admins = self.db.admins

        # Create indexes correctly (using list of tuples)
        await self.users.create_index([("user_id", 1)], unique=True)
        await self.bot_settings.create_index([("setting_key", 1)], unique=True)
        await self.admin_permissions.create_index([("user_id", 1), ("permission", 1)], unique=True)
        await self.user_cooldowns.create_index([("cooldown_key", 1)], unique=True)
        await self.banned_users.create_index([("user_id", 1)], unique=True)
        await self.inventory.create_index([("user_id", 1), ("item_name", 1)], unique=True)
        await self.admin_logs.create_index([("timestamp", -1)])
        await self.admins.create_index([("user_id", 1)], unique=True)

        print("[DEBUG] MongoDB connected and indexes created")
        return self

    async def close(self):
        if self.client:
            self.client.close()

    # ========== User Methods ==========
    async def fetch_user(self, user_id):
        return await self.users.find_one({"user_id": user_id})

    async def user_exists(self, user_id):
        return await self.users.find_one({"user_id": user_id}) is not None

    async def update_user(self, user_id, update_data):
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": update_data},
            upsert=True
        )

    async def get_user_stat(self, user_id, stat_name):
        user = await self.fetch_user(user_id)
        return user.get(stat_name) if user else None

    async def update_user_stat(self, user_id, stat_name, value):
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {stat_name: value}},
            upsert=True
        )

    # ========== Inventory Methods ==========
    async def get_inventory(self, user_id):
        cursor = self.inventory.find({"user_id": user_id})
        return await cursor.to_list(length=100)

    async def add_item(self, user_id, item_name, quantity=1, bound=False):
        await self.inventory.update_one(
            {"user_id": user_id, "item_name": item_name},
            {"$inc": {"quantity": quantity}, "$set": {"bound": 1 if bound else 0}},
            upsert=True
        )

    async def remove_item(self, user_id, item_name, quantity=1):
        item = await self.inventory.find_one({"user_id": user_id, "item_name": item_name})
        if not item or item.get("quantity", 0) < quantity:
            return False
        if item["quantity"] == quantity:
            await self.inventory.delete_one({"user_id": user_id, "item_name": item_name})
        else:
            await self.inventory.update_one(
                {"user_id": user_id, "item_name": item_name},
                {"$inc": {"quantity": -quantity}}
            )
        return True

    async def has_item(self, user_id, item_name, quantity=1):
        item = await self.inventory.find_one({"user_id": user_id, "item_name": item_name})
        return item is not None and item.get("quantity", 0) >= quantity

    # ========== Settings Methods ==========
    async def get_bot_setting(self, key, default=None):
        doc = await self.bot_settings.find_one({"setting_key": key})
        if not doc:
            return default
        value = doc.get("setting_value")
        if value == "True":
            return True
        if value == "False":
            return False
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value

    async def set_bot_setting(self, key, value):
        await self.bot_settings.update_one(
            {"setting_key": key},
            {"$set": {"setting_value": str(value)}},
            upsert=True
        )

    # ========== Permission Methods ==========
    async def get_user_permissions(self, user_id):
        cursor = self.admin_permissions.find({"user_id": user_id})
        docs = await cursor.to_list(length=10)
        return [doc["permission"] for doc in docs]

    async def add_user_permission(self, user_id, permission):
        await self.admin_permissions.update_one(
            {"user_id": user_id, "permission": permission},
            {"$set": {"user_id": user_id, "permission": permission}},
            upsert=True
        )

    async def remove_user_permission(self, user_id, permission):
        await self.admin_permissions.delete_one({"user_id": user_id, "permission": permission})

    # ========== Ban Methods ==========
    async def is_user_banned(self, user_id):
        return await self.banned_users.find_one({"user_id": user_id}) is not None

    async def ban_user(self, user_id, reason, banned_by):
        await self.banned_users.update_one(
            {"user_id": user_id},
            {"$set": {"reason": reason, "banned_at": datetime.datetime.now().isoformat(), "banned_by": banned_by}},
            upsert=True
        )

    async def unban_user(self, user_id):
        await self.banned_users.delete_one({"user_id": user_id})

    # ========== Cooldown Methods ==========
    async def get_user_cooldown(self, cooldown_key):
        doc = await self.user_cooldowns.find_one({"cooldown_key": cooldown_key})
        if doc:
            try:
                return datetime.datetime.fromisoformat(doc["last_used"])
            except:
                return None
        return None

    async def set_user_cooldown(self, cooldown_key):
        await self.user_cooldowns.update_one(
            {"cooldown_key": cooldown_key},
            {"$set": {"last_used": datetime.datetime.now().isoformat()}},
            upsert=True
        )

    # ========== Admin Log Methods ==========
    async def log_admin_action(self, admin_id, action, target_id=None, details=None):
        await self.admin_logs.insert_one({
            "admin_id": admin_id,
            "action": action,
            "target_id": target_id,
            "details": details,
            "timestamp": datetime.datetime.now().isoformat()
        })

    async def get_admin_logs(self, limit=10):
        cursor = self.admin_logs.find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    # ========== Legacy Admin Methods ==========
    async def get_admins(self):
        cursor = self.admins.find({})
        admins = await cursor.to_list(length=100)
        return [admin["user_id"] for admin in admins]

    async def add_admin(self, user_id):
        await self.admins.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )

    async def remove_admin(self, user_id):
        await self.admins.delete_one({"user_id": user_id})

    # ========== Initialization ==========
    async def initialize_default_settings(self):
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
            await self.bot_settings.update_one(
                {"setting_key": key},
                {"$set": {"setting_value": value}},
                upsert=True
            )
        print("[DEBUG] Default bot_settings initialized")

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

    async def get_top_players(self, sort_by="ki", limit=10):
        if not self.bot.db:
            return []
        try:
            cursor = self.bot.db.users.find().sort(sort_by, -1).limit(limit)
            return await cursor.to_list(length=limit)
        except:
            return []

    async def get_server_count(self):
        return len(self.bot.guilds)

    async def get_total_users(self):
        if not self.bot.db:
            return 0
        try:
            return await self.bot.db.users.count_documents({})
        except:
            return 0

    async def get_admin_logs(self, limit=10):
        if not self.bot.db:
            return []
        try:
            return await self.bot.db.get_admin_logs(limit)
        except:
            return []

    async def get_command_stats(self):
        return [
            {"name": "!work", "count": 1234},
            {"name": "!hunt", "count": 987},
            {"name": "!stats", "count": 567},
            {"name": "!observe", "count": 456},
            {"name": "!breakthrough", "count": 89},
        ]

    def _generate_top_players_html(self, players, stat="ki"):
        if not players:
            return "<tr><td colspan='4'>No data available</td></tr>"
        rows = []
        for i, player in enumerate(players, 1):
            name = f"<@{player.get('user_id', 0)}>" if player.get('user_id') else "Unknown"
            value = player.get(stat, 0)
            realm = player.get('rank', 'Unknown')[:20]
            rows.append(f"<tr><td>{i}</td><td>{name}</td><td>{value}</td><td>{realm}</td></tr>")
        return "".join(rows)

    def _generate_command_stats_html(self, stats):
        if not stats:
            return "<tr><td colspan='2'>No data available</td></tr>"
        rows = []
        for stat in stats:
            rows.append(f"<tr><td>{stat['name']}</td><td>{stat['count']}</td></tr>")
        return "".join(rows)

    def _generate_admin_logs_html(self, logs):
        if not logs:
            return "<div>No recent admin actions</div>"
        items = []
        for log in logs:
            action = log.get('action', 'Unknown')
            admin = f"<@{log.get('admin_id', 0)}>" if log.get('admin_id') else "Unknown"
            target = f"<@{log.get('target_id', 0)}>" if log.get('target_id') else ""
            time_str = log.get('timestamp', '')[:16]
            items.append(f"<div style='margin-bottom: 5px; font-size: 0.8rem;'>🔸 {action} by {admin} {target}<br><span style='color:#666;'>{time_str}</span></div>")
        return "".join(items)

    async def handle_index(self, request):
        user_count = await self.get_total_users()
        server_count = await self.get_server_count()
        top_ki_players = await self.get_top_players("ki", 5)
        top_taels_players = await self.get_top_players("taels", 5)
        command_stats = await self.get_command_stats()
        admin_logs = await self.get_admin_logs(5)

        cog_count = len(self.bot.cogs)
        cog_names = list(self.bot.cogs.keys())
        uptime = datetime.datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Empyrean Bot Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: #eee;
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                h1 {{ text-align: center; margin-bottom: 30px; color: #00ffcc; text-shadow: 0 0 10px rgba(0,255,204,0.3); }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 20px; }}
                .card {{
                    background: rgba(15, 25, 45, 0.8);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 20px;
                    border: 1px solid rgba(255,255,255,0.1);
                    transition: transform 0.2s;
                }}
                .card:hover {{ transform: translateY(-3px); }}
                .card h2 {{ color: #00ffcc; font-size: 1.2rem; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; }}
                .stat-value {{ font-size: 2rem; font-weight: bold; color: #ffcc00; }}
                .stat-label {{ font-size: 0.8rem; color: #aaa; }}
                .status-online {{ color: #00ff00; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }}
                th {{ color: #00ffcc; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.8rem; }}
                .refresh-btn {{
                    background: #00ffcc;
                    color: #1a1a2e;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 0.8rem;
                    margin-bottom: 10px;
                }}
                .refresh-btn:hover {{ background: #00ccaa; }}
                .logs-container {{ max-height: 200px; overflow-y: auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌿 Empyrean Ascent Bot Dashboard</h1>

                <div class="grid">
                    <div class="card">
                        <h2>🤖 Bot Status</h2>
                        <div class="stat-value status-online">ONLINE</div>
                        <div class="stat-label">Status</div>
                        <hr style="margin: 10px 0; border-color: rgba(255,255,255,0.1);">
                        <div>📦 Cogs Loaded: <strong>{cog_count}</strong> / {len(os.listdir('./cogs')) if os.path.exists('./cogs') else 0}</div>
                        <div>⏱️ Uptime: <strong>{uptime_str}</strong></div>
                        <div>🌐 Servers: <strong>{server_count}</strong></div>
                        <div>👥 Registered Users: <strong>{user_count}</strong></div>
                        <div>⚠️ Last Error: <strong style="color: #ff6666;">{self.last_error[:50]}</strong></div>
                    </div>

                    <div class="card">
                        <h2>📁 Loaded Cogs</h2>
                        <div class="logs-container">
                            {', '.join(cog_names) if cog_names else 'None'}
                        </div>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <h2>✨ Top Ki Cultivators</h2>
                        <table>
                            <tr><th>#</th><th>Player</th><th>Ki</th><th>Realm</th></tr>
                            {self._generate_top_players_html(top_ki_players, "ki")}
                        </table>
                    </div>

                    <div class="card">
                        <h2>💰 Wealthiest Warriors</h2>
                        <table>
                            <tr><th>#</th><th>Player</th><th>Taels</th><th>Realm</th></tr>
                            {self._generate_top_players_html(top_taels_players, "taels")}
                        </table>
                    </div>
                </div>

                <div class="grid">
                    <div class="card">
                        <h2>⚙️ Command Usage</h2>
                        <table>
                            <tr><th>Command</th><th>Uses</th></tr>
                            {self._generate_command_stats_html(command_stats)}
                        </table>
                        <div class="stat-label" style="margin-top: 10px;">* Approximate counts</div>
                    </div>

                    <div class="card">
                        <h2>🔧 Recent Admin Actions</h2>
                        <div class="logs-container">
                            {self._generate_admin_logs_html(admin_logs)}
                        </div>
                    </div>
                </div>

                <div class="footer">
                    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
                    <br>
                    Empyrean Ascent Bot | Dashboard auto-refreshes every 30 seconds
                </div>
            </div>
            <script>
                setTimeout(function() {{ location.reload(); }}, 30000);
            </script>
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

        print("📦 Connecting to MongoDB...")

        mongodb_uri = os.environ.get("MONGODB_URI")
        mongodb_db_name = os.environ.get("MONGODB_DB_NAME", "Empyrean-ascent")

        if not mongodb_uri:
            print("[ERROR] MONGODB_URI not set! Please set it in environment variables.")
            log_error_to_file("FATAL: MONGODB_URI not set")
            return

        print(f"[DEBUG] MongoDB URI found (length: {len(mongodb_uri)})")

        self.db = MongoDBWrapper(mongodb_uri, mongodb_db_name)
        await self.db.connect()
        await self.db.initialize_default_settings()

        print("🔗 MongoDB Connection Established")
        print("[DEBUG] setup_hook: Database connection opened")

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

        if not os.path.exists("./cogs"):
            print("[WARN] No 'cogs' directory found! Creating empty cogs directory.")
            os.makedirs("./cogs")
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