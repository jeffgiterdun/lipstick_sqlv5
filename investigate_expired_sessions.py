#!/usr/bin/env python3
"""
Investigate expired minor sessions issue.
"""

import sqlite3
from datetime import datetime, timezone
import pytz

DB_PATH = 'data/ohlc_data.db'
ET = pytz.timezone('US/Eastern')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def main():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Current time
    now = datetime.now(ET).isoformat()
    print(f"Current time: {now}")
    print()

    # Get session counts by type and status
    print("=" * 80)
    print("Session Status by Type")
    print("=" * 80)
    cursor.execute("""
        SELECT session_type, status, COUNT(*) as count
        FROM sessions
        GROUP BY session_type, status
        ORDER BY session_type, status
    """)

    for row in cursor.fetchall():
        print(f"{row['session_type']:10s} - {row['status']:10s}: {row['count']:4d}")

    print()

    # Check Minor sessions specifically
    print("=" * 80)
    print("Minor Sessions Analysis")
    print("=" * 80)

    cursor.execute("""
        SELECT COUNT(*) as count
        FROM sessions
        WHERE session_type = 'Minor'
    """)
    total_minor = cursor.fetchone()['count']
    print(f"Total Minor sessions: {total_minor}")

    cursor.execute("""
        SELECT COUNT(*) as count
        FROM sessions
        WHERE session_type = 'Minor'
        AND status = 'unbroken'
    """)
    unbroken_minor = cursor.fetchone()['count']
    print(f"Unbroken Minor sessions: {unbroken_minor}")

    # Check how many are expired
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM sessions
        WHERE session_type = 'Minor'
        AND status = 'unbroken'
        AND expires_at < ?
    """, (now,))
    expired_unbroken = cursor.fetchone()['count']
    print(f"Expired but still unbroken: {expired_unbroken}")

    print()

    # Show sample expired sessions
    print("=" * 80)
    print("Sample Expired Minor Sessions (First 10)")
    print("=" * 80)

    cursor.execute("""
        SELECT id, symbol, session_name, to_time, expires_at, status
        FROM sessions
        WHERE session_type = 'Minor'
        AND status = 'unbroken'
        AND expires_at < ?
        ORDER BY expires_at ASC
        LIMIT 10
    """, (now,))

    for row in cursor.fetchall():
        print(f"\nID: {row['id']}")
        print(f"  Symbol: {row['symbol']}")
        print(f"  Session: {row['session_name']}")
        print(f"  TO Time: {row['to_time']}")
        print(f"  Expires: {row['expires_at']}")
        print(f"  Status: {row['status']}")

    print()

    # Check latest data time
    print("=" * 80)
    print("Data Range")
    print("=" * 80)

    cursor.execute("SELECT MIN(time) as min_time, MAX(time) as max_time FROM ohlc_1m")
    result = cursor.fetchone()
    print(f"Min data time: {result['min_time']}")
    print(f"Max data time: {result['max_time']}")

    print()

    # Check a specific minor session's expiry logic
    print("=" * 80)
    print("Verify Expiry Calculation")
    print("=" * 80)

    cursor.execute("""
        SELECT id, session_name, to_time, expires_at
        FROM sessions
        WHERE session_type = 'Minor'
        LIMIT 1
    """)

    sample = cursor.fetchone()
    if sample:
        print(f"Sample session: {sample['session_name']}")
        print(f"  TO time: {sample['to_time']}")
        print(f"  Expires at: {sample['expires_at']}")

        # Parse and verify 24 hour difference
        to_dt = datetime.fromisoformat(sample['to_time'])
        expires_dt = datetime.fromisoformat(sample['expires_at'])
        diff = expires_dt - to_dt
        print(f"  Time difference: {diff.total_seconds() / 3600:.1f} hours")

    conn.close()

if __name__ == '__main__':
    main()
