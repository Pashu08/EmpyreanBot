print("[DEBUG] constants.py: Loading Murim game data...")

# ── RANKS (ordered, index = rank_id) ──────────────────────────
RANKS = [
    "The Bound (Mortal)",
    "Third-Rate Warrior",
    "Second-Rate Warrior",
    "First-Rate Warrior",
    "Peak Master",
]

# ── PER-RANK STATS ─────────────────────────────────────────────
RANK_STATS = {
    "The Bound (Mortal)":   {"vit_cap": 100,  "hp_cap": 100,  "ki_cap": 100,   "atk": 8,   "tech_atk": 15},
    "Third-Rate Warrior":   {"vit_cap": 300,  "hp_cap": 300,  "ki_cap": 1000,  "atk": 25,  "tech_atk": 50},
    "Second-Rate Warrior":  {"vit_cap": 600,  "hp_cap": 600,  "ki_cap": 3000,  "atk": 60,  "tech_atk": 120},
    "First-Rate Warrior":   {"vit_cap": 1000, "hp_cap": 1000, "ki_cap": 7500,  "atk": 150, "tech_atk": 300},
    "Peak Master":          {"vit_cap": 2000, "hp_cap": 2000, "ki_cap": 15000, "atk": 250, "tech_atk": 450},
}

# ── BREAKTHROUGH REQUIREMENTS ──────────────────────────────────
BREAKTHROUGH_KI = {
    "The Bound (Mortal)":  100,
    "Third-Rate Warrior":  1000,
    "Second-Rate Warrior": 3000,
    "First-Rate Warrior":  7500,
}

# ── HEARTBEAT (every 10 min) ───────────────────────────────────
HEARTBEAT_REGEN = {
    "The Bound (Mortal)":  25,
    "Third-Rate Warrior":  50,
    "Second-Rate Warrior": 100,
    "First-Rate Warrior":  175,
    "Peak Master":         250,
}

# ── AFK RATES (per hour) ──────────────────────────────────────
AFK_KI_PER_HOUR = {
    "The Bound (Mortal)":  150,
    "Third-Rate Warrior":  300,
    "Second-Rate Warrior": 600,
    "First-Rate Warrior":  1050,
    "Peak Master":         1500,
}
AFK_MASTERY_PER_HOUR = 0.5   # base, Instructor gets * 1.15

# ── ACTIONS ───────────────────────────────────────────────────
WORK_VIT_COST    = 10
OBSERVE_VIT_COST = 10
COMPREHEND_VIT_COST = 40
RECOVER_VIT_GAIN = 25
RECOVER_COOLDOWN = 300   # seconds
HUNT_COOLDOWN    = 600   # seconds
PVP_DAMAGE_RANGE = (10, 25)   # min, max damage per strike

# ── COMBAT ENEMIES ────────────────────────────────────────────
ENEMIES = {
    "Third-Rate Warrior":  {"name": "Spirit Wolf",       "hp": 100,  "atk": 15,  "reward": (30, 60),   "color": 0x2ecc71},
    "Second-Rate Warrior": {"name": "Shadow Tiger",      "hp": 250,  "atk": 45,  "reward": (60, 100),  "color": 0xe67e22},
    "First-Rate Warrior":  {"name": "Corrupted Elder",   "hp": 600,  "atk": 95,  "reward": (100, 200), "color": 0x992d22},
    "Peak Master":         {"name": "Ancient Bloodfiend","hp": 850,  "atk": 135, "reward": (200, 400), "color": 0x582f0e},
}

# ── TECHNIQUES ────────────────────────────────────────────────
TECHNIQUES = {
    "Flowing Cloud Steps": {
        "description": "Focus: Evasion & Agility",
        "emoji": "💨",
        "story": "The ink drifts like mist. A master walks through rain without a drop touching his robes.",
        "effect_text": "Increases **Dodge Chance by 15%**.",
        "combat_effect": "dodge_boost",
    },
    "Swift Wind Kick": {
        "description": "Focus: Speed & Multi-hit",
        "emoji": "🦶",
        "story": "The paper is warm. A warrior's legs move so fast they create vacuum blades.",
        "effect_text": "Chance to **strike twice** in one turn.",
        "combat_effect": "double_strike",
    },
    "Golden Bell Shield": {
        "description": "Focus: Damage Reduction",
        "emoji": "🔔",
        "story": "Heavy, bound in iron. The art of hardening Ki into an invisible bell of protection.",
        "effect_text": "Reduces **incoming damage by 20%**.",
        "combat_effect": "damage_reduction",
    },
    "Vajra Guard Mantra": {
        "description": "Focus: Vitality Regeneration",
        "emoji": "🧘",
        "story": "A soothing light radiates. Breathing in rhythm with the heavens heals wounds.",
        "effect_text": "Restores **5% HP every turn** during combat.",
        "combat_effect": "hp_regen",
    },
}

# ── BACKGROUNDS ───────────────────────────────────────────────
BACKGROUNDS = {
    "Laborer": {
        "emoji": "⚒️",
        "item": "Torn Page",
        "tagline": "One who finds wisdom in hard work.",
        "perk": "15% lower Ki requirement for breakthrough. 10% chance of Mastery gain from !work.",
    },
    "Outcast": {
        "emoji": "🌑",
        "item": "Black Coin",
        "tagline": "One who walks the shadows and forbidden markets.",
        "perk": "Unlocks the Shady Dealer stall in the Bazaar.",
    },
    "Hermit": {
        "emoji": "🌿",
        "item": "Glowing Fruit",
        "tagline": "One who lives in harmony with natural spirits.",
        "perk": "+15% HP/Vitality AFK regen rate.",
    },
}

# ── ITEM MUTATIONS ────────────────────────────────────────────
ITEM_MUTATIONS = {
    "Torn Page":     "Jade Scripture",
    "Black Coin":    "Shadow Seal",
    "Glowing Fruit": "Verdant Bone",
}

# ── SHOP ITEMS ────────────────────────────────────────────────
SHOP_ITEMS = {
    "Spirit Gathering Dan": {
        "price": 100,
        "desc": "Refines the soul. Restores 20 Ki.",
        "shop": "Apothecary",
        "effect": {"ki": 20},
    },
    "Jade Marrow Dew": {
        "price": 150,
        "desc": "Cool energy. Restores 50% Max Vitality.",
        "shop": "Apothecary",
        "effect": {"vit_pct": 0.5},
    },
    "Nine-Sun Restoration Soup": {
        "price": 30,
        "desc": "Warm soup. Restores 15 Vitality.",
        "shop": "Provisioner",
        "effect": {"vit": 15},
    },
    "Dried Rations": {
        "price": 10,
        "desc": "Travelers food. Restores 5 Vitality.",
        "shop": "Provisioner",
        "effect": {"vit": 5},
    },
    "Blood-Burning Catalyst": {
        "price": 1000,
        "desc": "Forbidden boost. +100 Ki but -50 HP.",
        "shop": "Shady Dealer",
        "effect": {"ki": 100, "hp": -50},
    },
    # === NEW SHOP ITEMS ===
    "Iron Bandage": {
        "price": 25,
        "desc": "Rough bandage. Restores 10 HP.",
        "shop": "Provisioner",
        "effect": {"hp": 10},
    },
    "Herbal Tea": {
        "price": 20,
        "desc": "Warm tea. Restores 10 Vitality.",
        "shop": "Provisioner",
        "effect": {"vit": 10},
    },
    "Qi Pill (small)": {
        "price": 50,
        "desc": "A small pill. Restores 10 Ki.",
        "shop": "Apothecary",
        "effect": {"ki": 10},
    },
    "Muscle Recovery Elixir": {
        "price": 80,
        "desc": "Eases sore muscles. Restores 20 Vitality.",
        "shop": "Apothecary",
        "effect": {"vit": 20},
    },
    "Broken Technique Scroll": {
        "price": 500,
        "desc": "Torn scroll with martial insights. +5% Mastery.",
        "shop": "Shady Dealer",
        "effect": {"mastery": 5},
    },
}

# ── UI ────────────────────────────────────────────────────────
COLOR_MAIN   = 0x700000
COLOR_WIN    = 0x00FF00
COLOR_LOSE   = 0x000000
COLOR_GOLD   = 0xFFD700
COLOR_TEAL   = 0x00AABB

STAGES = ["Initial", "Early", "Middle", "Late", "Peak"]

# ==========================================
# NEW MURIM IDEAS (added)
# ==========================================

# ── RANDOM MURIM EVENTS (for work, observe, hunt, etc.) ───────
MURIM_EVENTS = [
    ("🍂 A wandering master shares a breath technique.", {"ki": 15}),
    ("📜 You find an old martial arts scroll in a cave.", {"mastery": 2.0}),
    ("💊 A poisoned needle pricks your finger. You lose 10 Vitality.", {"vit": -10}),
    ("💰 A rich merchant thanks you for saving his son. You gain 50 Taels.", {"taels": 50}),
    ("🌙 Under the moonlight, your Ki circulation improves.", {"ki": 25}),
    ("⚔️ A rogue martial artist challenges you. You win and gain 5 Combat Mastery.", {"combat_mastery": 5}),
    ("📖 You meditate near a waterfall and gain insight.", {"mastery": 3.0}),
    ("🩸 An elder forces a Blood Pill into your mouth. +20 Ki, -5 HP.", {"ki": 20, "hp": -5}),
    ("🏮 You help an old woman carry her goods. She gives you 30 Taels.", {"taels": 30}),
    ("🌀 Your Qi fluctuates wildly – you lose 10 Ki.", {"ki": -10}),
    ("🌸 A mysterious fragrance heals your wounds. +15 HP.", {"hp": 15}),
    ("🏔️ You discover a hidden spring. +25 Vitality.", {"vit": 25}),
]

# ── FACTIONS (Reputation system) ─────────────────────────────
FACTIONS = {
    "Orthodox": {
        "desc": "Righteous sects like Mount Hua, Southern Edge, Beggar Sect.",
        "starting_reputation": 0,
        "rewards": {
            50: "Orthodox amulet – +5% Ki regen",
            100: "Martial technique: Righteous Palm",
        },
    },
    "Unorthodox": {
        "desc": "Neutral or independent martial artists, wanderers.",
        "starting_reputation": 0,
        "rewards": {
            50: "Unorthodox token – +5% Taels gain",
            100: "Martial technique: Shadow Step",
        },
    },
    "Demonic Cult": {
        "desc": "Forbidden sects that use blood arts and demonic energy.",
        "starting_reputation": -50,
        "rewards": {
            -100: "Demonic mark – +10% damage at night",
            -200: "Forbidden art: Blood Rebirth",
        },
    },
}

# ── HIDDEN TECHNIQUES (unlocked by mastering specific techniques) ──
HIDDEN_TECHNIQUES = {
    # Example structure – add your own hidden techniques here later
    # "Flowing Cloud Shadow Step": {
    #     "required_techniques": ["Flowing Cloud Steps", "Swift Wind Kick"],
    #     "description": "Teleport behind an enemy. Guaranteed critical hit.",
    #     "combat_effect": "teleport_crit",
    # },
}

print("[DEBUG] constants.py: Loaded Murim game data successfully")