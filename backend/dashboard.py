"""
backend/dashboard.py - Web Dashboard Server
Provides a web interface for monitoring bot status.

This file contains:
- DashboardServer class (aiohttp web server)
- HTML/CSS for the dashboard interface
- Real-time bot statistics (users, modules, uptime, etc.)
"""

import discord
from aiohttp import web
import datetime
import os
import config
from backend.helpers import format_embed_color

print("[DEBUG] dashboard.py: Loading Dashboard server...")


class DashboardServer:
    """
    Web dashboard server that displays bot statistics.
    Accessible via http://localhost:8080 (or your server's IP).
    """

    def __init__(self, bot):
        """
        Initialize the dashboard server.

        Args:
            bot: The MurimBot instance
        """
        self.bot = bot
        self.app = None
        self.runner = None
        self.site = None
        self.start_time = datetime.datetime.now()
        self.last_error = "No errors yet"

    def set_last_error(self, error):
        """
        Store the most recent error for display on the dashboard.

        Args:
            error (str): Error message (truncated to 500 chars)
        """
        self.last_error = str(error)[:500]

    async def get_top_players(self, sort_by="ki", limit=10):
        """
        Get top players sorted by a specific stat.

        Args:
            sort_by (str): Field to sort by (ki, taels, etc.)
            limit (int): Number of players to return

        Returns:
            list: List of player documents
        """
        if not self.bot.db:
            return []
        try:
            cursor = self.bot.db.users.find().sort(sort_by, -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception:
            return []

    async def get_server_count(self):
        """Get the number of Discord servers the bot is in."""
        return len(self.bot.guilds)

    async def get_total_users(self):
        """Get the total number of registered users."""
        if not self.bot.db:
            return 0
        try:
            return await self.bot.db.users.count_documents({})
        except Exception:
            return 0

    async def get_admin_logs(self, limit=10):
        """
        Get recent admin actions from the database.

        Args:
            limit (int): Number of logs to return

        Returns:
            list: List of admin log documents
        """
        if not self.bot.db:
            return []
        try:
            return await self.bot.db.get_admin_logs(limit)
        except Exception:
            return []

    async def get_command_stats(self):
        """
        Get command usage statistics.
        Note: This is currently placeholder data.
        In the future, this could track actual command usage.
        """
        return [
            {"name": "!work", "count": 1234},
            {"name": "!hunt", "count": 987},
            {"name": "!stats", "count": 567},
            {"name": "!observe", "count": 456},
            {"name": "!breakthrough", "count": 89},
        ]

    async def get_loaded_modules_count(self):
        """
        Get the number of loaded command modules from ./commands folder.
        
        Returns:
            int: Number of loaded command files
        """
        try:
            if os.path.exists('./commands'):
                count = 0
                for filename in os.listdir('./commands'):
                    if filename.endswith('.py') and filename != '__init__.py':
                        count += 1
                return count
        except Exception:
            pass
        return len(self.bot.cogs) if self.bot.cogs else 0

    def _generate_top_players_html(self, players, stat="ki"):
        """
        Generate HTML table rows for top players.

        Args:
            players (list): List of player documents
            stat (str): Stat being displayed (ki or taels)

        Returns:
            str: HTML table rows
        """
        if not players:
            return "<tr><td colspan='4'>No data available</td></tr>"
        rows = []
        for i, player in enumerate(players, 1):
            user_id = player.get('user_id', 0)
            name = f"<@{user_id}>" if user_id else "Unknown"
            value = player.get(stat, 0)
            realm = player.get('rank', 'Unknown')[:20]
            rows.append(f"<tr><td>{i}</td><td>{name}</td><td>{value}</td><td>{realm}</td></tr>")
        return "".join(rows)

    def _generate_command_stats_html(self, stats):
        """
        Generate HTML table rows for command statistics.

        Args:
            stats (list): List of command stat dictionaries

        Returns:
            str: HTML table rows
        """
        if not stats:
            return "<tr><td colspan='2'>No data available</td></tr>"
        rows = []
        for stat in stats:
            rows.append(f"<tr><td>{stat['name']}</td><td>{stat['count']}</td></tr>")
        return "".join(rows)

    def _generate_admin_logs_html(self, logs):
        """
        Generate HTML for recent admin actions.

        Args:
            logs (list): List of admin log documents

        Returns:
            str: HTML div content
        """
        if not logs:
            return "<div>No recent admin actions</div>"
        items = []
        for log in logs:
            action = log.get('action', 'Unknown')
            admin_id = log.get('admin_id', 0)
            admin = f"<@{admin_id}>" if admin_id else "Unknown"
            target_id = log.get('target_id', 0)
            target = f"<@{target_id}>" if target_id else ""
            time_str = log.get('timestamp', '')[:16]
            items.append(
                f"<div style='margin-bottom: 5px; font-size: 0.8rem;'>"
                f"🔸 {action} by {admin} {target}<br>"
                f"<span style='color:#666;'>{time_str}</span>"
                f"</div>"
            )
        return "".join(items)

    async def handle_index(self, request):
        """
        Handle requests to the dashboard root URL.
        Renders the HTML dashboard with current bot statistics.

        Args:
            request: aiohttp request object

        Returns:
            web.Response: HTML page
        """
        # Gather all data for the dashboard
        user_count = await self.get_total_users()
        server_count = await self.get_server_count()
        top_ki_players = await self.get_top_players("ki", 5)
        top_taels_players = await self.get_top_players("taels", 5)
        command_stats = await self.get_command_stats()
        admin_logs = await self.get_admin_logs(5)
        loaded_modules = await self.get_loaded_modules_count()

        cog_count = len(self.bot.cogs)
        cog_names = list(self.bot.cogs.keys())
        uptime = datetime.datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]

        # HTML template for the dashboard
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
                        <div>📦 Commands Loaded: <strong>{loaded_modules}</strong></div>
                        <div>🔧 Cogs Loaded: <strong>{cog_count}</strong></div>
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
        """
        Start the aiohttp web server.
        Binds to 0.0.0.0 so it's accessible from other devices on the same network.
        """
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', config.WEB_DASHBOARD_PORT)
        await self.site.start()

        # Print access URLs for convenience
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"[DEBUG] Web dashboard: http://localhost:{config.WEB_DASHBOARD_PORT}")
            print(f"[DEBUG] Web dashboard: http://{local_ip}:{config.WEB_DASHBOARD_PORT}")
        except Exception:
            print(f"[DEBUG] Web dashboard: http://localhost:{config.WEB_DASHBOARD_PORT}")

    async def stop(self):
        """Stop the web server gracefully."""
        if self.runner:
            await self.runner.cleanup()


print("[DEBUG] dashboard.py: Dashboard server loaded successfully")