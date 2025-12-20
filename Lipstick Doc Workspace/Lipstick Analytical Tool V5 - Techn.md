
# Lipstick Analytical Tool V5 - Technical Specification

**Version:** 5.0  
**Date:** November 28, 2025  
**Purpose:** Hindsight analysis system for ES/NQ futures POI methodology with indefinite session tracking, echo chamber analysis, and swing detection

---

## Table of Contents

1. [Overview](#1-overview)
2. [Existing Data Structure](#2-existing-data-structure)
3. [Database Schema](#3-database-schema)
4. [Trading Day Definition](#4-trading-day-definition)
5. [Session Definitions](#5-session-definitions)
6. [Range Calculation Logic](#6-range-calculation-logic)
7. [State Machine](#7-state-machine)
8. [Touch Detection Logic](#8-touch-detection-logic)
9. [Session Activity Rules](#9-session-activity-rules)
10. [Processing Algorithm](#10-processing-algorithm)
11. [Edge Cases and Missing Data](#11-edge-cases-and-missing-data)
12. [Implementation Phases](#12-implementation-phases)
13. [Insights Table](#13-insights-table)
14. [Summary and Checklist](#14-summary-and-checklist)

---

## 1. Overview

This document provides complete, unambiguous specifications for building the Lipstick Analytical Tool V5 database system. The system tracks algorithmic price behavior through time-segmented sessions (Major, Minor, Weekly, Monthly), calculates ranges (True Open, Point of Control, Range Projection Point), and monitors price interactions with these levels.

**Purpose:** Hindsight analysis only. Not for live trading.

**Assets:** ES (S&P 500 futures), NQ (Nasdaq futures)

**Database:** SQLite at `data/ohlc_data.db`

**Key V5 Changes from V4:**
- Sessions track indefinitely until resolved (no trading_day constraint)
- Weekly and Monthly sessions added
- Quartile sessions removed
- Echo chamber analysis built into poi_events (ES/NQ timing in single row)
- Swing detection added with hierarchical classification (Class 1-4)
- Merged time_groups + session_status into single sessions table
- Minor sessions expire after 24 hours from TO time

---

## 2. Existing Data Structure

### 2.1 ohlc_1m Table (Pre-existing)
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

## 3. Database Schema

V5 uses three core tables instead of the previous five-table structure.

### 3.1 sessions Table

**Purpose:** Single table for session ranges AND status tracking. Replaces both time_groups and session_status from V4.

**Key Change:** No trading_day constraint. Sessions identified by (symbol, session_type, session_name, session_start_time).
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    session_type TEXT NOT NULL,  -- 'Major', 'Minor', 'Weekly', 'Monthly'
    session_name TEXT NOT NULL,  -- 'Asia', 'London', 'm0900', 'Weekly', 'Monthly'
    
    -- Time boundaries
    session_start_time TEXT NOT NULL,  -- ISO timestamp when session begins
    to_time TEXT NOT NULL,  -- True Open time (when range is set)
    
    -- Range values
    true_open REAL,
    poc REAL,
    rpp REAL,
    
    -- Status tracking
    status TEXT NOT NULL,  -- 'unbroken', 'break', 'return', 'resolved'
    first_break_time TEXT,
    first_break_side TEXT,  -- 'PoC' or 'RPP'
    first_return_time TEXT,
    second_break_time TEXT,
    second_break_side TEXT,
    resolution_time TEXT,
    resolution_type TEXT,  -- 'single_sided' or 'double_sided'
    
    -- Expiry tracking (for Minor sessions)
    expires_at TEXT,  -- NULL for Major/Weekly/Monthly, ISO timestamp for Minor
    
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    UNIQUE(symbol, session_type, session_name, session_start_time)
);

CREATE INDEX idx_sessions_symbol_status ON sessions(symbol, status);
CREATE INDEX idx_sessions_active ON sessions(symbol, status) WHERE status != 'resolved';
CREATE INDEX idx_sessions_unexpired ON sessions(symbol, expires_at) WHERE expires_at IS NULL OR expires_at > datetime('now');
```

**Column Definitions:**

- `session_start_time`: ISO timestamp when the session begins (e.g., `2025-11-27T18:00:00-05:00`)
- `to_time`: ISO timestamp of the True Open candle (when range is calculated)
- `expires_at`: For Minor sessions only, set to TO time + 24 hours. NULL for Major/Weekly/Monthly
- `status`: Current state in the state machine
- All `*_time` columns: ISO timestamp format

**Session Tracking Duration:**
- Major: `expires_at = NULL` (tracks until resolved)
- Weekly: `expires_at = NULL` (tracks until resolved)
- Monthly: `expires_at = NULL` (tracks until resolved)
- Minor: `expires_at = to_time + 24 hours` (expires after 24 hours)

---

### 3.2 poi_events Table

**Purpose:** Record POI touches with echo chamber analysis built-in. ONE row per session POI event, captures BOTH ES and NQ timing and status.

**Key V5 Change:** Single row contains both ES and NQ event timing, enabling direct echo chamber analysis without post-processing.
```sql
CREATE TABLE poi_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,  -- FK to sessions table
    poi_type TEXT NOT NULL,  -- 'PoC', 'RPP', 'TO'
    event_type TEXT NOT NULL,  -- 'break', 'return', 'resolution'
    
    -- ES timing
    es_event_time TEXT,  -- NULL if ES hasn't touched yet
    
    -- NQ timing
    nq_event_time TEXT,  -- NULL if NQ hasn't touched yet
    
    -- Echo Chamber metrics (auto-calculated)
    time_delta_seconds INTEGER,  -- abs(es_time - nq_time), NULL if only one touched
    leader TEXT,  -- 'ES', 'NQ', or 'simultaneous' (< 60 sec)
    
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_poi_events_session ON poi_events(session_id);
CREATE INDEX idx_poi_events_es_time ON poi_events(es_event_time);
CREATE INDEX idx_poi_events_nq_time ON poi_events(nq_event_time);
```

**Column Definitions:**

- `session_id`: Foreign key to the sessions table (which session this POI event belongs to)
- `poi_type`: Which level was touched ('PoC', 'RPP', or 'TO')
- `event_type`: What type of event this represents ('break', 'return', or 'resolution')
- `es_event_time`: ISO timestamp when ES touched this level (NULL if not touched yet)
- `nq_event_time`: ISO timestamp when NQ touched this level (NULL if not touched yet)
- `time_delta_seconds`: Time difference between ES and NQ touches in seconds
- `leader`: Which instrument touched first ('ES', 'NQ', or 'simultaneous' if within 60 seconds)

**POI Event Creation Logic:**

When processing a candle that touches a POI level:

1. Check if `poi_events` row exists for this `(session_id, poi_type, event_type)`
2. If NO row exists:
   - INSERT new row with appropriate `*_event_time`
   - Leave other instrument's fields as NULL
   - `time_delta_seconds`, `leader` remain NULL
3. If row EXISTS with one instrument already recorded:
   - UPDATE row with second instrument's `*_event_time`
   - Calculate `time_delta_seconds = abs(es_event_time - nq_event_time)`
   - Set `leader` based on which timestamp is earlier

**Example Flow:**
```python
# Candle 1 (09:15): ES breaks London PoC
INSERT INTO poi_events (
    session_id, poi_type, event_type, 
    es_event_time
) VALUES (
    123, 'PoC', 'break', 
    '2025-11-27T09:15:00-05:00'
)

# Candle 2 (09:18): NQ breaks London PoC
UPDATE poi_events 
SET 
    nq_event_time = '2025-11-27T09:18:00-05:00',
    time_delta_seconds = 180,
    leader = 'ES'
WHERE session_id = 123 
AND poi_type = 'PoC' 
AND event_type = 'break'
```

---

### 3.3 swings Table

**Purpose:** Hierarchical fractal swing detection with POI linkage and session context.
```sql
CREATE TABLE swings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    swing_time TEXT NOT NULL,
    swing_price REAL NOT NULL,
    swing_type TEXT NOT NULL,  -- 'high' or 'low'
    swing_class INTEGER NOT NULL,  -- 1, 2, 3, or 4 (final classification)
    
    -- Movement context
    prior_opposite_swing_id INTEGER,  -- Previous swing of opposite type
    points_from_prior REAL,
    candles_from_prior INTEGER,
    
    -- POI linkage
    nearest_poi_event_id INTEGER,  -- Closest POI event in time/price
    
    -- Session context snapshot (JSON)
    active_sessions_snapshot TEXT,  -- JSON: session statuses at this moment
    
    created_at TEXT NOT NULL,
    FOREIGN KEY (prior_opposite_swing_id) REFERENCES swings(id),
    FOREIGN KEY (nearest_poi_event_id) REFERENCES poi_events(id)
);

CREATE INDEX idx_swings_symbol_time ON swings(symbol, swing_time);
CREATE INDEX idx_swings_class ON swings(swing_class);
CREATE INDEX idx_swings_major ON swings(swing_class) WHERE swing_class >= 3;
CREATE INDEX idx_swings_poi_link ON swings(nearest_poi_event_id);
```

**Column Definitions:**

- `swing_time`: ISO timestamp when the swing occurred
- `swing_price`: Price level of the swing (high or low)
- `swing_type`: 'high' or 'low'
- `swing_class`: Final classification (1, 2, 3, or 4)
- `prior_opposite_swing_id`: Link to the previous swing of opposite type (used to measure moves)
- `points_from_prior`: Distance in points from prior opposite swing
- `candles_from_prior`: Number of candles between this swing and prior opposite swing
- `nearest_poi_event_id`: Link to the closest POI event (if any) that may have triggered this swing
- `active_sessions_snapshot`: JSON string containing session statuses at the moment of this swing

**Session Context Snapshot Format (JSON):**
```json
{
  "major_sessions": {
    "Asia": {"status": "resolved", "resolution_time": "2025-11-26T08:45:00-05:00"},
    "London": {"status": "break", "first_break_time": "2025-11-26T09:15:00-05:00"},
    "NY_AM": {"status": "unbroken"},
    "NY_PM": null,
    "Afternoon": null
  },
  "weekly_session": {
    "status": "return",
    "first_break_time": "2025-11-25T14:30:00-05:00",
    "first_return_time": "2025-11-26T07:15:00-05:00"
  },
  "monthly_session": {
    "status": "break",
    "first_break_time": "2025-11-20T11:00:00-05:00"
  },
  "current_minor": {
    "session": "m0900",
    "status": "break"
  }
}
```

**Swing Detection Processing:**

Swings are detected and classified AFTER poi_events processing is complete. The detection happens in multiple passes:

1. **Pass 1:** Detect all Class 1 swings (3-bar pivots)
2. **Pass 2:** Promote Class 1 → Class 2 (has opposite Class 1 swings on both sides)
3. **Pass 3:** Promote Class 2 → Class 3 (has same Class 2 swings on both sides)
4. **Pass 4:** Promote Class 3 → Class 4 (has same Class 3 swings on both sides)
5. **Pass 5:** Calculate movement metrics (points/candles from prior opposite swing)
6. **Pass 6:** Link to nearest POI events
7. **Pass 7:** Capture session context snapshot at each swing time

---

## 4. Trading Day Definition

**Trading Day Boundaries:** 18:00 → 16:59 (next calendar day)

**Important V5 Note:** While we still use "trading day" as a conceptual boundary for organizing price action, sessions are NO LONGER constrained by trading_day in the database. Major, Weekly, and Monthly sessions track indefinitely across multiple trading days until resolved.

### 4.1 Trading Day Calculation (for reference only)
```
If candle time is 00:00:00 to 16:59:59:
    trading_day = candle_calendar_date

If candle time is 18:00:00 to 23:59:59:
    trading_day = candle_calendar_date + 1 day
```

**Example:**
- Candle: 2025-11-27T18:00:00 → trading_day = 2025-11-28
- Candle: 2025-11-28T09:00:00 → trading_day = 2025-11-28
- Candle: 2025-11-28T18:00:00 → trading_day = 2025-11-29

---

## 5. Session Definitions

### 5.1 Major Sessions (5 per trading day)

Major sessions track indefinitely until reaching "resolved" status.

| Session | Start | End | PoC Start Reference | PoC Start Time | TO Time | TO Reference |
|---------|-------|-----|---------------------|----------------|---------|--------------|
| Asia | 18:00 | 23:59 | Previous day 16:59 close | N/A | 19:30 | open |
| London | 00:00 | 05:59 | 00:00 open | 00:00 | 01:30 | open |
| NY_AM | 06:00 | 11:59 | 06:00 open | 06:00 | 07:30 | open |
| NY_PM | 12:00 | 16:59 | 12:00 open | 12:00 | 13:30 | open |
| Afternoon | 13:30 | 16:59 | 13:30 open | 13:30 | 15:00 | open |

**session_start_time Examples:**
- Asia starting on Nov 27: `2025-11-27T18:00:00-05:00`
- London starting on Nov 28: `2025-11-28T00:00:00-05:00`
- NY_AM starting on Nov 28: `2025-11-28T06:00:00-05:00`

**expires_at:** NULL (tracks until resolved)

---

### 5.2 Minor Sessions (16 per trading day)

Minor sessions track for 24 hours from TO time, then expire regardless of status.

| Session | Start | End | PoC Start Time | TO Time | TO Reference |
|---------|-------|-----|----------------|---------|--------------|
| m1800 | 18:00 | 19:29 | Prev day close | 18:22 | close |
| m1930 | 19:30 | 20:59 | 19:30 | 19:52 | close |
| m2100 | 21:00 | 22:29 | 21:00 | 21:22 | close |
| m2230 | 22:30 | 23:59 | 22:30 | 22:52 | close |
| m0000 | 00:00 | 01:29 | 00:00 | 00:22 | close |
| m0130 | 01:30 | 02:59 | 01:30 | 01:52 | close |
| m0300 | 03:00 | 04:29 | 03:00 | 03:22 | close |
| m0430 | 04:30 | 05:59 | 04:30 | 04:52 | close |
| m0600 | 06:00 | 07:29 | 06:00 | 06:22 | close |
| m0730 | 07:30 | 08:59 | 07:30 | 07:52 | close |
| m0900 | 09:00 | 10:29 | 09:00 | 09:22 | close |
| m1030 | 10:30 | 11:59 | 10:30 | 10:52 | close |
| m1200 | 12:00 | 13:29 | 12:00 | 12:22 | close |
| m1330 | 13:30 | 14:59 | 13:30 | 13:52 | close |
| m1500 | 15:00 | 16:29 | 15:00 | 15:22 | close |
| m1630 | 16:30 | 16:59 | 16:30 | 16:52 | close |

**Note:** m1630 is only 30 minutes duration (not the standard 90 minutes).

**session_start_time Example:**
- m0900 starting on Nov 28: `2025-11-28T09:00:00-05:00`

**expires_at Calculation:**
- TO time + 24 hours
- Example: m0900 TO at `2025-11-28T09:22:00-05:00` → expires_at = `2025-11-29T09:22:00-05:00`

---

### 5.3 Weekly Session

One Weekly session is active at any given time. Tracks indefinitely until resolved.

**Weekly Session Calculation:**

- **session_start_time:** Every Sunday at 18:00 (the first candle of the Monday trading day)
- **PoC Tracking Begins:** Sunday 18:00
- **TO Time:** Monday 18:00 (the first candle of the Tuesday trading day)
- **TO Reference:** open
- **expires_at:** NULL (tracks until resolved)

**Example:**
- Week starting Sunday Nov 23, 2025:
  - `session_start_time = '2025-11-23T18:00:00-05:00'`
  - `to_time = '2025-11-24T18:00:00-05:00'`
  - PoC calculated from Sunday 18:00 until Monday 18:00 (exclusive)

**PoC Calculation Window:**
- Start: Sunday 18:00:00
- End: Monday 17:59:59 (last candle before Monday 18:00)
- TO: Monday 18:00 open

---

### 5.4 Monthly Session

One Monthly session is active at any given time. Tracks indefinitely until resolved.

**Monthly Session Calculation:**

- **session_start_time:** First full trading day of the month (see logic below)
- **PoC Tracking Begins:** First full trading day at 18:00
- **TO Time:** Sunday 18:00 that begins the second full week of the month
- **TO Reference:** open
- **expires_at:** NULL (tracks until resolved)

**First Full Trading Day Logic:**

The key rule: **We need Monday's trading session (Sunday 18:00) to be included.**

- If 1st = **Monday**: First trading day is **Sunday** (the day before) at 18:00 ✓
- If 1st = **Tuesday**: First trading day is **Monday** (the day before) at 18:00 ✓
- If 1st = **Wednesday**: First trading day is **Tuesday** (the day before) at 18:00 ✓
- If 1st = **Thursday**: First trading day is **Wednesday** (the day before) at 18:00 ✓
- If 1st = **Friday**: First trading day is **Thursday** (the day before) at 18:00 ✓
- If 1st = **Saturday**: First trading day is **Sunday** (the next day) at 18:00 ✓
- If 1st = **Sunday**: First trading day is **Sunday** (same day) at 18:00 ✓

**Second Full Week Logic:**

We need at least one complete week (Sunday 18:00 through Saturday 16:59) before setting the TO.

A "full week" must include Monday's trading session (Sunday 18:00).

**Examples:**

**November 2025 (1st = Saturday):**
- 1st falls on Saturday Nov 1 (no trading)
- First trading day: **Sunday Nov 2 at 18:00**
- Week 1 (full): Sun Nov 2 - Sat Nov 8 ✓
- Week 2 starts: **Sun Nov 9 at 18:00** 
- **TO = Monday Nov 9 18:00 open** (which is `2025-11-09T18:00:00-05:00`)

**December 2025 (1st = Monday):**
- 1st falls on Monday Dec 1
- First trading day: **Sunday Nov 30 at 18:00** (includes Monday)
- Week 1 (full): Sun Nov 30 - Sat Dec 6 ✓
- Week 2 starts: **Sun Dec 7 at 18:00**
- **TO = Monday Dec 7 18:00 open** (which is `2025-12-07T18:00:00-05:00`)

**January 2026 (1st = Thursday):**
- 1st falls on Thursday Jan 1
- First trading day: **Wednesday Dec 31 at 18:00** (includes Thursday)
- Week 1 (partial): Wed Dec 31 - Sat Jan 3 ✗ (no Monday in this week)
- Week 2 (full): Sun Jan 4 - Sat Jan 10 ✓ (first full week)
- Week 3 starts: **Sun Jan 11 at 18:00**
- **TO = Monday Jan 11 18:00 open** (which is `2026-01-11T18:00:00-05:00`)

**session_start_time and to_time Examples:**
- November 2025:
  - `session_start_time = '2025-11-02T18:00:00-05:00'`
  - `to_time = '2025-11-09T18:00:00-05:00'`
- December 2025:
  - `session_start_time = '2025-11-30T18:00:00-05:00'`
  - `to_time = '2025-12-07T18:00:00-05:00'`

---

## 6. Range Calculation Logic

### 6.1 True Open (TO)

**Definition:** The reference price at a specific time.

**Calculation:**
```
IF session requires 'open' price:
    TO = open price of candle at TO time
    
IF session requires 'close' price:
    TO = close price of candle at TO time
    
IF session uses previous day close:
    TO = close price of previous trading day's 16:59 candle
```

**Examples:**

**Major Session (uses 'open'):**
- London TO time: 01:30
- TO = open price of the 01:30 candle

**Minor Session (uses 'close'):**
- m0900 TO time: 09:22
- TO = close price of the 09:22 candle

**Asia Session (uses previous day close):**
- Asia starts: 2025-11-27T18:00:00
- TO = close price of 2025-11-26T16:59:00 candle

**Weekly Session (uses 'open'):**
- Weekly TO time: Monday 18:00
- TO = open price of Monday 18:00 candle

**Monthly Session (uses 'open'):**
- Monthly TO time: Second full week Sunday 18:00
- TO = open price of that Sunday 18:00 candle

---

### 6.2 Point of Control (PoC)

**Definition:** The price level with highest variance from TO during the calculation window.

**Calculation Window:** From PoC Start Time until TO Time (exclusive of TO candle)

**Algorithm:**
1. Track `highest_high` and `lowest_low` across all candles in window
2. Calculate: `variance_high = abs(highest_high - TO)`
3. Calculate: `variance_low = abs(lowest_low - TO)`
4. If `variance_high > variance_low`: `PoC = highest_high`
5. If `variance_low >= variance_high`: `PoC = lowest_low`

**Formula:**
```python
PoC = highest_high if abs(highest_high - TO) > abs(lowest_low - TO) else lowest_low
```

**Special Case - Previous Day Close Reference:**

For sessions that start with previous day close (Asia, m1800):
- Include the previous day close value when calculating highest_high/lowest_low
- This ensures the starting reference point is part of the range calculation

**Example:**

**London Session:**
- PoC Start: 00:00
- TO Time: 01:30
- Window: All candles from 00:00:00 to 01:29:59

Suppose during this window:
- highest_high = 5950.00
- lowest_low = 5920.00
- TO (01:30 open) = 5935.00

Calculate variance:
- variance_high = abs(5950.00 - 5935.00) = 15.00
- variance_low = abs(5920.00 - 5935.00) = 15.00

Since variance_low >= variance_high:
- **PoC = 5920.00** (the low side)

---

### 6.3 Range Projection Point (RPP)

**Definition:** Mirror projection of PoC distance on opposite side of TO.

**Formula:**
```python
RPP = 2 * TO - PoC
```

**Verification:** Distance from PoC to TO equals distance from TO to RPP.

**Example:**

Continuing London example:
- PoC = 5920.00
- TO = 5935.00
- RPP = 2 * 5935.00 - 5920.00 = **5950.00**

Verify:
- Distance PoC→TO: |5920.00 - 5935.00| = 15.00
- Distance TO→RPP: |5935.00 - 5950.00| = 15.00 ✓

The range is symmetrical: PoC (5920.00) ← TO (5935.00) → RPP (5950.00)

---

### 6.4 Missing Data Handling

**Rule:** If any candles are missing in the PoC calculation window OR the TO candle is missing:
- Set: `true_open = NULL`, `poc = NULL`, `rpp = NULL`
- Insert session record with NULL values
- Set: `status = 'unbroken'` (still create the session record)
- Do NOT process POI events for this session

**Rationale:** Cannot calculate range without complete data. Session exists in database but is non-functional.

---

### 6.5 Weekend Handling for Previous Day Close

**Issue:** When calculating Asia or m1800 sessions on Monday, the "previous day" is Sunday, which has no trading.

**Solution:** Skip back to Friday's 16:59 close.

**Algorithm:**
```python
def get_prev_day_close(trading_day):
    """
    Get the close price of previous trading day's 16:59 candle.
    Skips weekends.
    """
    prev_day = trading_day - 1 day
    
    # If prev_day is Sunday (weekday=6), go back to Friday
    if prev_day.weekday() == 6:  # Sunday
        prev_day = prev_day - 2 days  # Friday
    
    # If prev_day is Saturday (weekday=5), go back to Friday
    elif prev_day.weekday() == 5:  # Saturday
        prev_day = prev_day - 1 day  # Friday
    
    # Query for 16:59 candle on prev_day
    return query_close_price(prev_day, '16:59:00')
```

**Example:**
- Monday Nov 24 Asia session needs previous day close
- Previous calendar day: Sunday Nov 23 (no trading)
- Skip back to: Friday Nov 21 at 16:59 ✓

---

## 7. State Machine

### 7.1 States and Transitions

| Current State | Event | Records | Next State |
|---------------|-------|---------|------------|
| unbroken | Touch PoC or RPP | first_break_time, first_break_side | break |
| break | Touch PoC or RPP (repeat) | Nothing (ignore) | break |
| break | Touch TO | first_return_time | return |
| return | Touch PoC or RPP | second_break_time, second_break_side | return |
| return | Touch PoC or RPP (repeat) | Nothing (ignore) | return |
| return | Touch TO | resolution_time, resolution_type | resolved |
| resolved | Any touch | Nothing (session complete) | resolved |

### 7.2 Resolution Type Logic
```python
if first_break_side == second_break_side:
    resolution_type = 'single_sided'
else:
    resolution_type = 'double_sided'
```

**Single Sided:** Same side broken twice (PoC→PoC or RPP→RPP)
**Double Sided:** Both sides broken (PoC→RPP or RPP→PoC)

### 7.3 Reset Logic

After recording `first_return_time`, the break tracker resets:
- Next PoC/RPP touch becomes `second_break`
- Intermediate breaks between first return and second break are ignored

---

## 8. Touch Detection Logic

### 8.1 Touch Definition

A price level is "touched" when it falls within the candle's high-low range.

**Formulas:**
```python
PoC_touched = (candle_low <= PoC <= candle_high)
RPP_touched = (candle_low <= RPP <= candle_high)
TO_touched = (candle_low <= TO <= candle_high)
```

### 8.2 Multi-Level Touch Handling

If one candle touches multiple levels, record all events with same `event_time`.

**Example:** Candle with high=5950, low=5920, PoC=5945, TO=5935, RPP=5925
- Record: PoC break event
- Record: TO return event  
- Record: RPP break event
- All with same timestamp

---

## 9. Session Activity Rules

**Critical V5 Change:** Sessions track indefinitely (Major/Weekly/Monthly) or expire after 24 hours (Minor). No trading_day constraint.

### 9.1 Session Activity Windows

**Major Sessions:**
- **Range Calculation:** During session time window only (e.g., London: 00:00-05:59)
- **Touch Detection:** Active from TO time indefinitely until status = 'resolved'
- **Expiry:** Never expires (`expires_at = NULL`)

**Minor Sessions:**
- **Range Calculation:** During session time window only (e.g., m0900: 09:00-10:29)
- **Touch Detection:** Active from TO time for 24 hours
- **Expiry:** `expires_at = to_time + 24 hours`

**Weekly Sessions:**
- **Range Calculation:** Sunday 18:00 through Monday 17:59
- **Touch Detection:** Active from TO time (Monday 18:00) indefinitely until status = 'resolved'
- **Expiry:** Never expires (`expires_at = NULL`)

**Monthly Sessions:**
- **Range Calculation:** First full trading day through second full week Sunday 17:59
- **Touch Detection:** Active from TO time (second full week Sunday 18:00) indefinitely until status = 'resolved'
- **Expiry:** Never expires (`expires_at = NULL`)

---

### 9.2 When to Process POI Events for a Session

**For each candle, check if a session is "active" before detecting touches:**
```python
def is_session_active(session, current_candle_time):
    """
    Determine if a session should be checked for POI touches.
    
    Returns True if:
    1. Session TO time has been reached (range is defined)
    2. Session has not reached 'resolved' status
    3. Session has not expired (for Minor sessions)
    """
    # Check if TO time reached
    if current_candle_time < session.to_time:
        return False  # Range not yet defined
    
    # Check if resolved
    if session.status == 'resolved':
        return False  # Session complete
    
    # Check if expired (Minor sessions only)
    if session.expires_at is not None:
        if current_candle_time > session.expires_at:
            return False  # Minor session expired
    
    return True
```

**Example Timeline for Minor Session:**
```
m0900 on Nov 27, 2025:
- session_start_time: 2025-11-27T09:00:00-05:00
- to_time: 2025-11-27T09:22:00-05:00
- expires_at: 2025-11-28T09:22:00-05:00

Active window:
- 2025-11-27 09:22:00 → 2025-11-28 09:22:00 (24 hours)

Status at expiry:
- If status = 'resolved' before expiry → session complete
- If status = 'unbroken', 'break', or 'return' at expiry → session expires incomplete
```

---

### 9.3 Active Sessions Query

When processing a candle, determine which sessions are active:
```sql
SELECT * FROM sessions
WHERE symbol = ?
AND to_time <= ?  -- Range is defined
AND status != 'resolved'  -- Not complete
AND (expires_at IS NULL OR expires_at > ?)  -- Not expired
```

**Parameters:**
- `symbol`: 'ES' or 'NQ'
- First `?`: current candle time
- Second `?`: current candle time

---

### 9.4 Multiple Active Sessions Example

**Scenario:** Processing candle at 2025-11-27T14:30:00-05:00

**Active sessions might include:**
- **Asia** (started Nov 27 18:00, status='break', not resolved)
- **London** (started Nov 27 00:00, status='return', not resolved)
- **NY_AM** (started Nov 27 06:00, status='break', not resolved)
- **NY_PM** (started Nov 27 12:00, status='unbroken', just started)
- **Weekly** (started Nov 23 18:00, status='return', not resolved)
- **Monthly** (started Nov 2 18:00, status='break', not resolved)
- **m1330** (started Nov 27 13:30, status='break', expires Nov 28 13:52)
- **m1200** (started Nov 27 12:00, status='resolved', SKIP - resolved)
- **m1030** (started Nov 27 10:30, expires Nov 28 10:52, status='return')
- **m0900** (started Nov 26 09:00, expires Nov 27 09:22, SKIP - expired)

**Result:** 9 active sessions to check for touches on this candle

---

### 9.5 Indefinite Tracking Implications

**Key Insight:** Major/Weekly/Monthly sessions can remain active across many days or weeks.

**Example - Persistent Weekly Session:**
```
Week starting Nov 23:
- TO set: Monday Nov 24 18:00
- First break: Tuesday Nov 25 14:30 (PoC)
- Waiting for return...
- [Days pass, no TO touch]
- Still active on Friday Nov 28
- Still active on Monday Dec 1
- Finally returns: Wednesday Dec 3 09:15
- Status: 'return'
- Still active, waiting for second break...
```

This Weekly session could track for **weeks** until finally resolving.

**Database Impact:**
- Sessions table grows continuously (never deletes old sessions)
- Active sessions query becomes more important (could have 20+ active sessions at once)
- Index on `(symbol, status, expires_at)` critical for performance

---

### 9.6 Session Cleanup / Archival

**Question:** Do we ever mark old unresolved sessions as "abandoned"?

**Options:**
1. **Never** - let them stay active indefinitely (purist approach)
2. **After N days** - mark as 'abandoned' if not resolved within reasonable timeframe
3. **Manual** - you decide when to archive old sessions

**Recommendation for V5:** Keep them active indefinitely. You can always add cleanup logic later if database grows too large.

---

## 10. Processing Algorithm

### 10.1 Overview

V5 processing happens in three distinct phases:

**Phase 1: Range Calculation**
- Calculate ranges for all sessions (Major, Minor, Weekly, Monthly)
- Insert into `sessions` table with `status = 'unbroken'`
- Set `expires_at` for Minor sessions

**Phase 2: POI Event Detection**
- Process all candles chronologically
- Detect touches, update session status, create/update poi_events
- Process ES and NQ simultaneously for echo chamber analysis

**Phase 3: Swing Detection**
- After POI events complete, detect and classify swings
- Link swings to POI events
- Capture session context at each swing

---

### 10.2 Phase 1: Range Calculation

**Process each symbol (ES, NQ) independently.**

#### 10.2.1 Daily Session Calculation

For each calendar day in the dataset:
```python
def calculate_daily_sessions(symbol, calendar_date):
    """
    Calculate all Major and Minor sessions for a given calendar day.
    
    Args:
        symbol: 'ES' or 'NQ'
        calendar_date: Date in YYYY-MM-DD format
    
    Creates:
        5 Major sessions (Asia, London, NY_AM, NY_PM, Afternoon)
        16 Minor sessions (m1800 through m1630)
    """
    
    # Major Sessions
    for major_session in ['Asia', 'London', 'NY_AM', 'NY_PM', 'Afternoon']:
        session_start_time = get_session_start_time(major_session, calendar_date)
        to_time = get_to_time(major_session, calendar_date)
        
        # Calculate range
        ranges = calculate_session_ranges(
            symbol, 
            major_session, 
            session_start_time,
            to_time
        )
        
        # Insert into sessions table
        insert_session(
            symbol=symbol,
            session_type='Major',
            session_name=major_session,
            session_start_time=session_start_time,
            to_time=to_time,
            true_open=ranges['true_open'],
            poc=ranges['poc'],
            rpp=ranges['rpp'],
            status='unbroken',
            expires_at=None  # Never expires
        )
    
    # Minor Sessions
    for minor_session in ['m1800', 'm1930', ..., 'm1630']:
        session_start_time = get_session_start_time(minor_session, calendar_date)
        to_time = get_to_time(minor_session, calendar_date)
        expires_at = to_time + timedelta(hours=24)
        
        # Calculate range
        ranges = calculate_session_ranges(
            symbol,
            minor_session,
            session_start_time,
            to_time
        )
        
        # Insert into sessions table
        insert_session(
            symbol=symbol,
            session_type='Minor',
            session_name=minor_session,
            session_start_time=session_start_time,
            to_time=to_time,
            true_open=ranges['true_open'],
            poc=ranges['poc'],
            rpp=ranges['rpp'],
            status='unbroken',
            expires_at=expires_at  # Expires after 24 hours
        )
```

#### 10.2.2 Weekly Session Calculation

For each Sunday in the dataset:
```python
def calculate_weekly_session(symbol, sunday_date):
    """
    Calculate Weekly session starting on a Sunday.
    
    Args:
        symbol: 'ES' or 'NQ'
        sunday_date: Date of Sunday in YYYY-MM-DD format
    
    Creates:
        1 Weekly session
    """
    session_start_time = f"{sunday_date}T18:00:00-05:00"  # Adjust for DST
    
    # Monday is next day
    monday_date = sunday_date + timedelta(days=1)
    to_time = f"{monday_date}T18:00:00-05:00"
    
    # Calculate range (Sunday 18:00 through Monday 17:59)
    ranges = calculate_session_ranges(
        symbol,
        'Weekly',
        session_start_time,
        to_time
    )
    
    # Insert into sessions table
    insert_session(
        symbol=symbol,
        session_type='Weekly',
        session_name='Weekly',
        session_start_time=session_start_time,
        to_time=to_time,
        true_open=ranges['true_open'],
        poc=ranges['poc'],
        rpp=ranges['rpp'],
        status='unbroken',
        expires_at=None  # Never expires
    )
```

#### 10.2.3 Monthly Session Calculation

For each month in the dataset:
```python
def calculate_monthly_session(symbol, year, month):
    """
    Calculate Monthly session for a given month.
    
    Args:
        symbol: 'ES' or 'NQ'
        year: Year (e.g., 2025)
        month: Month (1-12)
    
    Creates:
        1 Monthly session
    """
    # Determine first full trading day
    first_day = date(year, month, 1)
    first_trading_day = get_first_full_trading_day(first_day)
    
    session_start_time = f"{first_trading_day}T18:00:00-05:00"
    
    # Determine second full week Sunday
    second_full_week_sunday = get_second_full_week_sunday(first_day)
    to_time = f"{second_full_week_sunday}T18:00:00-05:00"
    
    # Calculate range
    ranges = calculate_session_ranges(
        symbol,
        'Monthly',
        session_start_time,
        to_time
    )
    
    # Insert into sessions table
    insert_session(
        symbol=symbol,
        session_type='Monthly',
        session_name='Monthly',
        session_start_time=session_start_time,
        to_time=to_time,
        true_open=ranges['true_open'],
        poc=ranges['poc'],
        rpp=ranges['rpp'],
        status='unbroken',
        expires_at=None  # Never expires
    )
```

#### 10.2.4 Helper: get_first_full_trading_day()
```python
def get_first_full_trading_day(first_day_of_month):
    """
    Determine the first full trading day of the month.
    
    Rule: We need Monday's trading session (Sunday 18:00) included.
    
    Returns: Date of the Sunday 18:00 that starts the first trading day
    """
    weekday = first_day_of_month.weekday()  # 0=Monday, 6=Sunday
    
    if weekday == 6:  # Sunday
        # First is Sunday, start that day at 18:00
        return first_day_of_month
    
    elif weekday == 5:  # Saturday
        # First is Saturday, wait for next day (Sunday) at 18:00
        return first_day_of_month + timedelta(days=1)
    
    else:  # Monday-Friday (0-4)
        # First is Monday-Friday, start previous Sunday at 18:00
        days_back = weekday + 1  # Monday=1 day back, Tuesday=2, etc.
        return first_day_of_month - timedelta(days=days_back)
```

#### 10.2.5 Helper: get_second_full_week_sunday()
```python
def get_second_full_week_sunday(first_day_of_month):
    """
    Determine the Sunday that begins the second full week of the month.
    
    A "full week" includes Monday's trading session (Sunday 18:00).
    
    Returns: Date of the Sunday that starts the second full week
    """
    first_trading_day = get_first_full_trading_day(first_day_of_month)
    
    # Is the first trading day already a full week?
    # (i.e., does it include a Monday session?)
    weekday = first_day_of_month.weekday()
    
    if weekday in [6, 0, 1]:  # Sunday, Monday, or Tuesday
        # First week is full
        # Second week starts 7 days after first_trading_day
        return first_trading_day + timedelta(days=7)
    
    else:  # Wednesday-Saturday (2-5)
        # First week is partial (no Monday)
        # Need to find the next Sunday that starts a full week
        # Then add 7 more days for second full week
        
        # Find first Sunday that starts a full week
        days_to_next_sunday = (6 - weekday) % 7
        if days_to_next_sunday == 0:
            days_to_next_sunday = 7
        first_full_week_sunday = first_day_of_month + timedelta(days=days_to_next_sunday)
        
        # Second full week is 7 days later
        return first_full_week_sunday + timedelta(days=7)
```

---

### 10.3 Phase 2: POI Event Detection

**Critical V5 Change:** Process ES and NQ simultaneously to build echo chamber data in poi_events.
```python
def process_poi_events():
    """
    Process all candles chronologically, detecting POI touches
    and updating sessions + poi_events tables.
    
    Processes both ES and NQ together to capture echo chamber timing.
    """
    
    # Get all candles for both symbols, sorted chronologically
    all_candles = load_all_candles_sorted(['ES', 'NQ'])
    
    for candle in all_candles:
        symbol = candle['symbol']
        candle_time = candle['time']
        
        # Get all active sessions for this symbol
        active_sessions = get_active_sessions(symbol, candle_time)
        
        for session in active_sessions:
            # Detect touches
            touches = detect_touches(
                candle,
                true_open=session.true_open,
                poc=session.poc,
                rpp=session.rpp
            )
            
            # Process each touched level
            for poi_type in ['PoC', 'RPP', 'TO']:
                if touches[poi_type]:
                    process_poi_touch(
                        session=session,
                        symbol=symbol,
                        candle_time=candle_time,
                        poi_type=poi_type
                    )
```

#### 10.3.1 process_poi_touch() Logic
```python
def process_poi_touch(session, symbol, candle_time, poi_type):
    """
    Handle a POI touch event.
    
    Steps:
    1. Apply state machine to determine event_type
    2. Update session status
    3. Create or update poi_event record
    """
    
    # Apply state machine
    current_status = get_session_status_dict(session)
    updated_status, event_type, should_record = apply_touch_event(
        current_status,
        poi_type,
        candle_time
    )
    
    # Update session
    update_session_status(session.id, updated_status)
    
    # Record POI event if state machine says to
    if should_record:
        # Check if poi_event already exists for this session+poi+event
        existing_event = query_poi_event(
            session_id=session.id,
            poi_type=poi_type,
            event_type=event_type
        )
        
        if existing_event is None:
            # First touch - create new poi_event
            if symbol == 'ES':
                insert_poi_event(
                    session_id=session.id,
                    poi_type=poi_type,
                    event_type=event_type,
                    es_event_time=candle_time,
                    nq_event_time=None
                )
            else:  # NQ
                insert_poi_event(
                    session_id=session.id,
                    poi_type=poi_type,
                    event_type=event_type,
                    es_event_time=None,
                    nq_event_time=candle_time
                )
        
        else:
            # Second touch - update existing poi_event
            if symbol == 'ES':
                update_poi_event(
                    event_id=existing_event.id,
                    es_event_time=candle_time,
                    nq_event_time=existing_event.nq_event_time
                )
            else:  # NQ
                update_poi_event(
                    event_id=existing_event.id,
                    es_event_time=existing_event.es_event_time,
                    nq_event_time=candle_time
                )
            
            # Calculate echo chamber metrics
            calculate_echo_chamber_metrics(existing_event.id)
```

#### 10.3.2 calculate_echo_chamber_metrics()
```python
def calculate_echo_chamber_metrics(poi_event_id):
    """
    Calculate time_delta_seconds and leader for a poi_event.
    
    Called after both ES and NQ have touched.
    """
    event = get_poi_event(poi_event_id)
    
    if event.es_event_time is None or event.nq_event_time is None:
        # Only one instrument has touched - nothing to calculate
        return
    
    # Calculate time delta
    es_time = parse_iso_timestamp(event.es_event_time)
    nq_time = parse_iso_timestamp(event.nq_event_time)
    time_delta_seconds = abs((es_time - nq_time).total_seconds())
    
    # Determine leader
    if time_delta_seconds < 60:
        leader = 'simultaneous'
    elif es_time < nq_time:
        leader = 'ES'
    else:
        leader = 'NQ'
    
    # Update poi_event
    update_poi_event_metrics(
        poi_event_id,
        time_delta_seconds=time_delta_seconds,
        leader=leader
    )
```

---

### 10.4 Phase 3: Swing Detection

**Executes AFTER Phase 2 (POI events) is complete.**

Swing detection happens in multiple passes to classify swings hierarchically.

---

#### 10.4.1 Overview of Swing Detection Process
```python
def build_swings_table():
    """
    Detect and classify all swings for both symbols.
    
    Process:
    1. Detect Class 1 swings (3-bar pivots)
    2. Promote Class 1 → Class 2
    3. Promote Class 2 → Class 3
    4. Promote Class 3 → Class 4
    5. Calculate movement metrics
    6. Link to POI events
    7. Capture session context
    """
    
    for symbol in ['ES', 'NQ']:
        print(f"Processing swings for {symbol}...")
        
        # Load all candles
        candles = load_all_candles(symbol)
        
        # Pass 1: Detect Class 1 swings
        swings = detect_class1_swings(candles)
        
        # Pass 2: Promote to Class 2
        swings = promote_to_class2(swings)
        
        # Pass 3: Promote to Class 3
        swings = promote_to_class3(swings)
        
        # Pass 4: Promote to Class 4
        swings = promote_to_class4(swings)
        
        # Pass 5: Calculate movement metrics
        swings = calculate_movement_metrics(swings)
        
        # Pass 6: Link to POI events
        swings = link_to_poi_events(symbol, swings)
        
        # Pass 7: Capture session context
        swings = capture_session_context(symbol, swings)
        
        # Insert all swings
        for swing in swings:
            insert_swing(swing)
```

---

#### 10.4.2 Pass 1: Detect Class 1 Swings

**Class 1 Definition:** 3-bar pivot (high or low)
```python
def detect_class1_swings(candles):
    """
    Detect all Class 1 swings using 3-bar pivot logic.
    
    Class 1 High: high[i] > high[i-1] AND high[i] > high[i+1]
    Class 1 Low: low[i] < low[i-1] AND low[i] < low[i+1]
    
    Returns:
        List of swing dicts with keys: time, price, type, class
    """
    swings = []
    
    for i in range(1, len(candles) - 1):
        prev = candles[i-1]
        curr = candles[i]
        next = candles[i+1]
        
        # Class 1 High
        if curr['high'] > prev['high'] and curr['high'] > next['high']:
            swings.append({
                'time': curr['time'],
                'price': curr['high'],
                'type': 'high',
                'class': 1
            })
        
        # Class 1 Low
        if curr['low'] < prev['low'] and curr['low'] < next['low']:
            swings.append({
                'time': curr['time'],
                'price': curr['low'],
                'type': 'low',
                'class': 1
            })
    
    return swings
```

---

#### 10.4.3 Pass 2: Promote to Class 2

**Class 2 Definition:** Has opposite Class 1 swings on both sides
```python
def promote_to_class2(swings):
    """
    Promote Class 1 swings to Class 2.
    
    Rule:
    - Class 1 HIGH → Class 2 if has Class 1 LOWs before AND after
    - Class 1 LOW → Class 2 if has Class 1 HIGHs before AND after
    """
    for i, swing in enumerate(swings):
        if swing['class'] != 1:
            continue
        
        if swing['type'] == 'high':
            # Need Class 1 lows before and after
            lows_before = [s for s in swings[:i] if s['type'] == 'low' and s['class'] == 1]
            lows_after = [s for s in swings[i+1:] if s['type'] == 'low' and s['class'] == 1]
            
            if lows_before and lows_after:
                swing['class'] = 2
        
        elif swing['type'] == 'low':
            # Need Class 1 highs before and after
            highs_before = [s for s in swings[:i] if s['type'] == 'high' and s['class'] == 1]
            highs_after = [s for s in swings[i+1:] if s['type'] == 'high' and s['class'] == 1]
            
            if highs_before and highs_after:
                swing['class'] = 2
    
    return swings
```

---

#### 10.4.4 Pass 3: Promote to Class 3

**Class 3 Definition:** Has same Class 2 swings on both sides
```python
def promote_to_class3(swings):
    """
    Promote Class 2 swings to Class 3.
    
    Rule:
    - Class 2 HIGH → Class 3 if has Class 2 HIGHs before AND after
    - Class 2 LOW → Class 3 if has Class 2 LOWs before AND after
    """
    class2_swings = [s for s in swings if s['class'] == 2]
    
    for i, swing in enumerate(class2_swings):
        if swing['type'] == 'high':
            # Need Class 2 highs before and after
            highs_before = [s for s in class2_swings[:i] if s['type'] == 'high']
            highs_after = [s for s in class2_swings[i+1:] if s['type'] == 'high']
            
            if highs_before and highs_after:
                swing['class'] = 3
        
        elif swing['type'] == 'low':
            # Need Class 2 lows before and after
            lows_before = [s for s in class2_swings[:i] if s['type'] == 'low']
            lows_after = [s for s in class2_swings[i+1:] if s['type'] == 'low']
            
            if lows_before and lows_after:
                swing['class'] = 3
    
    return swings
```

---

#### 10.4.5 Pass 4: Promote to Class 4

**Class 4 Definition:** Has same Class 3 swings on both sides
```python
def promote_to_class4(swings):
    """
    Promote Class 3 swings to Class 4.
    
    Rule:
    - Class 3 HIGH → Class 4 if has Class 3 HIGHs before AND after
    - Class 3 LOW → Class 4 if has Class 3 LOWs before AND after
    """
    class3_swings = [s for s in swings if s['class'] == 3]
    
    for i, swing in enumerate(class3_swings):
        if swing['type'] == 'high':
            highs_before = [s for s in class3_swings[:i] if s['type'] == 'high']
            highs_after = [s for s in class3_swings[i+1:] if s['type'] == 'high']
            
            if highs_before and highs_after:
                swing['class'] = 4
        
        elif swing['type'] == 'low':
            lows_before = [s for s in class3_swings[:i] if s['type'] == 'low']
            lows_after = [s for s in class3_swings[i+1:] if s['type'] == 'low']
            
            if lows_before and lows_after:
                swing['class'] = 4
    
    return swings
```

---

#### 10.4.6 Pass 5: Calculate Movement Metrics
```python
def calculate_movement_metrics(swings):
    """
    Calculate points and candles from prior opposite swing.
    """
    for i, swing in enumerate(swings):
        # Find previous opposite swing
        opposite_type = 'low' if swing['type'] == 'high' else 'high'
        prior_swings = [s for s in swings[:i] if s['type'] == opposite_type]
        
        if prior_swings:
            prior = prior_swings[-1]  # Most recent opposite
            
            swing['prior_opposite_swing_id'] = prior.get('id')  # Set after DB insert
            swing['points_from_prior'] = abs(swing['price'] - prior['price'])
            swing['candles_from_prior'] = calculate_candles_between(
                prior['time'], 
                swing['time']
            )
        else:
            swing['prior_opposite_swing_id'] = None
            swing['points_from_prior'] = None
            swing['candles_from_prior'] = None
    
    return swings
```

---

#### 10.4.7 Pass 6: Link to POI Events
```python
def link_to_poi_events(symbol, swings):
    """
    Link each swing to nearest POI event (if any).
    
    Matching criteria:
    - Same symbol
    - POI event time within ±5 minutes of swing time
    - POI event price within ±5 ticks of swing price
    
    If multiple POI events match, choose closest in time.
    """
    for swing in swings:
        swing_time = parse_iso_timestamp(swing['time'])
        swing_price = swing['price']
        
        # Query POI events near this swing
        nearby_events = query_nearby_poi_events(
            symbol=symbol,
            center_time=swing_time,
            time_window_minutes=5,
            center_price=swing_price,
            price_window_ticks=5
        )
        
        if nearby_events:
            # Find closest in time
            closest = min(
                nearby_events,
                key=lambda e: abs((parse_iso_timestamp(e.es_event_time or e.nq_event_time) - swing_time).total_seconds())
            )
            swing['nearest_poi_event_id'] = closest.id
        else:
            swing['nearest_poi_event_id'] = None
    
    return swings
```

---

#### 10.4.8 Pass 7: Capture Session Context
```python
def capture_session_context(symbol, swings):
    """
    Capture active session statuses at the moment of each swing.
    
    Stores as JSON in active_sessions_snapshot field.
    """
    for swing in swings:
        swing_time = swing['time']
        
        # Get all active sessions at this moment
        active_sessions = get_active_sessions(symbol, swing_time)
        
        # Build snapshot JSON
        snapshot = {
            'major_sessions': {},
            'weekly_session': None,
            'monthly_session': None,
            'current_minor': None
        }
        
        for session in active_sessions:
            if session.session_type == 'Major':
                snapshot['major_sessions'][session.session_name] = {
                    'status': session.status,
                    'first_break_time': session.first_break_time,
                    'first_return_time': session.first_return_time,
                    'resolution_time': session.resolution_time
                }
            
            elif session.session_type == 'Weekly':
                snapshot['weekly_session'] = {
                    'status': session.status,
                    'first_break_time': session.first_break_time,
                    'first_return_time': session.first_return_time,
                    'resolution_time': session.resolution_time
                }
            
            elif session.session_type == 'Monthly':
                snapshot['monthly_session'] = {
                    'status': session.status,
                    'first_break_time': session.first_break_time,
                    'first_return_time': session.first_return_time,
                    'resolution_time': session.resolution_time
                }
            
            elif session.session_type == 'Minor':
                # Determine if this is the "current" minor (the one the swing is in)
                if (session.session_start_time <= swing_time and 
                    swing_time <= session.session_start_time + timedelta(minutes=90)):
                    snapshot['current_minor'] = {
                        'session': session.session_name,
                        'status': session.status
                    }
        
        # Convert to JSON string
        swing['active_sessions_snapshot'] = json.dumps(snapshot)
    
    return swings
```

---

## 11. Edge Cases and Missing Data

### 11.1 Missing Candles During PoC Calculation

**Rule:** If any candles missing in the window from PoC Start to TO Time:
- Set: `true_open = NULL`, `poc = NULL`, `rpp = NULL`
- Insert session record with NULL values
- Set: `status = 'unbroken'`
- Do NOT process POI events for this session (skip in `is_session_active()`)

**Rationale:** Cannot calculate range without complete data.

---

### 11.2 Missing True Open Candle

**Rule:** If the TO candle doesn't exist:
- Set: `true_open = NULL`, `poc = NULL`, `rpp = NULL`
- Insert session record with NULL values
- Session remains inactive (will be skipped for POI processing)

---

### 11.3 Partial Trading Days

**Rule:** Process whatever sessions have complete data.
- Some sessions may have valid ranges while others have NULL
- Each session is independent
- Database will contain mix of valid and NULL sessions

**Example:**
- Data starts at 2025-11-27T12:00:00
- Asia, London, NY_AM: NULL (no data for calculation windows)
- NY_PM, Afternoon: Valid ranges ✓
- Minor sessions m1200 onward: Valid ranges ✓

---

### 11.4 Multi-Day Data Gaps

**Scenario:** Processing stops on Nov 27 and resumes on Dec 1.

**Impact on Active Sessions:**

**Major/Weekly/Monthly sessions:**
- Remain in database with last known status
- When processing resumes, these sessions are still active
- Continue detecting touches and updating status
- This is correct behavior (indefinite tracking)

**Minor sessions:**
- Many will have expired during the gap (expires_at < current_time)
- `is_session_active()` correctly excludes them
- This is correct behavior (24-hour expiry)

**No special handling required** - the expiry logic handles gaps automatically.

---

### 11.5 Daylight Saving Time (DST) Transitions

**Issue:** Timezone offset changes between EDT (-04:00) and EST (-05:00).

**Impact:**
- Session start times shift by 1 hour in UTC terms
- But local times remain consistent (18:00 is always 18:00)

**Solution:** Always use local time portion (HH:MM:SS) for session boundary checks.
```python
def get_time_only(timestamp_str):
    """Extract HH:MM:SS from ISO timestamp, ignoring timezone."""
    dt = datetime.fromisoformat(timestamp_str)
    return dt.strftime('%H:%M:%S')
```

**DST Transition Dates (approximate):**
- Spring forward: Second Sunday in March (EDT begins)
- Fall back: First Sunday in November (EST begins)

**Session Calculation:** No special handling needed - use the actual timestamps from the data.

---

### 11.6 Same-Candle Multiple Events

**Scenario:** One candle touches PoC, TO, and RPP for same session.

**Handling:**
- Process each touch sequentially
- State machine may generate multiple events
- All events have same `event_time` (the candle timestamp)
- Multiple rows in `poi_events` for the same session (different poi_type or event_type)

**Example:**
```
Candle: 2025-11-27T09:15:00-05:00
Touches: London PoC, London TO, London RPP

Results:
- poi_events row 1: (London, PoC, break, 09:15)
- poi_events row 2: (London, TO, return, 09:15)
- poi_events row 3: (London, RPP, break, 09:15)

Session status progression:
- unbroken → break (PoC) → return (TO) → return (RPP touch ignored, already in return)
```

---

### 11.7 Echo Chamber Incomplete Data

**Scenario:** ES touches a POI level, but NQ never touches it.

**Handling:**
- `poi_events` row has `es_event_time` populated, `nq_event_time = NULL`
- `time_delta_seconds = NULL`
- `leader = NULL`
- This is valid data - represents divergence that never converged

**Query Implication:**
- Can identify "orphaned" touches where only one instrument hit the level
- This itself is meaningful (extreme divergence)

---

### 11.8 Weekly Session Crossing Month Boundary

**Scenario:** Weekly session starts in November, resolves in December.

**Handling:**
- `session_start_time = 2025-11-23T18:00:00-05:00` (November)
- `resolution_time = 2025-12-03T09:15:00-05:00` (December)
- No special handling needed - sessions are not month-constrained

---

### 11.9 Monthly Session Crossing Year Boundary

**Scenario:** December monthly session starts Dec 1, resolves Jan 15.

**Handling:**
- `session_start_time = 2025-12-01T18:00:00-05:00` (December)
- `resolution_time = 2026-01-15T14:30:00-05:00` (January, next year)
- No special handling needed - sessions are not year-constrained

---

### 11.10 Swing Detection at Data Boundaries

**Issue:** First few swings may not have prior opposite swings.

**Handling:**
- `prior_opposite_swing_id = NULL`
- `points_from_prior = NULL`
- `candles_from_prior = NULL`
- This is expected - early swings have incomplete context

**Similarly:** Last few swings may not have enough subsequent swings for Class 2/3/4 promotion.
- They remain Class 1 (or whatever class they achieved)
- This is expected behavior

---

### 11.11 POI Event Linking Ambiguity

**Issue:** Swing occurs near multiple POI events - which one to link?

**Current Logic:** Link to closest event in time (within ±5 minutes, ±5 ticks).

**If no events match criteria:**
- `nearest_poi_event_id = NULL`
- Swing is unlinked (may be noise or unrelated to POI activity)

---

### 11.12 Time Parsing Edge Cases

**Zero-padded times:** Always use zero-padded format (09:00, not 9:00)

**Microseconds:** Ignore if present (truncate to seconds)

**Timezone ambiguity:** Always include timezone offset in stored timestamps

---

## 12. Implementation Phases

### Phase 1: Database Setup
```bash
# Create schema
sqlite3 data/ohlc_data.db < schema_v5.sql

# Verify tables
sqlite3 data/ohlc_data.db ".tables"
# Expected: ohlc_1m, sessions, poi_events, swings, insights
```

### Phase 2: Range Calculation
```bash
python calculate_ranges_v5.py

# Output:
# - Populates sessions table
# - All Major, Minor, Weekly, Monthly sessions
# - Sets expires_at for Minor sessions
# - Status = 'unbroken' for all
```

### Phase 3: POI Event Processing
```bash
python process_poi_events_v5.py

# Output:
# - Updates sessions table (status changes)
# - Populates poi_events table
# - Echo chamber metrics calculated
```

### Phase 4: Swing Detection
```bash
python detect_swings_v5.py

# Output:
# - Populates swings table
# - Links to poi_events
# - Captures session context
```

### Phase 5: Verification
```bash
python verify_v5.py

# Checks:
# - Session count (21 per trading day + Weekly/Monthly)
# - POI event echo chamber completeness
# - Swing classification distribution
# - Session context snapshot validity
```

---

## 13. Insights Table

### 13.1 Purpose

The insights table serves as a research journal for recording qualitative observations, confluence patterns, and setup discoveries. Unlike the quantitative data in sessions/poi_events/swings, insights capture the narrative "story" of price action that spans multiple events and timeframes.

### 13.2 Schema
```sql
CREATE TABLE insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Temporal context
    observation_date TEXT NOT NULL,  -- When you recorded this (ISO format)
    market_date_start TEXT,  -- Start of date range (YYYY-MM-DD)
    market_date_end TEXT,    -- End of date range (YYYY-MM-DD), NULL if single day
    
    -- Session context
    sessions_involved TEXT,  -- Comma-separated or JSON (e.g., "London,NY_AM,Weekly")
    
    -- Classification/tags for searching
    confluence_factors TEXT,  -- Comma-separated tags (e.g., "POI break,Echo divergence,Weekly return")
    outcome_type TEXT,  -- Comma-separated tags (e.g., "Class 3 swing,Resolution,Failed setup")
    symbols TEXT,  -- "ES", "NQ", or "ES,NQ"
    
    -- The insight content
    title TEXT,  -- Short description
    insight_markdown TEXT NOT NULL,  -- Full narrative in markdown
    
    -- Query hints (optional)
    suggested_query TEXT,  -- SQL or description for auto-generating queries
    
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_insights_market_date_start ON insights(market_date_start);
CREATE INDEX idx_insights_market_date_end ON insights(market_date_end);
CREATE INDEX idx_insights_sessions ON insights(sessions_involved);
CREATE INDEX idx_insights_confluence ON insights(confluence_factors);
CREATE INDEX idx_insights_outcome ON insights(outcome_type);
CREATE INDEX idx_insights_symbols ON insights(symbols);

-- Full-text search on title and markdown content
CREATE VIRTUAL TABLE insights_fts USING fts5(
    title, 
    insight_markdown,
    content=insights
);
```

### 13.3 Usage Patterns

**Creating an insight:**
```python
from insights_manager import create_insight

insight_id = create_insight(
    observation_date='2025-11-28T14:30:00-05:00',
    market_date_start='2025-11-27',
    market_date_end=None,  # Single day
    sessions_involved='London,Weekly',
    confluence_factors='POI break,Echo divergence,Class 3 swing',
    outcome_type='Major move',
    symbols='ES,NQ',
    title='London PoC break during Weekly return with 5min ES/NQ divergence',
    insight_markdown="""
## Setup

London broke PoC at 09:15 (ES) while Weekly was in return status. 
NQ didn't break until 09:20 - a 5 minute divergence.

## Confluence Factors
- London Major session: first break
- Weekly session: in return status
- Echo Chamber: 5 minute divergence (ES led)
- Current minor: m0900 just formed its PoC

## Outcome

Class 3 swing high formed at 09:35 (20 minutes after London break). 
Move was 37 points from prior low.

## Key Observation

When London breaks while Weekly is in return + echo divergence >3min 
→ watch for Class 3 swing within 30 minutes.
""",
    suggested_query="""
SELECT s.* FROM swings s 
JOIN poi_events p ON s.nearest_poi_event_id = p.id
JOIN sessions sess ON p.session_id = sess.id
WHERE sess.session_name = 'London' 
AND sess.status = 'break'
AND s.swing_class >= 3
"""
)
```

**Searching insights:**
```python
from insights_manager import search_insights

# Find insights involving London and Weekly
results = search_insights(
    sessions_involved='London,Weekly'
)

# Find insights with echo divergence leading to Class 3+ swings
results = search_insights(
    confluence_factors='Echo divergence',
    outcome_type='Class 3'
)

# Full-text search
results = search_insights(
    text_search='5 minute divergence'
)
```

### 13.4 Integration with Analysis Workflow

**Daily Analysis Pattern:**
1. Run queries on sessions/poi_events/swings to find today's patterns
2. Search insights for similar historical patterns
3. Use `suggested_query` from matching insights to deepen analysis
4. Record new observations as insights if novel patterns emerge

**Example Workflow:**
```python
# 1. Identify today's major swings
swings = query_swings(date='2025-11-28', swing_class_min=3)

# 2. For each major swing, check for POI confluence
for swing in swings:
    poi_event = get_poi_event(swing.nearest_poi_event_id)
    session = get_session(poi_event.session_id)
    
    # 3. Search for similar insights
    insights = search_insights(
        sessions_involved=session.session_name,
        confluence_factors='POI break'
    )
    
    # 4. Review past observations
    for insight in insights:
        print(f"Similar setup: {insight.title}")
        print(f"Suggested query: {insight.suggested_query}")
```

### 13.5 Field Guidelines

**observation_date:**
- ISO timestamp when you record the insight (now)
- Use: `datetime.now().isoformat()`

**market_date_start / market_date_end:**
- YYYY-MM-DD format
- Single day: set start, leave end as NULL
- Multi-day: set both (e.g., "2025-11-25" to "2025-11-27")

**sessions_involved:**
- Free-form comma-separated
- Examples: "London", "London,Weekly", "NY_AM,m0900,Weekly"

**confluence_factors:**
- Free-form tags for searching
- Common tags: "POI break", "Echo divergence", "Weekly return", "Monthly break", "Class 3 swing"

**outcome_type:**
- What happened as a result
- Common tags: "Class 3 swing", "Class 4 swing", "Resolution", "Failed setup", "Major move"

**symbols:**
- "ES", "NQ", or "ES,NQ"

**title:**
- Short, descriptive (50-100 chars)
- Should be searchable/scannable

**insight_markdown:**
- Full narrative
- Use markdown formatting (headers, lists, code blocks)
- Recommended sections: Setup, Confluence Factors, Outcome, Key Observation

**suggested_query:**
- Optional SQL query or natural language description
- Used to auto-generate queries when similar conditions appear
- Can be NULL if not applicable

---

## 14. Summary and Checklist

### 14.1 V5 Key Changes from V4

**Removed:**
- ❌ `trading_day` constraint on sessions
- ❌ Quartile sessions (64 per day)
- ❌ Separate `time_groups` and `session_status` tables
- ❌ `context_snapshot` table

**Added:**
- ✅ Weekly sessions (indefinite tracking)
- ✅ Monthly sessions (indefinite tracking)
- ✅ Merged `sessions` table (ranges + status in one)
- ✅ Echo chamber built into `poi_events` (ES/NQ timing in single row)
- ✅ `swings` table with hierarchical classification (Class 1-4)
- ✅ Session context captured as JSON in swings
- ✅ `insights` table for research journal
- ✅ Minor sessions expire after 24 hours

**Database Size:**
- V4: 85 sessions per trading day (5 Major + 16 Minor + 64 Quartile)
- V5: 21 sessions per trading day (5 Major + 16 Minor) + Weekly + Monthly

---

### 14.2 Table Summary

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `sessions` | Session ranges and status tracking | Indefinite tracking for Major/Weekly/Monthly; 24hr expiry for Minor |
| `poi_events` | POI touch events with echo chamber | Single row captures both ES and NQ timing |
| `swings` | Hierarchical swing detection | Class 1-4 classification, POI linkage, session context JSON |
| `insights` | Research journal | Qualitative observations, confluence patterns, searchable |

---

### 14.3 Processing Checklist

**Before Building:**
- [ ] Confirm `ohlc_1m` table populated with ES and NQ data
- [ ] Verify time format matches ISO 8601 with timezone
- [ ] Database located at `data/ohlc_data.db`

**Phase 1 - Range Calculation:**
- [ ] `sessions` table created and populated
- [ ] 21 sessions per trading day calculated (5 Major + 16 Minor)
- [ ] Weekly sessions calculated (one per week)
- [ ] Monthly sessions calculated (one per month)
- [ ] NULL handling working for missing data
- [ ] `expires_at` set correctly for Minor sessions

**Phase 2 - POI Event Detection:**
- [ ] `poi_events` recording all touches
- [ ] Echo chamber metrics calculated (`time_delta_seconds`, `leader`)
- [ ] Sessions tracking indefinitely (Major/Weekly/Monthly)
- [ ] Minor sessions expiring after 24 hours
- [ ] Both ES and NQ processed simultaneously

**Phase 3 - Swing Detection:**
- [ ] `swings` table populated with all classifications
- [ ] Class 1-4 promotion working correctly
- [ ] Movement metrics calculated (points/candles from prior)
- [ ] POI event linkage working
- [ ] Session context JSON captured correctly

**Phase 4 - Insights Setup:**
- [ ] `insights` table created
- [ ] Full-text search (FTS5) working
- [ ] CRUD operations tested

**Final Verification:**
- [ ] No orphaned records
- [ ] All foreign keys valid
- [ ] Status transitions logical
- [ ] Echo chamber data complete where applicable
- [ ] Swing classifications make sense
- [ ] Session context JSON parseable

---

**End of Technical Specification**