"""
Swing Detection Script for Yearly/Monthly Database

This script detects hierarchical swings (Class 1-6) from 4H OHLC data
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

Usage:
    python detect_swings.py
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Database path
DB_PATH = 'data/yearly_monthly.db'


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

    A swing high: middle candle's high > both adjacent candles' highs
    A swing low: middle candle's low < both adjacent candles' lows

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

        # Check for swing high
        if (curr_candle['high'] > prev_candle['high'] and
            curr_candle['high'] > next_candle['high']):
            swings.append({
                'index': i,
                'time': curr_candle['time'],
                'price': curr_candle['high'],
                'type': 'high',
                'class': 1
            })

        # Check for swing low
        elif (curr_candle['low'] < prev_candle['low'] and
              curr_candle['low'] < next_candle['low']):
            swings.append({
                'index': i,
                'time': curr_candle['time'],
                'price': curr_candle['low'],
                'type': 'low',
                'class': 1
            })

    return swings


# ============================================================================
# Hierarchical Classification (Class 2, 3, 4)
# ============================================================================

def is_promotable(
    swing: Dict,
    all_swings: List[Dict],
    source_class: int,
    swing_type: str
) -> bool:
    """
    Check if a swing qualifies for promotion.

    Requirements:
    1. Has source_class swings of same type on BOTH left and right sides
    2. Price significance: Is higher/lower than CLOSEST source_class neighbors

    Args:
        swing: The swing to check
        all_swings: List of all swings (sorted by index)
        source_class: Class to look for (1, 2, or 3)
        swing_type: 'high' or 'low'

    Returns:
        True if swing qualifies for promotion to next class
    """
    swing_index = swing['index']
    swing_price = swing['price']

    # Find swings of same type and source_class on each side
    left_swings = [s for s in all_swings
                   if s['index'] < swing_index
                   and s['class'] == source_class
                   and s['type'] == swing_type]

    right_swings = [s for s in all_swings
                    if s['index'] > swing_index
                    and s['class'] == source_class
                    and s['type'] == swing_type]

    # Must have at least one on each side
    if len(left_swings) == 0 or len(right_swings) == 0:
        return False

    # Get CLOSEST swing on each side (not ANY swing)
    closest_left = max(left_swings, key=lambda s: s['index'])
    closest_right = min(right_swings, key=lambda s: s['index'])

    # Price comparison against closest neighbors
    if swing_type == 'high':
        # Must be HIGHER than both closest neighbors
        return swing_price > closest_left['price'] and swing_price > closest_right['price']
    else:  # 'low'
        # Must be LOWER than both closest neighbors
        return swing_price < closest_left['price'] and swing_price < closest_right['price']


def filter_to_local_extrema(
    promotable_swings: List[Dict],
    swing_type: str
) -> List[Dict]:
    """
    Among promotable swings, only select local maxima/minima.

    Groups nearby swings and only promotes the most extreme one from each group.
    This prevents over-promotion and creates the pyramid distribution.

    Args:
        promotable_swings: List of swings eligible for promotion
        swing_type: 'high' or 'low'

    Returns:
        Filtered list containing only local extrema
    """
    if len(promotable_swings) == 0:
        return []

    # Sort by index
    promotable_swings.sort(key=lambda s: s['index'])

    # Group swings within proximity threshold
    PROXIMITY_THRESHOLD = 5  # Swings within 5 positions are "nearby"

    groups = []
    current_group = [promotable_swings[0]]

    for i in range(1, len(promotable_swings)):
        prev = promotable_swings[i-1]
        curr = promotable_swings[i]

        if curr['index'] - prev['index'] <= PROXIMITY_THRESHOLD:
            current_group.append(curr)
        else:
            groups.append(current_group)
            current_group = [curr]

    groups.append(current_group)

    # Select most extreme swing from each group
    selected = []
    for group in groups:
        if swing_type == 'high':
            best = max(group, key=lambda s: s['price'])  # Highest high
        else:
            best = min(group, key=lambda s: s['price'])  # Lowest low
        selected.append(best)

    return selected


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
            # For highs: must be HIGHER than both adjacent highs
            if curr['price'] > left['price'] and curr['price'] > right['price']:
                curr['class'] = target_class
                promoted_count += 1
        else:  # 'low'
            # For lows: must be LOWER than both adjacent lows
            if curr['price'] < left['price'] and curr['price'] < right['price']:
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


# ============================================================================
# Movement Metrics
# ============================================================================

def calculate_movement_metrics(swings: List[Dict]) -> List[Dict]:
    """
    Calculate movement metrics for each swing.

    For each swing, finds the most recent swing of opposite type and calculates:
    - points_from_prior: Price difference
    - candles_from_prior: Number of candles between swings
    - prior_opposite_swing_index: Index in swings list (for ID lookup later)

    Args:
        swings: List of swings (sorted by index)

    Returns:
        Updated swings list with movement metrics
    """
    for i, swing in enumerate(swings):
        # Find the most recent swing of opposite type
        prior_opposite = None
        prior_opposite_index = None

        # Look backwards through swings
        for j in range(i - 1, -1, -1):
            if swings[j]['type'] != swing['type']:
                prior_opposite = swings[j]
                prior_opposite_index = j
                break

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
) -> Optional[int]:
    """
    Find the nearest POI event at or before the swing time.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        swing_time: ISO timestamp of the swing

    Returns:
        POI event ID or None
    """
    cursor = conn.cursor()

    # Column to check depends on symbol
    time_column = 'es_event_time' if symbol == 'ES' else 'nq_event_time'

    # Find most recent POI event where event_time <= swing_time
    cursor.execute(f"""
        SELECT id
        FROM poi_events
        WHERE {time_column} IS NOT NULL
        AND {time_column} <= ?
        ORDER BY {time_column} DESC
        LIMIT 1
    """, (swing_time,))

    result = cursor.fetchone()
    return result['id'] if result else None


# ============================================================================
# Active Sessions Snapshot
# ============================================================================

def get_active_sessions_snapshot(
    conn: sqlite3.Connection,
    symbol: str,
    swing_time: str
) -> str:
    """
    Get JSON snapshot of all active sessions at swing time.

    Args:
        conn: Database connection
        symbol: 'ES' or 'NQ'
        swing_time: ISO timestamp of the swing

    Returns:
        JSON string with session_name: status mappings
    """
    cursor = conn.cursor()

    # Get all sessions for this symbol that were active at swing_time
    cursor.execute("""
        SELECT session_name, status
        FROM sessions
        WHERE symbol = ?
        AND session_start_time <= ?
        AND (status != 'resolved' OR resolution_time >= ?)
        ORDER BY session_name
    """, (symbol, swing_time, swing_time))

    sessions = {}
    for row in cursor.fetchall():
        sessions[row['session_name']] = row['status']

    return json.dumps(sessions)


# ============================================================================
# Database Operations
# ============================================================================

def get_candles(conn: sqlite3.Connection, symbol: str) -> List[Dict]:
    """Get all 4H candles for a symbol, sorted by time."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time, open, high, low, close
        FROM ohlc_4h
        WHERE symbol = ?
        ORDER BY time ASC
    """, (symbol,))

    return [dict(row) for row in cursor.fetchall()]


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
        poi_event_id = find_nearest_poi_event(conn, symbol, swing['time'])

        # Get active sessions snapshot
        sessions_snapshot = get_active_sessions_snapshot(conn, symbol, swing['time'])

        cursor.execute("""
            INSERT INTO swings (
                symbol, swing_time, swing_price, swing_type, swing_class,
                prior_opposite_swing_id, points_from_prior, candles_from_prior,
                nearest_poi_event_id, active_sessions_snapshot, created_at
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
            sessions_snapshot,
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

def process_symbol(conn: sqlite3.Connection, symbol: str):
    """Process all swings for a symbol."""
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


def main():
    """Main processing function."""
    print("="*80)
    print("Swing Detection - Yearly/Monthly Database")
    print("="*80)

    conn = get_db_connection()

    try:
        # Process both symbols
        for symbol in ['ES', 'NQ']:
            process_symbol(conn, symbol)

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
