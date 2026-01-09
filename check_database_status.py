#!/usr/bin/env python3
"""
Quick database status check for POI event troubleshooting.
"""

import sqlite3

DB_PATH = 'data/ohlc_data.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("1M DATABASE STATUS CHECK")
print("=" * 80)
print()

# Check OHLC data
cursor.execute("SELECT COUNT(*) as count FROM ohlc_1m")
ohlc_count = cursor.fetchone()['count']
print(f"1. OHLC Data: {ohlc_count:,} candles")

if ohlc_count > 0:
    cursor.execute("SELECT MIN(time) as min_time, MAX(time) as max_time FROM ohlc_1m")
    row = cursor.fetchone()
    print(f"   Date range: {row['min_time']} to {row['max_time']}")

    cursor.execute("SELECT symbol, COUNT(*) as count FROM ohlc_1m GROUP BY symbol")
    for row in cursor.fetchall():
        print(f"   {row['symbol']}: {row['count']:,} candles")

print()

# Check sessions
cursor.execute("SELECT COUNT(*) as count FROM sessions")
session_count = cursor.fetchone()['count']
print(f"2. Sessions Total: {session_count:,}")

if session_count > 0:
    cursor.execute("SELECT session_type, COUNT(*) as count FROM sessions GROUP BY session_type")
    for row in cursor.fetchall():
        print(f"   {row['session_type']}: {row['count']:,}")

    print()

    # Check sessions with calculated ranges
    cursor.execute("""
        SELECT COUNT(*) as count FROM sessions
        WHERE true_open IS NOT NULL AND poc IS NOT NULL AND rpp IS NOT NULL
    """)
    sessions_with_range = cursor.fetchone()['count']
    print(f"3. Sessions with Calculated Ranges (PoC/TO/RPP): {sessions_with_range:,}")

    if sessions_with_range > 0:
        cursor.execute("""
            SELECT session_type, COUNT(*) as count FROM sessions
            WHERE true_open IS NOT NULL AND poc IS NOT NULL AND rpp IS NOT NULL
            GROUP BY session_type
        """)
        for row in cursor.fetchall():
            print(f"   {row['session_type']}: {row['count']:,}")

    print()

    # Check session status distribution
    cursor.execute("SELECT status, COUNT(*) as count FROM sessions GROUP BY status")
    print(f"4. Session Status Distribution:")
    for row in cursor.fetchall():
        print(f"   {row['status']}: {row['count']:,}")

print()

# Check POI events
cursor.execute("SELECT COUNT(*) as count FROM poi_events")
poi_count = cursor.fetchone()['count']
print(f"5. POI Events: {poi_count:,}")

if poi_count > 0:
    cursor.execute("SELECT event_type, COUNT(*) as count FROM poi_events GROUP BY event_type")
    for row in cursor.fetchall():
        print(f"   {row['event_type']}: {row['count']:,}")

print()

# Check processing metadata
cursor.execute("SELECT * FROM processing_metadata ORDER BY updated_at DESC")
rows = cursor.fetchall()
if rows:
    print(f"6. Processing Metadata:")
    for row in rows:
        print(f"   {row['symbol']}/{row['process_type']}: {row['last_processed_time']} ({row['status']})")
else:
    print(f"6. Processing Metadata: No records")

print()
print("=" * 80)
print("DIAGNOSIS:")
print("=" * 80)

if ohlc_count == 0:
    print("X PROBLEM: No OHLC data loaded!")
    print("   SOLUTION: Run load_1m_csv.py to load data first")
elif session_count == 0:
    print("X PROBLEM: No sessions calculated!")
    print("   SOLUTION: Run calculate_daily_sessions.py to create sessions")
elif sessions_with_range == 0:
    print("X PROBLEM: Sessions exist but have no calculated ranges (PoC/TO/RPP)!")
    print("   SOLUTION: Run calculate_daily_sessions.py to calculate ranges")
elif poi_count == 0:
    print("WARNING: READY: Data and sessions exist, but no POI events yet")
    print("   ACTION: Run process_poi_events_1m.py to create POI events")
    print()
    print("   Let me check if there are candles after TO times...")

    # Check if there are candles after any session TO time
    cursor.execute("""
        SELECT s.session_name, s.to_time, s.symbol,
               (SELECT COUNT(*) FROM ohlc_1m o
                WHERE o.symbol = s.symbol AND o.time > s.to_time) as candles_after_to
        FROM sessions s
        WHERE s.true_open IS NOT NULL
        LIMIT 5
    """)

    print()
    print("   Sample sessions with candles after TO:")
    found_candles = False
    for row in cursor.fetchall():
        print(f"   {row['session_name']} ({row['symbol']}): {row['candles_after_to']} candles after TO")
        if row['candles_after_to'] > 0:
            found_candles = True

    if not found_candles:
        print()
        print("   WARNING: No candles found after session TO times!")
        print("   This means sessions were calculated at the end of available data.")
        print("   POI events can only be created when price touches occur AFTER the TO time.")
else:
    print("OK ALL GOOD: POI events exist!")

print()

conn.close()
