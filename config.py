import os
from dotenv import load_dotenv

# Load the secrets from .env
load_dotenv()

# --- BOT CORE (ONLY these belong here) ---
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = "!"

# --- STARTING STATS ---
START_VITALITY = 100
START_HP = 100
KI_THRESHOLD = 100

# --- ECONOMY (Base values only) ---
STALE_RATION_RECOVERY = 20
STALE_RATION_COST = 1

# --- UI COLORS ---
COLOR_MURIM = 0x700000

# --- DATABASE PATH ---
DB_PATH = "murim.db"