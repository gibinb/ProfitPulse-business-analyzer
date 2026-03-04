import sqlite3

DB_NAME = "profitpulse.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    conn   = get_connection()
    cursor = conn.cursor()

    # ───────────────── USERS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        gmail    TEXT,
        password BLOB,
        role     TEXT DEFAULT 'Owner'
    )
    """)

    # ───────────────── BUSINESS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS business (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_username TEXT,
        business_name  TEXT,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(owner_username) REFERENCES users(username)
    )
    """)

    # ───────────────── TRANSACTIONS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT,
        type        TEXT,
        amount      REAL,
        business_id INTEGER,
        cogs        REAL DEFAULT 0,
        category    TEXT,
        product     TEXT,
        quantity    INTEGER DEFAULT 0,
        txn_date    DATE,
        notes       TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(business_id) REFERENCES business(id)
    )
    """)

    # ───────────────── INVENTORY ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        username            TEXT,
        product             TEXT,
        quantity            INTEGER,
        unit_cost           REAL,
        purchase_date       DATE,
        business_id         INTEGER,
        low_stock_threshold INTEGER DEFAULT 5,
        FOREIGN KEY(business_id) REFERENCES business(id)
    )
    """)

    # ───────────────── INVENTORY MOVEMENTS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory_movements (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id   INTEGER,
        product       TEXT,
        change_qty    INTEGER,
        movement_type TEXT,
        movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(business_id) REFERENCES business(id)
    )
    """)

    # ───────────────── REPORTS LOG ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id  INTEGER,
        report_type  TEXT,
        file_url     TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(business_id) REFERENCES business(id)
    )
    """)

    # ───────────────── SYSTEM SETTINGS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key   TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # ───────────────── BUSINESS ACCESS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS business_access (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT,
        business_id INTEGER,
        granted_by  TEXT,
        granted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(username)    REFERENCES users(username),
        FOREIGN KEY(business_id) REFERENCES business(id)
    )
    """)

    conn.commit()
    conn.close()