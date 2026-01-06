#!/usr/bin/env python3
"""
Calculate all session types for 1M database.

This script populates the sessions table with:
- Daily Major sessions (5 per day: Asia, London, NY_AM, NY_PM, Afternoon)
- Daily Minor sessions (16 per day: m1800, m1930, m2100, etc. at 90-min intervals)
- Weekly sessions (1 per week)
- Monthly sessions (1 per month)
- Yearly sessions (1 per year)

All session calculations follow the specs in docs/reference/session-tables.md

Supports incremental processing - only calculates new/affected sessions.

Usage:
    # Incremental mode (default)
    python calculate_daily_sessions.py

    # Full mode (recalculate all)
    python calculate_daily_sessions.py --full

    # Specific symbol
    python calculate_daily_sessions.py --symbol ES
"""

import sqlite3
import argparse
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
import pytz
from metadata_helpers_1m import (
    get_last_processed_time,
    update_processing_metadata,
    get_data_range
)

DB_PATH = 'data/ohlc_data.db'
ET = pytz.timezone('US/Eastern')

# Major session definitions (times in ET)
# Per docs/reference/session-tables.md
MAJOR_SESSIONS = {
    'Asia': {
        'start': time(18, 0),
        'end': time(23, 59),
        'to_time': time(19, 30),  # True Open: Open of 19:30 candle
        'begin_looking': 'previous_close'  # Start looking at closing price of previous day
    },
    'London': {
        'start': time(0, 0),
        'end': time(5, 59),
        'to_time': time(1, 30),  # True Open: Open of 01:30 candle
        'begin_looking': 'session_open'  # Start looking at opening of 00:00 candle
    },
    'NY_AM': {
        'start': time(6, 0),
        'end': time(11, 59),
        'to_time': time(7, 30),  # True Open: Open of 07:30 candle
        'begin_looking': 'session_open'  # Start looking at opening of 06:00 candle
    },
    'NY_PM': {
        'start': time(12, 0),
        'end': time(16, 59),
        'to_time': time(13, 30),  # True Open: Open of 13:30 candle
        'begin_looking': 'session_open'  # Start looking at opening of 12:00 candle
    },
    'Afternoon': {
        'start': time(13, 30),
        'end': time(16, 59),
        'to_time': time(15, 0),  # True Open: Open of 15:00 candle
        'begin_looking': 'session_open'  # Start looking at opening of 13:30 candle
    }
}

# Minor session definitions (90-minute intervals)
# Per docs/reference/session-tables.md
# Format: (name, start_time, to_offset_minutes, duration_minutes, begin_looking)
MINOR_SESSIONS = [
    ('m1800', time(18, 0), 22, 89, 'previous_close'),  # 18:00-19:29, TO at close of 18:22
    ('m1930', time(19, 30), 22, 89, 'session_open'),   # 19:30-20:59, TO at close of 19:52
    ('m2100', time(21, 0), 22, 89, 'session_open'),    # 21:00-22:29, TO at close of 21:22
    ('m2230', time(22, 30), 22, 89, 'session_open'),   # 22:30-23:59, TO at close of 22:52
    ('m0000', time(0, 0), 22, 89, 'session_open'),     # 00:00-01:29, TO at close of 00:22
    ('m0130', time(1, 30), 22, 89, 'session_open'),    # 01:30-02:59, TO at close of 01:52
    ('m0300', time(3, 0), 22, 89, 'session_open'),     # 03:00-04:29, TO at close of 03:22
    ('m0430', time(4, 30), 22, 89, 'session_open'),    # 04:30-05:59, TO at close of 04:52
    ('m0600', time(6, 0), 22, 89, 'session_open'),     # 06:00-07:29, TO at close of 06:22
    ('m0730', time(7, 30), 22, 89, 'session_open'),    # 07:30-08:59, TO at close of 07:52
    ('m0900', time(9, 0), 22, 89, 'session_open'),     # 09:00-10:29, TO at close of 09:22
    ('m1030', time(10, 30), 22, 89, 'session_open'),   # 10:30-11:59, TO at close of 10:52
    ('m1200', time(12, 0), 22, 89, 'session_open'),    # 12:00-13:29, TO at close of 12:22
    ('m1330', time(13, 30), 22, 89, 'session_open'),   # 13:30-14:59, TO at close of 13:52
    ('m1500', time(15, 0), 22, 89, 'session_open'),    # 15:00-16:29, TO at close of 15:22
    ('m1630', time(16, 30), 22, 29, 'session_open'),   # 16:30-16:59, TO at close of 16:52 (only 30 min)
]


def get_db_connection():
    """Create database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def calculate_poc_and_rpp(
    candles: List[Tuple],
    to_price: float
) -> Tuple[float, float]:
    """
    Calculate PoC and RPP from candles and TO price.

    PoC = highest high or lowest low with greatest variance from TO
    RPP = 2 * TO - PoC (mirror projection)
    """
    if not candles:
        return None, None

    highest = max(candle[2] for candle in candles)  # high
    lowest = min(candle[3] for candle in candles)   # low

    high_variance = abs(highest - to_price)
    low_variance = abs(lowest - to_price)

    poc = highest if high_variance > low_variance else lowest
    rpp = 2 * to_price - poc

    return poc, rpp


def has_complete_data(
    conn: sqlite3.Connection,
    symbol: str,
    start_time: datetime,
    end_time: datetime,
    min_coverage_pct: float = 0.95
) -> bool:
    """
    Check if we have complete data coverage for a time period.

    Args:
        conn: Database connection
        symbol: Symbol to check
        start_time: Period start
        end_time: Period end
        min_coverage_pct: Minimum percentage of expected candles (default 95%)

    Returns:
        True if we have sufficient data coverage, False otherwise
    """
    cursor = conn.cursor()

    # Get first available data point
    cursor.execute("""
        SELECT MIN(time) FROM ohlc_1m WHERE symbol = ?
    """, (symbol,))

    first_data = cursor.fetchone()[0]
    if not first_data:
        return False

    first_data_dt = datetime.fromisoformat(first_data)

    # If our data starts after the required start time, we don't have complete coverage
    if first_data_dt > start_time:
        return False

    # Count actual candles in the period
    cursor.execute("""
        SELECT COUNT(*) FROM ohlc_1m
        WHERE symbol = ?
        AND time >= ?
        AND time < ?
    """, (symbol, start_time.isoformat(), end_time.isoformat()))

    actual_count = cursor.fetchone()[0]

    # Calculate expected candles (1 per minute)
    total_minutes = int((end_time - start_time).total_seconds() / 60)

    # For 1M data, we expect most minutes to have data (allow for some gaps due to holidays/weekends)
    # But we need at least min_coverage_pct of expected candles
    if actual_count < (total_minutes * min_coverage_pct):
        return False

    return True


def get_candles(
    conn: sqlite3.Connection,
    symbol: str,
    start_time: datetime,
    end_time: datetime
) -> List[Tuple]:
    """Fetch candles between start and end time."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT time, open, high, low, close
        FROM ohlc_1m
        WHERE symbol = ?
        AND time >= ?
        AND time < ?
        ORDER BY time
    """, (symbol, start_time.isoformat(), end_time.isoformat()))

    return cursor.fetchall()


def get_candle_at_time(
    conn: sqlite3.Connection,
    symbol: str,
    target_time: datetime
) -> Optional[Tuple]:
    """Get candle at specific time."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT time, open, high, low, close
        FROM ohlc_1m
        WHERE symbol = ?
        AND time = ?
    """, (symbol, target_time.isoformat()))

    return cursor.fetchone()


def calculate_major_session(
    conn: sqlite3.Connection,
    symbol: str,
    session_name: str,
    trading_day: datetime
) -> Optional[Dict]:
    """
    Calculate a Major session (Asia, London, NY_AM, NY_PM, Afternoon).

    Per docs/reference/session-tables.md:
    - Begin Looking: Either previous close or session open (depends on session)
    - True Open: Specific time per session (open price of that candle)
    - PoC Window: From begin_looking through TO time (exclusive)

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        session_name: 'Asia', 'London', etc.
        trading_day: The trading day (date)

    Returns:
        Session dictionary or None
    """
    session_def = MAJOR_SESSIONS[session_name]

    # Session start and end times (for reference/range)
    session_start = ET.localize(datetime.combine(trading_day, session_def['start']))
    session_end = ET.localize(datetime.combine(trading_day, session_def['end']))

    # Handle overnight sessions (Asia crosses midnight)
    if session_def['end'] < session_def['start']:
        session_end += timedelta(days=1)

    # True Open time (specific per session)
    to_time = ET.localize(datetime.combine(trading_day, session_def['to_time']))
    if session_def['to_time'] < session_def['start']:
        to_time += timedelta(days=1)

    # Get TO candle
    to_candle = get_candle_at_time(conn, symbol, to_time)
    if not to_candle:
        return None  # No data at TO time

    to_price = to_candle[1]  # open price

    # Determine PoC window start (begin_looking)
    if session_def['begin_looking'] == 'previous_close':
        # Start from closing price of previous trading day (same calendar day 16:59 candle)
        # Trading day ends at 16:59, so previous close is same calendar day as session start
        begin_looking_time = ET.localize(datetime.combine(trading_day, time(16, 59)))
        # Get the close price of the previous trading day's last candle
        prev_close_candle = get_candle_at_time(conn, symbol, begin_looking_time)
        if not prev_close_candle:
            return None
    else:  # 'session_open'
        # Start from session open
        begin_looking_time = session_start

    # Get PoC window candles (from begin_looking through TO time, exclusive)
    poc_candles = get_candles(conn, symbol, begin_looking_time, to_time)
    if not poc_candles:
        return None

    # Calculate PoC and RPP
    poc, rpp = calculate_poc_and_rpp(poc_candles, to_price)

    now = datetime.now(ET).isoformat()

    # Determine trading day for session name
    # Sessions starting at 18:00 or later belong to the next trading day
    if session_def['start'].hour >= 18:
        name_trading_day = trading_day + timedelta(days=1)
    else:
        name_trading_day = trading_day

    return {
        'symbol': symbol,
        'session_type': 'Major',
        'session_name': f'{session_name} {name_trading_day.strftime("%Y-%m-%d")}',
        'session_start_time': session_start.isoformat(),
        'to_time': to_time.isoformat(),
        'true_open': to_price,
        'poc': poc,
        'rpp': rpp,
        'status': 'unbroken',
        'expires_at': None,  # Major sessions don't expire
        'created_at': now,
        'updated_at': now
    }


def calculate_minor_session(
    conn: sqlite3.Connection,
    symbol: str,
    session_name: str,
    session_start_time: time,
    to_offset_minutes: int,
    duration_minutes: int,
    begin_looking: str,
    trading_day: datetime
) -> Optional[Dict]:
    """
    Calculate a Minor session (m1800, m1930, etc.).

    Per docs/reference/session-tables.md:
    - Begin Looking: Either previous close or session open
    - True Open: Close of (session_start + to_offset_minutes) candle
    - PoC Window: From begin_looking through TO time (exclusive)
    - Expiry: TO time + 24 hours

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        session_name: 'm1800', 'm1930', etc.
        session_start_time: Session start time
        to_offset_minutes: Minutes from start to TO candle (22 for most sessions)
        duration_minutes: Session duration (89 for most, 29 for m1630)
        begin_looking: 'previous_close' or 'session_open'
        trading_day: The trading day (date)

    Returns:
        Session dictionary or None
    """
    # Session start
    session_start = ET.localize(datetime.combine(trading_day, session_start_time))

    # Session end (for reference)
    session_end = session_start + timedelta(minutes=duration_minutes)

    # True Open time: Close of (session_start + to_offset_minutes) candle
    to_candle_time = session_start + timedelta(minutes=to_offset_minutes)

    # Get TO candle
    to_candle = get_candle_at_time(conn, symbol, to_candle_time)
    if not to_candle:
        return None

    to_price = to_candle[4]  # close price of the TO candle

    # Expires 24 hours after TO candle time
    expires_at = to_candle_time + timedelta(hours=24)

    # Determine PoC window start (begin_looking)
    if begin_looking == 'previous_close':
        # Start from closing price of previous trading day (same calendar day 16:59 candle)
        # Trading day ends at 16:59, so previous close is same calendar day as session start
        begin_looking_time = ET.localize(datetime.combine(trading_day, time(16, 59)))
        # Verify we have the previous close candle
        prev_close_candle = get_candle_at_time(conn, symbol, begin_looking_time)
        if not prev_close_candle:
            return None
    else:  # 'session_open'
        # Start from session open
        begin_looking_time = session_start

    # Get PoC window candles (from begin_looking through TO candle time, inclusive of TO)
    poc_end_time = to_candle_time + timedelta(minutes=1)  # Include the TO candle
    poc_candles = get_candles(conn, symbol, begin_looking_time, poc_end_time)
    if not poc_candles:
        return None

    # Calculate PoC and RPP
    poc, rpp = calculate_poc_and_rpp(poc_candles, to_price)

    now = datetime.now(ET).isoformat()

    # Determine trading day for session name
    # Sessions starting at 18:00 or later belong to the next trading day
    if session_start_time.hour >= 18:
        name_trading_day = trading_day + timedelta(days=1)
    else:
        name_trading_day = trading_day

    return {
        'symbol': symbol,
        'session_type': 'Minor',
        'session_name': f'{session_name} {name_trading_day.strftime("%Y-%m-%d")}',
        'session_start_time': session_start.isoformat(),
        'to_time': to_candle_time.isoformat(),
        'true_open': to_price,
        'poc': poc,
        'rpp': rpp,
        'status': 'unbroken',
        'expires_at': expires_at.isoformat(),
        'created_at': now,
        'updated_at': now
    }


def calculate_weekly_session(
    conn: sqlite3.Connection,
    symbol: str,
    week_start: datetime
) -> Optional[Dict]:
    """
    Calculate a Weekly session.

    Per docs/user-guide/02-sessions.md:
    - PoC Tracking Begins: Sunday 18:00 (first candle of Monday trading day)
    - True Open (TO): Monday 18:00 (first candle of Tuesday trading day)
    - PoC Window: Sunday 18:00 → Monday 17:59 (24 hours, exclusive of TO)
    """
    # Find Sunday of this week (day before Monday)
    # If week_start is a date, we need to find the Sunday that starts this week
    if isinstance(week_start, datetime):
        week_date = week_start.date()
    else:
        week_date = week_start

    # Get to the Sunday that starts this week
    # 0=Monday, 6=Sunday
    days_since_sunday = (week_date.weekday() + 1) % 7
    sunday = week_date - timedelta(days=days_since_sunday)

    # PoC window start: Sunday 18:00
    poc_start = ET.localize(datetime.combine(sunday, time(18, 0)))

    # TO time: Monday 18:00 (24 hours after Sunday 18:00)
    to_time = poc_start + timedelta(days=1)

    # PoC window end: Monday 17:59 (right before TO)
    poc_end = to_time - timedelta(minutes=1)

    # Get TO candle
    to_candle = get_candle_at_time(conn, symbol, to_time)
    if not to_candle:
        return None

    to_price = to_candle[1]  # open

    # Get PoC window candles (Sunday 18:00 to Monday 17:59)
    poc_candles = get_candles(conn, symbol, poc_start, to_time)
    if not poc_candles:
        return None

    # Calculate PoC and RPP
    poc, rpp = calculate_poc_and_rpp(poc_candles, to_price)

    now = datetime.now(ET).isoformat()

    # Week name format: "Week of YYYY-MM-DD" (using Sunday date)
    week_name = f'Week of {sunday.strftime("%Y-%m-%d")}'

    return {
        'symbol': symbol,
        'session_type': 'Weekly',
        'session_name': week_name,
        'session_start_time': poc_start.isoformat(),
        'to_time': to_time.isoformat(),
        'true_open': to_price,
        'poc': poc,
        'rpp': rpp,
        'status': 'unbroken',
        'expires_at': None,  # Weekly sessions don't expire
        'created_at': now,
        'updated_at': now
    }


def get_first_full_trading_day_of_month(year: int, month: int) -> datetime:
    """
    Determine the first full trading day of the month.

    Per docs/reference/session-tables.md:
    The key rule: We need Monday's trading session (Sunday 18:00) to be included.

    - If 1st = Monday: First trading day is Sunday (the day before) at 18:00
    - If 1st = Tuesday: First trading day is Monday (the day before) at 18:00
    - If 1st = Wednesday: First trading day is Tuesday (the day before) at 18:00
    - If 1st = Thursday: First trading day is Wednesday (the day before) at 18:00
    - If 1st = Friday: First trading day is Thursday (the day before) at 18:00
    - If 1st = Saturday: First trading day is Sunday (the next day) at 18:00
    - If 1st = Sunday: First trading day is Sunday (same day) at 18:00

    Returns:
        Datetime of the first full trading day start (at 18:00 ET)
    """
    first_of_month = datetime(year, month, 1)
    day_of_week = first_of_month.weekday()  # 0=Monday, 6=Sunday

    if day_of_week == 0:  # Monday
        # First trading day is Sunday before at 18:00
        trading_day = first_of_month - timedelta(days=1)
    elif day_of_week == 1:  # Tuesday
        # First trading day is Monday before at 18:00
        trading_day = first_of_month - timedelta(days=1)
    elif day_of_week == 2:  # Wednesday
        # First trading day is Tuesday before at 18:00
        trading_day = first_of_month - timedelta(days=1)
    elif day_of_week == 3:  # Thursday
        # First trading day is Wednesday before at 18:00
        trading_day = first_of_month - timedelta(days=1)
    elif day_of_week == 4:  # Friday
        # First trading day is Thursday before at 18:00
        trading_day = first_of_month - timedelta(days=1)
    elif day_of_week == 5:  # Saturday
        # First trading day is Sunday after at 18:00
        trading_day = first_of_month + timedelta(days=1)
    else:  # Sunday
        # First trading day is Sunday same day at 18:00
        trading_day = first_of_month

    return ET.localize(datetime.combine(trading_day.date(), time(18, 0)))


def get_second_full_week_sunday(year: int, month: int) -> datetime:
    """
    Determine the Sunday 18:00 that begins the second full week of the month.

    Per docs/reference/session-tables.md:
    - If the 1st falls on Saturday, Sunday, or Monday → that week is the first full week
    - If the 1st falls on Tuesday, Wednesday, Thursday, or Friday → that is NOT a full week;
      the following week is the first full week
    - The TO is set at the Sunday 18:00 candle that begins the week AFTER the first full week

    Returns:
        Datetime of second full week Sunday at 18:00 ET
    """
    first_of_month = datetime(year, month, 1)
    day_of_week = first_of_month.weekday()  # 0=Monday, 6=Sunday

    # Determine the Monday that starts the first full week
    if day_of_week == 0:  # 1st is Monday
        # This Monday (the 1st) starts the first full week
        first_full_week_monday = first_of_month
    elif day_of_week == 6:  # 1st is Sunday
        # Next day (Monday the 2nd) starts the first full week
        first_full_week_monday = first_of_month + timedelta(days=1)
    elif day_of_week == 5:  # 1st is Saturday
        # Day after tomorrow (Monday the 3rd) starts the first full week
        first_full_week_monday = first_of_month + timedelta(days=2)
    else:  # 1st is Tuesday (1), Wednesday (2), Thursday (3), or Friday (4)
        # The week containing the 1st is NOT a full week
        # Find the next Monday after the 1st - that's the start of the first full week
        days_until_monday = 7 - day_of_week  # Days from Tue/Wed/Thu/Fri to next Monday
        first_full_week_monday = first_of_month + timedelta(days=days_until_monday)

    # Second full week is the week after the first full week
    second_full_week_monday = first_full_week_monday + timedelta(weeks=1)

    # The Sunday before this Monday at 18:00 is the TO
    second_full_week_sunday = second_full_week_monday - timedelta(days=1)

    return ET.localize(datetime.combine(second_full_week_sunday.date(), time(18, 0)))


def calculate_monthly_session(
    conn: sqlite3.Connection,
    symbol: str,
    year: int,
    month: int
) -> Optional[Dict]:
    """
    Calculate a Monthly session.

    Per docs/reference/session-tables.md:
    - PoC Tracking Begins: First full trading day at 18:00
    - True Open Time: Second full week Sunday 18:00 (open price)
    - PoC Window: From first full trading day through TO time (exclusive)

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        year: Year
        month: Month (1-12)

    Returns:
        Session dictionary or None if data is insufficient
    """
    # Determine first full trading day and second full week Sunday
    poc_start = get_first_full_trading_day_of_month(year, month)
    to_time = get_second_full_week_sunday(year, month)

    # Check if we have complete data coverage for the PoC window
    if not has_complete_data(conn, symbol, poc_start, to_time, min_coverage_pct=0.80):
        return None  # Insufficient data

    # Get TO candle
    to_candle = get_candle_at_time(conn, symbol, to_time)
    if not to_candle:
        return None

    to_price = to_candle[1]  # open price

    # Get PoC window candles (from first full trading day through TO time, exclusive)
    poc_candles = get_candles(conn, symbol, poc_start, to_time)
    if not poc_candles:
        return None

    # Calculate PoC and RPP
    poc, rpp = calculate_poc_and_rpp(poc_candles, to_price)

    now = datetime.now(ET).isoformat()

    # Month name format: "YYYY-MM"
    month_name = f'{year}-{month:02d}'

    return {
        'symbol': symbol,
        'session_type': 'Monthly',
        'session_name': month_name,
        'session_start_time': poc_start.isoformat(),
        'to_time': to_time.isoformat(),
        'true_open': to_price,
        'poc': poc,
        'rpp': rpp,
        'status': 'unbroken',
        'expires_at': None,  # Monthly sessions don't expire
        'created_at': now,
        'updated_at': now
    }


def get_first_full_trading_day_of_year(year: int) -> datetime:
    """
    Determine the first full trading day of the year (January).

    Per docs/reference/session-tables.md:
    Same rules as monthly - we need Monday's trading session (Sunday 18:00) to be included.

    Returns:
        Datetime of the first full trading day start (at 18:00 ET)
    """
    return get_first_full_trading_day_of_month(year, 1)


def get_first_sunday_of_april(year: int) -> datetime:
    """
    Determine the first Sunday 18:00 of April.

    This is the True Open for the yearly session.
    The Sunday 18:00 begins the first Monday trading day of April.

    Returns:
        Datetime of first Sunday of April at 18:00 ET
    """
    april_first = datetime(year, 4, 1)
    day_of_week = april_first.weekday()  # 0=Monday, 6=Sunday

    # Find the first Sunday of April
    if day_of_week == 6:  # April 1st is Sunday
        first_sunday = april_first
    else:  # Find the next Sunday
        days_until_sunday = (6 - day_of_week) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        first_sunday = april_first + timedelta(days=days_until_sunday)

    return ET.localize(datetime.combine(first_sunday.date(), time(18, 0)))


def calculate_yearly_session(
    conn: sqlite3.Connection,
    symbol: str,
    year: int
) -> Optional[Dict]:
    """
    Calculate a Yearly session.

    Per docs/reference/session-tables.md:
    - PoC Tracking Begins: First full trading day of January at 18:00
    - True Open Time: First Sunday 18:00 of April (open price)
    - Range Window: First trading day of year through end of March (Q1)
    - The Sunday 18:00 that starts the first Monday of April is the TO

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        year: Year

    Returns:
        Session dictionary or None if data is insufficient
    """
    # Determine PoC start and TO time
    poc_start = get_first_full_trading_day_of_year(year)
    to_time = get_first_sunday_of_april(year)

    # Check if we have complete data coverage for the PoC window (Q1)
    if not has_complete_data(conn, symbol, poc_start, to_time, min_coverage_pct=0.80):
        return None  # Insufficient data

    # Get TO candle
    to_candle = get_candle_at_time(conn, symbol, to_time)
    if not to_candle:
        return None

    to_price = to_candle[1]  # open price

    # Get PoC window candles (Q1: from first trading day through TO time, exclusive)
    poc_candles = get_candles(conn, symbol, poc_start, to_time)
    if not poc_candles:
        return None

    # Calculate PoC and RPP
    poc, rpp = calculate_poc_and_rpp(poc_candles, to_price)

    now = datetime.now(ET).isoformat()

    return {
        'symbol': symbol,
        'session_type': 'Yearly',
        'session_name': str(year),
        'session_start_time': poc_start.isoformat(),
        'to_time': to_time.isoformat(),
        'true_open': to_price,
        'poc': poc,
        'rpp': rpp,
        'status': 'unbroken',
        'expires_at': None,  # Yearly sessions don't expire
        'created_at': now,
        'updated_at': now
    }


def insert_session(conn: sqlite3.Connection, session: Dict) -> bool:
    """Insert session, return True if inserted, False if duplicate."""
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
        return False  # Duplicate


def process_trading_day(
    conn: sqlite3.Connection,
    symbol: str,
    trading_day: datetime
) -> Dict:
    """
    Process all daily sessions for a single trading day.

    Returns statistics.
    """
    stats = {
        'major_created': 0,
        'minor_created': 0,
        'major_skipped': 0,
        'minor_skipped': 0
    }

    # Calculate Major sessions
    for session_name in MAJOR_SESSIONS.keys():
        session = calculate_major_session(conn, symbol, session_name, trading_day)
        if session:
            if insert_session(conn, session):
                stats['major_created'] += 1
            else:
                stats['major_skipped'] += 1

    # Calculate Minor sessions
    for session_name, session_start_time, to_offset, duration, begin_looking in MINOR_SESSIONS:
        session = calculate_minor_session(
            conn, symbol, session_name, session_start_time,
            to_offset, duration, begin_looking, trading_day
        )
        if session:
            if insert_session(conn, session):
                stats['minor_created'] += 1
            else:
                stats['minor_skipped'] += 1

    return stats


def process_full(conn: sqlite3.Connection, symbols: List[str]) -> Dict:
    """
    Full mode: Calculate all sessions from scratch.
    """
    print("\nMODE: Full Processing")
    print()

    cursor = conn.cursor()
    total_stats = {
        'major_created': 0,
        'minor_created': 0,
        'weekly_created': 0,
        'monthly_created': 0,
        'yearly_created': 0,
        'major_skipped': 0,
        'minor_skipped': 0,
        'weekly_skipped': 0,
        'monthly_skipped': 0,
        'yearly_skipped': 0
    }

    for symbol in symbols:
        print(f"\n{symbol}:")
        print("-" * 80)

        # Get data range
        data_range = get_data_range(symbol, cursor)
        if not data_range['min_time']:
            print(f"  No data for {symbol}, skipping")
            continue

        min_date = datetime.fromisoformat(data_range['min_time']).date()
        max_date = datetime.fromisoformat(data_range['max_time']).date()

        print(f"  Data range: {min_date} to {max_date}")
        print(f"  Processing daily sessions...")

        # Process each trading day
        current_date = min_date
        days_processed = 0

        while current_date <= max_date:
            day_stats = process_trading_day(conn, symbol, current_date)

            for key in ['major_created', 'minor_created', 'major_skipped', 'minor_skipped']:
                total_stats[key] += day_stats[key]

            days_processed += 1
            current_date += timedelta(days=1)

        print(f"  Days processed: {days_processed}")
        print(f"  Major sessions: {total_stats['major_created']} created")
        print(f"  Minor sessions: {total_stats['minor_created']} created")

        # Process weekly sessions
        print(f"\n  Processing weekly sessions...")
        current_week = min_date
        while current_week <= max_date:
            session = calculate_weekly_session(conn, symbol, current_week)
            if session:
                if insert_session(conn, session):
                    total_stats['weekly_created'] += 1
                else:
                    total_stats['weekly_skipped'] += 1

            current_week += timedelta(weeks=1)

        print(f"  Weekly sessions: {total_stats['weekly_created']} created")

        # Process monthly sessions
        print(f"\n  Processing monthly sessions...")
        year_month_set = set()
        current_date = min_date

        while current_date <= max_date:
            year_month = (current_date.year, current_date.month)
            if year_month not in year_month_set:
                year_month_set.add(year_month)
                session = calculate_monthly_session(conn, symbol, year_month[0], year_month[1])
                if session:
                    if insert_session(conn, session):
                        total_stats['monthly_created'] += 1
                    else:
                        total_stats['monthly_skipped'] += 1

            current_date += timedelta(days=1)

        print(f"  Monthly sessions: {total_stats['monthly_created']} created")

        # Process yearly sessions
        print(f"\n  Processing yearly sessions...")
        year_set = set()
        current_date = min_date

        while current_date <= max_date:
            year = current_date.year
            if year not in year_set:
                year_set.add(year)
                session = calculate_yearly_session(conn, symbol, year)
                if session:
                    if insert_session(conn, session):
                        total_stats['yearly_created'] += 1
                    else:
                        total_stats['yearly_skipped'] += 1

            current_date += timedelta(days=1)

        print(f"  Yearly sessions: {total_stats['yearly_created']} created")

    return total_stats


def main():
    parser = argparse.ArgumentParser(
        description='Calculate all session types (Major, Minor, Weekly, Monthly, Yearly)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--full', action='store_true',
                        help='Full mode: Calculate all sessions')
    parser.add_argument('--incremental', action='store_true',
                        help='Incremental mode: Only new/affected sessions')
    parser.add_argument('--symbol', type=str, choices=['ES', 'NQ'],
                        help='Process only this symbol')

    args = parser.parse_args()

    # Default to full for now (incremental mode will be added later)
    if not args.full and not args.incremental:
        args.full = True

    symbols = [args.symbol] if args.symbol else ['ES', 'NQ']

    print("="*80)
    print("Session Calculation (Major, Minor, Weekly, Monthly, Yearly)")
    print("="*80)

    conn = get_db_connection()

    try:
        stats = process_full(conn, symbols)

        conn.commit()

        print("\n" + "="*80)
        print("Summary")
        print("="*80)
        print(f"Major sessions: {stats['major_created']} created, {stats['major_skipped']} skipped")
        print(f"Minor sessions: {stats['minor_created']} created, {stats['minor_skipped']} skipped")
        print(f"Weekly sessions: {stats['weekly_created']} created, {stats['weekly_skipped']} skipped")
        print(f"Monthly sessions: {stats['monthly_created']} created, {stats['monthly_skipped']} skipped")
        print(f"Yearly sessions: {stats['yearly_created']} created, {stats['yearly_skipped']} skipped")
        print()

        # Update metadata
        cursor = conn.cursor()
        for symbol in symbols:
            data_range = get_data_range(symbol, cursor)
            update_processing_metadata(
                symbol=symbol,
                process_type='session_calc',
                last_time=data_range['max_time'],
                records_count=stats['major_created'] + stats['minor_created'] +
                             stats['weekly_created'] + stats['monthly_created'] +
                             stats['yearly_created'],
                status='success',
                cursor=cursor,
                commit=True
            )

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()


if __name__ == '__main__':
    main()
