#!/usr/bin/env python3
"""Check corrected weekly sessions."""
import sqlite3

conn = sqlite3.connect('data/ohlc_data.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT symbol, session_name, session_start_time, to_time, true_open, poc, rpp
    FROM sessions
    WHERE session_type = 'Weekly'
    ORDER BY symbol, to_time
""")

print("=" * 120)
print("Weekly Sessions (CORRECTED)")
print("=" * 120)
print(f"{'Symbol':<6} {'Session Name':<22} {'Start Time':<20} {'TO Time':<20} {'TO':>10} {'PoC':>10} {'RPP':>10}")
print("-" * 120)

for row in cursor.fetchall():
    symbol, name, start, to, to_price, poc, rpp = row
    print(f"{symbol:<6} {name:<22} {start[:19]:<20} {to[:19]:<20} {to_price:>10.2f} {poc:>10.2f} {rpp:>10.2f}")

print("=" * 120)

# Verify the TO times are Monday 18:00
print()
print("Verification: TO times should all be Monday 18:00")
print("-" * 120)

cursor.execute("""
    SELECT symbol, session_name, to_time
    FROM sessions
    WHERE session_type = 'Weekly'
    ORDER BY symbol, to_time
""")

for row in cursor.fetchall():
    symbol, name, to = row
    from datetime import datetime
    to_dt = datetime.fromisoformat(to)
    day_name = to_dt.strftime("%A")
    time_str = to_dt.strftime("%H:%M")
    status = "OK" if day_name == "Monday" and time_str == "18:00" else "ERROR"
    print(f"  {symbol} {name:<22} {to[:19]} ({day_name} {time_str}) [{status}]")

conn.close()
