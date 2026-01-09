# Database Schema - Quick Reference

Quick reference for table structures and key fields. For full technical schema details, see `docs/technical/database-schema.md` in main repository.

---

## Table: ohlc_1m

**Purpose:** Raw 1-minute OHLC candle data

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| symbol | TEXT | 'ES' or 'NQ' |
| time | TEXT | ISO timestamp with timezone |
| open | REAL | Open price |
| high | REAL | High price |
| low | REAL | Low price |
| close | REAL | Close price |

**Key Index:** `idx_ohlc_symbol_time` on (symbol, time)

**Unique Constraint:** (symbol, time)

---

## Table: sessions

**Purpose:** Session ranges and status tracking

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| symbol | TEXT | 'ES' or 'NQ' |
| session_type | TEXT | 'Major', 'Minor', 'Weekly', 'Monthly', 'Yearly' |
| session_name | TEXT | 'Asia', 'London', 'm0900', etc. |
| session_start_time | TEXT | When session begins |
| to_time | TEXT | True Open time |
| true_open | REAL | TO price |
| poc | REAL | PoC price |
| rpp | REAL | RPP price |
| status | TEXT | 'unbroken', 'break', 'return', 'resolved' |
| first_break_time | TEXT | When first PoC/RPP touched |
| first_break_side | TEXT | 'PoC' or 'RPP' |
| first_return_time | TEXT | When first TO return |
| second_break_time | TEXT | When second PoC/RPP touched |
| second_break_side | TEXT | 'PoC' or 'RPP' |
| resolution_time | TEXT | When resolved |
| resolution_type | TEXT | 'single_sided' or 'double_sided' |
| expires_at | TEXT | NULL for Major/Weekly/Monthly/Yearly, to_time+24h for Minor |
| last_poi_check_time | TEXT | Last time POI processing scanned this session |
| created_at | TEXT | When record created |
| updated_at | TEXT | When record last updated |

**Key Indexes:**
- `idx_sessions_symbol_status` on (symbol, status)
- `idx_sessions_active` for non-resolved sessions

**Unique Constraint:** (symbol, session_type, session_name, session_start_time)

---

## Table: poi_events

**Purpose:** POI touch events with Echo Chamber data

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| es_session_id | INTEGER | ES session FK |
| nq_session_id | INTEGER | NQ session FK |
| trading_day | TEXT | Trading day (YYYY-MM-DD) |
| session_type | TEXT | 'Major', 'Minor', 'Weekly', 'Monthly', 'Yearly' |
| session_name | TEXT | Session identifier |
| poi_type | TEXT | 'PoC', 'RPP', 'TO' |
| event_type | TEXT | 'break', 'return', 'resolution' |
| es_event_time | TEXT | When ES touched (NULL if not yet) |
| nq_event_time | TEXT | When NQ touched (NULL if not yet) |
| time_delta_minutes | INTEGER | abs(ES - NQ) in minutes |
| leader | TEXT | 'ES', 'NQ', 'simultaneous' |
| created_at | TEXT | When record created |
| updated_at | TEXT | When record last updated |

**Key Indexes:**
- `idx_poi_events_session_name` on (session_name)
- `idx_poi_events_es_session` on (es_session_id)
- `idx_poi_events_nq_session` on (nq_session_id)
- `idx_poi_events_trading_day` on (trading_day)

**Foreign Keys:** Links to sessions table via es_session_id and nq_session_id

---

## Table: swings

**Purpose:** Hierarchical swing classification with POI linkage

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| symbol | TEXT | 'ES' or 'NQ' |
| swing_time | TEXT | When swing occurred |
| swing_price | REAL | Price level |
| swing_type | TEXT | 'high' or 'low' |
| swing_class | INTEGER | 1-6 (higher = more significant) |
| prior_opposite_swing_id | INTEGER | Link to prior opposite swing |
| points_from_prior | REAL | Move size in points |
| candles_from_prior | INTEGER | Move duration in candles |
| candles_from_poi_event | INTEGER | Candles since nearest POI event |
| nearest_poi_event_id | INTEGER | Link to POI event |
| created_at | TEXT | When record created |

**Key Indexes:**
- `idx_swings_symbol_time` on (symbol, swing_time)
- `idx_swings_class` on (swing_class)
- `idx_swings_major` on Class 3+ swings
- `idx_swings_poi_link` on (nearest_poi_event_id)

**Foreign Keys:**
- prior_opposite_swing_id → swings(id)
- nearest_poi_event_id → poi_events(id)

---

## Table: insights

**Purpose:** Research journal for discoveries and patterns

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| observation_date | TEXT | When recorded |
| market_date_start | TEXT | Start of date range (YYYY-MM-DD) |
| market_date_end | TEXT | End of date range (NULL if single day) |
| sessions_involved | TEXT | Comma-separated session names |
| confluence_factors | TEXT | Comma-separated tags |
| outcome_type | TEXT | Comma-separated tags |
| symbols | TEXT | 'ES', 'NQ', or 'ES,NQ' |
| title | TEXT | Short headline |
| insight_markdown | TEXT | Full narrative |
| suggested_query | TEXT | SQL to reproduce analysis |
| created_at | TEXT | When record created |
| updated_at | TEXT | When record last updated |

**Full-text Search:** FTS5 index on title and insight_markdown (insights_fts table)

**Key Indexes:** On all tag fields for filtering

---

## Foreign Key Relationships

```
sessions (id) ←── poi_events (es_session_id, nq_session_id)
                        ↑
                        │
                   swings (nearest_poi_event_id)
                        ↑
                        │
                   swings (prior_opposite_swing_id) → swings (id)
```

---

## Data Type Standards

### Timestamps
All timestamps in ISO 8601 format with timezone:
```
YYYY-MM-DDTHH:MM:SS±HH:MM
Example: 2025-12-16T09:15:00-05:00
```

### Session Types
- 'Major'
- 'Minor'
- 'Weekly'
- 'Monthly'
- 'Yearly'

### Session Status
- 'unbroken'
- 'break'
- 'return'
- 'resolved'

### POI Types
- 'PoC'
- 'RPP'
- 'TO'

### Event Types
- 'break'
- 'return'
- 'resolution'

### Swing Types
- 'high'
- 'low'

### Echo Chamber Leaders
- 'ES'
- 'NQ'
- 'simultaneous'

### Resolution Types
- 'single_sided'
- 'double_sided'

---

## Query Best Practices

1. Always filter by `symbol` first for performance
2. Use date ranges to limit results
3. When joining poi_events, remember it links to BOTH es_session_id and nq_session_id
4. Use `COALESCE(es_event_time, nq_event_time)` for POI event ordering
5. Check NULL values when filtering Echo Chamber data (time_delta, leader)
6. Use `swing_class >= 3` to filter for structural swings
7. Reference `expires_at` for active sessions
