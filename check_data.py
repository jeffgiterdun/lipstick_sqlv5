#!/usr/bin/env python3
"""Quick check of current 1M data in database."""
import sqlite3

conn = sqlite3.connect('data/ohlc_data.db')
cursor = conn.cursor()

print("Current 1M Data:")
print("-" * 80)

cursor.execute("""
    SELECT symbol, MIN(time) as first_candle, MAX(time) as last_candle, COUNT(*) as total_candles
    FROM ohlc_1m
    GROUP BY symbol
""")

for row in cursor.fetchall():
    symbol, first, last, count = row
    print(f"{symbol:>6}: {first} to {last} ({count:,} candles)")

conn.close()
