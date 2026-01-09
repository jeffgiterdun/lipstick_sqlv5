#!/usr/bin/env python3
"""
Check swings linked to December 2025 Monthly POI events.
"""
import sqlite3

DB_PATH = 'data/ohlc_data.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("="*80)
print("Swings Linked to December 2025 Monthly POI Events")
print("="*80)
print()

# Get December 2025 POI event IDs
cursor.execute("""
    SELECT id, poi_type, event_type, es_event_time, nq_event_time
    FROM poi_events
    WHERE session_name = 'December 2025'
    ORDER BY
        CASE event_type
            WHEN 'break' THEN 1
            WHEN 'return' THEN 2
            WHEN 'resolution' THEN 3
        END,
        poi_type
""")

december_poi_events = cursor.fetchall()

if not december_poi_events:
    print("[X] No December 2025 POI events found!")
    conn.close()
    exit(1)

print(f"December 2025 POI Events: {len(december_poi_events)}")
for event in december_poi_events:
    print(f"  - {event['event_type'].upper()} {event['poi_type']} (ID: {event['id']})")
print()

# Get swings linked to December POI events
print("="*80)
print("Swings Near December 2025 POI Events")
print("="*80)
print()

for poi_event in december_poi_events:
    poi_id = poi_event['id']
    poi_type = poi_event['poi_type']
    event_type = poi_event['event_type']

    print(f"\n{event_type.upper()} - {poi_type} (POI Event ID: {poi_id})")
    print("-" * 80)

    # Get swings linked to this POI event
    cursor.execute("""
        SELECT
            id,
            symbol,
            swing_time,
            swing_price,
            swing_type,
            swing_class,
            points_from_prior,
            candles_from_prior,
            candles_from_poi_event
        FROM swings
        WHERE nearest_poi_event_id = ?
        ORDER BY swing_time
        LIMIT 20
    """, (poi_id,))

    swings = cursor.fetchall()

    if not swings:
        print("  No swings linked to this POI event.")
        continue

    print(f"\n  Found {len(swings)} swings linked to this POI event (showing first 20):")
    print()

    # Group by symbol
    for symbol in ['ES', 'NQ']:
        symbol_swings = [s for s in swings if s['symbol'] == symbol]

        if not symbol_swings:
            continue

        print(f"  {symbol}:")
        for swing in symbol_swings[:10]:  # Show first 10 per symbol
            candles_from_poi = swing['candles_from_poi_event'] if swing['candles_from_poi_event'] else 'N/A'
            points = f"{swing['points_from_prior']:.2f}" if swing['points_from_prior'] else 'N/A'

            print(f"    Class {swing['swing_class']} {swing['swing_type']:4s} | "
                  f"{swing['swing_time']} | Price: {swing['swing_price']:8.2f} | "
                  f"Move: {points:>7s} pts | "
                  f"{candles_from_poi} candles from POI")

        if len(symbol_swings) > 10:
            print(f"    ... and {len(symbol_swings) - 10} more {symbol} swings")
        print()

# Summary statistics
print("="*80)
print("Summary - Swings by Class Near December Events")
print("="*80)
print()

cursor.execute("""
    SELECT
        s.symbol,
        s.swing_class,
        COUNT(*) as count
    FROM swings s
    INNER JOIN poi_events pe ON s.nearest_poi_event_id = pe.id
    WHERE pe.session_name = 'December 2025'
    GROUP BY s.symbol, s.swing_class
    ORDER BY s.symbol, s.swing_class
""")

summary = cursor.fetchall()

if summary:
    current_symbol = None
    for row in summary:
        if row['symbol'] != current_symbol:
            current_symbol = row['symbol']
            print(f"{current_symbol}:")
        print(f"  Class {row['swing_class']}: {row['count']} swings")
    print()

# Get significant swings (Class 3+)
print("="*80)
print("Significant Swings (Class 3+) Near December Events")
print("="*80)
print()

cursor.execute("""
    SELECT
        s.id,
        s.symbol,
        s.swing_time,
        s.swing_price,
        s.swing_type,
        s.swing_class,
        s.points_from_prior,
        s.candles_from_prior,
        s.candles_from_poi_event,
        pe.poi_type,
        pe.event_type
    FROM swings s
    INNER JOIN poi_events pe ON s.nearest_poi_event_id = pe.id
    WHERE pe.session_name = 'December 2025'
    AND s.swing_class >= 3
    ORDER BY s.swing_class DESC, s.swing_time
    LIMIT 30
""")

major_swings = cursor.fetchall()

if major_swings:
    print(f"Found {len(major_swings)} Class 3+ swings (showing up to 30):")
    print()

    for swing in major_swings:
        points = f"{swing['points_from_prior']:.2f}" if swing['points_from_prior'] else 'N/A'
        candles = swing['candles_from_prior'] if swing['candles_from_prior'] else 'N/A'
        candles_from_poi = swing['candles_from_poi_event'] if swing['candles_from_poi_event'] else 'N/A'

        print(f"{swing['symbol']} Class {swing['swing_class']} {swing['swing_type']:4s} | "
              f"{swing['swing_time']} | "
              f"Price: {swing['swing_price']:8.2f} | "
              f"Move: {points:>7s} pts in {candles} candles")
        print(f"  Near: {swing['event_type'].upper()} {swing['poi_type']} ({candles_from_poi} candles from POI)")
        print()
else:
    print("No Class 3+ swings found near December POI events.")

conn.close()
