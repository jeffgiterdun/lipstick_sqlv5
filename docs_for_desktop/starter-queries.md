# Starter SQL Queries

Common queries for analysis and pattern discovery. Adapt these to your specific hypotheses.

---

## Data Range & Status

### Check your historical data range
```sql
SELECT
    symbol,
    MIN(time) as first_candle,
    MAX(time) as last_candle,
    COUNT(*) as total_candles
FROM ohlc_1m
GROUP BY symbol;
```

### Active sessions overview
```sql
SELECT
    symbol,
    session_type,
    session_name,
    status,
    to_time,
    poc,
    true_open,
    rpp,
    first_break_side,
    first_break_time
FROM sessions
WHERE status != 'resolved'
  AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY
    symbol,
    CASE session_type
        WHEN 'Yearly' THEN 1
        WHEN 'Monthly' THEN 2
        WHEN 'Weekly' THEN 3
        WHEN 'Major' THEN 4
        WHEN 'Minor' THEN 5
    END,
    to_time DESC;
```

---

## POI Event Analysis

### Recent POI events with Echo Chamber data
```sql
SELECT
    trading_day,
    session_type,
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    time_delta_minutes,
    leader
FROM poi_events
WHERE COALESCE(es_event_time, nq_event_time) >= datetime('now', '-7 days')
ORDER BY COALESCE(es_event_time, nq_event_time) DESC
LIMIT 50;
```

### POI events with large Echo Chamber divergence
```sql
SELECT
    trading_day,
    session_type,
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    time_delta_minutes,
    leader
FROM poi_events
WHERE time_delta_minutes > 360  -- >6 hours divergence
ORDER BY time_delta_minutes DESC
LIMIT 50;
```

### POI events by session type (testing hierarchy)
```sql
SELECT
    session_type,
    poi_type,
    COUNT(*) as total_events,
    AVG(time_delta_minutes) as avg_divergence,
    COUNT(CASE WHEN time_delta_minutes > 360 THEN 1 END) as large_divergence_count
FROM poi_events
WHERE time_delta_minutes IS NOT NULL
GROUP BY session_type, poi_type
ORDER BY session_type, poi_type;
```

---

## Swing Analysis

### Class distribution at POI levels
```sql
-- Count swings by class that occurred near POI events
SELECT
    s.swing_class,
    COUNT(*) as swing_count,
    AVG(s.points_from_prior) as avg_point_move,
    AVG(s.candles_from_poi_event) as avg_candles_from_poi
FROM swings s
WHERE s.nearest_poi_event_id IS NOT NULL
  AND s.candles_from_poi_event <= 60  -- within 60 candles of POI event
GROUP BY s.swing_class
ORDER BY s.swing_class;
```

### Class 3+ swings at specific POI types
```sql
SELECT
    s.symbol,
    s.swing_time,
    s.swing_type,
    s.swing_class,
    s.swing_price,
    s.points_from_prior,
    s.candles_from_poi_event,
    p.session_name,
    p.poi_type,
    p.event_type,
    COALESCE(p.es_event_time, p.nq_event_time) as poi_event_time
FROM swings s
JOIN poi_events p ON s.nearest_poi_event_id = p.id
WHERE s.swing_class >= 3
  AND s.candles_from_poi_event <= 30
ORDER BY s.swing_time DESC
LIMIT 100;
```

### Test swing class significance
```sql
-- For each swing class, see if it's linked to POI events more often
SELECT
    swing_class,
    COUNT(*) as total_swings,
    COUNT(nearest_poi_event_id) as swings_near_poi,
    ROUND(COUNT(nearest_poi_event_id) * 100.0 / COUNT(*), 2) as pct_near_poi,
    AVG(points_from_prior) as avg_move_points
FROM swings
GROUP BY swing_class
ORDER BY swing_class;
```

---

## Hypothesis Testing Queries

### Template: Test if [CONDITION] predicts POI-to-POI moves

**Step 1: Identify all instances of your setup**

```sql
-- Example: Class 3+ swing within 20 candles of PoC first_break event
SELECT
    s.symbol,
    s.swing_time,
    s.swing_price,
    s.swing_class,
    p.session_name,
    p.poi_type,
    p.event_type,
    COALESCE(p.es_event_time, p.nq_event_time) as poi_time,
    sess.true_open,
    sess.poc,
    sess.rpp,
    sess.status as session_status
FROM swings s
JOIN poi_events p ON s.nearest_poi_event_id = p.id
JOIN sessions sess ON (
    (s.symbol = 'ES' AND p.es_session_id = sess.id)
    OR (s.symbol = 'NQ' AND p.nq_session_id = sess.id)
)
WHERE s.swing_class >= 3
  AND s.candles_from_poi_event <= 20
  AND p.poi_type = 'PoC'
  AND p.event_type = 'first_break'
ORDER BY s.swing_time;
```

**Step 2: For each instance, manually check outcome**

You'll need to look at subsequent price action:
- Did price reach TO (target) before hitting invalidation?
- How long did it take?
- What was the point move?

This is manual scoring for now. As you identify winning patterns, you can build automated backtesting queries.

### Template: Echo Chamber setup testing

```sql
-- Large divergence at PoC first_break, NQ leading ES
SELECT
    p.trading_day,
    p.session_name,
    p.poi_type,
    p.event_type,
    p.es_event_time,
    p.nq_event_time,
    p.time_delta_minutes,
    p.leader,
    es_sess.status as es_status,
    nq_sess.status as nq_status,
    es_sess.true_open,
    es_sess.poc,
    es_sess.rpp
FROM poi_events p
JOIN sessions es_sess ON p.es_session_id = es_sess.id
JOIN sessions nq_sess ON p.nq_session_id = nq_sess.id
WHERE p.time_delta_minutes > 180  -- >3 hours divergence
  AND p.leader = 'NQ'
  AND p.poi_type = 'PoC'
  AND p.event_type = 'first_break'
ORDER BY p.time_delta_minutes DESC;
```

Then manually score:
- After NQ broke and ES finally caught up, did price move to TO?
- Did the "lagging" ES break predict directional move?

---

## Confluence Pattern Queries

### Multi-timeframe POI confluence
```sql
-- Find instances where Major and Weekly POIs are within 5 points
SELECT
    major.symbol,
    major.session_name as major_session,
    major.to_time as major_to_time,
    major.poc as major_poc,
    weekly.session_name as weekly_session,
    weekly.poc as weekly_poc,
    ABS(major.poc - weekly.poc) as poi_distance
FROM sessions major
JOIN sessions weekly ON (
    major.symbol = weekly.symbol
    AND weekly.session_type = 'Weekly'
    AND major.to_time BETWEEN weekly.to_time AND COALESCE(weekly.resolution_time, datetime('now'))
)
WHERE major.session_type = 'Major'
  AND ABS(major.poc - weekly.poc) <= 5  -- within 5 points
ORDER BY major.to_time DESC;
```

### Session status alignment (ES and NQ both in same status)
```sql
SELECT
    es.session_type,
    es.session_name,
    es.status,
    es.to_time,
    es.first_break_time as es_break_time,
    nq.first_break_time as nq_break_time,
    ABS((julianday(es.first_break_time) - julianday(nq.first_break_time)) * 1440) as break_time_delta_minutes
FROM sessions es
JOIN sessions nq ON (
    es.session_type = nq.session_type
    AND es.session_name = nq.session_name
    AND es.session_start_time = nq.session_start_time
    AND nq.symbol = 'NQ'
)
WHERE es.symbol = 'ES'
  AND es.status = nq.status
  AND es.status != 'resolved'
ORDER BY es.to_time DESC;
```

---

## OOO (Order of Operations) Testing

### Unresolved sessions in chronological order
```sql
-- The "checklist" of unresolved sessions
SELECT
    symbol,
    session_type,
    session_name,
    status,
    to_time,
    poc,
    true_open,
    rpp,
    first_break_time,
    CASE
        WHEN status = 'unbroken' THEN 'Awaiting first break'
        WHEN status = 'break' THEN 'Awaiting return to TO'
        WHEN status = 'return' THEN 'Awaiting second break and resolution'
    END as next_task
FROM sessions
WHERE status != 'resolved'
  AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY
    symbol,
    to_time ASC;  -- Chronological order
```

### Test OOO hypothesis: After resolution, does price move to next unresolved session?
```sql
-- Sessions that resolved recently
SELECT
    symbol,
    session_type,
    session_name,
    resolution_time,
    resolution_type,
    poc,
    true_open,
    rpp
FROM sessions
WHERE status = 'resolved'
  AND resolution_time >= datetime('now', '-30 days')
ORDER BY resolution_time DESC;
```

Then manually check:
- What was the next chronologically older unresolved session?
- Did price move toward that session's POI levels after this resolution?
- How long did it take?

---

## Performance Analysis Queries

### Session type resolution statistics
```sql
SELECT
    session_type,
    COUNT(*) as total_sessions,
    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_count,
    ROUND(COUNT(CASE WHEN status = 'resolved' THEN 1 END) * 100.0 / COUNT(*), 2) as resolution_rate,
    AVG(
        CASE
            WHEN resolution_time IS NOT NULL AND to_time IS NOT NULL
            THEN (julianday(resolution_time) - julianday(to_time)) * 1440  -- minutes
        END
    ) as avg_time_to_resolution_minutes
FROM sessions
GROUP BY session_type
ORDER BY
    CASE session_type
        WHEN 'Yearly' THEN 1
        WHEN 'Monthly' THEN 2
        WHEN 'Weekly' THEN 3
        WHEN 'Major' THEN 4
        WHEN 'Minor' THEN 5
    END;
```

### Echo Chamber leader statistics
```sql
SELECT
    leader,
    session_type,
    poi_type,
    COUNT(*) as event_count,
    AVG(time_delta_minutes) as avg_divergence,
    MIN(time_delta_minutes) as min_divergence,
    MAX(time_delta_minutes) as max_divergence
FROM poi_events
WHERE leader IS NOT NULL
  AND leader != 'simultaneous'
GROUP BY leader, session_type, poi_type
ORDER BY leader, session_type, poi_type;
```

---

## Specific Date Analysis

### Everything that happened on a specific trading day
```sql
-- Change the date to your target trading day
WITH target_day AS (
    SELECT '2025-12-16' as day
)
SELECT
    'POI Event' as event_type,
    p.session_name,
    p.poi_type,
    COALESCE(p.es_event_time, p.nq_event_time) as event_time,
    p.time_delta_minutes,
    p.leader,
    NULL as swing_class
FROM poi_events p, target_day
WHERE p.trading_day = target_day.day

UNION ALL

SELECT
    'Swing' as event_type,
    'N/A' as session_name,
    s.swing_type as poi_type,
    s.swing_time as event_time,
    NULL as time_delta_minutes,
    s.symbol as leader,
    s.swing_class
FROM swings s, target_day
WHERE DATE(s.swing_time) = target_day.day
  AND s.swing_class >= 3

ORDER BY event_time;
```

---

## Tips for Query Development

### Building Hypothesis Tests

1. **Start broad** - Get all instances of a pattern
2. **Add filters** - Narrow to specific confluence conditions
3. **Join related data** - Link swings → POI events → sessions
4. **Score outcomes** - Manually check each instance for win/loss
5. **Calculate metrics** - Win rate, avg time, avg points

### Common Patterns

**Time-based filtering:**
```sql
WHERE time >= datetime('now', '-30 days')
WHERE DATE(time) = '2025-12-16'
WHERE time BETWEEN '2025-12-01' AND '2025-12-31'
```

**Symbol filtering:**
```sql
WHERE symbol = 'ES'
WHERE symbol IN ('ES', 'NQ')
```

**Session type filtering:**
```sql
WHERE session_type IN ('Major', 'Weekly', 'Monthly')
WHERE session_type != 'Minor'
```

**POI event ordering:**
```sql
ORDER BY COALESCE(es_event_time, nq_event_time) DESC
```

**Time delta calculations:**
```sql
-- Minutes between two timestamps
(julianday(time1) - julianday(time2)) * 1440

-- Hours
(julianday(time1) - julianday(time2)) * 24

-- Days
julianday(time1) - julianday(time2)
```

---

## Next Steps

1. Run the data range query to see what you have
2. Explore POI events and swings with the provided queries
3. Adapt these templates for your specific hypotheses
4. Build your own queries as patterns emerge
5. Document reproducible queries in Notion tests

Remember: Every hypothesis test should have a corresponding SQL query that you can re-run as new data arrives.
