
import sqlite3
import os

DB_PATH = "data/trackly.db"


def get_connection():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                target_date TEXT,
                status TEXT DEFAULT 'In Progress',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_date TEXT,
                priority TEXT DEFAULT 'Medium',
                completed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Habits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Habit completion history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                UNIQUE(habit_id, log_date),
                FOREIGN KEY(habit_id) REFERENCES habits(id)
                ON DELETE CASCADE
            )
        """)

        # Gamification: User XP and levels
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                total_xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id)
                ON DELETE CASCADE
            )
        """)

        # Gamification: XP transaction history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS xp_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                activity_id INTEGER NOT NULL,
                xp_earned INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, activity_type, activity_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
                ON DELETE CASCADE
            )
        """)

        # Gamification: Achievement badges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge_code TEXT NOT NULL,
                unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge_code),
                FOREIGN KEY(user_id) REFERENCES users(id)
                ON DELETE CASCADE
            )
        """)

        # Safe migration helper
        def add_column_if_missing(table, column, definition):
            columns = [
                row[1]
                for row in cursor.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            ]

            if column not in columns:
                cursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )

        # Existing user ownership migrations
        add_column_if_missing(
            "goals",
            "user_id",
            "INTEGER REFERENCES users(id) ON DELETE CASCADE"
        )

        add_column_if_missing(
            "tasks",
            "user_id",
            "INTEGER REFERENCES users(id) ON DELETE CASCADE"
        )

        add_column_if_missing(
            "habits",
            "user_id",
            "INTEGER REFERENCES users(id) ON DELETE CASCADE"
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
