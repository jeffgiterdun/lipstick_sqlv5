# Architecture Overview

**Version:** 5.0
**Date:** November 28, 2025
**Purpose:** Hindsight analysis system for ES/NQ futures POI methodology with indefinite session tracking, echo chamber analysis, and swing detection

---

## System Overview

The Lipstick Analytical Tool V5 is a database system that tracks algorithmic price behavior through time-segmented sessions (Major, Minor, Weekly, Monthly), calculates ranges (True Open, Point of Control, Range Projection Point), and monitors price interactions with these levels.

**Purpose:** Hindsight analysis only. Not for live trading.

**Assets:** ES (S&P 500 futures), NQ (Nasdaq futures)

**Database:** SQLite at `data/ohlc_data.db`

---

## Key V5 Changes from V4

### Removed
- ❌ `trading_day` constraint on sessions
- ❌ Quartile sessions (64 per day)
- ❌ Separate `time_groups` and `session_status` tables
- ❌ `context_snapshot` table

### Added
- ✅ Weekly sessions (indefinite tracking)
- ✅ Monthly sessions (indefinite tracking)
- ✅ Merged `sessions` table (ranges + status in one)
- ✅ Echo chamber built into `poi_events` (ES/NQ timing in single row)
- ✅ `swings` table with hierarchical classification (Class 1-4)
- ✅ Session context captured as JSON in swings
- ✅ `insights` table for research journal
- ✅ Minor sessions expire after 24 hours

### Database Size
- **V4:** 85 sessions per trading day (5 Major + 16 Minor + 64 Quartile)
- **V5:** 21 sessions per trading day (5 Major + 16 Minor) + Weekly + Monthly

---

## Data Structure Overview

### Existing Data: ohlc_1m Table

Pre-existing table containing 1-minute OHLC data:

```sql
ohlc_1m (
    symbol TEXT,
    time TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    UNIQUE(symbol, time)
)
```

**Time Format:** ISO 8601 with timezone: `2025-11-27T18:00:00-05:00`
- All timestamps in Eastern Time (New York)
- Timezone offset varies: `-04:00` (EDT) or `-05:00` (EST)
- For session comparisons, use local time only (ignore timezone offset)

**Symbols:** 'ES', 'NQ'

---

## Core Tables

V5 uses three core tables instead of the previous five-table structure:

### 1. sessions Table

**Purpose:** Single table for session ranges AND status tracking. Replaces both time_groups and session_status from V4.

**Key Features:**
- No trading_day constraint
- Sessions identified by (symbol, session_type, session_name, session_start_time)
- Indefinite tracking for Major/Weekly/Monthly
- 24-hour expiry for Minor sessions

**Contains:**
- Range values (TO, PoC, RPP)
- Status tracking (unbroken → break → return → resolved)
- Time boundaries and expiry timestamps

### 2. poi_events Table

**Purpose:** Record POI touches with echo chamber analysis built-in. ONE row per session POI event, captures BOTH ES and NQ timing and status.

**Key V5 Features:**
- Single row contains both ES and NQ event timing, enabling direct echo chamber analysis without post-processing
- Denormalized columns (trading_day, symbol, session_type, session_name) for easy direct SQL querying without joins

**Contains:**
- Trading day and session context (denormalized)
- ES and NQ event timestamps
- Echo chamber metrics (time_delta_seconds, leader)
- Event type (break, return, resolution)

### 3. swings Table

**Purpose:** Hierarchical fractal swing detection with POI linkage and session context.

**Contains:**
- Swing classifications (Class 1-4)
- Movement metrics (points/candles from prior swing)
- POI event linkage
- Session context snapshot (JSON)

---

## Processing Architecture

V5 processing happens in three distinct phases:

### Phase 1: Range Calculation
- Calculate ranges for all sessions (Major, Minor, Weekly, Monthly)
- Insert into `sessions` table with `status = 'unbroken'`
- Set `expires_at` for Minor sessions

### Phase 2: POI Event Detection
- Process all candles chronologically
- Detect touches, update session status, create/update poi_events
- Process ES and NQ simultaneously for echo chamber analysis

### Phase 3: Swing Detection
- After POI events complete, detect and classify swings
- Link swings to POI events
- Capture session context at each swing

---

## Session Tracking Model

### Session Types and Duration

| Session Type | Count | Tracking Duration | Expiry |
|--------------|-------|-------------------|--------|
| Yearly | 1 per year | Indefinite | Never (expires_at = NULL) |
| Monthly | 1 per month | Indefinite | Never (expires_at = NULL) |
| Weekly | 1 per week | Indefinite | Never (expires_at = NULL) |
| Major | 5 per day | Indefinite | Never (expires_at = NULL) |
| Minor | 16 per day | 24 hours from TO | expires_at = to_time + 24h |

### Active Session Criteria

A session is "active" for POI processing when:
1. Session TO time has been reached (range is defined)
2. Session has not reached 'resolved' status
3. Session has not expired (for Minor sessions only)

**Implication:** At any given moment, there may be 10-20+ active sessions being tracked simultaneously across different timeframes.

---

## State Machine

Sessions progress through states based on price interaction with range levels:

```
unbroken → break → return → resolved
```

**Transitions:**
- **unbroken → break**: Touch PoC or RPP
- **break → return**: Touch TO after first break
- **return → resolved**: Touch TO after second break (can be same or opposite side)

**Resolution Types:**
- **Single Sided:** Both breaks on same side (PoC→PoC or RPP→RPP)
- **Double Sided:** Breaks on opposite sides (PoC→RPP or RPP→PoC)

---

## Echo Chamber Architecture

### Built-In Echo Chamber

Unlike V4, which required post-processing to analyze ES/NQ divergences, V5 captures echo chamber data directly in the `poi_events` table:

**Single Row Captures:**
- `es_event_time`: When ES touched the level
- `nq_event_time`: When NQ touched the level
- `time_delta_seconds`: Time difference
- `leader`: Which instrument touched first ('ES', 'NQ', or 'simultaneous')

**Benefits:**
- No post-processing required
- Direct querying of divergences
- Real-time echo chamber analysis capability

---

## Swing Detection Architecture

### Hierarchical Classification

Swings are classified in a multi-pass process:

1. **Pass 1:** Detect all Class 1 swings (3-bar pivots)
2. **Pass 2:** Promote Class 1 → Class 2 (has opposite Class 1 swings on both sides)
3. **Pass 3:** Promote Class 2 → Class 3 (has same Class 2 swings on both sides)
4. **Pass 4:** Promote Class 3 → Class 4 (has same Class 3 swings on both sides)

### Integration with POI Events

After classification, swings are linked to POI events based on:
- Time proximity (±5 minutes)
- Price proximity (±5 ticks)

This enables analysis of which POI events triggered significant swings.

### Session Context Capture

Each swing captures a JSON snapshot of all active sessions at that moment, enabling analysis like:
- "Show all Class 3 swings that occurred during Weekly return status"
- "Find swings that happened when London broke while Monthly was in break"

---

## Insights Table Architecture

### Purpose

Research journal for recording qualitative observations, confluence patterns, and setup discoveries.

**Key Features:**
- Full-text search (FTS5)
- Tagging system (confluence_factors, outcome_type)
- Suggested queries for pattern recognition
- Links to specific date ranges and sessions

**Integration:**
- Complements quantitative data in sessions/poi_events/swings
- Enables pattern discovery across historical data
- Supports manual annotation and learning

---

## Performance Considerations

### Indexing Strategy

Critical indexes for performance:
- `idx_sessions_active`: Sessions not resolved
- `idx_sessions_unexpired`: Sessions still active (not expired)
- `idx_poi_events_session`: Fast POI event lookups by session
- `idx_swings_major`: Filter for Class 3+ swings only

### Query Patterns

**Common Queries:**
1. "Get all active sessions for symbol X at time Y"
2. "Find POI events where ES/NQ had >5 minute divergence"
3. "Show Class 3+ swings linked to Weekly session breaks"
4. "Search insights for patterns involving London + Weekly confluence"

### Data Growth

**Expected Growth:**
- Sessions: ~21 per trading day per symbol = ~42 rows/day
- POI Events: Variable (depends on price action), ~50-200/day
- Swings: Variable, ~100-500/day across all classes
- Insights: Manual entries, ~1-10/week

**Annual Estimate (250 trading days):**
- Sessions: ~10,500 rows
- POI Events: ~12,500 - 50,000 rows
- Swings: ~25,000 - 125,000 rows
- Insights: ~50-500 rows

SQLite handles this volume easily with proper indexing.

---

## Implementation Sequence

1. **Database Setup** - Create schema with all tables and indexes
2. **Range Calculation** - Populate sessions table
3. **POI Event Processing** - Update sessions, populate poi_events
4. **Swing Detection** - Populate swings table with classifications
5. **Verification** - Validate data integrity and correctness

---

## Next Steps

For detailed information about specific components:

- [Database Schema](database-schema.md) - Complete table definitions and relationships
- [Calculation Logic](calculation-logic.md) - How ranges and touches are calculated
- [Processing Algorithm](processing-algorithm.md) - Step-by-step implementation guide
- [Edge Cases](edge-cases.md) - Handling missing data, gaps, and special scenarios
