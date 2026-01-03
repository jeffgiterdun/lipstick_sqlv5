#!/usr/bin/env python3
"""
Load 4-hour OHLC data from CSV into the yearly_monthly.db database.

This script loads 4H candles for Yearly/Monthly session analysis.

Usage:
    python load_4h_csv.py [csv_filename] [symbol]

Example:
    python load_4h_csv.py ES_4H_2024.csv ES
    python load_4h_csv.py NQ_4H_2024.csv NQ
"""

import sys
import os
import sqlite3
import csv
import argparse
from datetime import datetime, timedelta
from metadata_helpers import (
    get_last_processed_time,
    update_processing_metadata,
    get_max_time,
    get_min_time,
    check_timestamp_exists,
    get_data_range
)

# Constants
DB_PATH = 'data/yearly_monthly.db'
CSV_FOLDER = 'Raw 4H CSV Data'

def load_csv_to_db(csv_filename, symbol, force_reload=False, from_date=None):
    """
    Load 4-hour OHLC data from CSV file into database with incremental support.

    Args:
        csv_filename: Name of CSV file in Raw 4H CSV Data folder
        symbol: Symbol name (ES or NQ)
        force_reload: If True, reload all data (update existing records)
        from_date: If specified, only load data from this date forward (ISO format)

    Returns:
        dict: Statistics about the load operation
    """
    csv_path = os.path.join(CSV_FOLDER, csv_filename)

    # Check if file exists
    if not os.path.exists(csv_path):
        print(f"[ERROR] File not found: {csv_path}")
        sys.exit(1)

    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        print("Run create_yearly_monthly_db.py first to create the database.")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")

    # Determine incremental loading strategy
    existing_max = None
    start_time = None

    if not force_reload:
        existing_max = get_max_time(symbol, cursor)

        if from_date:
            start_time = from_date
            print(f"\n[INFO] Loading from specified date: {from_date}")
        elif existing_max:
            start_time = existing_max
            print(f"\n[INFO] Incremental mode: Loading data after {existing_max}")
        else:
            print(f"\n[INFO] No existing data for {symbol}. Loading all data.")
    else:
        print(f"\n[INFO] Force reload mode: Updating all existing records")

    # Statistics
    stats = {
        'total_rows': 0,
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
        'min_time': None,
        'max_time': None,
        'error_details': [],
        'start_time': start_time
    }

    print(f"\nLoading 4H data: {csv_filename} for symbol: {symbol}")
    print("=" * 80)

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)

            # Verify expected columns
            expected_columns = {'time', 'open', 'high', 'low', 'close'}
            if not expected_columns.issubset(reader.fieldnames):
                print(f"[ERROR] CSV missing required columns: {expected_columns}")
                print(f"Found columns: {reader.fieldnames}")
                sys.exit(1)

            for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                stats['total_rows'] += 1

                try:
                    time = row['time'].strip()
                    open_price = float(row['open'])
                    high_price = float(row['high'])
                    low_price = float(row['low'])
                    close_price = float(row['close'])

                    # Skip if before our start time (incremental mode)
                    if start_time and time <= start_time:
                        stats['skipped'] += 1
                        continue

                    # Track date range of processed data
                    if stats['min_time'] is None or time < stats['min_time']:
                        stats['min_time'] = time
                    if stats['max_time'] is None or time > stats['max_time']:
                        stats['max_time'] = time

                    # Check if record already exists
                    cursor.execute("""
                        SELECT id FROM ohlc_4h
                        WHERE symbol = ? AND time = ?
                    """, (symbol, time))

                    existing = cursor.fetchone()

                    if existing:
                        if force_reload:
                            # Update existing record (force reload mode)
                            cursor.execute("""
                                UPDATE ohlc_4h
                                SET open = ?, high = ?, low = ?, close = ?
                                WHERE symbol = ? AND time = ?
                            """, (open_price, high_price, low_price, close_price, symbol, time))
                            stats['updated'] += 1
                        else:
                            # Skip (already have this data)
                            stats['skipped'] += 1
                    else:
                        # Insert new record
                        cursor.execute("""
                            INSERT INTO ohlc_4h (symbol, time, open, high, low, close)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (symbol, time, open_price, high_price, low_price, close_price))
                        stats['inserted'] += 1

                    # Progress indicator
                    if stats['total_rows'] % 100 == 0:
                        print(f"Processed {stats['total_rows']} rows ({stats['inserted']} new, {stats['skipped']} skipped)...", end='\r')

                except ValueError as e:
                    stats['errors'] += 1
                    error_msg = f"Row {row_num}: Invalid data format - {e}"
                    stats['error_details'].append(error_msg)
                    if stats['errors'] <= 5:  # Only show first 5 errors
                        print(f"[WARNING] {error_msg}")

                except Exception as e:
                    stats['errors'] += 1
                    error_msg = f"Row {row_num}: {e}"
                    stats['error_details'].append(error_msg)
                    if stats['errors'] <= 5:
                        print(f"[ERROR] {error_msg}")

        # Update processing metadata
        if stats['inserted'] > 0 or stats['updated'] > 0:
            new_max = get_max_time(symbol, cursor)
            update_processing_metadata(
                symbol=symbol,
                process_type='ohlc_load',
                last_time=new_max,
                records_count=stats['inserted'] + stats['updated'],
                status='success',
                cursor=cursor,
                commit=False  # Don't commit yet, we'll do it below
            )
            print(f"[OK] Updated processing metadata: last_processed_time = {new_max}")

        # Commit transaction (includes both data and metadata)
        conn.commit()
        print(f"Processed {stats['total_rows']} rows ({stats['inserted']} new, {stats['skipped']} skipped)... Done!")

    except Exception as e:
        print(f"\n[ERROR] Failed to process file: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()

    return stats

def print_summary(stats, symbol):
    """Print summary of load operation."""
    print("\n" + "=" * 80)
    print("LOAD SUMMARY")
    print("=" * 80)
    print(f"Symbol:           {symbol}")
    print(f"Total Rows:       {stats['total_rows']}")
    print(f"Inserted:         {stats['inserted']}")
    print(f"Updated:          {stats['updated']}")
    print(f"Skipped:          {stats['skipped']}")
    print(f"Errors:           {stats['errors']}")

    if stats['start_time']:
        print(f"\nIncremental Load:")
        print(f"  Start After:    {stats['start_time']}")

    if stats['min_time'] and stats['max_time']:
        print(f"\nProcessed Date Range:")
        print(f"  Start:          {stats['min_time']}")
        print(f"  End:            {stats['max_time']}")

    if stats['errors'] > 0:
        print(f"\n[WARNING] {stats['errors']} errors occurred during load")
        if len(stats['error_details']) > 5:
            print(f"(Showing first 5 errors, {len(stats['error_details']) - 5} more not shown)")

    print("=" * 80)

def verify_data(symbol):
    """Verify loaded data in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("DATABASE VERIFICATION")
    print("=" * 80)

    # Count records for this symbol
    cursor.execute("SELECT COUNT(*) FROM ohlc_4h WHERE symbol = ?", (symbol,))
    count = cursor.fetchone()[0]
    print(f"4H candles in database for {symbol}: {count}")

    # Show first 3 records
    cursor.execute("""
        SELECT time, open, high, low, close
        FROM ohlc_4h
        WHERE symbol = ?
        ORDER BY time ASC
        LIMIT 3
    """, (symbol,))

    print(f"\nFirst 3 candles:")
    for row in cursor.fetchall():
        print(f"  {row[0]} | O:{row[1]} H:{row[2]} L:{row[3]} C:{row[4]}")

    # Show last 3 records
    cursor.execute("""
        SELECT time, open, high, low, close
        FROM ohlc_4h
        WHERE symbol = ?
        ORDER BY time DESC
        LIMIT 3
    """, (symbol,))

    print(f"\nLast 3 candles:")
    for row in cursor.fetchall():
        print(f"  {row[0]} | O:{row[1]} H:{row[2]} L:{row[3]} C:{row[4]}")

    conn.close()
    print("=" * 80)


def detect_gaps(symbol, expected_interval_hours=4):
    """
    Detect gaps in 4H data.

    Args:
        symbol: Symbol name (e.g., 'ES', 'NQ')
        expected_interval_hours: Expected interval between candles (default 4)

    Returns:
        List of gap dictionaries with gap_start, gap_end, and duration
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT time,
               LAG(time) OVER (ORDER BY time) as prev_time
        FROM ohlc_4h
        WHERE symbol = ?
        ORDER BY time
    """

    gaps = []
    for row in cursor.execute(query, (symbol,)):
        current = row[0]
        previous = row[1]

        if previous:
            # Parse timestamps
            current_dt = datetime.fromisoformat(current)
            previous_dt = datetime.fromisoformat(previous)

            delta = current_dt - previous_dt
            expected = timedelta(hours=expected_interval_hours)

            # Allow for weekends (2.5 days = 60 hours)
            # If gap is more than 60 hours, report it
            if delta > timedelta(hours=60):
                gaps.append({
                    'gap_start': previous,
                    'gap_end': current,
                    'duration': str(delta)
                })

    conn.close()
    return gaps


def report_data_gaps(symbol):
    """Report gaps in data for awareness."""
    print("\n" + "=" * 80)
    print("GAP DETECTION")
    print("=" * 80)

    gaps = detect_gaps(symbol, expected_interval_hours=4)

    if gaps:
        print(f"[WARNING] Data Gaps Detected for {symbol}:")
        for gap in gaps:
            print(f"  {gap['gap_start']} -> {gap['gap_end']} (Duration: {gap['duration']})")
        print(f"  Total gaps: {len(gaps)}")
    else:
        print(f"[OK] No significant gaps detected for {symbol}")

    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Load 4-hour OHLC data from CSV into yearly_monthly.db database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Incremental load (default - only load new data)
  python load_4h_csv.py ES4H_01032026.csv ES

  # Force reload (update all existing records)
  python load_4h_csv.py ES4H_01032026.csv ES --force-reload

  # Load from specific date
  python load_4h_csv.py ES4H_01032026.csv ES --from-date 2025-12-01T00:00:00-05:00

Note: CSV files should be placed in 'Raw 4H CSV Data' folder
      CSV format: time,open,high,low,close
      Time format: ISO 8601 with timezone (e.g., 2025-01-01T00:00:00-05:00)
        """
    )

    parser.add_argument('csv_filename', help='CSV filename in Raw 4H CSV Data folder')
    parser.add_argument('symbol', help='Symbol name (ES or NQ)')
    parser.add_argument('--force-reload', action='store_true',
                        help='Force reload all data (update existing records)')
    parser.add_argument('--from-date', type=str,
                        help='Load data from this date forward (ISO format)')

    args = parser.parse_args()

    # Uppercase symbol
    symbol = args.symbol.upper()

    # Validate symbol
    if symbol not in ['ES', 'NQ']:
        print(f"[WARNING] Symbol '{symbol}' is not ES or NQ. Continuing anyway...")

    # Load data
    stats = load_csv_to_db(
        csv_filename=args.csv_filename,
        symbol=symbol,
        force_reload=args.force_reload,
        from_date=args.from_date
    )

    # Print summary
    print_summary(stats, symbol)

    # Verify data
    verify_data(symbol)

    # Report gaps
    report_data_gaps(symbol)

    if stats['inserted'] > 0 or stats['updated'] > 0:
        print(f"\n[OK] Successfully processed {stats['inserted']} new + {stats['updated']} updated 4H candles for {symbol}")
    else:
        print(f"\n[INFO] No new data to process for {symbol}")

    print(f"[OK] Database: {DB_PATH}")

if __name__ == '__main__':
    main()
