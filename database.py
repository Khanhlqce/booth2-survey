import sqlite3

def init_db():
    conn = sqlite3.connect("booth2.db")

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS survey (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue TEXT,
        score INTEGER
    )
    """)

    conn.commit()
    conn.close()    