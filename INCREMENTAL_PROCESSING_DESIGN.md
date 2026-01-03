# Incremental Processing System - Design Document

**Date:** 2026-01-03
**Scope:** 4H Database (yearly_monthly.db) - Blueprint for 1M Database
**Goal:** Efficient incremental data loading and processing pipeline

---

## REQUIREMENTS

1. **Data Loading:** Daily/Weekly CSV updates with overlap handling
2. **Corrections:** Force reload capability for historical data fixes
3. **Gap Handling:** Accept gaps (missing data access), seamless flow when data exists
4. **Session Recalc:** Auto-detect sessions affected by new data and recalculate
5. **Complete Pipeline:** Sessions → POI Events → Swings (all incremental)

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────┐
│  New CSV File   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  1. SMART CSV LOADER            │
│  - Check last timestamp         │
│  - Load only new rows           │
│  - Validate continuity          │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  2. AFFECTED SESSION DETECTOR   │
│  - Find sessions with new data  │
│  - Identify incomplete sessions │
│  - Mark for recalculation       │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  3. INCREMENTAL SESSION CALC    │
│  - Recalc affected sessions     │
│  - Update PoC/TO/RPP if changed │
│  - Preserve unchanged sessions  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  4. INCREMENTAL POI PROCESSING  │
│  - Scan only new candles        │
│  - Update session status        │
│  - Create new POI events        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  5. INCREMENTAL SWING DETECTION │
│  - Detect swings in new data    │
│  - Maintain hierarchy           │
│  - Link to POI events           │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  6. VALIDATION & REPORTING      │
│  - Check data continuity        │
│  - Verify sessions              │
│  - Report statistics            │
└─────────────────────────────────┘
```

---

## COMPONENT 1: PROCESSING METADATA TRACKING

### New Database Table

```sql
CREATE TABLE processing_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    process_type TEXT NOT NULL,
    last_processed_time TEXT,
    last_processed_candle_id INTEGER,
    records_processed INTEGER,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE(symbol, process_type)
);

CREATE INDEX idx_metadata_symbol_type ON processing_metadata(symbol, process_type);
```

### Process Types
- `'ohlc_load'` - Last OHLC data load timestamp
- `'session_calc'` - Last session calculation run
- `'poi_processing'` - Last POI event processing run
- `'swing_detection'` - Last swing detection run

### Metadata Functions

```python
def get_last_processed_time(symbol, process_type):
    """Get the last timestamp processed for a symbol/process."""
    query = """
        SELECT last_processed_time
        FROM processing_metadata
        WHERE symbol = ? AND process_type = ?
    """
    result = cursor.execute(query, (symbol, process_type)).fetchone()
    return result[0] if result else None

def update_processing_metadata(symbol, process_type, last_time, records_count, status='success'):
    """Update or insert processing metadata."""
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO processing_metadata
        (symbol, process_type, last_processed_time, records_processed, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, process_type) DO UPDATE SET
            last_processed_time = excluded.last_processed_time,
            records_processed = excluded.records_processed,
            status = excluded.status,
            updated_at = excluded.updated_at
    """, (symbol, process_type, last_time, records_count, status, now, now))
```

---

## COMPONENT 2: SMART CSV LOADER

### Enhanced load_4h_csv.py

**Key Features:**
- Check existing data range
- Only load NEW rows (time > max existing time)
- Force reload option for corrections
- Gap detection and reporting
- Overlap validation

**New Command Line Args:**

```bash
# Incremental load (default)
python load_4h_csv.py ES4H_01032026.csv ES

# Force reload (re-process all rows, update existing)
python load_4h_csv.py ES4H_01032026.csv ES --force-reload

# Reload from specific date
python load_4h_csv.py ES4H_01032026.csv ES --from-date 2025-12-01
```

### Algorithm

```python
def load_csv_incremental(csv_file, symbol, force_reload=False, from_date=None):
    # Step 1: Get current data range
    existing_max = get_max_time(symbol) if not force_reload else None

    # Step 2: Apply date filter
    if from_date:
        start_time = from_date
    elif existing_max:
        start_time = existing_max
    else:
        start_time = None  # Load all

    # Step 3: Process CSV
    new_rows = 0
    updated_rows = 0

    for row in csv_reader:
        timestamp = row['time']

        # Skip if before our start time
        if start_time and timestamp <= start_time:
            continue

        # Check for existence (for force reload or overlap)
        exists = check_exists(symbol, timestamp)

        if exists and force_reload:
            update_row(symbol, timestamp, row)
            updated_rows += 1
        elif not exists:
            insert_row(symbol, timestamp, row)
            new_rows += 1
        # else: skip (already have this data)

    # Step 4: Update metadata
    new_max = get_max_time(symbol)
    update_processing_metadata(symbol, 'ohlc_load', new_max, new_rows + updated_rows)

    return {
        'new_rows': new_rows,
        'updated_rows': updated_rows,
        'date_range': (get_min_time(symbol), new_max)
    }
```

### Gap Detection

```python
def detect_gaps(symbol, expected_interval_hours=4):
    """Detect gaps in 4H data."""
    query = """
        SELECT time,
               LAG(time) OVER (ORDER BY time) as prev_time
        FROM ohlc_4h
        WHERE symbol = ?
        ORDER BY time
    """

    gaps = []
    for current, previous in cursor.execute(query, (symbol,)):
        if previous:
            delta = parse_time(current) - parse_time(previous)
            expected = timedelta(hours=expected_interval_hours)

            if delta > expected * 2:  # Allow for weekends
                gaps.append({
                    'gap_start': previous,
                    'gap_end': current,
                    'duration': delta
                })

    return gaps
```

---

## COMPONENT 3: AFFECTED SESSION DETECTION

### Strategy

When new OHLC data is loaded, we need to identify which sessions are affected:

1. **Incomplete Sessions** - Sessions where new data extends their PoC window or TO calculation
2. **Active Sessions** - Sessions in 'unbroken', 'break', or 'return' status that might see new POI touches
3. **Future Sessions** - New sessions that can now be created from new data

### Detection Algorithm

```python
def find_affected_sessions(symbol, new_data_start_time, new_data_end_time):
    """
    Find all sessions affected by new data range.

    Returns:
        - sessions_to_recalc: Sessions needing range recalculation
        - sessions_to_scan: Sessions needing POI rescanning
        - new_sessions_possible: Date ranges where new sessions can be created
    """

    # 1. Sessions with PoC windows overlapping new data
    sessions_to_recalc = cursor.execute("""
        SELECT id, symbol, session_type, session_name, session_start_time, to_time
        FROM sessions
        WHERE symbol = ?
        AND (
            -- PoC window overlaps new data (for incomplete sessions)
            (session_start_time <= ? AND to_time >= ?)

            -- OR session doesn't have TO yet (year in progress)
            OR (true_open IS NULL)
        )
    """, (symbol, new_data_end_time, new_data_start_time)).fetchall()

    # 2. Active sessions that might see new POI touches
    sessions_to_scan = cursor.execute("""
        SELECT id, symbol, session_type, to_time, poc, rpp, status
        FROM sessions
        WHERE symbol = ?
        AND status IN ('unbroken', 'break', 'return')
        AND to_time < ?
    """, (symbol, new_data_end_time)).fetchall()

    # 3. Check if new sessions can be created
    # (e.g., new month started, new year started)
    new_sessions_possible = check_new_session_periods(new_data_start_time, new_data_end_time)

    return sessions_to_recalc, sessions_to_scan, new_sessions_possible
```

### Session Status Flags

Add columns to sessions table to track recalculation needs:

```sql
ALTER TABLE sessions ADD COLUMN needs_recalc INTEGER DEFAULT 0;
ALTER TABLE sessions ADD COLUMN last_recalc_time TEXT;
```

---

## COMPONENT 4: INCREMENTAL SESSION CALCULATION

### Modified calculate_yearly_monthly_sessions.py

**Changes:**
1. Accept `--incremental` mode
2. Query for sessions with `needs_recalc = 1` or new session periods
3. Only recalculate affected sessions
4. Preserve unchanged sessions

**Key Logic:**

```python
def calculate_sessions_incremental(symbol, new_data_range):
    """
    Calculate sessions incrementally.

    Args:
        symbol: 'ES' or 'NQ'
        new_data_range: (start_time, end_time) of new data
    """

    # Step 1: Find sessions needing recalculation
    sessions_to_recalc, sessions_to_scan, new_periods = find_affected_sessions(
        symbol, new_data_range[0], new_data_range[1]
    )

    # Step 2: Recalculate affected sessions
    for session in sessions_to_recalc:
        # Recalculate PoC, TO, RPP with new data
        recalculate_session_ranges(session)

    # Step 3: Create new sessions if applicable
    for period in new_periods:
        if period['type'] == 'Yearly':
            create_yearly_session(symbol, period['year'])
        elif period['type'] == 'Monthly':
            create_monthly_session(symbol, period['year'], period['month'])

    # Step 4: Update metadata
    update_processing_metadata(symbol, 'session_calc', new_data_range[1],
                               len(sessions_to_recalc) + len(new_periods))
```

### Session Recalculation Impact

**Important:** When PoC/TO/RPP values change for a session:
- **POI events** for that session become invalid (need recalculation)
- **Swings** linked to those POI events might need re-linking

**Solution:** Mark dependent data for recalculation:

```python
def recalculate_session_ranges(session):
    old_poc = session['poc']
    old_rpp = session['rpp']
    old_to = session['true_open']

    # Recalculate with new data
    new_ranges = calculate_ranges(session)

    # Check if ranges changed
    if (new_ranges['poc'] != old_poc or
        new_ranges['rpp'] != old_rpp or
        new_ranges['true_open'] != old_to):

        # Update session
        update_session_ranges(session['id'], new_ranges)

        # Mark POI events for recalculation
        mark_poi_events_for_recalc(session['id'])

        return True  # Changed

    return False  # No change
```

---

## COMPONENT 5: INCREMENTAL POI EVENT PROCESSING

### Modified process_poi_events.py

**Strategy:**
1. Track last processed candle time per session
2. Only scan new candles
3. Continue state machine from current status

**Algorithm:**

```python
def process_poi_events_incremental(symbol, new_data_range):
    """
    Process POI events incrementally.

    Only scans new candles, continues from existing session status.
    """

    # Get sessions that need POI scanning
    sessions = cursor.execute("""
        SELECT id, to_time, poc, rpp, status,
               first_break_side, second_break_side
        FROM sessions
        WHERE symbol = ?
        AND status IN ('unbroken', 'break', 'return')
        AND to_time < ?
    """, (symbol, new_data_range[1])).fetchall()

    for session in sessions:
        # Get last POI check time for this session
        last_check = get_last_poi_check(session['id'])

        # Only scan candles after last check
        start_scan = max(last_check or session['to_time'], new_data_range[0])

        # Scan new candles
        new_candles = cursor.execute("""
            SELECT time, high, low, open, close
            FROM ohlc_4h
            WHERE symbol = ?
            AND time > ?
            AND time <= ?
            ORDER BY time ASC
        """, (symbol, start_scan, new_data_range[1])).fetchall()

        # Process touches
        for candle in new_candles:
            check_poi_touches(session, candle)

        # Update last check time
        update_last_poi_check(session['id'], new_data_range[1])
```

### Session Metadata Extension

Add to sessions table:

```sql
ALTER TABLE sessions ADD COLUMN last_poi_check_time TEXT;
```

---

## COMPONENT 6: INCREMENTAL SWING DETECTION

### Modified detect_swings.py

**Strategy:**
1. Find last detected swing timestamp
2. Maintain swing hierarchy context (need some lookback)
3. Detect new swings only
4. Link to nearest POI events

**Algorithm:**

```python
def detect_swings_incremental(symbol, new_data_range):
    """
    Detect swings incrementally.

    Maintains hierarchy by looking back at recent swings.
    """

    # Get last swing time
    last_swing = cursor.execute("""
        SELECT MAX(time) FROM swings WHERE symbol = ?
    """, (symbol,)).fetchone()[0]

    # Need lookback for Class 1 detection (3-bar pattern)
    # Start scanning from last_swing - 3 candles
    lookback_start = get_time_n_candles_back(last_swing, 3) if last_swing else None

    scan_start = max(lookback_start or '1900-01-01', new_data_range[0])

    # Get candle data
    candles = cursor.execute("""
        SELECT id, time, high, low
        FROM ohlc_4h
        WHERE symbol = ?
        AND time >= ?
        AND time <= ?
        ORDER BY time ASC
    """, (symbol, scan_start, new_data_range[1])).fetchall()

    # Detect Class 1 swings (3-bar pivots)
    class1_swings = detect_class1_pivots(candles)

    # Classify higher classes
    # Load recent existing swings for context
    recent_swings = load_recent_swings(symbol, scan_start)
    all_swings = recent_swings + class1_swings

    classified = classify_swing_hierarchy(all_swings)

    # Only insert NEW swings (time > last_swing)
    new_swings = [s for s in classified if s['time'] > (last_swing or '1900-01-01')]

    # Insert new swings
    for swing in new_swings:
        insert_swing(swing)
        link_to_nearest_poi(swing)

    # Update metadata
    update_processing_metadata(symbol, 'swing_detection', new_data_range[1], len(new_swings))
```

---

## COMPONENT 7: GAP HANDLING

### Strategy

As per your requirement: Gaps are OK (data access limitations), but when data exists it should flow seamlessly.

**Implementation:**

1. **Gap Detection:** Report gaps, don't error
2. **Session Calculation:** Skip sessions where required candles missing
3. **POI Processing:** Continue across gaps (sessions track indefinitely)
4. **Swing Detection:** Mark gaps, continue on other side

**Gap Reporting:**

```python
def report_data_gaps(symbol):
    """Report gaps in data for awareness."""
    gaps = detect_gaps(symbol, expected_interval_hours=4)

    if gaps:
        print(f"\n⚠️  Data Gaps Detected for {symbol}:")
        for gap in gaps:
            print(f"   {gap['gap_start']} → {gap['gap_end']} ({gap['duration']})")
        print(f"   Total gaps: {len(gaps)}")
    else:
        print(f"✅ No gaps detected for {symbol}")
```

---

## COMPONENT 8: MASTER PIPELINE SCRIPT

### New Script: process_incremental.py

**Purpose:** Orchestrate entire incremental pipeline

```python
#!/usr/bin/env python3
"""
Master incremental processing pipeline.

Runs all processing steps in order:
1. Load new CSV data
2. Detect affected sessions
3. Recalculate sessions
4. Process POI events
5. Detect swings
6. Validate and report

Usage:
    # Incremental mode (default)
    python process_incremental.py ES4H_01032026.csv ES

    # Force full recalculation
    python process_incremental.py ES4H_01032026.csv ES --force-full
"""

def process_incremental_pipeline(csv_file, symbol, force_full=False):
    print("=" * 80)
    print(f"INCREMENTAL PROCESSING PIPELINE - {symbol}")
    print("=" * 80)

    # Step 1: Load CSV data
    print("\n[1/6] Loading CSV data...")
    load_result = load_csv_incremental(csv_file, symbol, force_reload=force_full)
    print(f"   ✅ Loaded {load_result['new_rows']} new rows")

    if load_result['new_rows'] == 0 and not force_full:
        print("\n✅ No new data to process. Exiting.")
        return

    new_data_range = (load_result['date_range'][0], load_result['date_range'][1])

    # Step 2: Detect affected sessions
    print("\n[2/6] Detecting affected sessions...")
    affected = find_affected_sessions(symbol, *new_data_range)
    print(f"   ✅ Found {len(affected[0])} sessions to recalc")
    print(f"   ✅ Found {len(affected[1])} sessions to scan")
    print(f"   ✅ Found {len(affected[2])} new session periods")

    # Step 3: Recalculate sessions
    print("\n[3/6] Recalculating sessions...")
    session_result = calculate_sessions_incremental(symbol, new_data_range)
    print(f"   ✅ Recalculated {session_result['recalculated']} sessions")
    print(f"   ✅ Created {session_result['created']} new sessions")

    # Step 4: Process POI events
    print("\n[4/6] Processing POI events...")
    poi_result = process_poi_events_incremental(symbol, new_data_range)
    print(f"   ✅ Created {poi_result['new_events']} new POI events")
    print(f"   ✅ Updated {poi_result['updated_sessions']} session statuses")

    # Step 5: Detect swings
    print("\n[5/6] Detecting swings...")
    swing_result = detect_swings_incremental(symbol, new_data_range)
    print(f"   ✅ Detected {swing_result['new_swings']} new swings")

    # Step 6: Validate
    print("\n[6/6] Validating...")
    validation = validate_data(symbol)
    print(f"   ✅ Total sessions: {validation['total_sessions']}")
    print(f"   ✅ Total POI events: {validation['total_poi_events']}")
    print(f"   ✅ Total swings: {validation['total_swings']}")

    # Gap report
    report_data_gaps(symbol)

    print("\n" + "=" * 80)
    print("✅ INCREMENTAL PROCESSING COMPLETE")
    print("=" * 80)
```

---

## TESTING STRATEGY

### Test Scenarios

1. **Initial Load** - Empty database → Full data load
2. **Incremental Load** - Existing data + new CSV with overlap
3. **Gap Handling** - Load CSV with gaps, verify graceful handling
4. **Force Reload** - Correct historical data, verify updates cascade
5. **Session Boundaries** - New data creates new Yearly/Monthly sessions
6. **POI State Changes** - New data causes session status transitions
7. **Swing Hierarchy** - New swings maintain proper classification

### Validation Queries

```sql
-- Check processing metadata
SELECT * FROM processing_metadata ORDER BY updated_at DESC;

-- Check session recalculation times
SELECT session_name, last_recalc_time, needs_recalc
FROM sessions
WHERE symbol = 'ES'
ORDER BY session_start_time DESC;

-- Check POI event continuity
SELECT session_name, COUNT(*) as event_count, MAX(es_event_time) as last_event
FROM poi_events
WHERE symbol = 'ES'
GROUP BY session_name;

-- Check swing detection coverage
SELECT DATE(time) as date, COUNT(*) as swings
FROM swings
WHERE symbol = 'ES'
GROUP BY DATE(time)
ORDER BY date DESC;
```

---

## ROLLOUT PLAN

### Phase 1: Infrastructure (Week 1)
- [ ] Add processing_metadata table
- [ ] Add session tracking columns (needs_recalc, last_poi_check_time, last_recalc_time)
- [ ] Create metadata helper functions

### Phase 2: CSV Loader (Week 1)
- [ ] Enhance load_4h_csv.py with incremental mode
- [ ] Add --force-reload and --from-date options
- [ ] Add gap detection
- [ ] Test with sample data

### Phase 3: Session Processing (Week 2)
- [ ] Add affected session detection
- [ ] Modify calculate_yearly_monthly_sessions.py for incremental mode
- [ ] Test session recalculation
- [ ] Verify PoC/TO/RPP updates

### Phase 4: POI & Swings (Week 2)
- [ ] Modify process_poi_events.py for incremental mode
- [ ] Modify detect_swings.py for incremental mode
- [ ] Test POI event continuity
- [ ] Test swing hierarchy maintenance

### Phase 5: Master Pipeline (Week 3)
- [ ] Create process_incremental.py orchestration script
- [ ] End-to-end testing
- [ ] Performance benchmarking
- [ ] Documentation

### Phase 6: 1M Database (Week 4+)
- [ ] Replicate architecture for ohlc_data.db
- [ ] Scale testing with large datasets
- [ ] Production deployment

---

## EXPECTED PERFORMANCE

### Current System (Full Reprocessing)
- Load 1000 new 4H candles: ~2 minutes
- Calculate all sessions: ~5 minutes
- Process all POI events: ~8 minutes
- Detect all swings: ~10 minutes
- **Total: ~25 minutes**

### Incremental System (Optimized)
- Load 1000 new 4H candles: ~5 seconds (skip existing)
- Calculate affected sessions (~5): ~10 seconds
- Process POI for active sessions (~20): ~30 seconds
- Detect new swings: ~1 minute
- **Total: ~2 minutes (12.5x faster)**

### For 1M Database (Projected)
- Current: Would take **hours** for daily updates
- Incremental: **Under 5 minutes** for daily updates

---

## NEXT STEPS

1. **Review this design** - Discuss any concerns or changes needed
2. **Approve architecture** - Confirm this approach meets your needs
3. **Begin implementation** - Start with Phase 1 (Infrastructure)
4. **Iterative testing** - Test each component before moving to next
5. **Documentation updates** - Update progress.md as we build

---

**Questions for Discussion:**

1. Does this architecture cover all your requirements?
2. Any specific edge cases we should account for?
3. Priority on timeline - aggressive (2 weeks) or thorough (4 weeks)?
4. Should we implement for 4H first, validate, then replicate for 1M?

---

**Status:** 📋 DESIGN COMPLETE - AWAITING APPROVAL
