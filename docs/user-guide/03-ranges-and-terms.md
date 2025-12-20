# Ranges and Key Terms

## What is a Range?

A range is a boundary identified by a symmetrical horizontal plane. Ranges are made of 3 price points extended in time:
- **True Open (TO)** - the middle
- **Point of Control (PoC)** - one boundary
- **Range Projection Point (RPP)** - opposite boundary

The price action range established from the identified time segments is where we look for reactions at these levels. We track touch points and set session status based on the touches and breaks throughout the tracking period.

---

## 1. True Opens (TO)

### Definition

True opens are very important time and price points that we use to evaluate and create session ranges. We look for price action to return to True Open as they serve as magnets for price. They are believed to be specific time/price/asset alignment tools and work hand in hand with OOO's (order of operations, 3o's) instructions.

### Tracking Duration by Session Type

- **Major True Opens:** Extended from the inception point throughout the trading day and beyond until resolved
- **Weekly True Opens:** Extended from inception indefinitely until resolved
- **Monthly True Opens:** Extended from inception indefinitely until resolved
- **Minor True Opens:** Extended from inception for 24 hours

### Significance

In some cases, a return to a True Open represents a completion of a task or set of instructions in the OOO's (Order of Operations).

---

## 2. Point of Control (PoC)

### Definition

The Point of Control is the price level with the highest variance from the True Open during the PoC calculation window. It represents one boundary of the range.

### PoC Calculation Window

From the "Start Looking for PoC" time until the True Open time (exclusive of TO candle), we record the highest high and lowest low.

### Calculation Process

1. Track `highest_high` and `lowest_low` across all candles in the window
2. Calculate: `variance_high = abs(highest_high - TO)`
3. Calculate: `variance_low = abs(lowest_low - TO)`
4. If `variance_high > variance_low`: PoC = highest_high
5. If `variance_low >= variance_high`: PoC = lowest_low

**Formula:**
```
PoC = highest_high if abs(highest_high - TO) > abs(lowest_low - TO) else lowest_low
```

### Example

**London Session:**
- PoC Calculation Window: 00:00 to 01:29
- During this window:
  - highest_high = 5950.00
  - lowest_low = 5920.00
  - TO (01:30 open) = 5935.00

Calculate variance:
- variance_high = abs(5950.00 - 5935.00) = 15.00
- variance_low = abs(5920.00 - 5935.00) = 15.00

Since variance_low >= variance_high:
- **PoC = 5920.00** (the low side)

---

## 3. Range Projection Point (RPP)

### Definition

The Range Projection Point is a mirror projection of the PoC distance on the opposite side of the True Open. It represents the opposite boundary of the range.

### Formula

```
RPP = 2 * TO - PoC
```

### Verification

Distance from PoC to TO equals distance from TO to RPP.

### Example

Continuing the London example:
- PoC = 5920.00
- TO = 5935.00
- RPP = 2 * 5935.00 - 5920.00 = **5950.00**

Verify:
- Distance PoC→TO: |5920.00 - 5935.00| = 15.00
- Distance TO→RPP: |5935.00 - 5950.00| = 15.00 ✓

The range is symmetrical: **PoC (5920.00) ← TO (5935.00) → RPP (5950.00)**

---

## 4. Session Status Tracking

### The Break and Return Model

Our market premise is based on a **break and return model**. A range is established at the True Open time with an "unbroken" status—this is the default status. At that point in time we begin watching for a break of either the PoC or RPP of that range.

### Status Progression

#### Unbroken → Break
- With a simple touch of any kind on the price levels identified as PoC or RPP, the status advances to "break"
- We record which side was broken first (PoC or RPP)

#### Break → Return
- Only after a break of the RPP or PoC do we begin looking for a touch of the True Open price level
- A single break of the range boundary and touch of the True Open is classified as "return" status

#### Return → Resolved
- After reaching return status, we watch for a second break (can be same side or opposite side)
- Once the second break occurs and price returns to TO again, the session reaches "resolved" status

### Resolution Types

- **Single Sided Resolution:** Both breaks occurred on the same side (PoC→PoC or RPP→RPP)
- **Double Sided Resolution:** Breaks occurred on opposite sides (PoC→RPP or RPP→PoC)

### Critical Rule

Major, Weekly, and Monthly sessions track indefinitely until reaching "resolved" status. Minor sessions track for 24 hours after TO is established.

---

## Touch Detection

### What is a "Touch"?

A price level is considered "touched" when it falls within the candle's high-low range.

**Touch Formulas:**
```
PoC_touched = (candle_low <= PoC <= candle_high)
RPP_touched = (candle_low <= RPP <= candle_high)
TO_touched = (candle_low <= TO <= candle_high)
```

### Multiple Level Touches

If one candle touches multiple levels, all events are recorded with the same timestamp.

**Example:**
A candle with high=5950, low=5920 touches PoC=5945, TO=5935, and RPP=5925:
- Record: PoC break event
- Record: TO return event
- Record: RPP break event
- All with the same timestamp

---

## State Machine Summary

| Current State | Event | Records | Next State |
|---------------|-------|---------|------------|
| unbroken | Touch PoC or RPP | first_break_time, first_break_side | break |
| break | Touch PoC or RPP (repeat) | Nothing (ignore) | break |
| break | Touch TO | first_return_time | return |
| return | Touch PoC or RPP | second_break_time, second_break_side | return |
| return | Touch PoC or RPP (repeat) | Nothing (ignore) | return |
| return | Touch TO | resolution_time, resolution_type | resolved |
| resolved | Any touch | Nothing (session complete) | resolved |

---

## Next Steps

- [Order of Operations](04-order-of-operations.md) - Understanding market narrative
- [Echo Chamber Analysis](05-echo-chamber.md) - ES/NQ correlation strategies
- [Session Tables (Reference)](../reference/session-tables.md) - Quick reference for all session timings
- [Formulas (Reference)](../reference/formulas.md) - All calculation formulas in one place
