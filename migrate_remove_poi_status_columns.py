#!/usr/bin/env python3
"""
Remove es_status and nq_status columns from POI Events Table

This migration removes the es_status and nq_status columns from poi_events
and aligns event_type to use the full session status vocabulary.

Rationale:
- event_type should match session.status values for consistency
- Removes redundancy (es_status/nq_status were a workaround)
- Simplifies queries: event_type is now the single source of truth

New event_type values will be:
- 'first_break' (was 'break')
- 'return' (unchanged)
- 'second_break_same' (was 'break')
- 'second_break_opposite' (was 'break')
- 'resolved' (was 'resolution')

Usage:
    python migrate_remove_poi_status_columns.py
"""

import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH_1M = 'data/ohlc_data.db'

def migrate_database(db_path, db_name, auto_confirm=False):
    """Remove status columns from poi_events table."""
    print(f"\n{'=' * 80}")
    print(f"Migrating {db_name}")
    print('=' * 80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(poi_events)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'es_status' not in columns:
            print(f"  Status columns already removed from {db_name}")
            return

        print(f"  Current schema has es_status and nq_status columns")
        print(f"  Removing status columns...")

        # Check if there's any data
        cursor.execute("SELECT COUNT(*) as count FROM poi_events")
        event_count = cursor.fetchone()[0]

        if event_count > 0:
            print(f"\n  WARNING: Found {event_count} existing POI events")
            print(f"     This migration will recreate the poi_events table")
            print(f"     Existing data will be preserved (es_status/nq_status dropped)")
            print()

            if not auto_confirm:
                response = input("     Continue? (yes/no): ")
                if response.lower() != 'yes':
                    print("     Migration cancelled")
                    conn.close()
                    return
            else:
                print("     Auto-confirmed (--yes flag)")

            # Step 1: Backup existing data (without es_status/nq_status)
            print(f"\n  Step 1: Backing up existing POI events...")
            cursor.execute("""
                CREATE TEMPORARY TABLE poi_events_backup AS
                SELECT
                    id,
                    es_session_id,
                    nq_session_id,
                    trading_day,
                    session_type,
                    session_name,
                    poi_type,
                    event_type,
                    es_event_time,
                    nq_event_time,
                    time_delta_minutes,
                    leader,
                    created_at,
                    updated_at
                FROM poi_events
            """)
            print(f"     Backed up {event_count} POI events")

        # Step 2: Drop existing table
        print(f"\n  Step 2: Dropping existing poi_events table...")
        cursor.execute("DROP TABLE poi_events")

        # Step 3: Create new table without status columns
        print(f"\n  Step 3: Creating new poi_events table...")
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
        print(f"\n  Step 4: Creating indexes...")
        cursor.execute("CREATE INDEX idx_poi_events_es_session ON poi_events(es_session_id)")
        cursor.execute("CREATE INDEX idx_poi_events_nq_session ON poi_events(nq_session_id)")
        cursor.execute("CREATE INDEX idx_poi_events_trading_day ON poi_events(trading_day)")
        cursor.execute("CREATE INDEX idx_poi_events_session_name ON poi_events(session_name)")
        cursor.execute("CREATE INDEX idx_poi_events_es_time ON poi_events(es_event_time)")
        cursor.execute("CREATE INDEX idx_poi_events_nq_time ON poi_events(nq_event_time)")
        cursor.execute("CREATE INDEX idx_poi_events_event_type ON poi_events(event_type)")

        # Step 5: Restore data if we had any
        if event_count > 0:
            print(f"\n  Step 5: Restoring POI events...")
            cursor.execute("""
                INSERT INTO poi_events (
                    id,
                    es_session_id,
                    nq_session_id,
                    trading_day,
                    session_type,
                    session_name,
                    poi_type,
                    event_type,
                    es_event_time,
                    nq_event_time,
                    time_delta_minutes,
                    leader,
                    created_at,
                    updated_at
                )
                SELECT
                    id,
                    es_session_id,
                    nq_session_id,
                    trading_day,
                    session_type,
                    session_name,
                    poi_type,
                    event_type,
                    es_event_time,
                    nq_event_time,
                    time_delta_minutes,
                    leader,
                    created_at,
                    updated_at
                FROM poi_events_backup
            """)
            print(f"     Restored {event_count} POI events")

            # Drop backup table
            cursor.execute("DROP TABLE poi_events_backup")

        conn.commit()
        print(f"\n  Successfully migrated {db_name}")

    except Exception as e:
        conn.rollback()
        print(f"  Error migrating {db_name}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def main():
    # Check for --yes flag
    auto_confirm = '--yes' in sys.argv

    print("=" * 80)
    print("POI Events - Remove Status Columns Migration")
    print("=" * 80)
    print()
    print("This will remove es_status and nq_status columns from poi_events table.")
    print("The event_type column will become the single source of truth.")
    print()
    print(f"Database: {DB_PATH_1M}")
    print()

    # Migrate database
    migrate_database(DB_PATH_1M, "1M Database (ohlc_data.db)", auto_confirm=auto_confirm)

    print("\n" + "=" * 80)
    print("Migration Complete!")
    print("=" * 80)
    print()
    print("Changes:")
    print("  [OK] Removed es_status column")
    print("  [OK] Removed nq_status column")
    print("  [OK] Added index on event_type")
    print()
    print("Next steps:")
    print("  1. Run updated process_poi_events_1m.py to create new events")
    print("  2. Update queries to use event_type instead of es_status/nq_status")
    print("  3. Update documentation (poi-status-queries.md, starter-queries.md)")
    print()

if __name__ == '__main__':
    main()
