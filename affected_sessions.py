#!/usr/bin/env python3
"""
Affected Session Detection Module

Identifies which sessions are affected by new OHLC data and need recalculation.
This enables incremental processing instead of recalculating all sessions.

Key Functions:
- find_affected_sessions(): Main entry point to find all affected sessions
- detect_new_session_periods(): Check if new sessions can be created
- mark_sessions_for_recalc(): Mark sessions that need recalculation
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pytz

DB_PATH = 'data/yearly_monthly.db'
ET = pytz.timezone('US/Eastern')


def find_affected_sessions(
    conn: sqlite3.Connection,
    symbol: str,
    new_data_start_time: str,
    new_data_end_time: str
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Find all sessions affected by new data range.

    Args:
        conn: Database connection
        symbol: Symbol name (e.g., 'ES', 'NQ')
        new_data_start_time: Start of new data (ISO format)
        new_data_end_time: End of new data (ISO format)

    Returns:
        Tuple of:
        - sessions_to_recalc: Sessions needing PoC/TO/RPP recalculation
        - sessions_to_scan: Sessions needing POI rescanning (future phase)
        - new_sessions_possible: New session periods that can be created
    """
    cursor = conn.cursor()

    # ========================================================================
    # 1. Sessions with PoC windows overlapping new data
    # ========================================================================
    # These sessions might have their PoC/TO/RPP values change
    # We need to check:
    # - Yearly sessions: If new data falls in Q1 (January-March) of that year
    # - Monthly sessions: If new data falls in first week of that month
    # - Sessions without TO yet (incomplete sessions)

    sessions_to_recalc = []

    # Find sessions where:
    # - Session start time <= new_data_end AND
    # - TO time >= new_data_start (their window overlaps)
    # OR
    # - true_open IS NULL (incomplete session, still being calculated)
    cursor.execute("""
        SELECT id, symbol, session_type, session_name, session_start_time, to_time,
               true_open, poc, rpp, status
        FROM sessions
        WHERE symbol = ?
        AND (
            -- PoC window overlaps new data
            (session_start_time <= ? AND to_time >= ?)

            -- OR session doesn't have TO yet (incomplete)
            OR (true_open IS NULL)
        )
        ORDER BY session_start_time
    """, (symbol, new_data_end_time, new_data_start_time))

    for row in cursor.fetchall():
        sessions_to_recalc.append({
            'id': row[0],
            'symbol': row[1],
            'session_type': row[2],
            'session_name': row[3],
            'session_start_time': row[4],
            'to_time': row[5],
            'true_open': row[6],
            'poc': row[7],
            'rpp': row[8],
            'status': row[9]
        })

    # ========================================================================
    # 2. Active sessions that might see new POI touches (for Phase 3)
    # ========================================================================
    # These sessions don't need PoC/TO/RPP recalc, but need POI event rescanning
    # Status 'unbroken', 'break', or 'return' means they're actively tracking
    # We'll implement this in Phase 3 (POI processing)

    sessions_to_scan = []

    cursor.execute("""
        SELECT id, symbol, session_type, session_name, to_time, poc, rpp, status
        FROM sessions
        WHERE symbol = ?
        AND status IN ('unbroken', 'break', 'return')
        AND to_time < ?
        ORDER BY to_time
    """, (symbol, new_data_end_time))

    for row in cursor.fetchall():
        sessions_to_scan.append({
            'id': row[0],
            'symbol': row[1],
            'session_type': row[2],
            'session_name': row[3],
            'to_time': row[4],
            'poc': row[5],
            'rpp': row[6],
            'status': row[7]
        })

    # ========================================================================
    # 3. Check if new sessions can be created
    # ========================================================================
    new_sessions_possible = detect_new_session_periods(
        conn, symbol, new_data_start_time, new_data_end_time
    )

    return sessions_to_recalc, sessions_to_scan, new_sessions_possible


def detect_new_session_periods(
    conn: sqlite3.Connection,
    symbol: str,
    new_data_start_time: str,
    new_data_end_time: str
) -> List[Dict]:
    """
    Detect new session periods that can now be created with new data.

    For example:
    - If new data brings us into a new year, we can create that year's Yearly session
    - If new data brings us into a new month, we can create that month's Monthly session

    Args:
        conn: Database connection
        symbol: Symbol name
        new_data_start_time: Start of new data (ISO format)
        new_data_end_time: End of new data (ISO format)

    Returns:
        List of dictionaries describing new session periods
    """
    cursor = conn.cursor()
    new_periods = []

    # Parse dates
    new_start = datetime.fromisoformat(new_data_start_time)
    new_end = datetime.fromisoformat(new_data_end_time)

    # ========================================================================
    # Check for new YEARLY sessions
    # ========================================================================
    # A Yearly session can be created if we have data through at least April
    # (since TO is first Monday of April)

    # Get existing Yearly sessions for this symbol
    cursor.execute("""
        SELECT session_name FROM sessions
        WHERE symbol = ? AND session_type = 'Yearly'
    """, (symbol,))

    existing_years = set()
    for row in cursor.fetchall():
        # Session name is like "Year 2019"
        year_str = row[0].replace('Year ', '')
        existing_years.add(int(year_str))

    # Check if new data allows creating new Yearly sessions
    # We need data through at least April to calculate a Yearly session
    if new_end.month >= 4:  # Have data into April or later
        year = new_end.year
        if year not in existing_years:
            # Check if we have enough data for this year
            # Need data from January 1st through at least first week of April
            cursor.execute("""
                SELECT COUNT(*) FROM ohlc_4h
                WHERE symbol = ?
                AND time >= ?
                AND time <= ?
            """, (symbol, f"{year}-01-01T00:00:00-05:00", f"{year}-04-07T23:59:59-04:00"))

            count = cursor.fetchone()[0]
            if count > 0:
                new_periods.append({
                    'type': 'Yearly',
                    'year': year,
                    'symbol': symbol
                })

    # ========================================================================
    # Check for new MONTHLY sessions
    # ========================================================================
    # A Monthly session can be created if we have data through at least
    # the second full week of the month (for TO calculation)

    # Get existing Monthly sessions for this symbol
    cursor.execute("""
        SELECT session_name FROM sessions
        WHERE symbol = ? AND session_type = 'Monthly'
    """, (symbol,))

    existing_months = set()
    for row in cursor.fetchall():
        # Session name is like "January 2019"
        session_name = row[0]
        # Parse month and year
        parts = session_name.split()
        if len(parts) == 2:
            month_name, year_str = parts
            month_num = datetime.strptime(month_name, '%B').month
            year = int(year_str)
            existing_months.add((year, month_num))

    # Check each month in the new data range
    current_month = new_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_month = new_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    while current_month <= end_month:
        year = current_month.year
        month = current_month.month

        if (year, month) not in existing_months:
            # Check if we have enough data for this month
            # Need at least 2 weeks of data
            month_start = f"{year}-{month:02d}-01T00:00:00-05:00"
            if month == 12:
                next_month_start = f"{year + 1}-01-01T00:00:00-05:00"
            else:
                next_month_start = f"{year}-{month + 1:02d}-01T00:00:00-05:00"

            cursor.execute("""
                SELECT COUNT(*) FROM ohlc_4h
                WHERE symbol = ?
                AND time >= ?
                AND time < ?
            """, (symbol, month_start, next_month_start))

            count = cursor.fetchone()[0]
            # Roughly 2 weeks of 4H data = 2 * 7 * 6 = 84 candles
            # Use 50 as a conservative threshold
            if count >= 50:
                new_periods.append({
                    'type': 'Monthly',
                    'year': year,
                    'month': month,
                    'symbol': symbol
                })

        # Move to next month
        if current_month.month == 12:
            current_month = current_month.replace(year=current_month.year + 1, month=1)
        else:
            current_month = current_month.replace(month=current_month.month + 1)

    return new_periods


def mark_sessions_for_recalc(
    conn: sqlite3.Connection,
    session_ids: List[int]
) -> int:
    """
    Mark sessions as needing recalculation.

    Sets needs_recalc = 1 for specified sessions.

    Args:
        conn: Database connection
        session_ids: List of session IDs to mark

    Returns:
        Number of sessions marked
    """
    if not session_ids:
        return 0

    cursor = conn.cursor()
    now = datetime.now(ET).isoformat()

    placeholders = ','.join('?' * len(session_ids))
    cursor.execute(f"""
        UPDATE sessions
        SET needs_recalc = 1,
            updated_at = ?
        WHERE id IN ({placeholders})
    """, [now] + session_ids)

    return cursor.rowcount


def clear_recalc_flag(
    conn: sqlite3.Connection,
    session_id: int
) -> None:
    """
    Clear the needs_recalc flag and update last_recalc_time for a session.

    Args:
        conn: Database connection
        session_id: Session ID to clear
    """
    cursor = conn.cursor()
    now = datetime.now(ET).isoformat()

    cursor.execute("""
        UPDATE sessions
        SET needs_recalc = 0,
            last_recalc_time = ?,
            updated_at = ?
        WHERE id = ?
    """, (now, now, session_id))


def get_sessions_needing_recalc(
    conn: sqlite3.Connection,
    symbol: str = None
) -> List[Dict]:
    """
    Get all sessions that have needs_recalc = 1.

    Args:
        conn: Database connection
        symbol: Optional symbol filter

    Returns:
        List of session dictionaries
    """
    cursor = conn.cursor()

    if symbol:
        query = """
            SELECT id, symbol, session_type, session_name, session_start_time, to_time,
                   true_open, poc, rpp, status
            FROM sessions
            WHERE needs_recalc = 1
            AND symbol = ?
            ORDER BY session_start_time
        """
        cursor.execute(query, (symbol,))
    else:
        query = """
            SELECT id, symbol, session_type, session_name, session_start_time, to_time,
                   true_open, poc, rpp, status
            FROM sessions
            WHERE needs_recalc = 1
            ORDER BY session_start_time
        """
        cursor.execute(query)

    sessions = []
    for row in cursor.fetchall():
        sessions.append({
            'id': row[0],
            'symbol': row[1],
            'session_type': row[2],
            'session_name': row[3],
            'session_start_time': row[4],
            'to_time': row[5],
            'true_open': row[6],
            'poc': row[7],
            'rpp': row[8],
            'status': row[9]
        })

    return sessions


if __name__ == '__main__':
    # Test the affected sessions detection
    import sys

    print("Testing Affected Sessions Detection")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)

    # Simulate new data from last week
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(time) FROM ohlc_4h WHERE symbol = 'ES'")
    max_time = cursor.fetchone()[0]

    if max_time:
        print(f"Latest data time: {max_time}")
        print()

        # Simulate new data range (last 7 days)
        new_end = datetime.fromisoformat(max_time)
        new_start = new_end - timedelta(days=7)

        print(f"Simulating new data range:")
        print(f"  Start: {new_start.isoformat()}")
        print(f"  End:   {new_end.isoformat()}")
        print()

        # Find affected sessions
        sessions_to_recalc, sessions_to_scan, new_periods = find_affected_sessions(
            conn, 'ES', new_start.isoformat(), new_end.isoformat()
        )

        print(f"Sessions needing recalculation: {len(sessions_to_recalc)}")
        for session in sessions_to_recalc[:5]:  # Show first 5
            print(f"  - {session['session_name']} ({session['session_type']})")
        if len(sessions_to_recalc) > 5:
            print(f"  ... and {len(sessions_to_recalc) - 5} more")

        print()
        print(f"Sessions needing POI scan: {len(sessions_to_scan)}")
        for session in sessions_to_scan[:5]:
            print(f"  - {session['session_name']} ({session['session_type']}, status={session['status']})")
        if len(sessions_to_scan) > 5:
            print(f"  ... and {len(sessions_to_scan) - 5} more")

        print()
        print(f"New sessions possible: {len(new_periods)}")
        for period in new_periods:
            if period['type'] == 'Yearly':
                print(f"  - Yearly {period['year']}")
            else:
                print(f"  - Monthly {period['year']}-{period['month']:02d}")

    else:
        print("No data found in database")

    conn.close()
    print()
    print("=" * 80)
