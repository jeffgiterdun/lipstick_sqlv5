# Database Schema

Complete schema definitions for the Lipstick Analytical Tool V5 database.

**Database:** SQLite at `data/ohlc_data.db`

---

## Table of Contents

1. [ohlc_1m Table](#ohlc_1m-table)
2. [sessions Table](#sessions-table)
3. [poi_events Table](#poi_events-table)
4. [swings Table](#swings-table)
5. [insights Table](#insights-table)
6. [Foreign Key Relationships](#foreign-key-relationships)

---

## ohlc_1m Table

**Purpose:** Raw OHLC (Open, High, Low, Close) data storage. Foundation table for all session calculations and analysis.

**Key Feature:** Simple storage of 1-minute candle data for ES and NQ futures.

```sql
CREATE TABLE ohlc_1m (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    time TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    UNIQUE(symbol, time)
);

CREATE INDEX idx_ohlc_symbol_time ON ohlc_1m(symbol, time);
```

### Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `symbol` | TEXT | 'ES' or 'NQ' |
| `time` | TEXT | ISO timestamp of the candle (YYYY-MM-DDTHH:MM:SS±HH:MM) |
| `open` | REAL | Opening price of the 1-minute candle |
| `high` | REAL | Highest price during the 1-minute candle |
| `low` | REAL | Lowest price during the 1-minute candle |
| `close` | REAL | Closing price of the 1-minute candle |

### Constraints

- **UNIQUE constraint:** `(symbol, time)` - Ensures no duplicate candles for same symbol/time
- **Index:** `idx_ohlc_symbol_time` - Optimizes queries by symbol and time range

### Data Format

All timestamps must be in **ISO 8601 format with timezone**:
```
YYYY-MM-DDTHH:MM:SS±HH:MM
```

**Example:** `2025-12-16T09:15:00-05:00`

### Example Records

```sql
-- ES candle
INSERT INTO ohlc_1m (symbol, time, open, high, low, close)
VALUES ('ES', '2025-12-16T09:15:00-05:00', 6940.25, 6943.50, 6938.50, 6940.00);

-- NQ candle
INSERT INTO ohlc_1m (symbol, time, open, high, low, close)
VALUES ('NQ', '2025-12-16T09:15:00-05:00', 25997.25, 26017.25, 25991.50, 25998.25);
```

### Usage Notes

- This table is populated from CSV imports (see `load_csv.py`)
- Used as the data source for all range calculations, touch detection, and swing analysis
- Queries should always filter by `symbol` first for optimal performance
- Time ranges should use the index: `WHERE symbol = ? AND time >= ? AND time <= ?`

### Common Queries

**Get candles for a specific time range:**
```sql
SELECT * FROM ohlc_1m
WHERE symbol = 'ES'
AND time >= '2025-12-16T09:00:00-05:00'
AND time <= '2025-12-16T10:30:00-05:00'
ORDER BY time ASC;
```

**Get the highest high and lowest low in a window:**
```sql
SELECT
    MAX(high) as highest_high,
    MIN(low) as lowest_low
FROM ohlc_1m
WHERE symbol = 'ES'
AND time >= '2025-12-16T00:00:00-05:00'
AND time < '2025-12-16T01:30:00-05:00';
```

**Get a specific candle's OHLC values:**
```sql
SELECT open, high, low, close
FROM ohlc_1m
WHERE symbol = 'ES'
AND time = '2025-12-16T09:22:00-05:00';
```

---

## sessions Table

**Purpose:** Single table for session ranges AND status tracking. Replaces both time_groups and session_status from V4.

**Key Feature:** No trading_day constraint. Sessions identified by (symbol, session_type, session_name, session_start_time).

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

### Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `symbol` | TEXT | 'ES' or 'NQ' |
| `session_type` | TEXT | 'Major', 'Minor', 'Weekly', or 'Monthly' |
| `session_name` | TEXT | Specific session identifier |
| `session_start_time` | TEXT | ISO timestamp when session begins |
| `to_time` | TEXT | ISO timestamp of True Open candle |
| `true_open` | REAL | True Open price (NULL if missing data) |
| `poc` | REAL | Point of Control price (NULL if missing data) |
| `rpp` | REAL | Range Projection Point price (NULL if missing data) |
| `status` | TEXT | Current state: 'unbroken', 'break', 'return', 'resolved' |
| `first_break_time` | TEXT | ISO timestamp of first PoC/RPP touch |
| `first_break_side` | TEXT | Which side broke first: 'PoC' or 'RPP' |
| `first_return_time` | TEXT | ISO timestamp of first TO touch after break |
| `second_break_time` | TEXT | ISO timestamp of second PoC/RPP touch |
| `second_break_side` | TEXT | Which side broke second: 'PoC' or 'RPP' |
| `resolution_time` | TEXT | ISO timestamp when session resolved |
| `resolution_type` | TEXT | 'single_sided' or 'double_sided' |
| `expires_at` | TEXT | NULL for Major/Weekly/Monthly, to_time + 24h for Minor |
| `created_at` | TEXT | ISO timestamp when record created |
| `updated_at` | TEXT | ISO timestamp when record last updated |

### Session Tracking Duration

| Session Type | expires_at Value |
|--------------|------------------|
| Major | NULL (tracks until resolved) |
| Weekly | NULL (tracks until resolved) |
| Monthly | NULL (tracks until resolved) |
| Minor | to_time + 24 hours |

### Example Records

**Major Session (London):**
```sql
INSERT INTO sessions (
    symbol, session_type, session_name,
    session_start_time, to_time,
    true_open, poc, rpp,
    status, expires_at
) VALUES (
    'ES', 'Major', 'London',
    '2025-11-27T00:00:00-05:00', '2025-11-27T01:30:00-05:00',
    5935.00, 5920.00, 5950.00,
    'unbroken', NULL
);
```

**Minor Session (m0900):**
```sql
INSERT INTO sessions (
    symbol, session_type, session_name,
    session_start_time, to_time,
    true_open, poc, rpp,
    status, expires_at
) VALUES (
    'ES', 'Minor', 'm0900',
    '2025-11-27T09:00:00-05:00', '2025-11-27T09:22:00-05:00',
    5940.00, 5935.00, 5945.00,
    'unbroken', '2025-11-28T09:22:00-05:00'
);
```

---

## poi_events Table

**Purpose:** Record POI touches with echo chamber analysis built-in. ONE row per session POI event, captures BOTH ES and NQ timing and status.

**Key V5 Feature:** Single row contains both ES and NQ event timing.

**Denormalized Columns:** Includes trading_day, symbol, session_type, and session_name for easy direct SQL querying without joins.

```sql
CREATE TABLE poi_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,  -- FK to sessions table

    -- Denormalized session context (for easy querying)
    trading_day TEXT NOT NULL,  -- YYYY-MM-DD format (e.g., '2025-12-16')
    symbol TEXT NOT NULL,  -- 'ES' or 'NQ'
    session_type TEXT NOT NULL,  -- 'Major', 'Minor', 'Weekly', 'Monthly'
    session_name TEXT NOT NULL,  -- 'London', 'm0900', 'Weekly', 'Monthly'

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
CREATE INDEX idx_poi_events_trading_day ON poi_events(trading_day);
CREATE INDEX idx_poi_events_symbol_session ON poi_events(symbol, session_name);
CREATE INDEX idx_poi_events_es_time ON poi_events(es_event_time);
CREATE INDEX idx_poi_events_nq_time ON poi_events(nq_event_time);
```

### Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `session_id` | INTEGER | Foreign key to sessions table |
| `trading_day` | TEXT | Trading day in YYYY-MM-DD format (e.g., '2025-12-16') |
| `symbol` | TEXT | 'ES' or 'NQ' (denormalized from sessions) |
| `session_type` | TEXT | 'Major', 'Minor', 'Weekly', or 'Monthly' |
| `session_name` | TEXT | Specific session: 'London', 'm0900', 'Weekly', 'Monthly' |
| `poi_type` | TEXT | Which level touched: 'PoC', 'RPP', or 'TO' |
| `event_type` | TEXT | Type of event: 'break', 'return', or 'resolution' |
| `es_event_time` | TEXT | When ES touched (NULL if not yet) |
| `nq_event_time` | TEXT | When NQ touched (NULL if not yet) |
| `time_delta_seconds` | INTEGER | Time difference in seconds |
| `leader` | TEXT | 'ES', 'NQ', or 'simultaneous' |
| `created_at` | TEXT | When record created |
| `updated_at` | TEXT | When record last updated |

### Trading Day Calculation

The `trading_day` field represents the trading day (18:00 → 16:59 next calendar day):

```python
def get_trading_day(timestamp):
    """
    Calculate trading day from timestamp.

    Trading day runs 18:00 to 16:59 (next calendar day).
    """
    dt = parse_iso_timestamp(timestamp)

    # If time is 00:00 to 16:59, trading day is same calendar date
    if dt.hour < 18:
        return dt.date().isoformat()

    # If time is 18:00 to 23:59, trading day is next calendar date
    else:
        next_day = dt.date() + timedelta(days=1)
        return next_day.isoformat()
```

**Examples:**
- Event at `2025-12-16T09:15:00-05:00` → trading_day = `'2025-12-16'`
- Event at `2025-12-15T18:00:00-05:00` → trading_day = `'2025-12-16'`
- Event at `2025-12-16T23:45:00-05:00` → trading_day = `'2025-12-17'`

### POI Event Creation Logic

**Scenario 1: First Touch**
```sql
-- Candle 1 (09:15): ES breaks London PoC on 12/16/25
INSERT INTO poi_events (
    session_id, trading_day, symbol, session_type, session_name,
    poi_type, event_type,
    es_event_time, nq_event_time
) VALUES (
    123, '2025-12-16', 'ES', 'Major', 'London',
    'PoC', 'break',
    '2025-12-16T09:15:00-05:00', NULL
);

-- Result visible in table:
-- 2025-12-16 | ES | Major | London | PoC | break | 09:15:00 | NULL
```

**Scenario 2: Second Touch**
```sql
-- Candle 2 (09:18): NQ breaks London PoC
UPDATE poi_events
SET
    nq_event_time = '2025-12-16T09:18:00-05:00',
    time_delta_seconds = 180,
    leader = 'ES'
WHERE session_id = 123
AND poi_type = 'PoC'
AND event_type = 'break';

-- Result visible in table:
-- 2025-12-16 | ES | Major | London | PoC | break | 09:15:00 | 09:18:00 | 180s | ES
```

### Querying POI Events

With denormalized columns, you can easily query without joins:

```sql
-- Find all London PoC breaks on specific date
SELECT * FROM poi_events
WHERE trading_day = '2025-12-16'
AND session_name = 'London'
AND poi_type = 'PoC'
AND event_type = 'break';

-- Find all Major session events for ES
SELECT * FROM poi_events
WHERE symbol = 'ES'
AND session_type = 'Major'
ORDER BY trading_day DESC, es_event_time DESC;

-- Find Weekly session events
SELECT * FROM poi_events
WHERE session_name = 'Weekly'
ORDER BY trading_day DESC;
```

---

## swings Table

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

### Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `symbol` | TEXT | 'ES' or 'NQ' |
| `swing_time` | TEXT | ISO timestamp when swing occurred |
| `swing_price` | REAL | Price level of the swing |
| `swing_type` | TEXT | 'high' or 'low' |
| `swing_class` | INTEGER | Final classification: 1, 2, 3, or 4 |
| `prior_opposite_swing_id` | INTEGER | Link to previous opposite swing |
| `points_from_prior` | REAL | Distance in points from prior swing |
| `candles_from_prior` | INTEGER | Number of candles between swings |
| `nearest_poi_event_id` | INTEGER | Link to closest POI event |
| `active_sessions_snapshot` | TEXT | JSON snapshot of session statuses |
| `created_at` | TEXT | When record created |

### Session Context Snapshot Format (JSON)

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

---

## insights Table

**Purpose:** Research journal for recording qualitative observations, confluence patterns, and setup discoveries.

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

### Column Definitions

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `observation_date` | TEXT | When insight was recorded (ISO timestamp) |
| `market_date_start` | TEXT | Start date of observation (YYYY-MM-DD) |
| `market_date_end` | TEXT | End date of observation (NULL if single day) |
| `sessions_involved` | TEXT | Comma-separated session names |
| `confluence_factors` | TEXT | Searchable tags for confluence patterns |
| `outcome_type` | TEXT | Searchable tags for outcomes |
| `symbols` | TEXT | 'ES', 'NQ', or 'ES,NQ' |
| `title` | TEXT | Short descriptive title |
| `insight_markdown` | TEXT | Full narrative in markdown |
| `suggested_query` | TEXT | SQL query or description |
| `created_at` | TEXT | When record created |
| `updated_at` | TEXT | When record last updated |

---

## Foreign Key Relationships

```
sessions (id) ←─── poi_events (session_id)
                         ↑
                         │
                    swings (nearest_poi_event_id)
                         ↑
                         │
                    swings (prior_opposite_swing_id) → swings (id)
```

**Relationship Details:**

1. **sessions → poi_events**: One-to-many
   - Each session can have multiple POI events (PoC break, TO return, etc.)

2. **poi_events → swings**: One-to-many (optional)
   - A POI event may be linked to one or more swings (or none)
   - Links created based on time/price proximity

3. **swings → swings**: One-to-many (self-referential)
   - Each swing links to its prior opposite swing for movement metrics

---

## Data Integrity Constraints

### Required Fields

All timestamp fields must be in ISO 8601 format with timezone:
```
YYYY-MM-DDTHH:MM:SS±HH:MM
```

Example: `2025-11-27T09:15:00-05:00`

### Status Values

`sessions.status` must be one of:
- `'unbroken'`
- `'break'`
- `'return'`
- `'resolved'`

### Session Types

`sessions.session_type` must be one of:
- `'Major'`
- `'Minor'`
- `'Weekly'`
- `'Monthly'`

### POI Types

`poi_events.poi_type` must be one of:
- `'PoC'`
- `'RPP'`
- `'TO'`

### Event Types

`poi_events.event_type` must be one of:
- `'break'`
- `'return'`
- `'resolution'`

---

## Next Steps

- [Calculation Logic](calculation-logic.md) - How ranges and touches are calculated
- [Processing Algorithm](processing-algorithm.md) - Implementation details
- [Edge Cases](edge-cases.md) - Handling special scenarios
