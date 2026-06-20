# -*- coding: utf-8 -*-
"""Database migration system for the cadastral plugin database."""

import sqlite3

CURRENT_VERSION = 1

def get_db_version(conn: sqlite3.Connection) -> int:
    """Read the current schema version from schema_version table."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        if row:
            return int(row[0])
        return 0
    except sqlite3.OperationalError:
        # Table schema_version does not exist
        return 0

def migrate(conn: sqlite3.Connection, from_version: int):
    """Run migrations to bring the database schema up to the CURRENT_VERSION."""
    cursor = conn.cursor()
    if from_version < 1:
        # Initial version setup
        cursor.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
        cursor.execute("INSERT INTO schema_version (version) VALUES (1)")
        conn.commit()
        from_version = 1
        
    # Future migration steps can be added here:
    # if from_version < 2:
    #     cursor.execute("ALTER TABLE ...")
    #     cursor.execute("UPDATE schema_version SET version = 2")
    #     conn.commit()
    #     from_version = 2
