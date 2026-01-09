#!/usr/bin/env python3
"""
Verify that expired minor sessions are correctly filtered out during processing.
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = 'data/ohlc_data.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def is_session_expired(session, latest_data_time):
    """Same logic as in process_poi_events_1m.py"""
    if session['session_type'] != 'Minor':
        return False

    expires_at = session.get('expires_at')
    if expires_at is None:
        return False

    return latest_data_time > expires_at

def main():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get latest data time
    cursor.execute("SELECT MAX(time) FROM ohlc_1m")
    latest_data_time = cursor.fetchone()[0]

    print("=" * 80)
    print("Expiry Filtering Verification")
    print("=" * 80)
    print(f"\nLatest data time: {latest_data_time}")
    print()

    # Get all Minor sessions
    cursor.execute("""
        SELECT id, symbol, session_type, session_name, to_time, expires_at, status, true_open
        FROM sessions
        WHERE session_type = 'Minor'
        ORDER BY to_time ASC
    """)

    minor_sessions = [dict(row) for row in cursor.fetchall()]

    # Categorize sessions
    active_sessions = []
    expired_sessions = []

    for session in minor_sessions:
        if is_session_expired(session, latest_data_time):
            expired_sessions.append(session)
        else:
            active_sessions.append(session)

    print(f"Total Minor sessions: {len(minor_sessions)}")
    print(f"Active (within 24hr window): {len(active_sessions)}")
    print(f"Expired (past 24hr window): {len(expired_sessions)}")
    print()

    # Show status breakdown for expired sessions
    print("=" * 80)
    print("Expired Sessions - Status Breakdown")
    print("=" * 80)

    status_counts = {}
    for session in expired_sessions:
        status = session['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print()

    # Show status breakdown for active sessions
    print("=" * 80)
    print("Active Sessions (Still Being Processed) - Status Breakdown")
    print("=" * 80)

    status_counts = {}
    for session in active_sessions:
        status = session['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    print()

    # Show some examples of active sessions
    print("=" * 80)
    print("Active Minor Sessions (First 5)")
    print("=" * 80)

    for session in active_sessions[:5]:
        print(f"\n{session['symbol']} - {session['session_name']}")
        print(f"  TO: {session['to_time']}")
        print(f"  Expires: {session['expires_at']}")
        print(f"  Status: {session['status']}")
        print(f"  Hours until expiry: {calculate_hours_until_expiry(session['expires_at'], latest_data_time):.1f}")

    print()

    # Verify the filtering logic
    print("=" * 80)
    print("Filtering Logic Test")
    print("=" * 80)

    # Simulate what process_poi_events_1m.py does
    sessions_that_would_be_processed = [
        s for s in minor_sessions
        if s['symbol'] == 'ES'
        and s['true_open'] is not None
        and not is_session_expired(s, latest_data_time)
    ]

    print(f"\nES sessions that would be processed: {len(sessions_that_would_be_processed)}")
    print(f"ES sessions that would be skipped (expired): {len([s for s in minor_sessions if s['symbol'] == 'ES']) - len(sessions_that_would_be_processed)}")

    conn.close()

def calculate_hours_until_expiry(expires_at, current_time):
    """Calculate hours remaining until expiry (negative if expired)"""
    expires_dt = datetime.fromisoformat(expires_at)
    current_dt = datetime.fromisoformat(current_time)
    delta = expires_dt - current_dt
    return delta.total_seconds() / 3600

if __name__ == '__main__':
    main()
