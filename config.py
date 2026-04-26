import os
from dotenv import load_dotenv

# Load the secrets from .env
load_dotenv()

# --- BOT CORE ---
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = "!"

# --- MURIM RANKS ---
RANKS = {
    0: "The Bound (Mortal)",
    1: "Third-Rate Warrior",
    2: "Second-Rate Warrior",
    3: "First-Rate Warrior",
    4: "Peak Master"
}

# --- STARTING STATS ---
START_VITALITY = 100
START_HP = 100
KI_THRESHOLD = 100

# --- ECONOMY & ENERGY ---
WORK_VITALITY_COST = 10
OBSERVE_VITALITY_COST = 10
STALE_RATION_RECOVERY = 20
STALE_RATION_COST = 1

# --- UI COLORS ---
COLOR_MURIM = 0x700000 
