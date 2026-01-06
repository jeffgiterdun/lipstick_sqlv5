"""
Diagnostic script to identify the root cause of resolution-before-return bug.

This script analyzes POI events and session data to understand why some
sessions have resolution times that occur before return times.
"""

import sqlite3
from datetime import datetime

DB_PATH = 'data/ohlc_data.db'

def parse_time(time_str):
    """Parse ISO timestamp for comparison."""
    if time_str is None:
        return None
    # Simple parsing - just use the string directly for comparison
    return time_str

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 100)
    print("POI Event Resolution Bug Diagnostic")
    print("=" * 100)
    print()

    # Find all sessions with resolution-before-return issue
    cursor.execute("""
        SELECT
            s.id,
            s.symbol,
            s.session_name,
            s.status,
            s.first_break_time,
            s.first_return_time,
            s.second_break_time,
            s.resolution_time
        FROM sessions s
        WHERE s.status = 'resolved'
        AND s.resolution_time < s.first_return_time
        ORDER BY s.session_name, s.symbol
    """)

    problematic_sessions = cursor.fetchall()

    print(f"Found {len(problematic_sessions)} sessions with resolution_time < first_return_time")
    print()

    # Group by session_name to analyze ES/NQ pairs
    sessions_by_name = {}
    for session in problematic_sessions:
        name = session['session_name']
        if name not in sessions_by_name:
            sessions_by_name[name] = {}
        sessions_by_name[name][session['symbol']] = dict(session)

    # Analyze each problematic session
    for session_name in sorted(sessions_by_name.keys())[:5]:  # Analyze first 5
        print("=" * 100)
        print(f"Session: {session_name}")
        print("=" * 100)

        es_session = sessions_by_name[session_name].get('ES')
        nq_session = sessions_by_name[session_name].get('NQ')

        if es_session:
            print(f"\nES Session (ID: {es_session['id']}):")
            print(f"  Status: {es_session['status']}")
            print(f"  first_break:  {es_session['first_break_time']}")
            print(f"  first_return: {es_session['first_return_time']}")
            print(f"  second_break: {es_session['second_break_time']}")
            print(f"  resolution:   {es_session['resolution_time']} <-- PROBLEM!")

        if nq_session:
            print(f"\nNQ Session (ID: {nq_session['id']}):")
            print(f"  Status: {nq_session['status']}")
            print(f"  first_break:  {nq_session['first_break_time']}")
            print(f"  first_return: {nq_session['first_return_time']}")
            print(f"  second_break: {nq_session['second_break_time']}")
            print(f"  resolution:   {nq_session['resolution_time']}")

        # Get all POI events for this session
        es_id = es_session['id'] if es_session else None
        nq_id = nq_session['id'] if nq_session else None

        if es_id and nq_id:
            cursor.execute("""
                SELECT id, poi_type, event_type, es_event_time, nq_event_time
                FROM poi_events
                WHERE es_session_id = ? AND nq_session_id = ?
                ORDER BY poi_type, event_type
            """, (es_id, nq_id))

            events = cursor.fetchall()
            print(f"\nPOI Events ({len(events)} total):")
            for event in events:
                print(f"  {event['poi_type']:3} {event['event_type']:10} | " +
                      f"ES: {event['es_event_time'] or 'NULL':28} | " +
                      f"NQ: {event['nq_event_time'] or 'NULL':28}")

        # Check if ES actually touched TO after second_break
        if es_session and es_session['second_break_time']:
            cursor.execute("""
                SELECT MIN(time) as first_to_touch
                FROM ohlc_1m
                WHERE symbol = 'ES'
                AND time > ?
                AND time < datetime(?, '+1 day')
                AND ((low <= (SELECT true_open FROM sessions WHERE id = ?) + 0.25
                     AND high >= (SELECT true_open FROM sessions WHERE id = ?) - 0.25))
            """, (es_session['second_break_time'], es_session['second_break_time'], es_id, es_id))

            result = cursor.fetchone()
            first_to_touch = result['first_to_touch']

            print(f"\nES TO Touch Analysis:")
            print(f"  Second break time: {es_session['second_break_time']}")
            print(f"  Next TO touch:     {first_to_touch or 'NONE FOUND'}")
            print(f"  Recorded resolution: {es_session['resolution_time']}")

            if first_to_touch:
                if first_to_touch != es_session['resolution_time']:
                    print(f"  *** BUG: Resolution time doesn't match next TO touch! ***")
            else:
                print(f"  *** BUG: No TO touch after second break, but session is resolved! ***")

        print()

    print("\n" + "=" * 100)
    print("Summary")
    print("=" * 100)
    print(f"\nTotal problematic sessions: {len(problematic_sessions)}")
    print(f"Unique session names affected: {len(sessions_by_name)}")

    conn.close()

if __name__ == '__main__':
    main()
