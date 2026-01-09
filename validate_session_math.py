#!/usr/bin/env python3
"""Validate session PoC/TO/RPP symmetry."""
import sqlite3

conn = sqlite3.connect('data/ohlc_data.db')
cursor = conn.cursor()

print("=" * 80)
print("SESSION MATH VALIDATION")
print("=" * 80)
print()

# Check symmetry: RPP should equal 2*TO - PoC
cursor.execute("""
    SELECT
        session_name,
        true_open,
        poc,
        rpp,
        (2 * true_open - poc) as calculated_rpp,
        ABS(rpp - (2 * true_open - poc)) as error
    FROM sessions
    WHERE true_open IS NOT NULL
    ORDER BY error DESC
    LIMIT 10
""")

print("Top 10 Sessions by RPP Calculation Error:")
print("-" * 80)
print(f"{'Session':<30} {'TO':>10} {'PoC':>10} {'RPP':>10} {'Calc':>10} {'Error':>10}")
print("-" * 80)

max_error = 0
for row in cursor.fetchall():
    session_name, to, poc, rpp, calc_rpp, error = row
    max_error = max(max_error, error)
    # Truncate session name if needed
    session_short = session_name[:28] if len(session_name) > 28 else session_name
    print(f"{session_short:<30} {to:>10.2f} {poc:>10.2f} {rpp:>10.2f} {calc_rpp:>10.2f} {error:>10.4f}")

print()

if max_error < 0.01:
    print("[OK] All sessions have correct RPP = 2*TO - PoC symmetry!")
    print(f"     Maximum error: {max_error:.6f}")
else:
    print(f"[WARNING] Some sessions have calculation errors up to {max_error:.4f}")

print()

# Check for NULL values
cursor.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN true_open IS NULL THEN 1 ELSE 0 END) as null_to,
        SUM(CASE WHEN poc IS NULL THEN 1 ELSE 0 END) as null_poc,
        SUM(CASE WHEN rpp IS NULL THEN 1 ELSE 0 END) as null_rpp
    FROM sessions
""")

total, null_to, null_poc, null_rpp = cursor.fetchone()

print("NULL Value Check:")
print("-" * 80)
print(f"  Total sessions: {total}")
print(f"  NULL TO: {null_to}")
print(f"  NULL PoC: {null_poc}")
print(f"  NULL RPP: {null_rpp}")

if null_to == 0 and null_poc == 0 and null_rpp == 0:
    print()
    print("[OK] All sessions have complete PoC/TO/RPP values!")
else:
    print()
    print("[WARNING] Some sessions have NULL values")

print()
print("=" * 80)

conn.close()
