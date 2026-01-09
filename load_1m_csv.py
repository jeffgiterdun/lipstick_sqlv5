#!/usr/bin/env python3
"""
1-Minute OHLC CSV Loader with Incremental Support

Loads 1-minute OHLC data from CSV files into ohlc_data.db.

Features:
- Incremental loading (only new data by default)
- Force reload for corrections
- Gap detection and reporting
- Data continuity validation
- Metadata tracking

Usage:
    # Incremental load (default)
    python load_1m_csv.py "Raw CSV Data/ES_01032026.csv" ES

    # Force reload from specific date
    python load_1m_csv.py "Raw CSV Data/ES_01032026.csv" ES --from-date 2026-01-01

    # Full reload (re-import all rows)
    python load_1m_csv.py "Raw CSV Data/ES_01032026.csv" ES --force-reload
"""

import sqlite3
import csv
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from metadata_helpers_1m import (
    get_last_processed_time,
    update_processing_metadata,
    get_data_range
)

DB_PATH = 'data/ohlc_data.db'


def get_db_connection():
    """Create database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def detect_gaps(conn: sqlite3.Connection, symbol: str, expected_interval_minutes: int = 1) -> List[Dict]:
    """
    Detect gaps in 1-minute data.

    Returns list of gaps with start, end, and duration.
    """
    cursor = conn.cursor()

    cursor.execute("""
        WITH lagged AS (
            SELECT
                time,
                LAG(time) OVER (ORDER BY time) as prev_time
            FROM ohlc_1m
            WHERE symbol = ?
            ORDER BY time
        )
        SELECT time as gap_end, prev_time as gap_start
        FROM lagged
        WHERE prev_time IS NOT NULL
    """, (symbol,))

    gaps = []
    for row in cursor.fetchall():
        gap_start = datetime.fromisoformat(row['gap_start'])
        gap_end = datetime.fromisoformat(row['gap_end'])
        delta = gap_end - gap_start

        # If gap is > 2 hours (allows for market close), report it
        if delta > timedelta(hours=2):
            gaps.append({
                'gap_start': row['gap_start'],
                'gap_end': row['gap_end'],
                'duration': str(delta)
            })

    return gaps


def load_csv_incremental(
    csv_file: str,
    symbol: str,
    force_reload: bool = False,
    from_date: Optional[str] = None
) -> Dict:
    """
    Load CSV data incrementally.

    Args:
        csv_file: Path to CSV file
        symbol: 'ES' or 'NQ'
        force_reload: If True, update existing rows
        from_date: Start loading from this date (YYYY-MM-DD)

    Returns:
        Statistics dictionary
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"\n{'='*80}")
    print(f"Loading {symbol} 1-Minute Data")
    print(f"{'='*80}\n")
    print(f"Source: {csv_file}")
    print(f"Mode: {'Force Reload' if force_reload else 'Incremental'}")

    # Step 1: Get current data range
    data_range = get_data_range(symbol, cursor)
    existing_max = data_range['max_time']

    if existing_max and not force_reload:
        print(f"Current data ends: {existing_max}")

    # Step 2: Determine start time
    if from_date:
        start_time = from_date
        print(f"Loading from: {start_time} (--from-date)")
    elif existing_max and not force_reload:
        start_time = existing_max
        print(f"Loading from: {start_time} (last timestamp)")
    else:
        start_time = None
        print("Loading all data (no filter)")

    # Step 3: Process CSV
    new_rows = 0
    updated_rows = 0
    skipped_rows = 0

    print(f"\nProcessing CSV file...")

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            timestamp = row['time']

            # Skip if before our start time
            if start_time and timestamp <= start_time:
                skipped_rows += 1
                continue

            # Check if row exists
            cursor.execute("""
                SELECT 1 FROM ohlc_1m
                WHERE symbol = ? AND time = ?
            """, (symbol, timestamp))

            exists = cursor.fetchone() is not None

            if exists and force_reload:
                # Update existing row
                cursor.execute("""
                    UPDATE ohlc_1m
                    SET open = ?, high = ?, low = ?, close = ?
                    WHERE symbol = ? AND time = ?
                """, (
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    symbol,
                    timestamp
                ))
                updated_rows += 1

            elif not exists:
                # Insert new row
                cursor.execute("""
                    INSERT INTO ohlc_1m (symbol, time, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    timestamp,
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close'])
                ))
                new_rows += 1
            else:
                # Already exists, skip
                skipped_rows += 1

    # Step 4: Commit changes
    conn.commit()

    # Step 5: Update metadata
    new_data_range = get_data_range(symbol, cursor)
    update_processing_metadata(
        symbol=symbol,
        process_type='ohlc_load',
        last_time=new_data_range['max_time'],
        records_count=new_rows + updated_rows,
        status='success',
        cursor=cursor,
        commit=True
    )

    # Step 6: Detect gaps
    print(f"\nChecking for data gaps...")
    gaps = detect_gaps(conn, symbol)

    # Results
    print(f"\n{'='*80}")
    print("Loading Complete")
    print(f"{'='*80}")
    print(f"\nStatistics:")
    print(f"  New rows: {new_rows:,}")
    print(f"  Updated rows: {updated_rows:,}")
    print(f"  Skipped rows: {skipped_rows:,}")
    print(f"\nData Range:")
    print(f"  First: {new_data_range['min_time']}")
    print(f"  Last: {new_data_range['max_time']}")
    print(f"  Total: {new_data_range['total_candles']:,} candles")

    if gaps:
        print(f"\n[WARNING] Data Gaps Detected: {len(gaps)}")
        for i, gap in enumerate(gaps[:10], 1):  # Show first 10
            print(f"  {i}. {gap['gap_start']} -> {gap['gap_end']} ({gap['duration']})")
        if len(gaps) > 10:
            print(f"  ... and {len(gaps) - 10} more gaps")
    else:
        print(f"\n[OK] No significant gaps detected")

    conn.close()

    return {
        'new_rows': new_rows,
        'updated_rows': updated_rows,
        'skipped_rows': skipped_rows,
        'gaps': len(gaps),
        'date_range': (new_data_range['min_time'], new_data_range['max_time'])
    }


def main():
    parser = argparse.ArgumentParser(
        description='Load 1-minute OHLC data from CSV with incremental support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Incremental load (only new data)
  python load_1m_csv.py "Raw CSV Data/ES_01032026.csv" ES

  # Load from specific date
  python load_1m_csv.py "Raw CSV Data/ES_01032026.csv" ES --from-date 2026-01-01

  # Force reload all data
  python load_1m_csv.py "Raw CSV Data/ES_01032026.csv" ES --force-reload
        """
    )

    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('symbol', choices=['ES', 'NQ'], help='Symbol (ES or NQ)')
    parser.add_argument('--force-reload', action='store_true',
                        help='Update existing rows (default: skip existing)')
    parser.add_argument('--from-date', type=str,
                        help='Load from this date (YYYY-MM-DD)')

    args = parser.parse_args()

    load_csv_incremental(
        args.csv_file,
        args.symbol,
        force_reload=args.force_reload,
        from_date=args.from_date
    )


if __name__ == '__main__':
    main()
