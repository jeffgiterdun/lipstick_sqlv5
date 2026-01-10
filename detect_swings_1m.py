#!/usr/bin/env python3
"""
Swing Detection Script for 1M Database

This script detects hierarchical swings (Class 1-6) from 1M OHLC data
and populates the swings table with:
- Swing classification (1, 2, 3, 4, 5, or 6)
- Movement metrics (points/candles from prior opposite swing)
- POI event linkage (nearest POI event at or before swing time)
- Active sessions snapshot (JSON of session statuses at swing time)

Classification Rules (Single-Pass List Comparison):
- Class 1: 3-bar pivot (middle bar is high/low point)
- Class 2: Class 1 swing that is higher/lower than adjacent Class 1 swings (in time-sorted list)
- Class 3: Class 2 swing that is higher/lower than adjacent Class 2 swings (in time-sorted list)
- Class 4: Class 3 swing that is higher/lower than adjacent Class 3 swings (in time-sorted list)
- Class 5: Class 4 swing that is higher/lower than adjacent Class 4 swings (in time-sorted list)
- Class 6: Class 5 swing that is higher/lower than adjacent Class 5 swings (in time-sorted list)

Highs and lows are processed separately to create nested fractal structure.
Each class promotion is a single pass comparing adjacent swings in the sorted list.

Adapted from detect_swings.py for 1M data processing with performance optimizations.

Usage:
    # Full mode (recalculate all swings from scratch)
    python detect_swings_1m.py --full

    # Incremental mode (only process if new data exists)
    python detect_swings_1m.py --incremental
"""

import sqlite3
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from metadata_helpers_1m import (
    get_last_processed_time,
    update_processing_metadata,
    get_data_range
)

# Database path
DB_PATH = 'data/ohlc_data.db'


def get_db_connection():
    """Create database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string to datetime object."""
    return datetime.fromisoformat(timestamp_str)


# ============================================================================
# Class 1: 3-Bar Pivot Detection
# ============================================================================

def detect_class1_pivots(candles: List[Dict]) -> List[Dict]:
    """
    Detect Class 1 swings (3-bar pivots).

    A swing high: middle candle's high >= both adjacent candles' highs
    A swing low: middle candle's low <= both adjacent candles' lows

    Note: Using >= and <= to handle equal highs/lows, ensuring that when
    adjacent candles have the same price, at least one is detected as a swing.

    Args:
        candles: List of OHLC candles (must be sorted by time)

    Returns:
        List of swing dictionaries with:
        - index: position in candles list
        - time: swing time
        - price: swing price
        - type: 'high' or 'low'
        - class: 1
    """
    swings = []

    # Need at least 3 candles for a pivot
    if len(candles) < 3:
        return swings

    # Check each candle (skip first and last)
    for i in range(1, len(candles) - 1):
        prev_candle = candles[i - 1]
        curr_candle = candles[i]
        next_candle = candles[i + 1]

        # Check for swing high (using >= to handle equal highs)
        if (curr_candle['high'] >= prev_candle['high'] and
            curr_candle['high'] >= next_candle['high']):
            swings.append({
                'index': i,
                'time': curr_candle['time'],
                'price': curr_candle['high'],
                'type': 'high',
                'class': 1
            })

        # Check for swing low (using <= to handle equal lows)
        elif (curr_candle['low'] <= prev_candle['low'] and
              curr_candle['low'] <= next_candle['low']):
            swings.append({
                'index': i,
                'time': curr_candle['time'],
                'price': curr_candle['low'],
                'type': 'low',
                'class': 1
            })

    return swings


# ============================================================================
# Hierarchical Classification (Class 2, 3, 4, 5, 6)
# ============================================================================

def count_by_class(swings: List[Dict]) -> Dict[int, int]:
    """
    Count swings by class level.

    Args:
        swings: List of swings

    Returns:
        Dictionary mapping class number to count
    """
    counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    for s in swings:
        counts[s['class']] += 1
    return counts


def classify_to_target_class(
    swings: List[Dict],
    source_class: int,
    target_class: int,
    swing_type: str
) -> List[Dict]:
    """
    Single-pass promotion: Compare adjacent swings in time-sorted list.

    For each swing at source_class, compare to the adjacent swings
    (also at source_class) to its left and right in the time-sorted list.
    If higher/lower than both neighbors, promote to target_class.

    Args:
        swings: List of swings (sorted by time/index)
        source_class: Class to promote from (1, 2, 3, 4, or 5)
        target_class: Class to promote to (2, 3, 4, 5, or 6)
        swing_type: 'high' or 'low'

    Returns:
        Updated swings list with promotions
    """
    # Get only swings at source_class (already sorted by index)
    candidates = [s for s in swings if s['class'] == source_class]

    if len(candidates) < 3:
        print(f"    Only {len(candidates)} Class {source_class} swings, need at least 3")
        return swings

    promoted_count = 0

    # Compare each candidate (except first and last) to its adjacent neighbors
    for i in range(1, len(candidates) - 1):
        curr = candidates[i]
        left = candidates[i - 1]
        right = candidates[i + 1]

        # Compare prices to adjacent neighbors in the list
        if swing_type == 'high':
            # For highs: must be HIGHER than or EQUAL to both adjacent highs
            if curr['price'] >= left['price'] and curr['price'] >= right['price']:
                curr['class'] = target_class
                promoted_count += 1
        else:  # 'low'
            # For lows: must be LOWER than or EQUAL to both adjacent lows
            if curr['price'] <= left['price'] and curr['price'] <= right['price']:
                curr['class'] = target_class
                promoted_count += 1

    print(f"    Promoted {promoted_count} swings from Class {source_class} to Class {target_class}")

    return swings


def classify_higher_swings(swings: List[Dict]) -> List[Dict]:
    """
    Hierarchically classify swings using single-pass comparison.
    Processes swing highs and lows separately.

    Each class promotion compares adjacent swings in the time-sorted list:
    - A swing is promoted if it's higher/lower than its immediate neighbors
    - Only swings of the same class are compared to each other

    Args:
        swings: List of Class 1 swings (will be modified)

    Returns:
        Updated swings list with higher classifications
    """
    # Separate into highs and lows
    swing_highs = [s for s in swings if s['type'] == 'high']
    swing_lows = [s for s in swings if s['type'] == 'low']

    print(f"  Initial: {len(swing_highs)} highs, {len(swing_lows)} lows")

    # Process each class level (2, 3, 4, 5, 6)
    # Continue until no more promotions occur
    for target_class in [2, 3, 4, 5, 6]:
        source_class = target_class - 1
        print(f"\n  Promoting Class {source_class} -> Class {target_class}")

        swing_highs = classify_to_target_class(swing_highs, source_class, target_class, 'high')
        swing_lows = classify_to_target_class(swing_lows, source_class, target_class, 'low')

    # Recombine and sort by index
    all_swings = swing_highs + swing_lows
    all_swings.sort(key=lambda s: s['index'])

    return all_swings


def remove_adjacent_duplicate_prices(swings: List[Dict]) -> List[Dict]:
    """
    Remove adjacent swings with the same price, keeping only the first occurrence.

    When consecutive swings of the same type have the same price (no intervening
    swings of that type), only the first one is kept. The duplicates are removed
    entirely from the dataset.

    This ensures that each price level is represented only once in the time series,
    preventing incorrect promotions during hierarchical classification.

    Args:
        swings: List of swings (sorted by index)

    Returns:
        Filtered swings list with adjacent duplicates removed
    """
    # Separate into highs and lows
    swing_highs = [s for s in swings if s['type'] == 'high']
    swing_lows = [s for s in swings if s['type'] == 'low']

    def filter_duplicates(swing_list: List[Dict], swing_type: str) -> List[Dict]:
        """Remove adjacent duplicates from a list of swings of one type."""
        if len(swing_list) <= 1:
            return swing_list

        filtered = []
        i = 0
        removed_count = 0

        while i < len(swing_list):
            # Keep the first swing at this price level
            filtered.append(swing_list[i])

            # Skip any consecutive swings with the same price
            current_price = swing_list[i]['price']
            j = i + 1
            while j < len(swing_list) and swing_list[j]['price'] == current_price:
                removed_count += 1
                j += 1

            i = j

        if removed_count > 0:
            print(f"    Removed {removed_count} duplicate adjacent {swing_type}s at same price")

        return filtered

    # Filter highs and lows separately
    filtered_highs = filter_duplicates(swing_highs, 'high')
    filtered_lows = filter_duplicates(swing_lows, 'low')

    # Recombine and sort by index
    all_swings = filtered_highs + filtered_lows
    all_swings.sort(key=lambda s: s['index'])

    return all_swings


# ============================================================================
# Movement Metrics
# ============================================================================

def calculate_movement_metrics(swings: List[Dict]) -> List[Dict]:
    """
    Calculate movement metrics for each swing.

    For each swing, finds the appropriate prior opposite swing and calculates:
    - points_from_prior: Price difference
    - candles_from_prior: Number of candles between swings
    - prior_opposite_swing_index: Index in swings list (for ID lookup later)

    Logic:
    - Class 1 & 2 swings: Reference the immediate prior opposite swing (any class)
    - Class 3+ swings: Reference the most recent Class 3+ opposite swing
      (skips Class 1 & 2 noise to measure truly structural moves in 1M data)

    Args:
        swings: List of swings (sorted by index)

    Returns:
        Updated swings list with movement metrics
    """
    for i, swing in enumerate(swings):
        # Find the appropriate prior opposite swing based on class
        prior_opposite = None
        prior_opposite_index = None

        # Look backwards through swings
        for j in range(i - 1, -1, -1):
            candidate = swings[j]

            # Must be opposite type
            if candidate['type'] != swing['type']:
                # Class 1 & 2 swings: take the first (most recent) opposite swing
                if swing['class'] <= 2:
                    prior_opposite = candidate
                    prior_opposite_index = j
                    break

                # Class 3+ swings: skip Class 1 & 2, find first Class 3+ opposite
                elif candidate['class'] >= 3:
                    prior_opposite = candidate
                    prior_opposite_index = j
                    break
                # If candidate is Class 1 or 2 and we need Class 3+, continue searching

        if prior_opposite:
            # Calculate price difference
            points_from_prior = abs(swing['price'] - prior_opposite['price'])

            # Calculate candle difference
            candles_from_prior = swing['index'] - prior_opposite['index']

            swing['points_from_prior'] = points_from_prior
            swing['candles_from_prior'] = candles_from_prior
            swing['prior_opposite_swing_index'] = prior_opposite_index
        else:
            swing['points_from_prior'] = None
            swing['candles_from_prior'] = None
            swing['prior_opposite_swing_index'] = None

    return swings


# ============================================================================
# POI Event Linkage
# ============================================================================

def find_nearest_poi_event(
    conn: sqlite3.Connection,
    symbol: str,
    swing_time: str
) -> Tuple[Optional[int], Optional[str]]:
    """
    Find the nearest POI event at or before the swing time.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        swing_time: ISO timestamp of the swing

    Returns:
        Tuple of (POI event ID or None, POI event time or None)
    """
    cursor = conn.cursor()

    # Column to check depends on symbol
    time_column = 'es_event_time' if symbol == 'ES' else 'nq_event_time'

    # Find most recent POI event where event_time <= swing_time
    cursor.execute(f"""
        SELECT id, {time_column} as event_time
        FROM poi_events
        WHERE {time_column} IS NOT NULL
        AND {time_column} <= ?
        ORDER BY {time_column} DESC
        LIMIT 1
    """, (swing_time,))

    result = cursor.fetchone()
    if result:
        return result['id'], result['event_time']
    return None, None


# ============================================================================
# Database Operations
# ============================================================================

def get_candles(conn: sqlite3.Connection, symbol: str) -> List[Dict]:
    """Get all 1M candles for a symbol, sorted by time."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time, open, high, low, close
        FROM ohlc_1m
        WHERE symbol = ?
        ORDER BY time ASC
    """, (symbol,))

    return [dict(row) for row in cursor.fetchall()]


def delete_swings(conn: sqlite3.Connection, symbol: str) -> int:
    """
    Delete all swings for a symbol.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'

    Returns:
        Number of swings deleted
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM swings WHERE symbol = ?", (symbol,))
    return cursor.rowcount


def insert_swings(
    conn: sqlite3.Connection,
    symbol: str,
    swings: List[Dict]
) -> Dict[str, int]:
    """
    Insert swings into the database.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        swings: List of swing dictionaries

    Returns:
        Dictionary with counts by class
    """
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Track swing IDs for prior_opposite_swing_id linkage
    swing_ids = []

    # First pass: Insert all swings and capture IDs
    for swing in swings:
        # Find POI event linkage
        poi_event_id, poi_event_time = find_nearest_poi_event(conn, symbol, swing['time'])

        # Calculate candles from POI event (time difference in minutes for 1M data)
        candles_from_poi = None
        if poi_event_time:
            swing_dt = parse_iso_timestamp(swing['time'])
            poi_dt = parse_iso_timestamp(poi_event_time)
            time_delta = swing_dt - poi_dt
            candles_from_poi = int(time_delta.total_seconds() / 60)  # 1M candles = 1 minute each

        cursor.execute("""
            INSERT INTO swings (
                symbol, swing_time, swing_price, swing_type, swing_class,
                prior_opposite_swing_id, points_from_prior, candles_from_prior,
                nearest_poi_event_id, candles_from_poi_event, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol,
            swing['time'],
            swing['price'],
            swing['type'],
            swing['class'],
            None,  # Will update in second pass
            swing['points_from_prior'],
            swing['candles_from_prior'],
            poi_event_id,
            candles_from_poi,
            now
        ))

        swing_ids.append(cursor.lastrowid)

    # Second pass: Update prior_opposite_swing_id references
    for i, swing in enumerate(swings):
        if swing['prior_opposite_swing_index'] is not None:
            prior_id = swing_ids[swing['prior_opposite_swing_index']]
            current_id = swing_ids[i]

            cursor.execute("""
                UPDATE swings
                SET prior_opposite_swing_id = ?
                WHERE id = ?
            """, (prior_id, current_id))

    # Count by class
    counts = count_by_class(swings)

    return counts


# ============================================================================
# Main Processing
# ============================================================================

def detect_swings_for_symbol(conn: sqlite3.Connection, symbol: str) -> List[Dict]:
    """
    Detect and classify all swings for a symbol.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'

    Returns:
        List of swing dictionaries with all metrics calculated
    """
    print(f"\n{'='*80}")
    print(f"Processing {symbol} Swings")
    print(f"{'='*80}\n")

    # Get all candles
    candles = get_candles(conn, symbol)
    print(f"Loaded {len(candles)} candles")

    # Detect Class 1 pivots
    print("Detecting Class 1 pivots...")
    swings = detect_class1_pivots(candles)
    class1_count = len(swings)
    print(f"  Found {class1_count} Class 1 swings")

    # Remove adjacent duplicate prices (keep only first occurrence)
    print("Removing adjacent duplicate prices...")
    swings = remove_adjacent_duplicate_prices(swings)
    after_dedup_count = len(swings)
    print(f"  After deduplication: {after_dedup_count} swings")

    # Hierarchically classify higher classes
    print("Classifying higher classes...")
    swings = classify_higher_swings(swings)

    # Count by class after classification
    class_counts = count_by_class(swings)

    print(f"  Class 1: {class_counts[1]}")
    print(f"  Class 2: {class_counts[2]}")
    print(f"  Class 3: {class_counts[3]}")
    print(f"  Class 4: {class_counts[4]}")
    print(f"  Class 5: {class_counts[5]}")
    print(f"  Class 6: {class_counts[6]}")

    # Calculate movement metrics
    print("Calculating movement metrics...")
    swings = calculate_movement_metrics(swings)

    return swings


def process_full(conn: sqlite3.Connection, symbols: List[str]) -> Dict:
    """
    Full processing mode: Delete all swings and recalculate from scratch.

    Args:
        conn: Database connection
        symbols: List of symbols to process

    Returns:
        Dictionary with processing statistics
    """
    stats = {
        'total_swings': 0,
        'by_symbol': {}
    }

    print("\nMODE: Full Processing (delete and recalculate all swings)")
    print()

    for symbol in symbols:
        # Delete existing swings
        deleted = delete_swings(conn, symbol)
        if deleted > 0:
            print(f"Deleted {deleted} existing {symbol} swings")

        # Detect all swings
        swings = detect_swings_for_symbol(conn, symbol)

        # Insert into database
        print("Inserting swings into database...")
        insert_counts = insert_swings(conn, symbol, swings)

        print(f"\n{symbol} Complete:")
        print(f"  Total Swings: {len(swings)}")
        print(f"  Class 1: {insert_counts[1]}")
        print(f"  Class 2: {insert_counts[2]}")
        print(f"  Class 3: {insert_counts[3]}")
        print(f"  Class 4: {insert_counts[4]}")
        print(f"  Class 5: {insert_counts[5]}")
        print(f"  Class 6: {insert_counts[6]}")

        stats['total_swings'] += len(swings)
        stats['by_symbol'][symbol] = {
            'count': len(swings),
            'by_class': insert_counts
        }

    return stats


def process_incremental(conn: sqlite3.Connection, symbols: List[str]) -> Dict:
    """
    Incremental processing mode: Only process if new data exists since last run.

    Note: Because swing classification is hierarchical and depends on comparing
    adjacent swings, we re-run full detection when new data exists. This ensures
    correct classification as new swings may promote existing swings to higher classes.

    Args:
        conn: Database connection
        symbols: List of symbols to process

    Returns:
        Dictionary with processing statistics
    """
    stats = {
        'total_swings': 0,
        'by_symbol': {},
        'symbols_processed': [],
        'symbols_skipped': []
    }

    print("\nMODE: Incremental Processing (only process if new data exists)")
    print()

    for symbol in symbols:
        # Get last processed time
        cursor = conn.cursor()
        last_processed_time = get_last_processed_time(symbol, 'swing_detection', cursor)

        # Get current data range
        data_range = get_data_range(symbol, cursor)
        latest_data_time = data_range['max_time']

        if last_processed_time:
            print(f"{symbol}: Last processed {last_processed_time}")
            print(f"{symbol}: Latest data     {latest_data_time}")

            if last_processed_time >= latest_data_time:
                print(f"{symbol}: No new data - skipping")
                stats['symbols_skipped'].append(symbol)
                continue
            else:
                print(f"{symbol}: New data detected - reprocessing all swings")
        else:
            print(f"{symbol}: No previous processing found - running full detection")

        # Delete existing swings
        deleted = delete_swings(conn, symbol)
        if deleted > 0:
            print(f"Deleted {deleted} existing {symbol} swings")

        # Detect all swings (re-run full detection to handle classification changes)
        swings = detect_swings_for_symbol(conn, symbol)

        # Insert into database
        print("Inserting swings into database...")
        insert_counts = insert_swings(conn, symbol, swings)

        print(f"\n{symbol} Complete:")
        print(f"  Total Swings: {len(swings)}")
        print(f"  Class 1: {insert_counts[1]}")
        print(f"  Class 2: {insert_counts[2]}")
        print(f"  Class 3: {insert_counts[3]}")
        print(f"  Class 4: {insert_counts[4]}")
        print(f"  Class 5: {insert_counts[5]}")
        print(f"  Class 6: {insert_counts[6]}")

        stats['total_swings'] += len(swings)
        stats['by_symbol'][symbol] = {
            'count': len(swings),
            'by_class': insert_counts
        }
        stats['symbols_processed'].append(symbol)

    return stats


def main():
    """Main processing function."""
    parser = argparse.ArgumentParser(
        description='Detect hierarchical swings (Class 1-6) from 1M OHLC data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full mode (delete and recalculate all swings)
  python detect_swings_1m.py --full

  # Incremental mode (only process if new data exists)
  python detect_swings_1m.py --incremental

  # Process specific symbol
  python detect_swings_1m.py --incremental --symbol ES
        """
    )

    parser.add_argument('--full', action='store_true',
                        help='Full mode: Delete and recalculate all swings')
    parser.add_argument('--incremental', action='store_true',
                        help='Incremental mode: Only process if new data exists')
    parser.add_argument('--symbol', type=str,
                        help='Process only this symbol (ES or NQ)')

    args = parser.parse_args()

    # Default to incremental mode if neither specified
    if not args.full and not args.incremental:
        args.incremental = True

    symbols = [args.symbol.upper()] if args.symbol else ['ES', 'NQ']

    print("="*80)
    print("Swing Detection - 1M Database")
    print("="*80)

    conn = get_db_connection()

    try:
        # Process based on mode
        if args.full:
            stats = process_full(conn, symbols)
        else:
            stats = process_incremental(conn, symbols)

        # Update processing metadata for each symbol
        cursor = conn.cursor()
        for symbol in symbols:
            if symbol in stats.get('symbols_skipped', []):
                # Skipped - don't update metadata
                continue

            data_range = get_data_range(symbol, cursor)
            if data_range['max_time']:
                swing_count = stats['by_symbol'].get(symbol, {}).get('count', 0)
                update_processing_metadata(
                    symbol=symbol,
                    process_type='swing_detection',
                    last_time=data_range['max_time'],
                    records_count=swing_count,
                    status='success',
                    cursor=cursor,
                    commit=False
                )

        # Commit all changes
        conn.commit()

        # Final summary
        print("\n" + "="*80)
        print("Summary")
        print("="*80)

        cursor = conn.cursor()

        # Total swings
        cursor.execute("SELECT COUNT(*) as count FROM swings")
        total = cursor.fetchone()['count']
        print(f"\nTotal Swings: {total}")

        # By symbol
        print("\nBy Symbol:")
        cursor.execute("""
            SELECT symbol, COUNT(*) as count
            FROM swings
            GROUP BY symbol
            ORDER BY symbol
        """)
        for row in cursor.fetchall():
            print(f"  {row['symbol']}: {row['count']}")

        # By class
        print("\nBy Class:")
        cursor.execute("""
            SELECT swing_class, COUNT(*) as count
            FROM swings
            GROUP BY swing_class
            ORDER BY swing_class
        """)
        for row in cursor.fetchall():
            print(f"  Class {row['swing_class']}: {row['count']}")

        # POI linkage stats
        if total > 0:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM swings
                WHERE nearest_poi_event_id IS NOT NULL
            """)
            linked = cursor.fetchone()['count']
            print(f"\nSwings linked to POI events: {linked} ({100*linked/total:.1f}%)")

        print("\n[DONE] Swing detection complete!")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()


if __name__ == '__main__':
    main()
