#!/usr/bin/env python3
"""
Metadata helper functions for incremental processing.

Provides functions to track and update processing metadata for
the incremental data loading and processing pipeline.

Process Types:
- 'ohlc_load' - Last OHLC data load timestamp
- 'session_calc' - Last session calculation run
- 'poi_processing' - Last POI event processing run
- 'swing_detection' - Last swing detection run
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = 'data/yearly_monthly.db'


def get_last_processed_time(symbol: str, process_type: str, cursor: sqlite3.Cursor = None) -> Optional[str]:
    """
    Get the last timestamp processed for a symbol/process.

    Args:
        symbol: Symbol name (e.g., 'ES', 'NQ')
        process_type: Type of processing ('ohlc_load', 'session_calc', 'poi_processing', 'swing_detection')
        cursor: Optional database cursor (if None, creates own connection)

    Returns:
        Last processed timestamp as ISO string, or None if no record exists
    """
    should_close = False
    if cursor is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        should_close = True

    try:
        query = """
            SELECT last_processed_time
            FROM processing_metadata
            WHERE symbol = ? AND process_type = ?
        """
        result = cursor.execute(query, (symbol, process_type)).fetchone()
        return result[0] if result else None

    finally:
        if should_close:
            cursor.close()
            conn.close()


def update_processing_metadata(
    symbol: str,
    process_type: str,
    last_time: str,
    records_count: int,
    status: str = 'success',
    error_message: str = None,
    cursor: sqlite3.Cursor = None,
    commit: bool = True
) -> None:
    """
    Update or insert processing metadata.

    Args:
        symbol: Symbol name (e.g., 'ES', 'NQ')
        process_type: Type of processing ('ohlc_load', 'session_calc', 'poi_processing', 'swing_detection')
        last_time: Last processed timestamp (ISO format)
        records_count: Number of records processed
        status: Processing status ('success' or 'error')
        error_message: Error message if status is 'error'
        cursor: Optional database cursor (if None, creates own connection)
        commit: Whether to commit the transaction (default True)
    """
    should_close = False
    if cursor is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        should_close = True

    try:
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO processing_metadata
            (symbol, process_type, last_processed_time, records_processed, status, error_message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, process_type) DO UPDATE SET
                last_processed_time = excluded.last_processed_time,
                records_processed = excluded.records_processed,
                status = excluded.status,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
        """, (symbol, process_type, last_time, records_count, status, error_message, now, now))

        if commit and should_close:
            conn.commit()

    finally:
        if should_close:
            cursor.close()
            conn.close()


def get_max_time(symbol: str, cursor: sqlite3.Cursor = None) -> Optional[str]:
    """
    Get the maximum (latest) timestamp in the OHLC data for a symbol.

    Args:
        symbol: Symbol name (e.g., 'ES', 'NQ')
        cursor: Optional database cursor (if None, creates own connection)

    Returns:
        Maximum timestamp as ISO string, or None if no data exists
    """
    should_close = False
    if cursor is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        should_close = True

    try:
        query = "SELECT MAX(time) FROM ohlc_4h WHERE symbol = ?"
        result = cursor.execute(query, (symbol,)).fetchone()
        return result[0] if result else None

    finally:
        if should_close:
            cursor.close()
            conn.close()


def get_min_time(symbol: str, cursor: sqlite3.Cursor = None) -> Optional[str]:
    """
    Get the minimum (earliest) timestamp in the OHLC data for a symbol.

    Args:
        symbol: Symbol name (e.g., 'ES', 'NQ')
        cursor: Optional database cursor (if None, creates own connection)

    Returns:
        Minimum timestamp as ISO string, or None if no data exists
    """
    should_close = False
    if cursor is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        should_close = True

    try:
        query = "SELECT MIN(time) FROM ohlc_4h WHERE symbol = ?"
        result = cursor.execute(query, (symbol,)).fetchone()
        return result[0] if result else None

    finally:
        if should_close:
            cursor.close()
            conn.close()


def check_timestamp_exists(symbol: str, timestamp: str, cursor: sqlite3.Cursor = None) -> bool:
    """
    Check if a specific timestamp exists in the OHLC data for a symbol.

    Args:
        symbol: Symbol name (e.g., 'ES', 'NQ')
        timestamp: Timestamp to check (ISO format)
        cursor: Optional database cursor (if None, creates own connection)

    Returns:
        True if timestamp exists, False otherwise
    """
    should_close = False
    if cursor is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        should_close = True

    try:
        query = "SELECT 1 FROM ohlc_4h WHERE symbol = ? AND time = ? LIMIT 1"
        result = cursor.execute(query, (symbol, timestamp)).fetchone()
        return result is not None

    finally:
        if should_close:
            cursor.close()
            conn.close()


def get_data_range(symbol: str, cursor: sqlite3.Cursor = None) -> Dict[str, Any]:
    """
    Get comprehensive data range information for a symbol.

    Args:
        symbol: Symbol name (e.g., 'ES', 'NQ')
        cursor: Optional database cursor (if None, creates own connection)

    Returns:
        Dictionary with min_time, max_time, and total_candles
    """
    should_close = False
    if cursor is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        should_close = True

    try:
        query = """
            SELECT MIN(time), MAX(time), COUNT(*)
            FROM ohlc_4h
            WHERE symbol = ?
        """
        result = cursor.execute(query, (symbol,)).fetchone()

        return {
            'min_time': result[0],
            'max_time': result[1],
            'total_candles': result[2]
        }

    finally:
        if should_close:
            cursor.close()
            conn.close()


def get_processing_status(symbol: str = None, cursor: sqlite3.Cursor = None) -> list:
    """
    Get processing status for all process types, optionally filtered by symbol.

    Args:
        symbol: Optional symbol name to filter by (if None, returns all symbols)
        cursor: Optional database cursor (if None, creates own connection)

    Returns:
        List of dictionaries containing processing metadata
    """
    should_close = False
    if cursor is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        should_close = True

    try:
        if symbol:
            query = """
                SELECT symbol, process_type, last_processed_time, records_processed, status, updated_at
                FROM processing_metadata
                WHERE symbol = ?
                ORDER BY process_type
            """
            results = cursor.execute(query, (symbol,)).fetchall()
        else:
            query = """
                SELECT symbol, process_type, last_processed_time, records_processed, status, updated_at
                FROM processing_metadata
                ORDER BY symbol, process_type
            """
            results = cursor.execute(query).fetchall()

        return [
            {
                'symbol': row[0],
                'process_type': row[1],
                'last_processed_time': row[2],
                'records_processed': row[3],
                'status': row[4],
                'updated_at': row[5]
            }
            for row in results
        ]

    finally:
        if should_close:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    # Test the helper functions
    print("Testing metadata helper functions...")
    print("=" * 80)

    # Test get_data_range
    for symbol in ['ES', 'NQ']:
        data_range = get_data_range(symbol)
        print(f"\n{symbol} Data Range:")
        print(f"  Min Time: {data_range['min_time']}")
        print(f"  Max Time: {data_range['max_time']}")
        print(f"  Total Candles: {data_range['total_candles']}")

    # Test get_processing_status
    print("\nProcessing Status:")
    statuses = get_processing_status()
    if statuses:
        for status in statuses:
            print(f"  {status['symbol']} - {status['process_type']}: {status['last_processed_time']} ({status['records_processed']} records)")
    else:
        print("  No processing metadata found")

    print("\n" + "=" * 80)
