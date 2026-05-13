import aiosqlite
from typing import Optional, Any

# ── FETCH ──────────────────────────────────────────────────────

async def fetch_user(db: aiosqlite.Connection, user_id: int) -> Optional[dict]:
    """Returns full user row as a dict, or None if not registered."""
    async with db.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))

async def user_exists(db: aiosqlite.Connection, user_id: int) -> bool:
    async with db.execute(
        "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
    ) as cursor:
        return (await cursor.fetchone()) is not None

async def get_user_stat(db: aiosqlite.Connection, user_id: int, stat_name: str) -> Any:
    """Get a single stat from a user."""
    async with db.execute(
        f"SELECT {stat_name} FROM users WHERE user_id = ?", (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else None

async def update_user_stat(db: aiosqlite.Connection, user_id: int, stat_name: str, value: Any):
    """Update a single stat for a user."""
    await db.execute(
        f"UPDATE users SET {stat_name} = ? WHERE user_id = ?", (value, user_id)
    )
    await db.commit()

# ── INVENTORY ──────────────────────────────────────────────────

async def get_inventory(db: aiosqlite.Connection, user_id: int) -> list[dict]:
    """Returns list of {name, quantity} dicts."""
    async with db.execute(
        "SELECT item_name, quantity FROM inventory WHERE user_id = ? ORDER BY item_name",
        (user_id,)
    ) as cursor:
        rows = await cursor.fetchall()
        return [{"name": r[0], "quantity": r[1]} for r in rows]

async def add_item(db: aiosqlite.Connection, user_id: int, item_name: str, qty: int = 1):
    await db.execute(
        """INSERT INTO inventory (user_id, item_name, quantity)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, item_name) DO UPDATE SET quantity = quantity + ?""",
        (user_id, item_name, qty, qty)
    )
    await db.commit()

async def remove_item(db: aiosqlite.Connection, user_id: int, item_name: str, qty: int = 1) -> bool:
    """Returns False if player doesn't have enough."""
    async with db.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (user_id, item_name)
    ) as cursor:
        row = await cursor.fetchone()
    
    if not row or row[0] < qty:
        return False
    
    if row[0] == qty:
        await db.execute(
            "DELETE FROM inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        )
    else:
        await db.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_name = ?",
            (qty, user_id, item_name)
        )
    
    await db.commit()
    return True

async def has_item(db: aiosqlite.Connection, user_id: int, item_name: str, qty: int = 1) -> bool:
    """Check if user has at least qty of an item."""
    async with db.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
        (user_id, item_name)
    ) as cursor:
        row = await cursor.fetchone()
    
    return row is not None and row[0] >= qty

# ── ADMINS ─────────────────────────────────────────────────────

async def get_admins(db: aiosqlite.Connection) -> set[int]:
    async with db.execute("SELECT user_id FROM admins") as cursor:
        rows = await cursor.fetchall()
        return {r[0] for r in rows}

async def add_admin(db: aiosqlite.Connection, user_id: int):
    await db.execute(
        "INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,)
    )
    await db.commit()

async def remove_admin(db: aiosqlite.Connection, user_id: int):
    await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    await db.commit()