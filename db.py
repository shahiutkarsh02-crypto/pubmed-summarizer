# db.py
# Sets up a small local database (SQLite) to store user accounts
# and per-user search history.

import sqlite3
import bcrypt

DB_PATH = "users.db"


def get_connection():
    """Opens a connection to our database file (creates it if it doesn't exist)."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Creates the tables we need, if they don't already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            num_papers INTEGER NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()


def create_user(username, email, password):
    """
    Creates a new user account. Returns (True, "") on success,
    or (False, error_message) if something went wrong (e.g. username taken).
    """
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash.decode("utf-8")),
        )
        conn.commit()
        return True, ""
    except sqlite3.IntegrityError:
        return False, "That username or email is already taken."
    finally:
        conn.close()


def verify_user(username, password):
    """
    Checks a login attempt. Returns the user's id if correct,
    or None if the username doesn't exist or the password is wrong.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    user_id, stored_hash = row
    if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
        return user_id
    return None


def save_search(user_id, topic, num_papers, summary):
    """Saves a completed search into this user's permanent history."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO search_history (user_id, topic, num_papers, summary) VALUES (?, ?, ?, ?)",
        (user_id, topic, num_papers, summary),
    )
    conn.commit()
    conn.close()


def get_user_history(user_id, limit=20):
    """Fetches this user's most recent searches, newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT topic, num_papers, summary, created_at FROM search_history "
        "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows