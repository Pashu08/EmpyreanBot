"""
backend/status_helpers.py - Helper functions for Status cog
"""

import datetime
from backend.helpers import get_max_stats, calculate_stage_from_ki
from backend.constants import AFK_KI_PER_HOUR, AFK_MASTERY_PER_HOUR

print("[DEBUG] status_helpers.py: Loading status helpers...")


def progress_bar(current: float, total: float, length: int = 10) -> str:
    """Return a text progress bar."""
    if total <= 0:
        return "⬜" * length
    ratio = max(0, min(current / total, 1))
    filled = int(ratio * length)
    return "🟦" * filled + "⬜" * (length - filled)


async def calculate_and_apply_afk_gains(db, user_id: int, user_data: dict):
    """
    Calculate and apply AFK gains.
    Returns (updated_user_data, gains_dict, hours_passed)
    """
    now = datetime.datetime.now()
    last_refresh = user_data.get('last_refresh')
    gains = {"ki": 0, "mastery": 0.0}

    if not last_refresh:
        return user_data, gains, 0

    try:
        last_dt = datetime.datetime.fromisoformat(last_refresh)
        hours_passed = (now - last_dt).total_seconds() / 3600
        if hours_passed <= 0:
            return user_data, gains, 0

        rank = user_data.get('rank', 'The Bound (Mortal)')
        profession = user_data.get('profession')
        
        # Ki gains
        ki_rate = AFK_KI_PER_HOUR.get(rank, 150)
        ki_gain = int(ki_rate * hours_passed)
        gains["ki"] = ki_gain

        # Mastery gains (15% bonus for Instructor)
        mastery_multiplier = 1.15 if profession == "Instructor" else 1.0
        mastery_gain = AFK_MASTERY_PER_HOUR * hours_passed * mastery_multiplier
        gains["mastery"] = mastery_gain

        # Apply gains
        max_stats = get_max_stats(rank)
        new_ki = min(user_data.get('ki', 0) + ki_gain, max_stats['ki_cap'])
        new_mastery = min(100.0, user_data.get('mastery', 0.0) + mastery_gain)
        new_stage = calculate_stage_from_ki(new_ki, max_stats['ki_cap'])

        # Update database
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "ki": new_ki,
                "mastery": round(new_mastery, 2),
                "stage": new_stage,
                "last_refresh": now.isoformat()
            }}
        )

        # Update user_data dict
        user_data['ki'] = new_ki
        user_data['mastery'] = new_mastery
        user_data['stage'] = new_stage
        user_data['last_refresh'] = now.isoformat()

        return user_data, gains, hours_passed

    except Exception as e:
        print(f"[ERROR] calculate_afk_gains: {e}")
        return user_data, gains, 0


def get_background_emoji(bg: str) -> str:
    """Get emoji for background."""
    if bg == "Hermit":
        return "🌿"
    elif bg == "Laborer":
        return "⚒️"
    else:
        return "🌑"


def get_meridian_status(meridian_damage) -> tuple:
    """Check meridian damage status. Returns (damaged, minutes_left, status_text)."""
    if not meridian_damage:
        return False, 0, "✅ Healthy"
    
    try:
        damage_time = datetime.datetime.fromisoformat(meridian_damage)
        now = datetime.datetime.now()
        if now < damage_time:
            minutes = int((damage_time - now).total_seconds() / 60)
            return True, minutes, f"⚠️ Damaged ({minutes}m left)"
    except:
        pass
    
    return False, 0, "✅ Healthy"


print("[DEBUG] status_helpers.py: Status helpers loaded successfully")