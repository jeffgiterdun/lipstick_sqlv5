#!/usr/bin/env python3
"""
Diagnose POI event timing issue for Week of 12/28/25
"""

import sqlite3

DB_PATH = 'data/ohlc_data.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("POI Event Timing Diagnostic - Week of 12/28/25")
print("=" * 80)
print()

# Find the session
cursor.execute("""
    SELECT * FROM sessions
    WHERE session_name LIKE '%12-28%'
    AND session_type = 'Weekly'
    ORDER BY symbol
""")

sessions = cursor.fetchall()

for session in sessions:
    session = dict(session)
    print(f"Session: {session['session_name']} ({session['symbol']})")
    print(f"  ID: {session['id']}")
    print(f"  Session Start: {session['session_start_time']}")
    print(f"  TO Time: {session['to_time']}")
    print(f"  TO Price: {session['true_open']:.2f}")
    print(f"  PoC: {session['poc']:.2f}")
    print(f"  RPP: {session['rpp']:.2f}")
    print(f"  Status: {session['status']}")
    print(f"  First Break: {session['first_break_time']} ({session['first_break_side']})")
    print(f"  First Return: {session['first_return_time']}")
    print(f"  Second Break: {session['second_break_time']} ({session['second_break_side']})")
    print(f"  Resolution: {session['resolution_time']} ({session['resolution_type']})")
    print()

    # Get POI events for this session
    if session['symbol'] == 'ES':
        cursor.execute("""
            SELECT * FROM poi_events
            WHERE es_session_id = ?
            ORDER BY COALESCE(es_event_time, nq_event_time)
        """, (session['id'],))
    else:
        cursor.execute("""
            SELECT * FROM poi_events
            WHERE nq_session_id = ?
            ORDER BY COALESCE(es_event_time, nq_event_time)
        """, (session['id'],))

    events = cursor.fetchall()

    if events:
        print(f"  POI Events ({len(events)}):")
        for event in events:
            event = dict(event)
            print(f"    {event['poi_type']} {event['event_type']}:")
            print(f"      ES: {event['es_event_time']}")
            print(f"      NQ: {event['nq_event_time']}")
            if event['leader']:
                print(f"      Leader: {event['leader']} (Delta: {event['time_delta_minutes']} min)")
    else:
        print(f"  No POI events found")

    print()

    # Check what candles were AFTER the TO time for this session
    print(f"  Checking candles after TO time for {session['symbol']}...")

    # Find first PoC touch after TO
    cursor.execute("""
        SELECT time, high, low, close
        FROM ohlc_1m
        WHERE symbol = ?
        AND time > ?
        AND (
            (low <= ? AND high >= ?) OR
            (low <= ? AND high >= ?)
        )
        ORDER BY time
        LIMIT 5
    """, (
        session['symbol'],
        session['to_time'],
        session['poc'], session['poc'],
        session['rpp'], session['rpp']
    ))

    touches = cursor.fetchall()
    if touches:
        print(f"  First 5 PoC/RPP touches after TO:")
        for touch in touches:
            touch = dict(touch)
            touched_poc = touch['low'] <= session['poc'] <= touch['high']
            touched_rpp = touch['low'] <= session['rpp'] <= touch['high']
            level = 'PoC' if touched_poc else 'RPP'
            print(f"    {touch['time']}: {level} touched (L:{touch['low']:.2f} H:{touch['high']:.2f})")
    else:
        print(f"  No PoC/RPP touches found after TO")

    print()

print("=" * 80)

conn.close()
