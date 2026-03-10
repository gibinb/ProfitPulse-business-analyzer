import os
import psycopg2

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def initialize_database():
    conn   = get_connection()
    cursor = conn.cursor()

    # ───────────────── USERS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username   TEXT PRIMARY KEY,
        gmail      TEXT,
        password   TEXT,
        role       TEXT DEFAULT 'Owner'
    )
    """)

    # ───────────────── BUSINESS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS business (
        id             SERIAL PRIMARY KEY,
        owner_username TEXT,
        business_name  TEXT,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_username) REFERENCES users(username)
    )
    """)

    # ───────────────── TRANSACTIONS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id          SERIAL PRIMARY KEY,
        username    TEXT,
        type        TEXT,
        amount      REAL,
        business_id INTEGER,
        cogs        REAL DEFAULT 0,
        category    TEXT,
        product     TEXT,
        quantity    INTEGER DEFAULT 0,
        txn_date    TEXT,
        notes       TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (business_id) REFERENCES business(id)
    )
    """)

    # ───────────────── INVENTORY ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id                  SERIAL PRIMARY KEY,
        username            TEXT,
        product             TEXT,
        quantity            INTEGER,
        unit_cost           REAL,
        purchase_date       TEXT,
        business_id         INTEGER,
        low_stock_threshold INTEGER DEFAULT 5,
        FOREIGN KEY (business_id) REFERENCES business(id)
    )
    """)

    # ───────────────── INVENTORY MOVEMENTS ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory_movements (
        id            SERIAL PRIMARY KEY,
        business_id   INTEGER,
        product       TEXT,
        change_qty    INTEGER,
        movement_type TEXT,
        movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (business_id) REFERENCES business(id)
    )
    """)

    # ───────────────── REPORTS LOG ─────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id           SERIAL PRIMARY KEY,
        business_id  INTEGER,
        report_type  TEXT,
        file_url     TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (business_id) REFERENCES business(id)
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
        id          SERIAL PRIMARY KEY,
        username    TEXT,
        business_id INTEGER,
        granted_by  TEXT,
        granted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (username)    REFERENCES users(username),
        FOREIGN KEY (business_id) REFERENCES business(id)
    )
    """)

    conn.commit()
    conn.close()