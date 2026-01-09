#!/usr/bin/env python3
"""
Insert December 2025 Monthly sessions with correct PoC/TO/RPP values.
"""
import sqlite3
from datetime import datetime, timezone

DB_PATH = 'data/ohlc_data.db'

# December 2025 Monthly Session Values
# Provided by user - these are the correct values
ES_DECEMBER = {
    'symbol': 'ES',
    'session_type': 'Monthly',
    'session_name': 'December 2025',
    'session_start_time': '2025-12-01T18:00:00-05:00',  # First trading day of December
    'to_time': '2025-12-08T18:00:00-05:00',  # Second full week Sunday (estimated)
    'true_open': 6940.25,
    'poc': 6859.25,
    'rpp': 7021.00,
    'status': 'unbroken',
    'expires_at': None  # Monthly sessions don't expire
}

NQ_DECEMBER = {
    'symbol': 'NQ',
    'session_type': 'Monthly',
    'session_name': 'December 2025',
    'session_start_time': '2025-12-01T18:00:00-05:00',  # First trading day of December
    'to_time': '2025-12-08T18:00:00-05:00',  # Second full week Sunday (estimated)
    'true_open': 25997.25,
    'poc': 25440.50,
    'rpp': 26553.75,
    'status': 'unbroken',
    'expires_at': None  # Monthly sessions don't expire
}

def insert_monthly_session(conn, session_data):
    """Insert a monthly session into the database."""
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Check if session already exists
    cursor.execute("""
        SELECT id FROM sessions
        WHERE symbol = ?
        AND session_type = ?
        AND session_name = ?
    """, (session_data['symbol'], session_data['session_type'], session_data['session_name']))

    existing = cursor.fetchone()

    if existing:
        print(f"[SKIP] {session_data['symbol']} {session_data['session_name']} already exists (ID: {existing[0]})")
        return existing[0]

    # Insert new session
    cursor.execute("""
        INSERT INTO sessions (
            symbol, session_type, session_name,
            session_start_time, to_time,
            true_open, poc, rpp,
            status, expires_at,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_data['symbol'],
        session_data['session_type'],
        session_data['session_name'],
        session_data['session_start_time'],
        session_data['to_time'],
        session_data['true_open'],
        session_data['poc'],
        session_data['rpp'],
        session_data['status'],
        session_data['expires_at'],
        now,
        now
    ))

    session_id = cursor.lastrowid
    print(f"[INSERT] {session_data['symbol']} {session_data['session_name']}")
    print(f"  ID: {session_id}")
    print(f"  TO: {session_data['true_open']}")
    print(f"  PoC: {session_data['poc']}")
    print(f"  RPP: {session_data['rpp']}")
    print(f"  TO Time: {session_data['to_time']}")
    print()

    return session_id

def main():
    print("="*80)
    print("Inserting December 2025 Monthly Sessions")
    print("="*80)
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Insert ES December 2025
        es_id = insert_monthly_session(conn, ES_DECEMBER)

        # Insert NQ December 2025
        nq_id = insert_monthly_session(conn, NQ_DECEMBER)

        # Commit changes
        conn.commit()

        print("="*80)
        print("Success! December 2025 Monthly sessions inserted.")
        print("="*80)
        print()
        print("Next steps:")
        print("  1. Run: python process_poi_events_1m.py --full")
        print("     This will detect all POI touches for December sessions")
        print()
        print("  2. Run: python detect_swings_1m.py --incremental")
        print("     This will link swings to the December POI events")
        print()

        # Verify insertion
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, symbol, session_name, true_open, poc, rpp, status
            FROM sessions
            WHERE session_name = 'December 2025'
            ORDER BY symbol
        """)

        print("Verification - December 2025 sessions now in database:")
        print()
        for row in cursor.fetchall():
            print(f"  {row['symbol']}: ID={row['id']}, TO={row['true_open']}, PoC={row['poc']}, RPP={row['rpp']}, Status={row['status']}")
        print()

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
