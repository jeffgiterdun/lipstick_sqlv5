#!/usr/bin/env python3
"""Verify sessions created in database."""
import sqlite3

conn = sqlite3.connect('data/ohlc_data.db')
cursor = conn.cursor()

print("=" * 80)
print("SESSION VERIFICATION")
print("=" * 80)
print()

# Sessions by type
print("Sessions by Type:")
print("-" * 80)
cursor.execute("""
    SELECT session_type, COUNT(*) as count
    FROM sessions
    GROUP BY session_type
    ORDER BY session_type
""")

for row in cursor.fetchall():
    print(f"  {row[0]:10} {row[1]:>5} sessions")

# Total
cursor.execute("SELECT COUNT(*) FROM sessions")
total = cursor.fetchone()[0]
print("-" * 80)
print(f"  TOTAL:     {total:>5} sessions")
print()

# Sessions by symbol
print("Sessions by Symbol:")
print("-" * 80)
cursor.execute("""
    SELECT symbol, session_type, COUNT(*) as count
    FROM sessions
    GROUP BY symbol, session_type
    ORDER BY symbol, session_type
""")

current_symbol = None
for row in cursor.fetchall():
    symbol, session_type, count = row
    if symbol != current_symbol:
        if current_symbol is not None:
            print()
        print(f"  {symbol}:")
        current_symbol = symbol
    print(f"    {session_type:10} {count:>5}")

print()

# Sample sessions
print("Sample Major Sessions (first 5):")
print("-" * 80)
cursor.execute("""
    SELECT session_name, to_time, true_open, poc, rpp, status
    FROM sessions
    WHERE session_type = 'Major'
    ORDER BY to_time
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"  {row[0]:<25} TO: {row[1][:16]} | TO_Price: {row[2]:.2f} | PoC: {row[3]:.2f} | RPP: {row[4]:.2f} | {row[5]}")

print()

# Sample Weekly sessions
print("Weekly Sessions:")
print("-" * 80)
cursor.execute("""
    SELECT symbol, session_name, to_time, true_open, poc, rpp
    FROM sessions
    WHERE session_type = 'Weekly'
    ORDER BY symbol, to_time
""")

for row in cursor.fetchall():
    print(f"  {row[0]} {row[1]:<20} TO: {row[2][:16]} | TO: {row[3]:.2f} | PoC: {row[4]:.2f} | RPP: {row[5]:.2f}")

print()

# Sample Monthly sessions
print("Monthly Sessions:")
print("-" * 80)
cursor.execute("""
    SELECT symbol, session_name, to_time, true_open, poc, rpp
    FROM sessions
    WHERE session_type = 'Monthly'
    ORDER BY symbol, to_time
""")

for row in cursor.fetchall():
    print(f"  {row[0]} {row[1]:<10} TO: {row[2][:16]} | TO: {row[3]:.2f} | PoC: {row[4]:.2f} | RPP: {row[5]:.2f}")

print()
print("=" * 80)

conn.close()
