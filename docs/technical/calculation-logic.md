# Calculation Logic

Complete specification of all calculation algorithms used in the Lipstick Analytical Tool V5.

---

## Table of Contents

1. [Range Calculation](#range-calculation)
2. [Touch Detection](#touch-detection)
3. [State Machine Logic](#state-machine-logic)
4. [Session Activity Rules](#session-activity-rules)
5. [Echo Chamber Metrics](#echo-chamber-metrics)
6. [Swing Classification](#swing-classification)

---

## Range Calculation

### True Open (TO)

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

### Point of Control (PoC)

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

### Range Projection Point (RPP)

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

### Weekend Handling for Previous Day Close

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

## Touch Detection

### Touch Definition

A price level is "touched" when it falls within the candle's high-low range.

**Formulas:**
```python
PoC_touched = (candle_low <= PoC <= candle_high)
RPP_touched = (candle_low <= RPP <= candle_high)
TO_touched = (candle_low <= TO <= candle_high)
```

### Multi-Level Touch Handling

If one candle touches multiple levels, record all events with same `event_time`.

**Example:** Candle with high=5950, low=5920, PoC=5945, TO=5935, RPP=5925
- Record: PoC break event
- Record: TO return event
- Record: RPP break event
- All with same timestamp

---

## State Machine Logic

### States and Transitions

| Current State | Event | Records | Next State |
|---------------|-------|---------|------------|
| unbroken | Touch PoC or RPP | first_break_time, first_break_side | break |
| break | Touch PoC or RPP (repeat) | Nothing (ignore) | break |
| break | Touch TO | first_return_time | return |
| return | Touch PoC or RPP | second_break_time, second_break_side | return |
| return | Touch PoC or RPP (repeat) | Nothing (ignore) | return |
| return | Touch TO | resolution_time, resolution_type | resolved |
| resolved | Any touch | Nothing (session complete) | resolved |

### Resolution Type Logic

```python
if first_break_side == second_break_side:
    resolution_type = 'single_sided'
else:
    resolution_type = 'double_sided'
```

**Single Sided:** Same side broken twice (PoC→PoC or RPP→RPP)
**Double Sided:** Both sides broken (PoC→RPP or RPP→PoC)

### Reset Logic

After recording `first_return_time`, the break tracker resets:
- Next PoC/RPP touch becomes `second_break`
- Intermediate breaks between first return and second break are ignored

---

## Session Activity Rules

### When to Process POI Events for a Session

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

### Active Sessions Query

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

## Echo Chamber Metrics

### Time Delta Calculation

When both ES and NQ have touched a POI level:

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

### Leader Classification

- **ES**: ES touched first (es_event_time < nq_event_time)
- **NQ**: NQ touched first (nq_event_time < es_event_time)
- **simultaneous**: Time delta < 60 seconds

---

## Swing Classification

### Class 1: 3-Bar Pivot

**Class 1 High:**
```python
high[i] > high[i-1] AND high[i] > high[i+1]
```

**Class 1 Low:**
```python
low[i] < low[i-1] AND low[i] < low[i+1]
```

### Class 2: Has Opposite Class 1 Swings on Both Sides

**Class 1 HIGH → Class 2 if:**
- Has Class 1 LOWs before AND after

**Class 1 LOW → Class 2 if:**
- Has Class 1 HIGHs before AND after

### Class 3: Has Same Class 2 Swings on Both Sides

**Class 2 HIGH → Class 3 if:**
- Has Class 2 HIGHs before AND after

**Class 2 LOW → Class 3 if:**
- Has Class 2 LOWs before AND after

### Class 4: Has Same Class 3 Swings on Both Sides

**Class 3 HIGH → Class 4 if:**
- Has Class 3 HIGHs before AND after

**Class 3 LOW → Class 4 if:**
- Has Class 3 LOWs before AND after

### Movement Metrics

**Points from Prior:**
```python
points_from_prior = abs(swing_price - prior_opposite_swing_price)
```

**Candles from Prior:**
```python
candles_from_prior = count_candles_between(prior_time, swing_time)
```

### POI Event Linkage

**Matching Criteria:**
- Same symbol
- POI event time within ±5 minutes of swing time
- POI event price within ±5 ticks of swing price

**If multiple matches:**
- Choose closest in time

---

## Session Calculations

### Weekly Session

**PoC Tracking Begins:** Sunday 18:00 (first candle of Monday trading day)
**True Open (TO):** Opening price of Monday 18:00 candle
**PoC Window:** Sunday 18:00 through Monday 17:59

### Monthly Session

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

**Determining the Second Full Week:**
- If the 1st falls on Saturday, Sunday, or Monday → that week is the first full week
- If the 1st falls on Tuesday, Wednesday, Thursday, or Friday → that is NOT a full week; the following week is the first full week
- The TO is set at the Sunday 18:00 candle that begins the week AFTER the first full week

---

## Next Steps

- [Processing Algorithm](processing-algorithm.md) - Implementation details
- [Edge Cases](edge-cases.md) - Handling missing data and special scenarios
- [Database Schema](database-schema.md) - Table structure reference
