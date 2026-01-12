# POI Event Queries Guide

This guide demonstrates how to use the `event_type` column in the `poi_events` table for intuitive analysis.

## Column Description

- **`event_type`**: The session status transition that created this POI event
  - Values: `'first_break'`, `'return'`, `'second_break_same'`, `'second_break_opposite'`, `'resolved'`
  - This matches the session status vocabulary exactly for consistency

## Example Queries

### 1. Find First Break Events

**Question**: "Show me first break events (initial PoC/RPP touches)"

```sql
SELECT
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    leader,
    time_delta_minutes
FROM poi_events
WHERE event_type = 'first_break'
ORDER BY created_at DESC
LIMIT 20;
```

### 2. Find Same-Side Second Breaks

**Question**: "Show me sessions that broke the same side twice (single-sided sessions)"

```sql
SELECT
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    leader,
    time_delta_minutes
FROM poi_events
WHERE event_type = 'second_break_same'
ORDER BY created_at DESC
LIMIT 20;
```

### 3. Find Opposite-Side Second Breaks

**Question**: "Show me sessions that broke both sides (double-sided sessions)"

```sql
SELECT
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    leader,
    time_delta_minutes
FROM poi_events
WHERE event_type = 'second_break_opposite'
ORDER BY created_at DESC
LIMIT 20;
```

### 4. Echo Chamber - Large Time Divergence

**Question**: "When did ES and NQ have significant time gaps between touching the same POI?"

```sql
SELECT
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    leader,
    time_delta_minutes
FROM poi_events
WHERE time_delta_minutes IS NOT NULL
  AND time_delta_minutes > 60  -- More than 1 hour apart
ORDER BY time_delta_minutes DESC
LIMIT 20;
```

### 5. Session Timeline

**Question**: "Show me the complete POI timeline for session X"

```sql
SELECT
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    leader,
    time_delta_minutes
FROM poi_events
WHERE session_name = 'Afternoon 2026-01-09'
ORDER BY COALESCE(es_event_time, nq_event_time) ASC;
```

### 6. Return Events Analysis

**Question**: "Which sessions returned to TO quickly?"

```sql
SELECT
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    leader,
    time_delta_minutes
FROM poi_events
WHERE event_type = 'return'
  AND time_delta_minutes IS NOT NULL
ORDER BY time_delta_minutes ASC
LIMIT 20;
```

### 7. Resolution Analysis

**Question**: "Show me sessions that resolved (second return to TO)"

```sql
SELECT
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    leader,
    time_delta_minutes
FROM poi_events
WHERE event_type = 'resolved'
ORDER BY created_at DESC
LIMIT 20;
```

### 8. Event Type Counts

**Question**: "How many events of each type have occurred?"

```sql
SELECT
    event_type,
    COUNT(*) as event_count
FROM poi_events
GROUP BY event_type
ORDER BY event_count DESC;
```

### 9. Recent Activity by Session Type

**Question**: "Show recent Major session POI events"

```sql
SELECT
    session_name,
    poi_type,
    event_type,
    es_event_time,
    nq_event_time,
    leader
FROM poi_events
WHERE session_type = 'Major'
ORDER BY created_at DESC
LIMIT 20;
```

## Key Advantages

1. **Single Source of Truth**: event_type directly matches session status values
2. **Intuitive Filtering**: Simple `WHERE event_type = 'first_break'` conditions
3. **Echo Chamber Analysis**: Use time_delta_minutes and leader for timing analysis
4. **LLM-Friendly**: Claude Desktop can easily construct correct queries
5. **Consistent Vocabulary**: Same status values used across sessions and poi_events tables

## Session Status Flow

```
unbroken → first_break → return → second_break_same/opposite → resolved
    ↓          ↓            ↓              ↓                      ↓
  (TO)     (PoC/RPP)       (TO)        (PoC/RPP)               (TO)
```

- **unbroken**: Before any break
- **first_break**: After first PoC/RPP touch, before TO return
- **return**: After TO return, before second break
- **second_break_same**: Second break on SAME side as first (e.g., PoC → PoC or RPP → RPP)
- **second_break_opposite**: Second break on OPPOSITE side from first (e.g., PoC → RPP or RPP → PoC)
- **resolved**: After second TO return (session complete)

## Querying by Break Type

**Same-side breaks (single-sided sessions):**
- First break: PoC, Second break: PoC → `event_type = 'second_break_same'`
- First break: RPP, Second break: RPP → `event_type = 'second_break_same'`

**Opposite-side breaks (double-sided sessions):**
- First break: PoC, Second break: RPP → `event_type = 'second_break_opposite'`
- First break: RPP, Second break: PoC → `event_type = 'second_break_opposite'`

**Example Query:**
```sql
-- Find all single-sided sessions (second breaks on same side)
SELECT session_name, poi_type, event_type, es_event_time, nq_event_time
FROM poi_events
WHERE event_type = 'second_break_same'
ORDER BY created_at DESC;
```
