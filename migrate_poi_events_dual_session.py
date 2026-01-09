#!/usr/bin/env python3
"""
Migrate poi_events table to use dual-session tracking pattern.

This migration changes poi_events from:
  - session_id (single) + symbol
To:
  - es_session_id + nq_session_id (dual session pattern)

This matches the yearly_monthly.db pattern and enables proper Echo Chamber tracking.
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = 'data/ohlc_data.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("POI Events Table Migration - Dual Session Pattern")
    print("=" * 80)
    print()

    # Check current schema
    cursor.execute("PRAGMA table_info(poi_events)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'es_session_id' in columns:
        print("✓ Migration already applied - poi_events already uses dual session pattern")
        conn.close()
        return

    print("Current schema uses single session_id + symbol pattern")
    print("Migrating to dual session pattern (es_session_id + nq_session_id)...")
    print()

    # Step 1: Check if there's any data
    cursor.execute("SELECT COUNT(*) as count FROM poi_events")
    event_count = cursor.fetchone()[0]

    if event_count > 0:
        print(f"⚠️  WARNING: Found {event_count} existing POI events")
        print("   This migration will DROP and recreate the poi_events table")
        print("   All existing POI events will be LOST")
        print()
        response = input("   Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("   Migration cancelled")
            conn.close()
            return

    # Step 2: Drop existing table
    print("Dropping existing poi_events table...")
    cursor.execute("DROP TABLE IF EXISTS poi_events")

    # Step 3: Create new table with dual session pattern
    print("Creating new poi_events table with dual session pattern...")

    cursor.execute("""
    CREATE TABLE poi_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        -- Dual session tracking (ES + NQ)
        es_session_id INTEGER NOT NULL,
        nq_session_id INTEGER NOT NULL,

        -- Denormalized session context
        trading_day TEXT NOT NULL,
        session_type TEXT NOT NULL,
        session_name TEXT NOT NULL,

        poi_type TEXT NOT NULL,
        event_type TEXT NOT NULL,

        -- ES timing
        es_event_time TEXT,

        -- NQ timing
        nq_event_time TEXT,

        -- Echo Chamber metrics
        time_delta_minutes INTEGER,
        leader TEXT,

        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,

        FOREIGN KEY (es_session_id) REFERENCES sessions(id),
        FOREIGN KEY (nq_session_id) REFERENCES sessions(id)
    )
    """)

    # Step 4: Create indexes
    print("Creating indexes...")

    cursor.execute("CREATE INDEX idx_poi_events_es_session ON poi_events(es_session_id)")
    cursor.execute("CREATE INDEX idx_poi_events_nq_session ON poi_events(nq_session_id)")
    cursor.execute("CREATE INDEX idx_poi_events_trading_day ON poi_events(trading_day)")
    cursor.execute("CREATE INDEX idx_poi_events_session_name ON poi_events(session_name)")
    cursor.execute("CREATE INDEX idx_poi_events_es_time ON poi_events(es_event_time)")
    cursor.execute("CREATE INDEX idx_poi_events_nq_time ON poi_events(nq_event_time)")

    # Commit changes
    conn.commit()

    print()
    print("=" * 80)
    print("Migration Complete!")
    print("=" * 80)
    print()
    print("New schema:")
    print("  - es_session_id: References ES session")
    print("  - nq_session_id: References NQ session")
    print("  - Removed: session_id, symbol columns")
    print("  - Changed: time_delta_seconds → time_delta_minutes")
    print()
    print("Benefits:")
    print("  ✓ One POI event per occurrence (not per symbol)")
    print("  ✓ Tracks when BOTH ES and NQ touched")
    print("  ✓ Perfect Echo Chamber timing analysis")
    print("  ✓ Cleaner schema, easier queries")
    print()

    conn.close()


if __name__ == '__main__':
    migrate()
