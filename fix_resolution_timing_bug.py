"""
Fix Resolution Timing Bug

This script corrects sessions where resolution_time < first_return_time,
which violates the POI event lifecycle rules.

For affected sessions, it:
1. Resets the session status back to 'return' (waiting for valid resolution)
2. Clears the invalid resolution_time and resolution_type
3. Deletes the invalid resolution POI events

After running this script, process_poi_events_1m.py can be re-run to
recreate resolution events with correct timestamps (if valid TO touches exist).
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = 'data/ohlc_data.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 100)
    print("Fix Resolution Timing Bug")
    print("=" * 100)
    print()

    # Find all sessions with resolution_time < first_return_time
    cursor.execute("""
        SELECT id, symbol, session_name, status,
               first_return_time, resolution_time
        FROM sessions
        WHERE status = 'resolved'
        AND resolution_time < first_return_time
        ORDER BY session_name, symbol
    """)

    problematic_sessions = cursor.fetchall()

    print(f"Found {len(problematic_sessions)} sessions with invalid resolution times")
    print()

    if len(problematic_sessions) == 0:
        print("No corrupted sessions found. Exiting.")
        conn.close()
        return

    # Group by session name to handle ES/NQ pairs
    sessions_by_name = {}
    for session in problematic_sessions:
        name = session['session_name']
        if name not in sessions_by_name:
            sessions_by_name[name] = []
        sessions_by_name[name].append(dict(session))

    print(f"Affected session pairs: {len(sessions_by_name)}")
    print()

    # Ask for confirmation
    print("This script will:")
    print("  1. Reset affected sessions from 'resolved' back to 'return' status")
    print("  2. Clear invalid resolution_time and resolution_type fields")
    print("  3. Delete invalid resolution POI events")
    print()
    response = input("Do you want to proceed? (yes/no): ")

    if response.lower() != 'yes':
        print("Aborted.")
        conn.close()
        return

    print()
    print("Processing...")
    print()

    now = datetime.now(timezone.utc).isoformat()
    sessions_fixed = 0
    events_deleted = 0

    for session_name in sorted(sessions_by_name.keys()):
        sessions = sessions_by_name[session_name]

        print(f"Fixing: {session_name}")

        # Get ES and NQ session IDs
        es_session_id = None
        nq_session_id = None

        for session in sessions:
            if session['symbol'] == 'ES':
                es_session_id = session['id']
            elif session['symbol'] == 'NQ':
                nq_session_id = session['id']

            # Reset session status
            cursor.execute("""
                UPDATE sessions
                SET status = 'return',
                    resolution_time = NULL,
                    resolution_type = NULL,
                    updated_at = ?
                WHERE id = ?
            """, (now, session['id']))

            sessions_fixed += 1
            print(f"  Reset {session['symbol']} session (ID: {session['id']}) to 'return' status")

        # Delete invalid resolution POI events for this session pair
        if es_session_id and nq_session_id:
            cursor.execute("""
                DELETE FROM poi_events
                WHERE es_session_id = ?
                AND nq_session_id = ?
                AND poi_type = 'TO'
                AND event_type = 'resolution'
            """, (es_session_id, nq_session_id))

            deleted = cursor.rowcount
            events_deleted += deleted
            if deleted > 0:
                print(f"  Deleted {deleted} invalid resolution POI event(s)")

    # Commit all changes
    conn.commit()

    print()
    print("=" * 100)
    print("Fix Complete!")
    print("=" * 100)
    print()
    print(f"Sessions fixed: {sessions_fixed}")
    print(f"POI events deleted: {events_deleted}")
    print()
    print("Next steps:")
    print("  1. Run: python process_poi_events_1m.py --full")
    print("  2. This will recreate resolution events with correct timestamps")
    print("     (only for sessions that have valid TO touches after second_break)")
    print()

    conn.close()

if __name__ == '__main__':
    main()
