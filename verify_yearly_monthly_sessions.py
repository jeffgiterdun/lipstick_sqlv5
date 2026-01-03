"""
Verify Yearly and Monthly sessions in yearly_monthly.db.

This script performs comprehensive verification of the calculated sessions:
- Checks session counts by type and year
- Validates range symmetry (PoC ← TO → RPP)
- Displays sample sessions for manual review
- Checks for missing data

Usage:
    python verify_yearly_monthly_sessions.py
"""

import sqlite3
from datetime import datetime

DB_PATH = 'data/yearly_monthly.db'


def print_header(title: str, width: int = 80):
    """Print a formatted section header."""
    print()
    print("=" * width)
    print(title)
    print("=" * width)
    print()


def verify_session_counts(conn: sqlite3.Connection):
    """Verify session counts by type."""
    print_header("SESSION COUNTS BY TYPE")

    cursor = conn.cursor()

    # Count by session type
    cursor.execute("""
        SELECT session_type, COUNT(*) as count
        FROM sessions
        GROUP BY session_type
        ORDER BY session_type
    """)

    for session_type, count in cursor.fetchall():
        print(f"{session_type:10s}: {count:4d} sessions")

    # Count by symbol
    print()
    cursor.execute("""
        SELECT symbol, COUNT(*) as count
        FROM sessions
        GROUP BY symbol
        ORDER BY symbol
    """)

    for symbol, count in cursor.fetchall():
        print(f"{symbol:10s}: {count:4d} sessions")

    # Total
    print()
    cursor.execute("SELECT COUNT(*) FROM sessions")
    total = cursor.fetchone()[0]
    print(f"{'TOTAL':10s}: {total:4d} sessions")


def verify_yearly_sessions(conn: sqlite3.Connection):
    """Verify Yearly sessions by year."""
    print_header("YEARLY SESSIONS BY YEAR")

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            substr(session_start_time, 1, 4) as year,
            symbol,
            session_start_time,
            to_time,
            true_open,
            poc,
            rpp,
            ROUND(rpp - true_open, 2) as to_to_rpp,
            ROUND(true_open - poc, 2) as poc_to_to
        FROM sessions
        WHERE session_type = 'Yearly'
        ORDER BY year, symbol
    """)

    print(f"{'Year':<6} {'Symbol':<6} {'TO':<10} {'PoC':<10} {'RPP':<10} {'TO-RPP':<10} {'PoC-TO':<10} {'Symmetric?':<12}")
    print("-" * 80)

    for row in cursor.fetchall():
        year, symbol, start_time, to_time, to, poc, rpp, to_to_rpp, poc_to_to = row

        # Check if symmetric (PoC <- TO -> RPP)
        # TO - PoC should equal RPP - TO
        symmetric = abs(abs(to_to_rpp) - abs(poc_to_to)) < 0.01
        sym_str = "YES" if symmetric else "NO"

        print(f"{year:<6} {symbol:<6} {to:<10.2f} {poc:<10.2f} {rpp:<10.2f} "
              f"{to_to_rpp:<10.2f} {poc_to_to:<10.2f} {sym_str:<12}")

    print()
    print("Note: Symmetric = YES means RPP is a perfect mirror of PoC across TO")


def verify_monthly_sessions(conn: sqlite3.Connection):
    """Verify Monthly sessions by year/month."""
    print_header("MONTHLY SESSIONS BY YEAR/MONTH")

    cursor = conn.cursor()

    # Count by year-month
    cursor.execute("""
        SELECT
            substr(session_start_time, 1, 7) as year_month,
            COUNT(*) as count
        FROM sessions
        WHERE session_type = 'Monthly'
        GROUP BY year_month
        ORDER BY year_month
    """)

    print(f"{'Year-Month':<12} {'Count':<6} {'Expected':<10} {'Status':<10}")
    print("-" * 40)

    for year_month, count in cursor.fetchall():
        expected = 2  # ES and NQ
        status = "OK" if count == expected else f"MISSING {expected - count}"
        print(f"{year_month:<12} {count:<6} {expected:<10} {status:<10}")


def display_sample_sessions(conn: sqlite3.Connection):
    """Display sample sessions for manual review."""
    print_header("SAMPLE SESSIONS")

    cursor = conn.cursor()

    # Recent Yearly session
    print("Recent Yearly Session (2024 ES):")
    print("-" * 80)
    cursor.execute("""
        SELECT
            session_start_time,
            to_time,
            true_open,
            poc,
            rpp,
            status
        FROM sessions
        WHERE session_type = 'Yearly'
        AND symbol = 'ES'
        AND session_start_time LIKE '2024%'
    """)

    for row in cursor.fetchall():
        start_time, to_time, to, poc, rpp, status = row
        print(f"  Start Time: {start_time}")
        print(f"  TO Time:    {to_time}")
        print(f"  True Open:  {to:.2f}")
        print(f"  PoC:        {poc:.2f} ({poc - to:+.2f})")
        print(f"  RPP:        {rpp:.2f} ({rpp - to:+.2f})")
        print(f"  Status:     {status}")
        print()

    # Recent Monthly session
    print("Recent Monthly Session (2025-12 ES):")
    print("-" * 80)
    cursor.execute("""
        SELECT
            session_start_time,
            to_time,
            true_open,
            poc,
            rpp,
            status
        FROM sessions
        WHERE session_type = 'Monthly'
        AND symbol = 'ES'
        AND session_start_time LIKE '2025-12%'
    """)

    for row in cursor.fetchall():
        start_time, to_time, to, poc, rpp, status = row
        print(f"  Start Time: {start_time}")
        print(f"  TO Time:    {to_time}")
        print(f"  True Open:  {to:.2f}")
        print(f"  PoC:        {poc:.2f} ({poc - to:+.2f})")
        print(f"  RPP:        {rpp:.2f} ({rpp - to:+.2f})")
        print(f"  Status:     {status}")
        print()


def check_range_symmetry(conn: sqlite3.Connection):
    """Check that all ranges are symmetric."""
    print_header("RANGE SYMMETRY CHECK")

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            symbol,
            session_type,
            session_start_time,
            true_open,
            poc,
            rpp,
            ABS((true_open - poc) - (rpp - true_open)) as asymmetry
        FROM sessions
        WHERE ABS((true_open - poc) - (rpp - true_open)) > 0.01
        ORDER BY asymmetry DESC
    """)

    asymmetric = cursor.fetchall()

    if asymmetric:
        print(f"Found {len(asymmetric)} sessions with asymmetric ranges:")
        print()
        print(f"{'Symbol':<6} {'Type':<8} {'Start Time':<25} {'TO':<10} {'PoC':<10} {'RPP':<10} {'Asymmetry':<12}")
        print("-" * 90)

        for row in asymmetric:
            symbol, session_type, start_time, to, poc, rpp, asymmetry = row
            print(f"{symbol:<6} {session_type:<8} {start_time:<25} {to:<10.2f} {poc:<10.2f} {rpp:<10.2f} {asymmetry:<12.4f}")
    else:
        print("[OK] All ranges are perfectly symmetric!")
        print()


def check_null_values(conn: sqlite3.Connection):
    """Check for any NULL values in critical fields."""
    print_header("NULL VALUE CHECK")

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN true_open IS NULL THEN 1 ELSE 0 END) as null_to,
            SUM(CASE WHEN poc IS NULL THEN 1 ELSE 0 END) as null_poc,
            SUM(CASE WHEN rpp IS NULL THEN 1 ELSE 0 END) as null_rpp
        FROM sessions
    """)

    total, null_to, null_poc, null_rpp = cursor.fetchone()

    print(f"Total Sessions:        {total}")
    print(f"NULL True Open:        {null_to}")
    print(f"NULL PoC:              {null_poc}")
    print(f"NULL RPP:              {null_rpp}")
    print()

    if null_to == 0 and null_poc == 0 and null_rpp == 0:
        print("[OK] No NULL values in critical fields!")
    else:
        print("[WARNING] Found NULL values - check data quality")

    print()


def display_data_coverage(conn: sqlite3.Connection):
    """Display overall data coverage."""
    print_header("DATA COVERAGE")

    cursor = conn.cursor()

    # Date range
    cursor.execute("""
        SELECT
            MIN(session_start_time) as min_start,
            MAX(session_start_time) as max_start,
            MIN(to_time) as min_to,
            MAX(to_time) as max_to
        FROM sessions
    """)

    min_start, max_start, min_to, max_to = cursor.fetchone()

    print(f"Session Start Range:   {min_start[:10]} to {max_start[:10]}")
    print(f"True Open Range:       {min_to[:10]} to {max_to[:10]}")
    print()

    # Yearly coverage
    cursor.execute("""
        SELECT
            substr(session_start_time, 1, 4) as year,
            COUNT(DISTINCT symbol) as symbols
        FROM sessions
        WHERE session_type = 'Yearly'
        GROUP BY year
        ORDER BY year
    """)

    print("Yearly Sessions Coverage:")
    for year, symbols in cursor.fetchall():
        status = "Complete" if symbols == 2 else f"Missing {2-symbols} symbol(s)"
        print(f"  {year}: {symbols}/2 symbols ({status})")

    print()


def main():
    """Main verification function."""
    print("=" * 80)
    print("YEARLY AND MONTHLY SESSIONS VERIFICATION")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)

    # Run verification checks
    verify_session_counts(conn)
    display_data_coverage(conn)
    verify_yearly_sessions(conn)
    verify_monthly_sessions(conn)
    check_range_symmetry(conn)
    check_null_values(conn)
    display_sample_sessions(conn)

    conn.close()

    print_header("VERIFICATION COMPLETE")
    print("All checks completed successfully!")
    print()


if __name__ == '__main__':
    main()
