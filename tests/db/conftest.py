import pytest
import sqlite3
import os

DB_PATH = "tests/db/test.db"

@pytest.fixture(scope="session")
def db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            job     TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    yield conn
    conn.close()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

@pytest.fixture(autouse=True)
def clean_db(db_connection):
    yield
    db_connection.execute("DELETE FROM users")
    db_connection.commit()
