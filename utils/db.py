import aiosqlite
from typing import Optional, Any
import datetime

print("[DEBUG] db.py: Loading database helpers...")

# ==========================================
# FETCH & EXISTING HELPERS (with debug prints)
# ==========================================

async def fetch_user(db: aiosqlite.Connection, user_id: int) -> Optional[dict]:
    """Returns full user row as a dict, or None if not registered."""
    print(f"[DEBUG] db.fetch_user: user_id={user_id}")
    async with db.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            print(f"[DEBUG] db.fetch_user: No user found for {user_id}")
            return None
        cols = [d[0] for d in cursor.description]
        result = dict(zip(cols, row))
        print(f"[DEBUG] db.fetch_user: Found user {user_id}")
        return result

async def user_exists(db: aiosqlite.Connection, user_id: int) -> bool:
    print(f"[DEBUG] db.user_exists: user_id={user_id}")
    async with db.execute(
        "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
    ) as cursor:
        exists = await cursor.fetchone() is not None
        print(f"[DEBUG] db.user_exists: {exists}")
        return exists

async def get_user_stat(db: aiosqlite.Connection, user_id: int, stat_name: str) -> Any:
    """Get a single stat from a user."""
    print(f"[DEBUG] db.get_user_stat: user_id={user_id}, stat={stat_name}")
    async with db.execute(
        f"SELECT {stat_name} FROM users WHERE user_id = ?", (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        value = row[0] if row else None
        print(f"[DEBUG] db.get_user_stat: value={value}")
        return value

async def update_user_stat(db: aiosqlite.Connection, user_id: int, stat_name: str, value: Any):
    """Update a single stat for a user."""
    print(f"[DEBUG] db.update_user_stat: user_id={user_id}, stat={stat_name}, value={value}")
    await db.execute(
        f"UPDATE users SET {stat_name} = ? WHERE user_id = ?", (value, user_id)
    )
    await db.commit()
    print(f"[DEBUG] db.update_user_stat: Updated")

# ==========================================
# INVENTORY (with debug prints)
# ==========================================

async def get_inventory(db: aiosqlite.Connection, user_id: int) -> list[dict]:
    """Returns list of {name, quantity} dicts."""
    print(f"[DEBUG] db.get_inventory: user_id={user_id}")
    async with db.execute(
        "SELECT item_name, quantity FROM inventory WHERE user_id = ? ORDER BY item_name",
        (user_id,)
    ) as cursor:
        rows = await cursor.fetchall()
        result = [{"name": r[0], "quantity": r[1]} for r in rows]
        print(f"[DEBUG] db.get_inventory: Found {len(result)} items")
        return result

async def add_item(db: aiosqlite.Connection, user_id: int, item_name: str, qty: int = 1):
    print(f"[DEBUG] db.add_item: user_id={user_id}, item={item_name}, qty={qty}")
    await db.execute(
        """INSERT INTO inventory (user_id, item_name, quantity)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?""",
        (user_id, item_name, qty, qty)
    )
    await db.commit()
    print(f"[DEBUG] db.add_item: Added/updated")

async def remove_item(db: aiosqlite.Connection, user_id: int, item_name: str, qty: int = 1) -> bool:
    """Returns False if player doesn't have enough."""
    print(f"[DEBUG] db.remove_item: user_id={user_id}, item={item_name}, qty={qty}")
    async with db.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (user_id, item_name)
    ) as cursor:
        row = await cursor.fetchone()

    if not row or row[0] < qty:
        print(f"[DEBUG] db.remove_item: Not enough items")
        return False

    if row[0] == qty:
        await db.execute(
            "DELETE FROM inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        )
        print(f"[DEBUG] db.remove_item: Deleted entire stack")
    else:
        await db.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?",
            (qty, user_id, item_name)
        )
        print(f"[DEBUG] db.remove_item: Reduced quantity")

    await db.commit()
    return True

async def has_item(db: aiosqlite.Connection, user_id: int, item_name: str, qty: int = 1) -> bool:
    """Check if user has at least qty of an item."""
    print(f"[DEBUG] db.has_item: user_id={user_id}, item={item_name}, qty={qty}")
    async with db.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (user_id, item_name)
    ) as cursor:
        row = await cursor.fetchone()
    result = row is not None and row[0] >= qty
    print(f"[DEBUG] db.has_item: {result}")
    return result

# ==========================================
# ADMINS (with debug prints)
# ==========================================

async def get_admins(db: aiosqlite.Connection) -> set[int]:
    print(f"[DEBUG] db.get_admins: Fetching all admins")
    async with db.execute("SELECT user_id FROM admins") as cursor:
        rows = await cursor.fetchall()
        result = {r[0] for r in rows}
        print(f"[DEBUG] db.get_admins: Found {len(result)} admins")
        return result

async def add_admin(db: aiosqlite.Connection, user_id: int):
    print(f"[DEBUG] db.add_admin: user_id={user_id}")
    await db.execute(
        "INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,)
    )
    await db.commit()
    print(f"[DEBUG] db.add_admin: Added")

async def remove_admin(db: aiosqlite.Connection, user_id: int):
    print(f"[DEBUG] db.remove_admin: user_id={user_id}")
    await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    await db.commit()
    print(f"[DEBUG] db.remove_admin: Removed")

# ==========================================
# NEW HELPER FUNCTIONS (for settings, bans, permissions, cooldowns)
# ==========================================

# --- Bot Settings (from bot_settings table) ---
async def get_bot_setting(db: aiosqlite.Connection, key: str, default: Any = None) -> Any:
    """Get a setting from bot_settings table."""
    print(f"[DEBUG] db.get_bot_setting: key={key}")
    async with db.execute("SELECT setting_value FROM bot_settings WHERE setting_key = ?", (key,)) as cursor:
        row = await cursor.fetchone()
        if not row:
            print(f"[DEBUG] db.get_bot_setting: Not found, using default {default}")
            return default
        val = row[0]
        # Try to parse as number or boolean
        if isinstance(val, str):
            if val.isdigit():
                return int(val)
            if val.lower() in ('true', 'false'):
                return val.lower() == 'true'
        print(f"[DEBUG] db.get_bot_setting: returning {val}")
        return val

async def set_bot_setting(db: aiosqlite.Connection, key: str, value: Any):
    """Set a setting in bot_settings table."""
    print(f"[DEBUG] db.set_bot_setting: key={key}, value={value}")
    await db.execute(
        "INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
        (key, str(value))
    )
    await db.commit()
    print(f"[DEBUG] db.set_bot_setting: Saved")

# --- Banned Users ---
async def is_user_banned(db: aiosqlite.Connection, user_id: int) -> bool:
    """Check if a user is banned."""
    print(f"[DEBUG] db.is_user_banned: user_id={user_id}")
    async with db.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,)) as cursor:
        banned = await cursor.fetchone() is not None
        print(f"[DEBUG] db.is_user_banned: {banned}")
        return banned

async def ban_user(db: aiosqlite.Connection, user_id: int, reason: str, banned_by: int):
    """Ban a user."""
    print(f"[DEBUG] db.ban_user: user_id={user_id}, reason={reason}, by={banned_by}")
    now = datetime.datetime.now().isoformat()
    await db.execute(
        "INSERT OR REPLACE INTO banned_users (user_id, reason, banned_at, banned_by) VALUES (?, ?, ?, ?)",
        (user_id, reason, now, banned_by)
    )
    await db.commit()
    print(f"[DEBUG] db.ban_user: Banned")

async def unban_user(db: aiosqlite.Connection, user_id: int):
    """Unban a user."""
    print(f"[DEBUG] db.unban_user: user_id={user_id}")
    await db.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
    await db.commit()
    print(f"[DEBUG] db.unban_user: Unbanned")

# --- Permissions (from admin_permissions table) ---
async def get_user_permissions(db: aiosqlite.Connection, user_id: int) -> list[str]:
    """Get all permission strings for a user."""
    print(f"[DEBUG] db.get_user_permissions: user_id={user_id}")
    async with db.execute("SELECT permission FROM admin_permissions WHERE user_id = ?", (user_id,)) as cursor:
        rows = await cursor.fetchall()
        perms = [row[0] for row in rows]
        print(f"[DEBUG] db.get_user_permissions: {perms}")
        return perms

async def add_user_permission(db: aiosqlite.Connection, user_id: int, permission: str):
    """Grant a permission to a user."""
    print(f"[DEBUG] db.add_user_permission: user_id={user_id}, perm={permission}")
    await db.execute(
        "INSERT OR IGNORE INTO admin_permissions (user_id, permission) VALUES (?, ?)",
        (user_id, permission)
    )
    await db.commit()
    print(f"[DEBUG] db.add_user_permission: Added")

async def remove_user_permission(db: aiosqlite.Connection, user_id: int, permission: str):
    """Remove a permission from a user."""
    print(f"[DEBUG] db.remove_user_permission: user_id={user_id}, perm={permission}")
    await db.execute(
        "DELETE FROM admin_permissions WHERE user_id = ? AND permission = ?",
        (user_id, permission)
    )
    await db.commit()
    print(f"[DEBUG] db.remove_user_permission: Removed")

# --- User Cooldowns (survive bot restart) ---
async def get_user_cooldown(db: aiosqlite.Connection, cooldown_key: str) -> Optional[datetime.datetime]:
    """Get last used timestamp for a cooldown key."""
    print(f"[DEBUG] db.get_user_cooldown: key={cooldown_key}")
    async with db.execute("SELECT last_used FROM user_cooldowns WHERE cooldown_key = ?", (cooldown_key,)) as cursor:
        row = await cursor.fetchone()
        if row:
            try:
                dt = datetime.datetime.fromisoformat(row[0])
                print(f"[DEBUG] db.get_user_cooldown: found {dt}")
                return dt
            except:
                pass
        print(f"[DEBUG] db.get_user_cooldown: not found")
        return None

async def set_user_cooldown(db: aiosqlite.Connection, cooldown_key: str):
    """Set the current timestamp for a cooldown key."""
    print(f"[DEBUG] db.set_user_cooldown: key={cooldown_key}")
    now = datetime.datetime.now().isoformat()
    await db.execute(
        "INSERT OR REPLACE INTO user_cooldowns (cooldown_key, last_used) VALUES (?, ?)",
        (cooldown_key, now)
    )
    await db.commit()
    print(f"[DEBUG] db.set_user_cooldown: Saved")

print("[DEBUG] db.py: Database helpers loaded successfully")