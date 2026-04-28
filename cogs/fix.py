import sqlite3

def force_fix():
    conn = sqlite3.connect('murim.db')
    c = conn.cursor()
    
    # The columns that the error says are missing
    columns = [
        ("stage", "TEXT DEFAULT 'Initial'"),
        ("last_refresh", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("mastery", "REAL DEFAULT 0.0"),
        ("active_tech", "TEXT DEFAULT 'None'"),
        ("boss_flags", "TEXT DEFAULT ''"),
        ("profession", "TEXT DEFAULT 'None'"),
        ("prof_rank", "TEXT DEFAULT 'Apprentice'"),
        ("prof_xp", "INTEGER DEFAULT 0"),
        ("prof_req_xp", "INTEGER DEFAULT 1000")
    ]
    
    print("--- Starting Force Migration ---")
    for col_name, col_type in columns:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"✅ Added: {col_name}")
        except sqlite3.OperationalError as e:
            print(f"ℹ️ Skipped {col_name}: {e}")

    conn.commit()
    conn.close()
    print("--- Force Migration Complete ---")

if __name__ == "__main__":
    force_fix()
