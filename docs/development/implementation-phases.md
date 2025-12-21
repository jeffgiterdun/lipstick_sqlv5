# Implementation Phases

Step-by-step guide for building the Lipstick Analytical Tool V5.

---

## Overview

The implementation is divided into five phases:

1. **Database Setup** - Create schema
2. **Range Calculation** - Populate sessions table
3. **POI Event Processing** - Detect touches and update statuses
4. **Swing Detection** - Classify swings and link to POIs
5. **Verification** - Validate data integrity

---

## Phase 1: Database Setup

### Prerequisites

- SQLite installed
- Database directory exists: `data/`
- OHLC data loaded in `ohlc_1m` table

### Steps

```bash
# Create database schema
sqlite3 data/ohlc_data.db < schema_v5.sql

# Verify tables created
sqlite3 data/ohlc_data.db ".tables"
```

### Expected Output

```
insights          ohlc_1m           poi_events        sessions          swings
```

### Verification

```sql
-- Check table structures
.schema sessions
.schema poi_events
.schema swings
.schema insights

-- Verify indexes
.indexes sessions
.indexes poi_events
.indexes swings
```

### Success Criteria

- ✅ All 4 core tables exist
- ✅ All indexes created
- ✅ Foreign keys defined
- ✅ FTS5 table for insights created

---

## Phase 2: Range Calculation

### Overview

Calculate ranges for all sessions and insert into `sessions` table.

### Implementation Order

1. Major sessions (5 per day)
2. Minor sessions (16 per day)
3. Weekly sessions (1 per week)
4. Monthly sessions (1 per month)
5. Yearly sessions (1 per year)

### Script

```bash
python calculate_ranges_v5.py
```

### What This Does

**For Each Trading Day:**
- Calculate 5 Major session ranges
- Calculate 16 Minor session ranges
- Set `expires_at` for Minor sessions (TO + 24 hours)
- Set `expires_at = NULL` for Major sessions

**For Each Week:**
- Calculate 1 Weekly session range
- Set `expires_at = NULL`

**For Each Month:**
- Calculate 1 Monthly session range
- Set `expires_at = NULL`

**For Each Year:**
- Calculate 1 Yearly session range
- Set `expires_at = NULL`

### Expected Output

```
Processing ES...
  2025-11-01: 21 sessions calculated
  2025-11-04: 21 sessions calculated
  ...
  Weekly session 2025-11-03: calculated
  Monthly session 2025-11-01: calculated

Processing NQ...
  2025-11-01: 21 sessions calculated
  ...

Total sessions created: 10,500
```

### Verification Queries

```sql
-- Count sessions per symbol
SELECT symbol, session_type, COUNT(*) as count
FROM sessions
GROUP BY symbol, session_type;

-- Expected (for 250 trading days):
-- ES, Major: ~1,250 (5 per day)
-- ES, Minor: ~4,000 (16 per day)
-- ES, Weekly: ~52
-- ES, Monthly: ~12
-- ES, Yearly: 1
-- (Same for NQ)

-- Check for NULL ranges (indicates missing data)
SELECT COUNT(*) as null_ranges
FROM sessions
WHERE true_open IS NULL;

-- Check expires_at logic
SELECT session_type, COUNT(*) as count
FROM sessions
WHERE expires_at IS NULL
GROUP BY session_type;
-- Expected: Major, Weekly, Monthly, Yearly all have NULL expires_at

SELECT COUNT(*) as minor_with_expiry
FROM sessions
WHERE session_type = 'Minor'
AND expires_at IS NOT NULL;
-- Expected: All minor sessions have expires_at set
```

### Success Criteria

- ✅ 21 sessions per trading day per symbol
- ✅ Weekly sessions calculated correctly
- ✅ Monthly sessions calculated correctly
- ✅ Yearly sessions calculated correctly
- ✅ All sessions have `status = 'unbroken'`
- ✅ Minor sessions have `expires_at` set
- ✅ Major/Weekly/Monthly/Yearly have `expires_at = NULL`

---

## Phase 3: POI Event Processing

### Overview

Process all candles chronologically, detect POI touches, update session statuses, and populate `poi_events` table with Echo Chamber data.

### Script

```bash
python process_poi_events_v5.py
```

### What This Does

**For Each Candle (in chronological order):**
1. Get all active sessions for the candle's symbol
2. Detect touches of PoC, RPP, TO for each active session
3. Apply state machine logic
4. Update session status
5. Create or update POI events
6. Calculate Echo Chamber metrics (time delta, leader)

### Expected Output

```
Processing candles...
  2025-11-01 18:00: 0 active sessions
  2025-11-01 19:30: 1 active session (Asia TO reached)
  2025-11-01 19:45: Asia touched PoC -> status = 'break'
  2025-11-02 01:30: 2 active sessions (Asia, London)
  ...

POI Events created: 25,000
Sessions resolved: 8,500
Echo Chamber metrics calculated: 18,000
```

### Verification Queries

```sql
-- Count POI events by type
SELECT poi_type, event_type, COUNT(*) as count
FROM poi_events
GROUP BY poi_type, event_type;

-- Check Echo Chamber completeness
SELECT
  COUNT(*) as total_events,
  COUNT(es_event_time) as es_touches,
  COUNT(nq_event_time) as nq_touches,
  COUNT(time_delta_seconds) as complete_echo_chamber
FROM poi_events;

-- Check session status distribution
SELECT status, COUNT(*) as count
FROM sessions
GROUP BY status;

-- Find sessions with unusual status
SELECT * FROM sessions
WHERE status = 'return'
AND second_break_time IS NULL
LIMIT 10;
-- These are sessions waiting for second break

-- Check resolution types
SELECT resolution_type, COUNT(*) as count
FROM sessions
WHERE status = 'resolved'
GROUP BY resolution_type;
```

### Success Criteria

- ✅ POI events created for all touches
- ✅ Echo Chamber data populated (es_event_time, nq_event_time)
- ✅ Time delta and leader calculated
- ✅ Sessions progressed through states correctly
- ✅ Resolved sessions have resolution_type set
- ✅ No orphaned POI events (all link to valid sessions)

---

## Phase 4: Swing Detection

### Overview

Detect and classify swings, link to POI events, and capture session context.

### Script

```bash
python detect_swings_v5.py
```

### What This Does

**For Each Symbol (ES, NQ):**
1. **Pass 1:** Detect Class 1 swings (3-bar pivots)
2. **Pass 2:** Promote Class 1 → Class 2
3. **Pass 3:** Promote Class 2 → Class 3
4. **Pass 4:** Promote Class 3 → Class 4
5. **Pass 5:** Calculate movement metrics
6. **Pass 6:** Link to POI events
7. **Pass 7:** Capture session context snapshot

### Expected Output

```
Processing ES swings...
  Pass 1: 50,000 Class 1 swings detected
  Pass 2: 15,000 promoted to Class 2
  Pass 3: 5,000 promoted to Class 3
  Pass 4: 1,200 promoted to Class 4
  Pass 5: Movement metrics calculated
  Pass 6: 8,500 swings linked to POI events
  Pass 7: Session context captured

Processing NQ swings...
  ...

Total swings inserted: 100,000
```

### Verification Queries

```sql
-- Count swings by class
SELECT swing_class, COUNT(*) as count
FROM swings
GROUP BY swing_class;

-- Check POI linkage
SELECT
  COUNT(*) as total_swings,
  COUNT(nearest_poi_event_id) as linked_swings
FROM swings;

-- Find major swings (Class 3+)
SELECT * FROM swings
WHERE swing_class >= 3
ORDER BY swing_time DESC
LIMIT 10;

-- Check session context captured
SELECT COUNT(*) as swings_with_context
FROM swings
WHERE active_sessions_snapshot IS NOT NULL;
```

### Success Criteria

- ✅ All swings classified (Class 1-4)
- ✅ Movement metrics calculated
- ✅ POI linkage complete
- ✅ Session context JSON valid
- ✅ Class distribution makes sense (more Class 1, fewer Class 4)

---

## Phase 5: Verification

### Overview

Comprehensive validation of data integrity and correctness.

### Script

```bash
python verify_v5.py
```

### Verification Checklist

#### Sessions Table

```sql
-- Verify session count per day
SELECT
  DATE(session_start_time) as date,
  symbol,
  COUNT(*) as session_count
FROM sessions
WHERE session_type IN ('Major', 'Minor')
GROUP BY DATE(session_start_time), symbol
HAVING session_count != 21;
-- Should return empty (all days have 21 sessions)

-- Verify no orphaned sessions
SELECT COUNT(*) FROM sessions
WHERE id NOT IN (SELECT DISTINCT session_id FROM poi_events);
-- Some is OK (sessions with no touches)

-- Verify expiry logic
SELECT COUNT(*) FROM sessions
WHERE session_type = 'Minor'
AND (expires_at IS NULL OR expires_at <= to_time);
-- Should be 0
```

#### POI Events Table

```sql
-- Verify all poi_events link to valid sessions
SELECT COUNT(*) FROM poi_events
WHERE session_id NOT IN (SELECT id FROM sessions);
-- Should be 0

-- Check for invalid echo chamber data
SELECT COUNT(*) FROM poi_events
WHERE time_delta_seconds IS NOT NULL
AND (es_event_time IS NULL OR nq_event_time IS NULL);
-- Should be 0 (can't have delta without both times)

-- Verify leader logic
SELECT COUNT(*) FROM poi_events
WHERE leader IS NOT NULL
AND (es_event_time IS NULL OR nq_event_time IS NULL);
-- Should be 0 (can't have leader without both instruments)
```

#### Swings Table

```sql
-- Verify all linked POI events exist
SELECT COUNT(*) FROM swings
WHERE nearest_poi_event_id IS NOT NULL
AND nearest_poi_event_id NOT IN (SELECT id FROM poi_events);
-- Should be 0

-- Verify session context JSON valid
SELECT COUNT(*) FROM swings
WHERE active_sessions_snapshot NOT LIKE '{%}';
-- Should be 0 (all should be valid JSON objects)

-- Check class progression
SELECT swing_class, COUNT(*) as count
FROM swings
GROUP BY swing_class
ORDER BY swing_class;
-- Should show decreasing counts: Class 1 > Class 2 > Class 3 > Class 4
```

#### Cross-Table Validation

```sql
-- Verify status consistency
SELECT s.id, s.status, s.first_break_time, s.first_return_time
FROM sessions s
WHERE s.status = 'return'
AND (s.first_break_time IS NULL OR s.first_return_time IS NULL);
-- Should be 0 (return status requires both times set)

-- Verify resolution consistency
SELECT s.id, s.status, s.resolution_type
FROM sessions s
WHERE s.status = 'resolved'
AND s.resolution_type IS NULL;
-- Should be 0 (resolved requires resolution_type)
```

### Success Criteria

- ✅ No orphaned records
- ✅ All foreign keys valid
- ✅ Status transitions logical
- ✅ Echo chamber data complete where applicable
- ✅ Swing classifications make sense
- ✅ Session context JSON parseable
- ✅ No data integrity violations

---

## Rollback Procedures

### If Phase 2 Fails

```sql
-- Clear sessions table and restart
DELETE FROM sessions;
-- Re-run calculate_ranges_v5.py
```

### If Phase 3 Fails

```sql
-- Clear POI events and reset sessions
DELETE FROM poi_events;
UPDATE sessions SET
  status = 'unbroken',
  first_break_time = NULL,
  first_break_side = NULL,
  first_return_time = NULL,
  second_break_time = NULL,
  second_break_side = NULL,
  resolution_time = NULL,
  resolution_type = NULL;
-- Re-run process_poi_events_v5.py
```

### If Phase 4 Fails

```sql
-- Clear swings table and restart
DELETE FROM swings;
-- Re-run detect_swings_v5.py
```

---

## Performance Expectations

### Processing Times (approximate)

| Phase | Records | Duration | Rate |
|-------|---------|----------|------|
| Phase 2 | 10,000 sessions | 5-10 min | ~1,000/min |
| Phase 3 | 50,000 POI events | 30-60 min | ~1,000/min |
| Phase 4 | 100,000 swings | 20-40 min | ~2,500/min |

**Note:** Times vary based on hardware and dataset size.

---

## Next Steps

After successful implementation:

1. [Testing Guide](testing-guide.md) - Validate specific scenarios
2. [Technical Documentation](../technical/architecture-overview.md) - Understand system architecture
3. Begin analysis and insights collection

---

## Related Documentation

- [Processing Algorithm](../technical/processing-algorithm.md) - Detailed implementation
- [Database Schema](../technical/database-schema.md) - Table structures
- [Edge Cases](../technical/edge-cases.md) - Handle special scenarios
