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
from datetime import datetime

# Constants
DB_PATH = 'data/yearly_monthly.db'
CSV_FOLDER = 'Raw 4H CSV Data'

def load_csv_to_db(csv_filename, symbol):
    """
    Load 4-hour OHLC data from CSV file into database.

    Args:
        csv_filename: Name of CSV file in Raw 4H CSV Data folder
        symbol: Symbol name (ES or NQ)

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

    # Statistics
    stats = {
        'total_rows': 0,
        'inserted': 0,
        'updated': 0,
        'errors': 0,
        'min_time': None,
        'max_time': None,
        'error_details': []
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

                    # Track date range
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
                        # Update existing record
                        cursor.execute("""
                            UPDATE ohlc_4h
                            SET open = ?, high = ?, low = ?, close = ?
                            WHERE symbol = ? AND time = ?
                        """, (open_price, high_price, low_price, close_price, symbol, time))
                        stats['updated'] += 1
                    else:
                        # Insert new record
                        cursor.execute("""
                            INSERT INTO ohlc_4h (symbol, time, open, high, low, close)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (symbol, time, open_price, high_price, low_price, close_price))
                        stats['inserted'] += 1

                    # Progress indicator
                    if stats['total_rows'] % 100 == 0:
                        print(f"Processed {stats['total_rows']} rows...", end='\r')

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

        # Commit transaction
        conn.commit()
        print(f"Processed {stats['total_rows']} rows... Done!")

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
    print(f"Errors:           {stats['errors']}")

    if stats['min_time'] and stats['max_time']:
        print(f"\nDate Range:")
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

def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python load_4h_csv.py [csv_filename] [symbol]")
        print("\nExample:")
        print("  python load_4h_csv.py ES_4H_2024.csv ES")
        print("  python load_4h_csv.py NQ_4H_2024.csv NQ")
        print("\nNote: CSV files should be placed in 'Raw 4H CSV Data' folder")
        print("      CSV format: time,open,high,low,close")
        print("      Time format: ISO 8601 with timezone (e.g., 2025-01-01T00:00:00-05:00)")
        sys.exit(1)

    csv_filename = sys.argv[1]
    symbol = sys.argv[2].upper()

    # Validate symbol
    if symbol not in ['ES', 'NQ']:
        print(f"[WARNING] Symbol '{symbol}' is not ES or NQ. Continuing anyway...")

    # Load data
    stats = load_csv_to_db(csv_filename, symbol)

    # Print summary
    print_summary(stats, symbol)

    # Verify data
    verify_data(symbol)

    print(f"\n[OK] Successfully loaded {stats['inserted']} new 4H candles for {symbol}")
    print(f"[OK] Database: {DB_PATH}")

if __name__ == '__main__':
    main()
