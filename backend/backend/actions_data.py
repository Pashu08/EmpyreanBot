"""
backend/actions_data.py - Constants for Actions feature (work, observe, comprehend)
All balance values are here for easy tuning.
"""

# ==========================================
# WORK COMMAND CONSTANTS
# ==========================================
WORK_VIT_COST = 10
WORK_BASE_GAIN_MIN = 5
WORK_BASE_GAIN_MAX = 15

# Rank bonuses for work (added to base gain)
WORK_RANK_BONUS = {
    "Third-Rate Warrior": 5,
    "Second-Rate Warrior": 10,
}

# ==========================================
# OBSERVE COMMAND CONSTANTS
# ==========================================
OBSERVE_VIT_COST = 10
OBSERVE_BASE_KI_MIN = 3
OBSERVE_BASE_KI_MAX = 8

# Rank bonuses for observe (added to base Ki gain)
OBSERVE_RANK_BONUS = {
    "Third-Rate Warrior": 2,
    "Second-Rate Warrior": 4,
}

# ==========================================
# COMPREHEND COMMAND CONSTANTS
# ==========================================
COMPREHEND_VIT_COST = 40
COMPREHEND_COOLDOWN_SECONDS = 1800  # 30 minutes
COMPREHEND_GAIN_MIN = 5.0
COMPREHEND_GAIN_MAX = 10.0

# ==========================================
# MASTERY GAINS
# ==========================================
LABORER_MASTERY_CHANCE = 0.10  # 10% chance
LABORER_MASTERY_GAIN = 0.5  # 0.5% mastery
MARTIAL_INSIGHT_MIN = 0.5
MARTIAL_INSIGHT_MAX = 1.5

# ==========================================
# EVENT CHANCES
# ==========================================
CHOICE_EVENT_CHANCE = 0.05  # 5% chance for choice event
RANDOM_EVENT_CHANCE = 0.2   # 20% chance for random event
