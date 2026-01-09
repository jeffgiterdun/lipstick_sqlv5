#!/usr/bin/env python3
"""
Metadata helper functions for 1M database incremental processing.

Modified from metadata_helpers.py to work with ohlc_1m table instead of ohlc_4h.

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

DB_PATH = 'data/ohlc_data.db'


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
    commit: bool = False
) -> None:
    """
    Update (or insert) processing metadata for a symbol/process.

    Args:
        symbol: Symbol name
        process_type: Type of processing
        last_time: Last processed timestamp (ISO format)
        records_count: Number of records processed
        status: Status ('success', 'error', 'partial')
        error_message: Optional error message if status='error'
        cursor: Optional database cursor
        commit: Whether to commit the transaction
    """
    should_close = False
    if cursor is None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        should_close = True
    else:
        conn = cursor.connection

    try:
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO processing_metadata (
                symbol, process_type, last_processed_time,
                records_processed, status, error_message,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, process_type) DO UPDATE SET
                last_processed_time = excluded.last_processed_time,
                records_processed = excluded.records_processed,
                status = excluded.status,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
        """, (symbol, process_type, last_time, records_count,
              status, error_message, now, now))

        if commit:
            conn.commit()

    finally:
        if should_close:
            if commit:
                conn.commit()
            cursor.close()
            conn.close()


def get_data_range(symbol: str, cursor: sqlite3.Cursor = None) -> Dict[str, Any]:
    """
    Get the time range and count of OHLC data for a symbol.

    Args:
        symbol: Symbol name
        cursor: Optional database cursor

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
            FROM ohlc_1m
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
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        should_close = True

    try:
        if symbol:
            query = """
                SELECT symbol, process_type, last_processed_time, records_processed, status, updated_at
                FROM processing_metadata
                WHERE symbol = ?
                ORDER BY updated_at DESC
            """
            rows = cursor.execute(query, (symbol,)).fetchall()
        else:
            query = """
                SELECT symbol, process_type, last_processed_time, records_processed, status, updated_at
                FROM processing_metadata
                ORDER BY symbol, updated_at DESC
            """
            rows = cursor.execute(query).fetchall()

        return [dict(row) for row in rows]

    finally:
        if should_close:
            cursor.close()
            conn.close()


def print_processing_status(symbol: str = None):
    """
    Print a formatted view of processing metadata.

    Args:
        symbol: Optional symbol name to filter by
    """
    status = get_processing_status(symbol)

    if not status:
        print("No processing metadata found")
        return

    print()
    print("=" * 100)
    print("PROCESSING STATUS")
    print("=" * 100)
    print()
    print(f"{'Symbol':<10} {'Process Type':<20} {'Last Processed':<25} {'Records':<10} {'Status':<10}")
    print("-" * 100)

    for record in status:
        symbol = record['symbol']
        process_type = record['process_type']
        last_time = record['last_processed_time'] or 'N/A'
        records = record['records_processed'] or 0
        status_val = record['status']

        # Truncate timestamp for display
        if len(last_time) > 25:
            last_time = last_time[:25]

        print(f"{symbol:<10} {process_type:<20} {last_time:<25} {records:<10} {status_val:<10}")

    print()
