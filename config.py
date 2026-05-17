import os
from dotenv import load_dotenv

# Load the secrets from .env
load_dotenv()

# ==========================================
# BOT CORE
# ==========================================
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = "!"

# ==========================================
# STARTING STATS
# ==========================================
START_VITALITY = 100
START_HP = 100
KI_THRESHOLD = 100

# ==========================================
# ECONOMY (Base values)
# ==========================================
STALE_RATION_RECOVERY = 20
STALE_RATION_COST = 1

# ==========================================
# UI COLORS
# ==========================================
COLOR_MURIM = 0x700000

# ==========================================
# DATABASE PATH
# ==========================================
DB_PATH = "murim.db"

# ==========================================
# WEB DASHBOARD (from main.py)
# ==========================================
WEB_DASHBOARD_ENABLED = True
WEB_DASHBOARD_PORT = 8080
STARTUP_ANNOUNCE_CHANNEL_ID = 0   # Put your channel ID here, 0 = disabled

# ==========================================
# IDEA 3: FEATURE TOGGLES (Default values)
# ==========================================
PVP_ENABLED = True
PROFESSIONS_ENABLED = True
BAZAAR_ENABLED = True
AFK_GAINS_ENABLED = True
COMBAT_ENABLED = True
CULTIVATION_ENABLED = True
ITEMS_ENABLED = True
PAVILION_ENABLED = True

# ==========================================
# IDEA 4: COOLDOWN DURATIONS (in seconds)
# ==========================================
WORK_COOLDOWN = 5
OBSERVE_COOLDOWN = 5
HUNT_COOLDOWN = 10
RECOVER_COOLDOWN = 300
FOCUS_COOLDOWN = 300
REST_COOLDOWN = 3600
BREAKTHROUGH_COOLDOWN = 3600
SPAR_COOLDOWN = 60

# ==========================================
# IDEA 5: EMOJI MAPPING
# ==========================================
EMOJI_KI = "✨"
EMOJI_TAEL = "💰"
EMOJI_HP = "🩸"
EMOJI_VITALITY = "❤️"
EMOJI_MASTERY = "📖"
EMOJI_COMBAT = "⚔️"
EMOJI_MEDITATE = "🧘"
EMOJI_WORK = "⚒️"
EMOJI_OBSERVE = "👁️"
EMOJI_BREAKTHROUGH = "🌀"
EMOJI_SUCCESS = "✅"
EMOJI_FAILURE = "❌"
EMOJI_COOLDOWN = "⏳"

# ==========================================
# IDEA 6: MESSAGE TEMPLATES
# ==========================================
MSG_NOT_REGISTERED = "❌ Use `!start` first."
MSG_MERIDIAN_DAMAGE = "❌ Your meridians are damaged. Wait **{minutes}m**."
MSG_COOLDOWN = "⏳ Wait **{seconds}s** before using this again."
MSG_NO_KI = "❌ Not enough Ki. You need **{required}** Ki."
MSG_NO_VITALITY = "❌ Not enough Vitality. You need **{required}** Vitality."
MSG_ALREADY_MEDITATING = "🧘 You are already in deep meditation. Use `!cancel` to stop."
MSG_NOT_MEDITATING = "❌ You are not meditating."
MSG_CANCELLED = "🧘 Meditation cancelled."
MSG_RECOVER_COMPLETE = "✨ Meditation complete! You regained **+{vit} Vitality** and **+{ki} Ki**."
MSG_FOCUS_COMPLETE = "🌀 Focused! Converted **10 Vitality** → **5 Ki**."
MSG_REST_COMPLETE = "🛌 Rest taken! Restored **10 HP** and **10 Vitality**."
MSG_FEATURE_DISABLED = "❌ The **{feature}** feature is currently disabled."
MSG_BANNED = "❌ You are banned from using this bot."

# ==========================================
# IDEA 7: DEBUG MODE (default value)
# ==========================================
DEBUG_MODE = False