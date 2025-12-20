# Edge Cases and Special Scenarios

Comprehensive guide to handling missing data, gaps, special calendar events, and other edge cases in the Lipstick Analytical Tool V5.

---

## Table of Contents

1. [Missing Data](#missing-data)
2. [Data Gaps](#data-gaps)
3. [Calendar and Timezone](#calendar-and-timezone)
4. [Multi-Level Events](#multi-level-events)
5. [Echo Chamber Edge Cases](#echo-chamber-edge-cases)
6. [Swing Detection Edge Cases](#swing-detection-edge-cases)
7. [Session Boundary Edge Cases](#session-boundary-edge-cases)

---

## Missing Data

### Missing Candles During PoC Calculation

**Rule:** If any candles missing in the window from PoC Start to TO Time:
- Set: `true_open = NULL`, `poc = NULL`, `rpp = NULL`
- Insert session record with NULL values
- Set: `status = 'unbroken'`
- Do NOT process POI events for this session (skip in `is_session_active()`)

**Rationale:** Cannot calculate range without complete data.

**Example:**
```python
# London session 00:00 - 01:30
# Missing candles: 00:45, 00:46, 00:47

# Result:
sessions.insert({
    'session_name': 'London',
    'true_open': None,
    'poc': None,
    'rpp': None,
    'status': 'unbroken'
})
# This session will be skipped in POI processing
```

---

### Missing True Open Candle

**Rule:** If the TO candle doesn't exist:
- Set: `true_open = NULL`, `poc = NULL`, `rpp = NULL`
- Insert session record with NULL values
- Session remains inactive (will be skipped for POI processing)

**Example:**
```python
# m0900 TO time: 09:22
# 09:22 candle missing from database

# Result: Session created with NULL values, never becomes active
```

---

### Partial Trading Days

**Rule:** Process whatever sessions have complete data.
- Some sessions may have valid ranges while others have NULL
- Each session is independent
- Database will contain mix of valid and NULL sessions

**Example:**
- Data starts at 2025-11-27T12:00:00
- **Asia, London, NY_AM**: NULL (no data for calculation windows)
- **NY_PM, Afternoon**: Valid ranges ✓
- **Minor sessions m1200 onward**: Valid ranges ✓

---

## Data Gaps

### Multi-Day Data Gaps

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

**Example:**
```python
# Before gap (Nov 27):
# - London session status = 'break'
# - m0900 session expires_at = Nov 28 09:22

# After gap (Dec 1):
# - London session still active (expires_at = NULL)
# - m0900 session excluded (expired)
```

---

### Weekend Gaps

**Handling:** Normal behavior. Markets closed Saturday/Sunday.

**Weekly Session Behavior:**
- Weekly session starts Sunday 18:00
- No candles Saturday 17:00 - Sunday 17:59
- This is expected (markets closed)
- Weekly TO set at Monday 18:00

**Monthly Session:**
- If month starts on weekend, logic correctly determines first trading day
- See [Monthly Session Calculation](calculation-logic.md#monthly-session)

---

## Calendar and Timezone

### Daylight Saving Time (DST) Transitions

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
- **Spring forward:** Second Sunday in March (EDT begins)
- **Fall back:** First Sunday in November (EST begins)

**Session Calculation:** No special handling needed - use the actual timestamps from the data.

---

### Holidays and Market Closures

**Issue:** Markets closed for holidays (e.g., Thanksgiving, Christmas).

**Handling:**
- Missing data handled same as any other missing data scenario
- Sessions on holiday will have NULL ranges
- This is correct behavior

**Special Case - Early Close Days:**
- Some holidays close early (e.g., 13:00 instead of 16:59)
- Afternoon sessions may be incomplete
- Handle as partial trading day

---

## Multi-Level Events

### Same-Candle Multiple Events

**Scenario:** One candle touches PoC, TO, and RPP for same session.

**Handling:**
- Process each touch sequentially
- State machine may generate multiple events
- All events have same `event_time` (the candle timestamp)
- Multiple rows in `poi_events` for the same session (different poi_type or event_type)

**Example:**
```python
# Candle: 2025-11-27T09:15:00-05:00
# Touches: London PoC, London TO, London RPP

# Results:
# - poi_events row 1: (London, PoC, break, 09:15)
# - poi_events row 2: (London, TO, return, 09:15)
# - poi_events row 3: (London, RPP, break, 09:15)

# Session status progression:
# unbroken → break (PoC) → return (TO) → return (RPP touch ignored, already in return)
```

---

## Echo Chamber Edge Cases

### Incomplete Echo Chamber Data

**Scenario:** ES touches a POI level, but NQ never touches it.

**Handling:**
- `poi_events` row has `es_event_time` populated, `nq_event_time = NULL`
- `time_delta_seconds = NULL`
- `leader = NULL`
- This is valid data - represents divergence that never converged

**Query Implication:**
- Can identify "orphaned" touches where only one instrument hit the level
- This itself is meaningful (extreme divergence)

**Example:**
```sql
-- Find extreme divergences (one instrument touched, other didn't)
SELECT * FROM poi_events
WHERE (es_event_time IS NULL AND nq_event_time IS NOT NULL)
   OR (es_event_time IS NOT NULL AND nq_event_time IS NULL);
```

---

### Simultaneous Touches

**Scenario:** ES and NQ touch within same minute.

**Handling:**
- `time_delta_seconds` calculated normally (even if < 60)
- `leader` set to 'simultaneous' if time_delta < 60 seconds
- This indicates strong correlation/synchronization

**Example:**
```python
# ES: 09:15:23
# NQ: 09:15:45
# time_delta_seconds = 22
# leader = 'simultaneous'
```

---

## Swing Detection Edge Cases

### Swings at Data Boundaries

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

### POI Event Linking Ambiguity

**Issue:** Swing occurs near multiple POI events - which one to link?

**Current Logic:** Link to closest event in time (within ±5 minutes, ±5 ticks).

**If no events match criteria:**
- `nearest_poi_event_id = NULL`
- Swing is unlinked (may be noise or unrelated to POI activity)

**If multiple events match:**
- Choose event closest in time (minimize time delta)

**Example:**
```python
# Swing at 09:30:00
# POI Event 1 at 09:27:30 (PoC break)
# POI Event 2 at 09:32:15 (TO return)

# Time deltas:
# Event 1: 150 seconds (2.5 min) ✓
# Event 2: 135 seconds (2.25 min) ✓ closest

# Link to Event 2
```

---

## Session Boundary Edge Cases

### Weekly Session Crossing Month Boundary

**Scenario:** Weekly session starts in November, resolves in December.

**Handling:**
- `session_start_time = 2025-11-23T18:00:00-05:00` (November)
- `resolution_time = 2025-12-03T09:15:00-05:00` (December)
- No special handling needed - sessions are not month-constrained

---

### Monthly Session Crossing Year Boundary

**Scenario:** December monthly session starts Dec 1, resolves Jan 15.

**Handling:**
- `session_start_time = 2025-12-01T18:00:00-05:00` (December)
- `resolution_time = 2026-01-15T14:30:00-05:00` (January, next year)
- No special handling needed - sessions are not year-constrained

---

### Overlapping Sessions

**Scenario:** Afternoon session (13:30-16:59) overlaps with NY_PM session (12:00-16:59).

**Handling:**
- Both sessions are independent
- Both can be active simultaneously
- Each tracks its own range and status
- This is correct behavior - sessions can overlap

**Example:**
```python
# At 14:00:
# - NY_PM (12:00-16:59): status = 'break'
# - Afternoon (13:30-16:59): status = 'unbroken'

# Both sessions are active and tracking independently
```

---

## Time Parsing Edge Cases

### Zero-Padded Times

**Rule:** Always use zero-padded format (09:00, not 9:00)

**Example:**
```python
# Correct:
'2025-11-27T09:00:00-05:00'

# Incorrect:
'2025-11-27T9:00:00-05:00'
```

---

### Microseconds

**Handling:** Ignore if present (truncate to seconds)

**Example:**
```python
# Input: '2025-11-27T09:15:23.456789-05:00'
# Store: '2025-11-27T09:15:23-05:00'
```

---

### Timezone Ambiguity

**Rule:** Always include timezone offset in stored timestamps

**Example:**
```python
# Correct:
'2025-11-27T09:15:00-05:00'  # EST
'2025-06-15T09:15:00-04:00'  # EDT

# Incorrect:
'2025-11-27T09:15:00'  # Missing timezone
```

---

## Session Cleanup / Archival

**Question:** Do we ever mark old unresolved sessions as "abandoned"?

**Options:**
1. **Never** - let them stay active indefinitely (purist approach)
2. **After N days** - mark as 'abandoned' if not resolved within reasonable timeframe
3. **Manual** - you decide when to archive old sessions

**Recommendation for V5:** Keep them active indefinitely. You can always add cleanup logic later if database grows too large.

**Current Behavior:**
- Sessions remain active until resolved
- Could have sessions active for weeks/months
- Database grows continuously (never deletes)
- Index on `(symbol, status, expires_at)` critical for performance

---

## Next Steps

- [Calculation Logic](calculation-logic.md) - Detailed calculation algorithms
- [Processing Algorithm](processing-algorithm.md) - Implementation guide
- [Database Schema](database-schema.md) - Table structure reference
- [Development Guide](../development/implementation-phases.md) - Build phases and checklist
