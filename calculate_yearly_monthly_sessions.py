"""
Calculate Yearly and Monthly sessions using 4H OHLC data.

This script processes 4H data from yearly_monthly.db and populates
the sessions table with Yearly and Monthly session ranges.

Yearly Session:
- PoC Window: First full trading day of January → End of March (Q1)
- TO Time: First Sunday 18:00 of April
- PoC: Highest high or lowest low from Q1 with greatest variance from TO

Monthly Session:
- PoC Window: First full trading day of month → End of first full week
- TO Time: Sunday 18:00 of second full week
- PoC: Highest high or lowest low from window with greatest variance from TO

Usage:
    python calculate_yearly_monthly_sessions.py
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

# Database path
DB_PATH = 'data/yearly_monthly.db'

# Timezone
ET = pytz.timezone('US/Eastern')


def get_first_full_trading_day(year: int, month: int, conn: sqlite3.Connection = None, symbol: str = None) -> datetime:
    """
    Calculate the first full trading day of the month with complete 4H data.

    Rule: We need the first day's trading session to have a full day's worth of data (6 4H candles).

    Args:
        year: Year
        month: Month (1-12)
        conn: Optional database connection to validate trading data
        symbol: Optional symbol ('ES' or 'NQ') to validate trading data

    Returns:
        datetime: First full trading day at 18:00 ET with complete data
    """
    first_day = datetime(year, month, 1)
    first_day = ET.localize(first_day)

    # Try up to 7 days to find the first day with full data
    max_attempts = 7
    attempts = 0
    current_day = first_day

    while attempts < max_attempts:
        # What day of week is this day?
        # 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
        day_of_week = current_day.weekday()

        # Rule: Each calendar day's trading session starts at 18:00 the PREVIOUS day
        # Exception: Sunday's trading session starts Sunday 18:00 (same day)
        if day_of_week == 6:  # Sunday
            # Sunday's trading session starts Sunday 18:00 (same day)
            trading_day = current_day
        else:  # Monday through Saturday (0-5)
            # Go back 1 day (each day's trading session starts previous day at 18:00)
            trading_day = current_day - timedelta(days=1)

        # Set time to 18:00
        trading_day = trading_day.replace(hour=18, minute=0, second=0, microsecond=0)

        # If no connection provided, just return the first day (legacy behavior)
        if conn is None or symbol is None:
            return trading_day

        # Check if we have FULL day's worth of trading data (6 4H candles minimum)
        if has_full_day_data(conn, symbol, trading_day):
            # Found full day - this is our first full trading day with complete data
            if attempts > 0:
                print(f"  [INFO] First day with full data is {current_day.strftime('%Y-%m-%d')} (skipped {attempts} incomplete day(s))")
            return trading_day

        # Incomplete or no data - try next day
        if attempts == 0:
            print(f"  [INFO] Day {current_day.strftime('%Y-%m-%d')} in {year}-{month:02d} has incomplete data - checking next day")

        current_day += timedelta(days=1)
        attempts += 1

    # If we exhausted attempts, return the last day we tried
    print(f"  [WARN] No day with full data found in {year}-{month:02d} after {max_attempts} attempts - using last attempted day")
    return trading_day


def get_first_monday_trading_time(year: int, month: int, conn: sqlite3.Connection = None, symbol: str = None) -> datetime:
    """
    Get the 18:00 time that starts the first Monday of the month with actual trading data.

    This is the Sunday 18:00 (or same-day Monday 18:00 if Monday is the 1st)
    that begins the first Monday's trading session. If conn and symbol are provided,
    validates that trading data exists for that Monday.

    Args:
        year: Year
        month: Month (1-12)
        conn: Optional database connection to validate trading data
        symbol: Optional symbol ('ES' or 'NQ') to validate trading data

    Returns:
        datetime: 18:00 time that starts first Monday's trading with data
    """
    first_day = datetime(year, month, 1)
    first_day = ET.localize(first_day)

    # Find first Monday of the month
    day_of_week = first_day.weekday()  # 0=Mon, 6=Sun

    if day_of_week == 0:  # First day is Monday
        first_monday = first_day
    else:
        # Days until next Monday
        if day_of_week == 6:  # Sunday
            days_until_monday = 1
        else:  # Tuesday-Saturday
            days_until_monday = 7 - day_of_week
        first_monday = first_day + timedelta(days=days_until_monday)

    # If we have conn and symbol, validate that this Monday has FULL trading data
    # If not, keep trying next Mondays (max 4 attempts)
    max_attempts = 4
    attempts = 0

    while attempts < max_attempts:
        # Get the 18:00 time that starts this Monday's trading
        # Monday's trading starts the previous day (Sunday) at 18:00
        trading_start = first_monday - timedelta(days=1)
        trading_start = trading_start.replace(hour=18, minute=0, second=0, microsecond=0)

        # If no connection provided, just return the first Monday (legacy behavior)
        if conn is None or symbol is None:
            return trading_start

        # Check if we have FULL day's worth of trading data (6 4H candles minimum)
        if has_full_day_data(conn, symbol, trading_start):
            # Found full day - this is our first Monday with complete data
            if attempts > 0:
                print(f"  [INFO] First Monday with full data is {first_monday.strftime('%Y-%m-%d')} (skipped {attempts} incomplete Monday(s))")
            return trading_start

        # Incomplete or no data - try next Monday
        if attempts == 0:
            print(f"  [INFO] Monday {first_monday.strftime('%Y-%m-%d')} in {year}-{month:02d} has incomplete data - checking next Monday")

        first_monday += timedelta(weeks=1)
        attempts += 1

    # If we exhausted attempts, return the last Monday we tried
    # (This maintains backward compatibility but logs a warning)
    print(f"  [WARN] No Monday with full data found in {year}-{month:02d} after {max_attempts} attempts - using last attempted Monday")
    return trading_start


def get_second_full_week_sunday(year: int, month: int, conn: sqlite3.Connection = None, symbol: str = None) -> datetime:
    """
    Calculate the Sunday 18:00 that begins the second Monday of the month with complete data.

    The TO time is always the Sunday 18:00 that starts the second Monday's trading session.
    If conn and symbol are provided, will validate first Monday has complete data.

    Args:
        year: Year
        month: Month (1-12)
        conn: Optional database connection to check for trading data
        symbol: Optional symbol ('ES' or 'NQ') to check for trading data

    Returns:
        datetime: Sunday 18:00 that starts second Monday's trading
    """
    # If we have conn and symbol, get the first Monday WITH complete data
    # Otherwise fall back to calendar-based first Monday
    if conn is not None and symbol is not None:
        # Use get_first_monday_trading_time to get first Monday with data
        first_monday_trading_start = get_first_monday_trading_time(year, month, conn, symbol)
        # This returns Sunday 18:00 (timezone-aware), so we need to add 1 day to get the actual Monday
        first_monday_aware = first_monday_trading_start + timedelta(days=1)
        # Convert to naive datetime for processing
        first_monday = first_monday_aware.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    else:
        # Legacy behavior: calendar-based first Monday
        first_day = datetime(year, month, 1)
        day_of_week = first_day.weekday()

        if day_of_week == 0:  # Already Monday
            first_monday = first_day
        else:
            if day_of_week == 6:  # Sunday
                days_until_monday = 1
            else:  # Tuesday-Saturday
                days_until_monday = 7 - day_of_week
            first_monday = first_day + timedelta(days=days_until_monday)

    # Second Monday is always 1 week after first Monday (with data)
    second_monday = first_monday + timedelta(weeks=1)

    # Sunday 18:00 before second Monday is the TO time
    second_monday_sunday_naive = (second_monday - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)

    # Localize to ET, letting pytz determine DST automatically
    second_monday_sunday = ET.localize(second_monday_sunday_naive, is_dst=None)

    return second_monday_sunday


def calculate_poc_and_rpp(
    candles: List[Tuple],
    to_price: float
) -> Tuple[float, float]:
    """
    Calculate PoC (Point of Control) and RPP (Range Projection Point).

    PoC = highest high or lowest low with greatest variance from TO
    RPP = 2 * TO - PoC (mirror projection)

    Args:
        candles: List of (time, open, high, low, close) tuples
        to_price: True Open price

    Returns:
        Tuple of (poc, rpp)
    """
    if not candles:
        return None, None

    # Find highest high and lowest low in the window
    highest = max(candle[2] for candle in candles)  # high
    lowest = min(candle[3] for candle in candles)   # low

    # Calculate variance from TO
    high_variance = abs(highest - to_price)
    low_variance = abs(lowest - to_price)

    # PoC is the one with greater variance
    if high_variance > low_variance:
        poc = highest
    else:
        poc = lowest

    # Calculate RPP (mirror projection)
    rpp = 2 * to_price - poc

    return poc, rpp


def get_ohlc_candles(
    conn: sqlite3.Connection,
    symbol: str,
    start_time: datetime,
    end_time: datetime
) -> List[Tuple]:
    """
    Fetch OHLC candles between start and end time.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        start_time: Start datetime (inclusive)
        end_time: End datetime (exclusive)

    Returns:
        List of (time, open, high, low, close) tuples
    """
    cursor = conn.cursor()

    # Convert to ISO format strings
    start_str = start_time.isoformat()
    end_str = end_time.isoformat()

    cursor.execute("""
        SELECT time, open, high, low, close
        FROM ohlc_4h
        WHERE symbol = ?
        AND time >= ?
        AND time < ?
        ORDER BY time
    """, (symbol, start_str, end_str))

    return cursor.fetchall()


def get_candle_at_time(
    conn: sqlite3.Connection,
    symbol: str,
    target_time: datetime
) -> Optional[Tuple]:
    """
    Get the OHLC candle at a specific time.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        target_time: Target datetime

    Returns:
        Tuple of (time, open, high, low, close) or None
    """
    cursor = conn.cursor()
    time_str = target_time.isoformat()

    cursor.execute("""
        SELECT time, open, high, low, close
        FROM ohlc_4h
        WHERE symbol = ?
        AND time = ?
    """, (symbol, time_str))

    result = cursor.fetchone()
    return result


def has_full_day_data(
    conn: sqlite3.Connection,
    symbol: str,
    trading_start: datetime,
    min_candles: int = 6
) -> bool:
    """
    Check if a trading day has a full day's worth of 4H candle data.

    A full trading day starting at trading_start (18:00) should have 6 4H candles:
    18:00, 22:00, 02:00, 06:00, 10:00, 14:00

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        trading_start: Trading day start time (18:00)
        min_candles: Minimum number of candles required (default 6)

    Returns:
        bool: True if full day's data exists, False otherwise
    """
    # End of trading day is 18:00 next day (24 hours later)
    trading_end = trading_start + timedelta(hours=24)

    # Get all candles in this trading day
    candles = get_ohlc_candles(conn, symbol, trading_start, trading_end)

    return len(candles) >= min_candles


def calculate_yearly_session(
    conn: sqlite3.Connection,
    year: int,
    symbol: str
) -> Optional[Dict]:
    """
    Calculate Yearly session for a given year and symbol.

    Args:
        conn: Database connection
        year: Calendar year
        symbol: 'ES' or 'NQ'

    Returns:
        Dict with session data or None if data missing
    """
    # Get first full trading day of January (with data validation)
    session_start = get_first_full_trading_day(year, 1, conn, symbol)

    # Get the 18:00 time that starts the first Monday of April (with data validation)
    to_time = get_first_monday_trading_time(year, 4, conn, symbol)

    # PoC window: session_start through end of March (exclusive of TO candle)
    # End of March is March 31 23:59:59
    end_of_march = datetime(year, 3, 31, 23, 59, 59)
    end_of_march = ET.localize(end_of_march)

    # Get TO candle
    to_candle = get_candle_at_time(conn, symbol, to_time)
    if not to_candle:
        print(f"  [WARN] No TO candle found for {year} Yearly {symbol} at {to_time}")
        return None

    to_price = to_candle[1]  # open price

    # Get PoC window candles
    poc_candles = get_ohlc_candles(conn, symbol, session_start, end_of_march)
    if not poc_candles:
        print(f"  [WARN] No PoC candles found for {year} Yearly {symbol}")
        return None

    # Calculate PoC and RPP
    poc, rpp = calculate_poc_and_rpp(poc_candles, to_price)

    # Create session record
    now = datetime.now(ET).isoformat()

    session = {
        'symbol': symbol,
        'session_type': 'Yearly',
        'session_name': f'Year {year}',  # e.g., "Year 2019"
        'session_start_time': session_start.isoformat(),
        'to_time': to_time.isoformat(),
        'true_open': to_price,
        'poc': poc,
        'rpp': rpp,
        'status': 'unbroken',
        'expires_at': None,
        'created_at': now,
        'updated_at': now
    }

    return session


def calculate_monthly_session(
    conn: sqlite3.Connection,
    year: int,
    month: int,
    symbol: str
) -> Optional[Dict]:
    """
    Calculate Monthly session for a given month and symbol.

    Args:
        conn: Database connection
        year: Year
        month: Month (1-12)
        symbol: 'ES' or 'NQ'

    Returns:
        Dict with session data or None if data missing
    """
    # Get first full trading day of the month (with data validation)
    session_start = get_first_full_trading_day(year, month, conn, symbol)

    # Get second full week - the 18:00 time that starts that Monday
    # Pass conn and symbol so it can check for holidays
    to_time = get_second_full_week_sunday(year, month, conn, symbol)

    # Try to find a TO candle, accounting for holidays and data gaps
    # If no candle at calculated time, try next weeks (max 4 attempts)
    to_candle = None
    attempts = 0
    max_attempts = 4
    current_to_time = to_time

    while to_candle is None and attempts < max_attempts:
        to_candle = get_candle_at_time(conn, symbol, current_to_time)

        if to_candle is None:
            # No data at this time - likely a holiday or DST transition
            # Try next week
            if attempts == 0:
                print(f"  [INFO] No candle at {current_to_time.strftime('%Y-%m-%d')} for {year}-{month:02d} {symbol} - checking next week (holiday/data gap)")

            # Add 1 week preserving wall-clock time (18:00)
            current_naive = datetime(current_to_time.year, current_to_time.month, current_to_time.day,
                                   current_to_time.hour, current_to_time.minute, current_to_time.second)
            next_week_naive = current_naive + timedelta(weeks=1)
            current_to_time = ET.localize(next_week_naive, is_dst=None)
            attempts += 1
        else:
            # Found candle - use this as TO time
            to_time = current_to_time
            if attempts > 0:
                print(f"  [INFO] Found TO candle at {to_time.strftime('%Y-%m-%d')} (skipped {attempts} week(s))")

    if not to_candle:
        print(f"  [WARN] No TO candle found for {year}-{month:02d} Monthly {symbol} after {max_attempts} attempts")
        return None

    to_price = to_candle[1]  # open price

    # PoC window: session_start through end of first full week
    # End of first full week is the Saturday 16:59:59 before the second full week Sunday
    end_of_first_week = to_time - timedelta(hours=1, seconds=1)

    # Get PoC window candles
    poc_candles = get_ohlc_candles(conn, symbol, session_start, end_of_first_week)
    if not poc_candles:
        print(f"  [WARN] No PoC candles found for {year}-{month:02d} Monthly {symbol}")
        return None

    # Calculate PoC and RPP
    poc, rpp = calculate_poc_and_rpp(poc_candles, to_price)

    # Create session record
    now = datetime.now(ET).isoformat()

    # Get month name (e.g., "January", "February", etc.)
    month_name = datetime(year, month, 1).strftime('%B')

    session = {
        'symbol': symbol,
        'session_type': 'Monthly',
        'session_name': f'{month_name} {year}',  # e.g., "January 2019"
        'session_start_time': session_start.isoformat(),
        'to_time': to_time.isoformat(),
        'true_open': to_price,
        'poc': poc,
        'rpp': rpp,
        'status': 'unbroken',
        'expires_at': None,
        'created_at': now,
        'updated_at': now
    }

    return session


def insert_session(conn: sqlite3.Connection, session: Dict) -> bool:
    """
    Insert a session into the database.

    Args:
        conn: Database connection
        session: Session dictionary

    Returns:
        bool: True if inserted, False if duplicate
    """
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO sessions (
                symbol, session_type, session_name,
                session_start_time, to_time,
                true_open, poc, rpp,
                status, expires_at,
                created_at, updated_at
            ) VALUES (
                :symbol, :session_type, :session_name,
                :session_start_time, :to_time,
                :true_open, :poc, :rpp,
                :status, :expires_at,
                :created_at, :updated_at
            )
        """, session)
        return True
    except sqlite3.IntegrityError:
        # Duplicate - already exists
        return False


def main():
    """Main processing function."""
    print("=" * 80)
    print("Yearly and Monthly Session Calculation")
    print("=" * 80)
    print()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    # Get data range
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(time), MAX(time) FROM ohlc_4h WHERE symbol = 'ES'")
    min_time, max_time = cursor.fetchone()

    print(f"4H Data Range: {min_time} to {max_time}")
    print()

    # Parse dates
    min_date = datetime.fromisoformat(min_time)
    max_date = datetime.fromisoformat(max_time)

    start_year = min_date.year
    end_year = max_date.year

    symbols = ['ES', 'NQ']

    # ========================================================================
    # Calculate Yearly Sessions
    # ========================================================================
    print("YEARLY SESSIONS")
    print("-" * 80)

    yearly_count = 0
    yearly_skipped = 0

    for year in range(start_year, end_year + 1):
        for symbol in symbols:
            session = calculate_yearly_session(conn, year, symbol)

            if session:
                inserted = insert_session(conn, session)
                if inserted:
                    yearly_count += 1
                    print(f"[+] {year} Yearly {symbol}: TO={session['true_open']:.2f}, "
                          f"PoC={session['poc']:.2f}, RPP={session['rpp']:.2f}")
                else:
                    yearly_skipped += 1
                    print(f"[SKIP] {year} Yearly {symbol}: Already exists")
            else:
                yearly_skipped += 1

    print()
    print(f"Yearly Sessions: {yearly_count} inserted, {yearly_skipped} skipped")
    print()

    # ========================================================================
    # Calculate Monthly Sessions
    # ========================================================================
    print("MONTHLY SESSIONS")
    print("-" * 80)

    monthly_count = 0
    monthly_skipped = 0

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Skip months beyond our data range
            if year == end_year and month > max_date.month:
                break

            for symbol in symbols:
                session = calculate_monthly_session(conn, year, month, symbol)

                if session:
                    inserted = insert_session(conn, session)
                    if inserted:
                        monthly_count += 1
                        print(f"[+] {year}-{month:02d} Monthly {symbol}: "
                              f"TO={session['true_open']:.2f}, "
                              f"PoC={session['poc']:.2f}, RPP={session['rpp']:.2f}")
                    else:
                        monthly_skipped += 1
                        print(f"[SKIP] {year}-{month:02d} Monthly {symbol}: Already exists")
                else:
                    monthly_skipped += 1

    print()
    print(f"Monthly Sessions: {monthly_count} inserted, {monthly_skipped} skipped")
    print()

    # Commit changes
    conn.commit()

    # ========================================================================
    # Summary
    # ========================================================================
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    cursor.execute("""
        SELECT session_type, COUNT(*)
        FROM sessions
        GROUP BY session_type
        ORDER BY session_type
    """)

    for session_type, count in cursor.fetchall():
        print(f"{session_type:10s}: {count:4d} sessions")

    print()

    # Total sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    total = cursor.fetchone()[0]
    print(f"{'Total':10s}: {total:4d} sessions")
    print()

    conn.close()

    print("[DONE] Processing complete!")
    print()


if __name__ == '__main__':
    main()
