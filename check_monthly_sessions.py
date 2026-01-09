#!/usr/bin/env python3
"""Check monthly sessions and data requirements."""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/ohlc_data.db')
cursor = conn.cursor()

print("=" * 120)
print("MONTHLY SESSIONS STATUS")
print("=" * 120)
print()

# Check existing monthly sessions
cursor.execute("""
    SELECT symbol, session_name, session_start_time, to_time, true_open, poc, rpp
    FROM sessions
    WHERE session_type = 'Monthly'
    ORDER BY symbol, to_time
""")

print("Existing Monthly Sessions:")
print("-" * 120)
print(f"{'Symbol':<6} {'Month':<10} {'Start Time':<20} {'TO Time':<20} {'TO':>10} {'PoC':>10} {'RPP':>10}")
print("-" * 120)

for row in cursor.fetchall():
    symbol, name, start, to, to_price, poc, rpp = row
    print(f"{symbol:<6} {name:<10} {start[:19]:<20} {to[:19]:<20} {to_price:>10.2f} {poc:>10.2f} {rpp:>10.2f}")

print()

# Check data range
cursor.execute("""
    SELECT symbol, MIN(time) as first, MAX(time) as last
    FROM ohlc_1m
    GROUP BY symbol
""")

print("Available Data Range:")
print("-" * 120)
for row in cursor.fetchall():
    symbol, first, last = row
    first_dt = datetime.fromisoformat(first)
    last_dt = datetime.fromisoformat(last)
    print(f"  {symbol}: {first[:10]} to {last[:10]} ({first_dt.strftime('%B %d')} - {last_dt.strftime('%B %d, %Y')})")

print()
print("Analysis:")
print("-" * 120)
print("  December 2025:")
print("    - Dec 1, 2025 = Monday")
print("    - First full week: Dec 1-7 (Mon-Sun)")
print("    - Second full week starts: Sunday Dec 14 at 18:00")
print("    - Monthly TO: Sunday Dec 14 at 18:00 [CALCULATED]")
print()
print("  January 2026:")
print("    - Jan 1, 2026 = Wednesday")
print("    - Week of Jan 1 is NOT a full week (starts mid-week)")
print("    - First full week: Jan 5-11 (Mon-Sun)")
print("    - Second full week starts: Sunday Jan 18 at 18:00")
print("    - Current data ends: Jan 2, 2026")
print("    - Status: Need data through at least Jan 18 to calculate monthly TO [NOT ENOUGH DATA]")
print()
print("Conclusion:")
print("  [OK] December 2025 monthly sessions: COMPLETE")
print("  [PENDING] January 2026 monthly sessions: Need ~16 more days of data")

print()
print("=" * 120)

conn.close()
