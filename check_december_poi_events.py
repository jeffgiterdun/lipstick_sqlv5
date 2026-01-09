#!/usr/bin/env python3
"""
Check POI events for December 2025 Monthly sessions.
"""
import sqlite3

DB_PATH = 'data/ohlc_data.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("="*80)
print("December 2025 Monthly Session POI Events")
print("="*80)
print()

# Get December 2025 sessions
cursor.execute("""
    SELECT id, symbol, session_name, session_type,
           true_open, poc, rpp, status,
           first_break_time, first_break_side,
           first_return_time,
           second_break_time, second_break_side,
           resolution_time, resolution_type
    FROM sessions
    WHERE session_name = 'December 2025'
    ORDER BY symbol
""")

sessions = cursor.fetchall()

if not sessions:
    print("[X] No December 2025 sessions found!")
    conn.close()
    exit(1)

print("December 2025 Sessions:")
print()
for session in sessions:
    print(f"{session['symbol']} December 2025 (ID: {session['id']})")
    print(f"  TO: {session['true_open']}")
    print(f"  PoC: {session['poc']}")
    print(f"  RPP: {session['rpp']}")
    print(f"  Status: {session['status']}")
    if session['first_break_time']:
        print(f"  First Break: {session['first_break_time']} ({session['first_break_side']})")
    if session['first_return_time']:
        print(f"  First Return: {session['first_return_time']}")
    if session['second_break_time']:
        print(f"  Second Break: {session['second_break_time']} ({session['second_break_side']})")
    if session['resolution_time']:
        print(f"  Resolution: {session['resolution_time']} ({session['resolution_type']})")
    print()

# Get POI events for December 2025
print("="*80)
print("POI Events for December 2025 Monthly Sessions")
print("="*80)
print()

cursor.execute("""
    SELECT
        pe.id,
        pe.trading_day,
        pe.session_type,
        pe.session_name,
        pe.poi_type,
        pe.event_type,
        pe.es_event_time,
        pe.nq_event_time,
        pe.time_delta_minutes,
        pe.leader,
        pe.created_at
    FROM poi_events pe
    WHERE pe.session_name = 'December 2025'
    ORDER BY
        CASE pe.event_type
            WHEN 'break' THEN 1
            WHEN 'return' THEN 2
            WHEN 'resolution' THEN 3
        END,
        pe.poi_type,
        COALESCE(pe.es_event_time, pe.nq_event_time)
""")

poi_events = cursor.fetchall()

if not poi_events:
    print("[!] No POI events found for December 2025 sessions yet.")
    print("    POI processing may still be running or no touches occurred.")
else:
    print(f"Found {len(poi_events)} POI events:")
    print()

    for i, event in enumerate(poi_events, 1):
        print(f"{i}. {event['event_type'].upper()}: {event['poi_type']}")
        print(f"   Trading Day: {event['trading_day']}")

        if event['es_event_time'] and event['nq_event_time']:
            print(f"   ES Time: {event['es_event_time']}")
            print(f"   NQ Time: {event['nq_event_time']}")
            print(f"   Echo Chamber: {event['leader']} led by {event['time_delta_minutes']} minutes")
        elif event['es_event_time']:
            print(f"   ES Time: {event['es_event_time']}")
            print(f"   NQ Time: Not touched yet")
        elif event['nq_event_time']:
            print(f"   ES Time: Not touched yet")
            print(f"   NQ Time: {event['nq_event_time']}")

        print()

# Summary statistics
print("="*80)
print("Summary")
print("="*80)
print()

cursor.execute("""
    SELECT
        poi_type,
        event_type,
        COUNT(*) as count,
        COUNT(es_event_time) as es_touches,
        COUNT(nq_event_time) as nq_touches
    FROM poi_events
    WHERE session_name = 'December 2025'
    GROUP BY poi_type, event_type
    ORDER BY
        CASE event_type
            WHEN 'break' THEN 1
            WHEN 'return' THEN 2
            WHEN 'resolution' THEN 3
        END,
        poi_type
""")

summary = cursor.fetchall()

if summary:
    print("POI Event Summary:")
    print()
    for row in summary:
        print(f"  {row['event_type'].upper()} - {row['poi_type']}:")
        print(f"    Total events: {row['count']}")
        print(f"    ES touches: {row['es_touches']}")
        print(f"    NQ touches: {row['nq_touches']}")
        print()

# Check for candles_from_poi_event in swings
cursor.execute("""
    SELECT COUNT(*) as swing_count
    FROM swings
    WHERE nearest_poi_event_id IN (
        SELECT id FROM poi_events WHERE session_name = 'December 2025'
    )
""")

swing_count = cursor.fetchone()['swing_count']

if swing_count > 0:
    print(f"Swings linked to December POI events: {swing_count}")
    print()

conn.close()
