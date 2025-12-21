# Formulas Reference

All calculation formulas used in the Lipstick Trading System in one place.

---

## Range Calculations

### True Open (TO)

**For sessions using 'open' price:**
```
TO = open_price[to_time_candle]
```

**For sessions using 'close' price:**
```
TO = close_price[to_time_candle]
```

**For sessions using previous day close:**
```
TO = close_price[previous_trading_day @ 16:59]
```

**Sessions by Type:**
- **Major sessions**: Use 'open'
- **Minor sessions**: Use 'close'
- **Weekly sessions**: Use 'open'
- **Monthly sessions**: Use 'open'
- **Yearly sessions**: Use 'open'
- **Special cases**: Asia and m1800 use previous day close

---

### Point of Control (PoC)

**Formula:**
```
highest_high = max(candle.high for each candle in PoC_window)
lowest_low = min(candle.low for each candle in PoC_window)

variance_high = abs(highest_high - TO)
variance_low = abs(lowest_low - TO)

PoC = highest_high  if variance_high > variance_low
      lowest_low    if variance_low >= variance_high
```

**Python:**
```python
PoC = highest_high if abs(highest_high - TO) > abs(lowest_low - TO) else lowest_low
```

**PoC Window:**
```
Start: PoC_start_time
End: to_time - 1 minute (exclusive of TO candle)
```

---

### Range Projection Point (RPP)

**Formula:**
```
RPP = 2 * TO - PoC
```

**Verification:**
```
distance_poc_to_to = abs(PoC - TO)
distance_to_to_rpp = abs(TO - RPP)

# These should be equal
distance_poc_to_to == distance_to_to_rpp
```

**Example:**
```
PoC = 5920.00
TO = 5935.00
RPP = 2 * 5935.00 - 5920.00 = 5950.00

Verify:
abs(5920 - 5935) = 15
abs(5935 - 5950) = 15  ✓
```

---

## Touch Detection

### PoC Touch

```
PoC_touched = (candle.low <= PoC <= candle.high)
```

### RPP Touch

```
RPP_touched = (candle.low <= RPP <= candle.high)
```

### TO Touch

```
TO_touched = (candle.low <= TO <= candle.high)
```

**Python:**
```python
def is_touched(price_level, candle):
    return candle['low'] <= price_level <= candle['high']
```

---

## Echo Chamber Metrics

### Time Delta

**Formula:**
```
time_delta_seconds = abs(es_event_time - nq_event_time)
```

**In seconds:**
```python
es_time = parse_iso_timestamp(es_event_time)
nq_time = parse_iso_timestamp(nq_event_time)
time_delta_seconds = abs((es_time - nq_time).total_seconds())
```

---

### Leader Determination

**Formula:**
```
leader = 'simultaneous'  if time_delta_seconds < 60
         'ES'            if es_event_time < nq_event_time
         'NQ'            if nq_event_time < es_event_time
```

**Python:**
```python
if time_delta_seconds < 60:
    leader = 'simultaneous'
elif es_time < nq_time:
    leader = 'ES'
else:
    leader = 'NQ'
```

---

## Swing Metrics

### Points from Prior Swing

**Formula:**
```
points_from_prior = abs(swing_price - prior_opposite_swing_price)
```

**Example:**
```
Current swing: High at 5950.00
Prior swing: Low at 5920.00
points_from_prior = abs(5950.00 - 5920.00) = 30.00
```

---

### Candles from Prior Swing

**Formula:**
```
candles_from_prior = count(candles between prior_swing_time and current_swing_time)
```

**Python:**
```python
def count_candles_between(start_time, end_time):
    candles = query_candles_in_range(start_time, end_time)
    return len(candles)
```

---

## Resolution Type

### Determination

**Formula:**
```
resolution_type = 'single_sided'    if first_break_side == second_break_side
                  'double_sided'    if first_break_side != second_break_side
```

**Python:**
```python
if first_break_side == second_break_side:
    resolution_type = 'single_sided'
else:
    resolution_type = 'double_sided'
```

---

## Trading Day Calculation

### Trading Day from Timestamp

**Formula:**
```
IF time is 00:00 to 16:59:
    trading_day = calendar_date

IF time is 18:00 to 23:59:
    trading_day = calendar_date + 1 day
```

**Python:**
```python
def get_trading_day(timestamp):
    dt = parse_iso_timestamp(timestamp)

    if dt.hour < 18:
        return dt.date().isoformat()  # YYYY-MM-DD
    else:
        next_day = dt.date() + timedelta(days=1)
        return next_day.isoformat()
```

**Examples:**
```
Event at 2025-12-16T09:15:00-05:00 → trading_day = '2025-12-16'
Event at 2025-12-15T18:00:00-05:00 → trading_day = '2025-12-16'
Event at 2025-12-16T23:45:00-05:00 → trading_day = '2025-12-17'
```

---

## Session Expiry

### Minor Session Expiry

**Formula:**
```
expires_at = to_time + 24 hours
```

**Python:**
```python
from datetime import timedelta

expires_at = to_time + timedelta(hours=24)
```

**Example:**
```
m0900 TO time: 2025-11-27T09:22:00-05:00
expires_at: 2025-11-28T09:22:00-05:00
```

---

### Major/Weekly/Monthly/Yearly Expiry

**Formula:**
```
expires_at = NULL  # Never expires
```

---

## Session Activity Check

### Is Session Active?

**Formula:**
```
is_active = (current_time >= to_time)
            AND (status != 'resolved')
            AND ((expires_at IS NULL) OR (current_time < expires_at))
```

**Python:**
```python
def is_session_active(session, current_time):
    if current_time < session.to_time:
        return False  # Range not yet defined

    if session.status == 'resolved':
        return False  # Session complete

    if session.expires_at is not None:
        if current_time >= session.expires_at:
            return False  # Expired

    return True
```

---

## Swing Classification

### Class 1 (3-Bar Pivot)

**High:**
```
is_class1_high = (high[i] > high[i-1]) AND (high[i] > high[i+1])
```

**Low:**
```
is_class1_low = (low[i] < low[i-1]) AND (low[i] < low[i+1])
```

---

### Class 2

**High:**
```
is_class2_high = is_class1_high
                 AND (has_class1_low_before)
                 AND (has_class1_low_after)
```

**Low:**
```
is_class2_low = is_class1_low
                AND (has_class1_high_before)
                AND (has_class1_high_after)
```

---

### Class 3

**High:**
```
is_class3_high = is_class2_high
                 AND (has_class2_high_before)
                 AND (has_class2_high_after)
```

**Low:**
```
is_class3_low = is_class2_low
                AND (has_class2_low_before)
                AND (has_class2_low_after)
```

---

### Class 4

**High:**
```
is_class4_high = is_class3_high
                 AND (has_class3_high_before)
                 AND (has_class3_high_after)
```

**Low:**
```
is_class4_low = is_class3_low
                AND (has_class3_low_before)
                AND (has_class3_low_after)
```

---

## Weekend Handling

### Previous Day Close (Skip Weekends)

**Formula:**
```
prev_day = current_day - 1 day

if prev_day.weekday == Sunday:
    prev_day = prev_day - 2 days  # Friday

if prev_day.weekday == Saturday:
    prev_day = prev_day - 1 day  # Friday

prev_close = close_price[prev_day @ 16:59]
```

---

## Related Documentation

- [Calculation Logic](../technical/calculation-logic.md) - Detailed calculation algorithms
- [Session Tables](session-tables.md) - All session timings
- [State Machine](state-machine.md) - Status transitions
- [Glossary](glossary.md) - Term definitions
