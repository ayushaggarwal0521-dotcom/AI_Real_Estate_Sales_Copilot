# backend/leads_db.py
#
# A separate SQLite database for appointment / "book a visit" leads.
# Kept apart from properties.db on purpose: that one is read-only
# reference data checked into git; this one is data the SITE GENERATES
# at runtime, so it gets its own file and its own module.
#
# IMPORTANT - read before relying on this in production:
# On Render's free tier the filesystem is EPHEMERAL. It resets on every
# redeploy, and also whenever the free service spins down from inactivity
# and spins back up. That means leads saved here can be wiped without
# warning. This is fine for testing the flow end-to-end, but for real
# leads you want either a paid Render plan with a persistent disk, or an
# external database (e.g. a hosted Postgres instance). Ask if you'd like
# help wiring one of those up later.

import sqlite3
from pathlib import Path

LEADS_DB_PATH = Path(__file__).resolve().parent / "database" / "leads.db"


def init_leads_db() -> None:
    """Create the leads table if it doesn't exist yet. Safe to call every startup."""

    LEADS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(LEADS_DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            property_id TEXT,
            property_title TEXT,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


def save_lead(
    name: str,
    phone: str,
    email: str = "",
    property_id: str = "",
    property_title: str = "",
    message: str = "",
) -> int:
    """Insert one lead row and return its new id."""

    connection = sqlite3.connect(LEADS_DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO leads (name, phone, email, property_id, property_title, message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, phone, email, property_id, property_title, message),
    )

    connection.commit()
    lead_id = cursor.lastrowid
    connection.close()

    return lead_id
