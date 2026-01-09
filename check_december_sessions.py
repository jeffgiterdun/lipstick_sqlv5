#!/usr/bin/env python3
"""
Check for December 2025 Monthly sessions in the database.
"""
import sqlite3

DB_PATH = 'data/ohlc_data.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("="*80)
print("Checking for December 2025 Monthly Sessions")
print("="*80)
print()

# Check for December 2025 specifically
cursor.execute("""
    SELECT id, symbol, session_name, session_type,
           true_open, poc, rpp,
           status, to_time, session_start_time
    FROM sessions
    WHERE session_type = 'Monthly'
    AND session_start_time LIKE '2025-12%'
""")

december_sessions = cursor.fetchall()

if december_sessions:
    print(f"Found {len(december_sessions)} December 2025 Monthly sessions:")
    print()
    for row in december_sessions:
        print(f"ID: {row['id']}")
        print(f"  Symbol: {row['symbol']}")
        print(f"  Session Name: {row['session_name']}")
        print(f"  Session Type: {row['session_type']}")
        print(f"  Status: {row['status']}")
        print(f"  Session Start: {row['session_start_time']}")
        print(f"  TO Time: {row['to_time']}")
        print(f"  True Open: {row['true_open']}")
        print(f"  PoC: {row['poc']}")
        print(f"  RPP: {row['rpp']}")
        print()
else:
    print("[X] No December 2025 Monthly sessions found!")
    print()

# Check all monthly sessions to see what we have
print("="*80)
print("All Monthly Sessions in Database")
print("="*80)
print()

cursor.execute("""
    SELECT id, symbol, session_name, session_type,
           true_open, poc, rpp,
           status, to_time, session_start_time
    FROM sessions
    WHERE session_type = 'Monthly'
    ORDER BY session_start_time DESC
    LIMIT 10
""")

all_monthly = cursor.fetchall()

if all_monthly:
    print(f"Most recent {len(all_monthly)} Monthly sessions:")
    print()
    for row in all_monthly:
        to_str = f"{row['true_open']:.2f}" if row['true_open'] else 'NULL'
        poc_str = f"{row['poc']:.2f}" if row['poc'] else 'NULL'
        print(f"{row['symbol']:3s} | {row['session_name']:20s} | TO: {to_str:>10s} | PoC: {poc_str:>10s} | Status: {row['status']}")
else:
    print("[X] No Monthly sessions found in database!")

print()

# Check data range in ohlc_1m
print("="*80)
print("OHLC 1M Data Range")
print("="*80)
print()

cursor.execute("""
    SELECT symbol,
           MIN(time) as earliest,
           MAX(time) as latest,
           COUNT(*) as candle_count
    FROM ohlc_1m
    GROUP BY symbol
""")

data_ranges = cursor.fetchall()

for row in data_ranges:
    print(f"{row['symbol']}:")
    print(f"  Earliest: {row['earliest']}")
    print(f"  Latest: {row['latest']}")
    print(f"  Total Candles: {row['candle_count']:,}")
    print()

# Check if we have December data
print("="*80)
print("December 2025 Data Availability")
print("="*80)
print()

cursor.execute("""
    SELECT symbol,
           MIN(time) as earliest_dec,
           MAX(time) as latest_dec,
           COUNT(*) as dec_candles
    FROM ohlc_1m
    WHERE time >= '2025-12-01' AND time < '2026-01-01'
    GROUP BY symbol
""")

dec_data = cursor.fetchall()

if dec_data:
    for row in dec_data:
        print(f"{row['symbol']} December 2025:")
        print(f"  First candle: {row['earliest_dec']}")
        print(f"  Last candle: {row['latest_dec']}")
        print(f"  Total candles: {row['dec_candles']:,}")
        print()
else:
    print("[X] No December 2025 data found in ohlc_1m table!")
    print()

conn.close()
