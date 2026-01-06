"""
POI Event Processing Script for Yearly and Monthly Sessions

This script processes Point of Interest (POI) touches for Yearly and Monthly sessions
in the yearly_monthly.db database. It:

1. Scans 4H OHLC data for touches of PoC, RPP, and TO levels
2. Tracks session status through the state machine (unbroken → break → return → resolved)
3. Creates POI events with Echo Chamber data (ES/NQ timing)
4. Updates session status as events occur
5. Supports incremental processing to only scan new candles

Usage:
    # Full mode (scan all candles from TO time)
    python process_poi_events.py --full

    # Incremental mode (only scan new candles since last check)
    python process_poi_events.py --incremental
"""

import sqlite3
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple
from metadata_helpers import (
    get_last_processed_time,
    update_processing_metadata,
    get_data_range
)


# ============================================================================
# Configuration
# ============================================================================

DB_PATH = 'data/yearly_monthly.db'
TOUCH_THRESHOLD = 0.25  # Points - how close is considered a "touch"


# ============================================================================
# Database Connection
# ============================================================================

def get_db_connection():
    """Create database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


# ============================================================================
# Utility Functions
# ============================================================================

def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string to datetime object."""
    # Handle timezone offset
    if '+' in timestamp_str or timestamp_str.count('-') > 2:
        # Has timezone - parse it
        from datetime import timezone
        # Simple parser for ±HH:MM format
        if '+' in timestamp_str:
            dt_str, tz_str = timestamp_str.rsplit('+', 1)
            tz_sign = 1
        else:
            parts = timestamp_str.rsplit('-', 1)
            dt_str = parts[0]
            tz_str = parts[1]
            tz_sign = -1

        # Parse base datetime
        dt = datetime.fromisoformat(dt_str)

        # Parse timezone offset
        if ':' in tz_str:
            tz_hours, tz_mins = map(int, tz_str.split(':'))
        else:
            tz_hours = int(tz_str[:2])
            tz_mins = int(tz_str[2:]) if len(tz_str) > 2 else 0

        offset = timedelta(hours=tz_sign * tz_hours, minutes=tz_sign * tz_mins)
        dt = dt.replace(tzinfo=timezone(offset))

        return dt
    else:
        return datetime.fromisoformat(timestamp_str)


def get_trading_day(timestamp_str: str) -> str:
    """
    Calculate trading day from timestamp.
    Trading day runs 18:00 to 16:59 (next calendar day).
    """
    dt = parse_iso_timestamp(timestamp_str)

    # If time is 00:00 to 16:59, trading day is same calendar date
    if dt.hour < 18:
        return dt.date().isoformat()

    # If time is 18:00 to 23:59, trading day is next calendar date
    else:
        next_day = dt.date() + timedelta(days=1)
        return next_day.isoformat()


def is_touch(price: float, level: float, threshold: float = TOUCH_THRESHOLD) -> bool:
    """Check if price touched level within threshold."""
    return abs(price - level) <= threshold


def calculate_echo_chamber(es_time_str: Optional[str], nq_time_str: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    """
    Calculate Echo Chamber metrics (time_delta, leader).

    Returns:
        (time_delta_minutes, leader)
        - time_delta_minutes: absolute difference in minutes, or None
        - leader: 'ES', 'NQ', 'simultaneous', or None
    """
    if es_time_str is None or nq_time_str is None:
        return None, None

    es_time = parse_iso_timestamp(es_time_str)
    nq_time = parse_iso_timestamp(nq_time_str)

    delta_seconds = abs((es_time - nq_time).total_seconds())
    time_delta_minutes = int(delta_seconds / 60)

    # Determine leader
    if delta_seconds < 60:  # Less than 1 minute = simultaneous
        leader = 'simultaneous'
    elif es_time < nq_time:
        leader = 'ES'
    else:
        leader = 'NQ'

    return time_delta_minutes, leader


# ============================================================================
# POI Event Detection
# ============================================================================

def detect_touch(candle: Dict, poi_type: str, poi_value: float) -> bool:
    """
    Detect if a candle touched a POI level.

    Args:
        candle: Dictionary with 'high' and 'low' keys
        poi_type: 'PoC', 'RPP', or 'TO'
        poi_value: The price level to check

    Returns:
        True if touched, False otherwise
    """
    if poi_value is None:
        return False

    # Check if level is within candle range
    return candle['low'] <= poi_value <= candle['high']


def get_candles_after_time(
    conn: sqlite3.Connection,
    symbol: str,
    start_time: str,
    end_time: Optional[str] = None
) -> List[Dict]:
    """
    Get all 4H candles for a symbol after start_time.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        start_time: ISO timestamp to start scanning from
        end_time: Optional ISO timestamp to end scanning (inclusive)

    Returns:
        List of candle dictionaries
    """
    cursor = conn.cursor()

    if end_time:
        cursor.execute("""
            SELECT time, open, high, low, close
            FROM ohlc_4h
            WHERE symbol = ?
            AND time >= ?
            AND time <= ?
            ORDER BY time ASC
        """, (symbol, start_time, end_time))
    else:
        cursor.execute("""
            SELECT time, open, high, low, close
            FROM ohlc_4h
            WHERE symbol = ?
            AND time >= ?
            ORDER BY time ASC
        """, (symbol, start_time))

    return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# POI Event Management
# ============================================================================

def get_or_create_poi_event(
    conn: sqlite3.Connection,
    es_session_id: int,
    nq_session_id: int,
    session_type: str,
    session_name: str,
    poi_type: str,
    event_type: str,
    symbol: str,
    event_time: str
) -> int:
    """
    Get existing POI event or create new one.
    Records the time each asset (ES/NQ) performed the event.
    Trading day is based on whichever asset touched first.

    Args:
        es_session_id: Session ID for ES
        nq_session_id: Session ID for NQ
        session_type: 'Yearly' or 'Monthly'
        session_name: Session name
        poi_type: 'PoC', 'RPP', or 'TO'
        event_type: 'break', 'return', or 'resolution'
        symbol: 'ES' or 'NQ' (which asset touched in this call)
        event_time: ISO timestamp of the touch

    Returns:
        POI event ID
    """
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Check if event already exists for these sessions + POI type + event type
    cursor.execute("""
        SELECT id, es_event_time, nq_event_time
        FROM poi_events
        WHERE es_session_id = ?
        AND nq_session_id = ?
        AND poi_type = ?
        AND event_type = ?
    """, (es_session_id, nq_session_id, poi_type, event_type))

    existing = cursor.fetchone()

    if existing:
        # Update existing event
        event_id = existing['id']
        es_time = existing['es_event_time']
        nq_time = existing['nq_event_time']

        # Update the appropriate symbol's time
        if symbol == 'ES':
            es_time = event_time
        else:
            nq_time = event_time

        # Recalculate Echo Chamber metrics
        time_delta, leader = calculate_echo_chamber(es_time, nq_time)

        # Trading day remains based on first touch (don't update it)
        cursor.execute("""
            UPDATE poi_events
            SET es_event_time = ?,
                nq_event_time = ?,
                time_delta_minutes = ?,
                leader = ?,
                updated_at = ?
            WHERE id = ?
        """, (es_time, nq_time, time_delta, leader, now, event_id))

    else:
        # Create new event
        es_time = event_time if symbol == 'ES' else None
        nq_time = event_time if symbol == 'NQ' else None
        time_delta, leader = calculate_echo_chamber(es_time, nq_time)

        # Trading day based on first touch (this event_time)
        trading_day = get_trading_day(event_time)

        cursor.execute("""
            INSERT INTO poi_events (
                es_session_id, nq_session_id, trading_day, session_type, session_name,
                poi_type, event_type,
                es_event_time, nq_event_time,
                time_delta_minutes, leader,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            es_session_id, nq_session_id, trading_day, session_type, session_name,
            poi_type, event_type,
            es_time, nq_time,
            time_delta, leader,
            now, now
        ))
        event_id = cursor.lastrowid

    return event_id


# ============================================================================
# Session State Machine
# ============================================================================

def update_session_status(
    conn: sqlite3.Connection,
    session: Dict,
    poi_type: str,
    event_time: str
) -> bool:
    """
    Update session status based on POI touch.

    Returns:
        True if status changed (POI event should be created)
        False if no status change (touch ignored)
    """
    cursor = conn.cursor()
    session_id = session['id']
    current_status = session['status']
    now = datetime.now(timezone.utc).isoformat()

    # State machine logic
    if current_status == 'unbroken':
        # First break (PoC or RPP)
        if poi_type in ['PoC', 'RPP']:
            cursor.execute("""
                UPDATE sessions
                SET status = 'break',
                    first_break_time = ?,
                    first_break_side = ?,
                    updated_at = ?
                WHERE id = ?
            """, (event_time, poi_type, now, session_id))
            return True
        else:
            # TO touch while unbroken - ignore
            return False

    elif current_status == 'break':
        # Waiting for first return to TO
        if poi_type == 'TO':
            cursor.execute("""
                UPDATE sessions
                SET status = 'return',
                    first_return_time = ?,
                    updated_at = ?
                WHERE id = ?
            """, (event_time, now, session_id))
            return True
        else:
            # Additional PoC/RPP touches - ignore
            return False

    elif current_status == 'return':
        # Waiting for second break OR resolution
        if poi_type in ['PoC', 'RPP']:
            # Second break
            if session['second_break_time'] is None:
                # First touch of PoC/RPP after return
                cursor.execute("""
                    UPDATE sessions
                    SET second_break_time = ?,
                        second_break_side = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (event_time, poi_type, now, session_id))
                return True
            else:
                # Additional touches after second break - ignore
                return False

        elif poi_type == 'TO':
            # Resolution (second return to TO)
            if session['second_break_time'] is not None:
                # CRITICAL VALIDATION: Resolution MUST occur after first_return
                # This prevents resolution_time from being set to timestamps from the 'unbroken' state
                if session['first_return_time'] is None:
                    # No first return yet - this shouldn't happen, but guard against it
                    return False

                if event_time <= session['first_return_time']:
                    # Resolution time must be AFTER return time - ignore this touch
                    # This prevents the bug where resolution_time < first_return_time
                    return False

                # Determine resolution type
                resolution_type = 'single_sided' if session['first_break_side'] == session['second_break_side'] else 'double_sided'

                cursor.execute("""
                    UPDATE sessions
                    SET status = 'resolved',
                        resolution_time = ?,
                        resolution_type = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (event_time, resolution_type, now, session_id))
                return True
            else:
                # TO touch but no second break yet - ignore
                return False

    elif current_status == 'resolved':
        # Session complete - ignore all touches
        return False

    return False


# ============================================================================
# Main Processing
# ============================================================================

def get_matching_session(conn: sqlite3.Connection, session: Dict, target_symbol: str) -> Optional[Dict]:
    """
    Find the matching session for the target symbol.

    Args:
        session: Current session dict
        target_symbol: 'ES' or 'NQ' - the symbol we're looking for

    Returns:
        Matching session dict or None if not found
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM sessions
        WHERE symbol = ?
        AND session_type = ?
        AND session_name = ?
        AND session_start_time = ?
    """, (target_symbol, session['session_type'], session['session_name'], session['session_start_time']))

    result = cursor.fetchone()
    return dict(result) if result else None


def process_session(
    conn: sqlite3.Connection,
    session: Dict,
    incremental: bool = False,
    latest_data_time: Optional[str] = None
):
    """
    Process POI events for a single session (both ES and NQ).

    Args:
        conn: Database connection
        session: Session dictionary (ES session)
        incremental: If True, only scan candles after last_poi_check_time
        latest_data_time: Latest data timestamp (for end_time in incremental mode)
    """
    # Only process ES sessions (to avoid duplicate processing)
    if session['symbol'] != 'ES':
        return

    session_type = session['session_type']
    session_name = session['session_name']
    to_time = session['to_time']

    # Skip if no range calculated yet
    if session['true_open'] is None or session['poc'] is None or session['rpp'] is None:
        return

    # Find matching NQ session
    nq_session = get_matching_session(conn, session, 'NQ')
    if nq_session is None:
        print(f"\nSkipping {session_name}: No matching NQ session found")
        return

    # Verify NQ session has range calculated
    if nq_session['true_open'] is None or nq_session['poc'] is None or nq_session['rpp'] is None:
        print(f"\nSkipping {session_name}: NQ session has no range calculated")
        return

    es_session_id = session['id']
    nq_session_id = nq_session['id']

    # Determine scan range
    if incremental:
        # Use last_poi_check_time if available, otherwise use to_time
        es_scan_start = session.get('last_poi_check_time') or to_time
        nq_scan_start = nq_session.get('last_poi_check_time') or to_time

        # Skip if already processed all available data
        if latest_data_time and es_scan_start >= latest_data_time:
            return
    else:
        # Full mode: scan from TO time
        es_scan_start = to_time
        nq_scan_start = to_time

    print(f"\nProcessing: {session_name}")
    print(f"  ES Session ID: {es_session_id}, NQ Session ID: {nq_session_id}")
    print(f"  ES Range: PoC={session['poc']:.2f} <-- TO={session['true_open']:.2f} --> RPP={session['rpp']:.2f}")
    print(f"  NQ Range: PoC={nq_session['poc']:.2f} <-- TO={nq_session['true_open']:.2f} --> RPP={nq_session['rpp']:.2f}")
    print(f"  ES Status: {session['status']}, NQ Status: {nq_session['status']}")

    if incremental:
        print(f"  Mode: Incremental (ES from {es_scan_start}, NQ from {nq_scan_start})")
    else:
        print(f"  Mode: Full (from TO time)")

    # Track the latest candle time we process for each symbol
    latest_es_time = es_scan_start
    latest_nq_time = nq_scan_start

    # Process both ES and NQ
    for symbol in ['ES', 'NQ']:
        if symbol == 'ES':
            scan_start = es_scan_start
        else:
            scan_start = nq_scan_start

        candles = get_candles_after_time(conn, symbol, scan_start, latest_data_time)

        print(f"  {symbol}: {len(candles)} candles to check")

        # Get the appropriate session and levels for this symbol
        if symbol == 'ES':
            current_symbol_session_id = es_session_id
            current_symbol_session = session
        else:
            current_symbol_session_id = nq_session_id
            current_symbol_session = nq_session

        # Use this symbol's POI levels
        poc = current_symbol_session['poc']
        rpp = current_symbol_session['rpp']
        to = current_symbol_session['true_open']

        for candle in candles:
            candle_time = candle['time']

            # Skip the TO candle itself - it's the definition/reference point, not a touch
            if candle_time == to_time:
                continue

            # Track latest candle time for this symbol
            if symbol == 'ES':
                latest_es_time = candle_time
            else:
                latest_nq_time = candle_time

            # Check each POI level in order
            for poi_type, poi_value in [('PoC', poc), ('RPP', rpp), ('TO', to)]:
                if detect_touch(candle, poi_type, poi_value):
                    # Re-fetch this symbol's session to get latest status
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM sessions WHERE id = ?", (current_symbol_session_id,))
                    current_session = dict(cursor.fetchone())

                    # Update this symbol's session status
                    status_changed = update_session_status(conn, current_session, poi_type, candle_time)

                    if status_changed:
                        # Determine event type based on new status
                        cursor.execute("SELECT status FROM sessions WHERE id = ?", (current_symbol_session_id,))
                        new_status = cursor.fetchone()['status']

                        if new_status == 'break':
                            event_type = 'break'
                        elif new_status == 'return':
                            if current_session['first_return_time'] is None:
                                event_type = 'return'
                            else:
                                event_type = 'break'  # Second break
                        elif new_status == 'resolved':
                            event_type = 'resolution'
                        else:
                            continue

                        # Create or update POI event (shared between ES and NQ)
                        get_or_create_poi_event(
                            conn,
                            es_session_id,
                            nq_session_id,
                            session_type,
                            session_name,
                            poi_type,
                            event_type,
                            symbol,
                            candle_time
                        )

                        print(f"    {symbol} touched {poi_type} at {candle_time} -> {event_type} event")

                    # Break after first detected touch in this candle
                    # (Don't process multiple POI types in same candle)
                    break

    # Update last_poi_check_time for both sessions after processing
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        UPDATE sessions
        SET last_poi_check_time = ?,
            updated_at = ?
        WHERE id = ?
    """, (latest_es_time, now, es_session_id))

    cursor.execute("""
        UPDATE sessions
        SET last_poi_check_time = ?,
            updated_at = ?
        WHERE id = ?
    """, (latest_nq_time, now, nq_session_id))


def main():
    """Main processing function."""
    parser = argparse.ArgumentParser(
        description='Process POI events for Yearly and Monthly sessions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full mode (scan all candles from TO time)
  python process_poi_events.py --full

  # Incremental mode (only scan new candles since last check)
  python process_poi_events.py --incremental
        """
    )

    parser.add_argument('--full', action='store_true',
                        help='Full mode: Scan all candles from TO time')
    parser.add_argument('--incremental', action='store_true',
                        help='Incremental mode: Only scan new candles since last check')

    args = parser.parse_args()

    # Default to incremental mode if neither specified
    if not args.full and not args.incremental:
        args.incremental = True

    print("=" * 80)
    print("POI Event Processing - Yearly and Monthly Sessions")
    print("=" * 80)
    print()

    if args.full:
        print("MODE: Full Processing (scan all candles from TO time)")
    else:
        print("MODE: Incremental Processing (scan only new candles)")

    print()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get latest data time from ohlc_4h table
        cursor.execute("SELECT MAX(time) FROM ohlc_4h")
        latest_data_time = cursor.fetchone()[0]

        print(f"Latest data available: {latest_data_time}")
        print()

        # Get all sessions ordered by start time
        cursor.execute("""
            SELECT *
            FROM sessions
            ORDER BY session_start_time ASC
        """)

        sessions = [dict(row) for row in cursor.fetchall()]

        print(f"Found {len(sessions)} total sessions")

        # Filter sessions that need processing in incremental mode
        if args.incremental:
            # Filter out sessions that are already up-to-date
            sessions_to_process = []
            for session in sessions:
                # Only process ES sessions (NQ sessions are handled together)
                if session['symbol'] != 'ES':
                    continue

                # Skip if no range calculated yet
                if session['true_open'] is None:
                    continue

                # Get last check time
                last_check = session.get('last_poi_check_time') or session['to_time']

                # Process if there's new data since last check
                if last_check < latest_data_time:
                    sessions_to_process.append(session)

            print(f"Sessions needing incremental update: {len(sessions_to_process)}")
        else:
            # Full mode: process all ES sessions with calculated ranges
            sessions_to_process = [s for s in sessions if s['symbol'] == 'ES' and s['true_open'] is not None]
            print(f"Sessions to process (ES only): {len(sessions_to_process)}")

        print()
        print("Processing sessions chronologically...")

        processed_count = 0
        events_created = 0

        # Track events before processing
        cursor.execute("SELECT COUNT(*) as count FROM poi_events")
        events_before = cursor.fetchone()['count']

        for session in sessions_to_process:
            process_session(
                conn,
                session,
                incremental=args.incremental,
                latest_data_time=latest_data_time
            )
            processed_count += 1

        # Commit all changes
        conn.commit()

        # Track events after processing
        cursor.execute("SELECT COUNT(*) as count FROM poi_events")
        events_after = cursor.fetchone()['count']
        events_created = events_after - events_before

        # Update processing metadata
        update_processing_metadata(
            symbol='ES',  # Track for ES as representative
            process_type='poi_events',
            last_time=latest_data_time,
            records_count=events_created,
            status='success',
            cursor=cursor,
            commit=True
        )

        print("\n" + "=" * 80)
        print("Processing Complete!")
        print("=" * 80)

        # Summary statistics
        cursor.execute("SELECT COUNT(*) as count FROM poi_events")
        event_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE status = 'resolved'")
        resolved_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE status = 'return'")
        return_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE status = 'break'")
        break_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE status = 'unbroken'")
        unbroken_count = cursor.fetchone()['count']

        print(f"\nProcessing Summary:")
        print(f"  Sessions processed: {processed_count}")
        print(f"  POI events created: {events_created}")

        print(f"\nTotal POI Events: {event_count}")
        print(f"\nSession Status:")
        print(f"  Resolved: {resolved_count}")
        print(f"  Return: {return_count}")
        print(f"  Break: {break_count}")
        print(f"  Unbroken: {unbroken_count}")

        # Show some recent events
        if events_created > 0:
            print(f"\nRecent POI Events (last {min(10, events_created)}):")
            cursor.execute("""
                SELECT
                    trading_day,
                    session_name,
                    poi_type,
                    event_type,
                    es_event_time,
                    nq_event_time,
                    time_delta_minutes,
                    leader
                FROM poi_events
                ORDER BY created_at DESC
                LIMIT 10
            """)

            for row in cursor.fetchall():
                row = dict(row)
                print(f"\n  {row['session_name']} - {row['poi_type']} {row['event_type']}")
                print(f"    ES: {row['es_event_time'] or 'N/A'}")
                print(f"    NQ: {row['nq_event_time'] or 'N/A'}")
                if row['leader']:
                    print(f"    Leader: {row['leader']} (Delta {row['time_delta_minutes']} min)")

        print()

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()


if __name__ == '__main__':
    main()
