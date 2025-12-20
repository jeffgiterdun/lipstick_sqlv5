# Glossary

Comprehensive definitions of all terms used in the Lipstick Trading System.

---

## A

### Active Session
A session that is currently being monitored for POI touches. A session is active when:
1. The TO time has been reached (range is defined)
2. Status is not 'resolved'
3. Session has not expired (for Minor sessions)

---

## B

### Break
The first state transition after a range is established. Occurs when price touches either the PoC or RPP for the first time. Also used as a verb: "London broke its PoC at 09:15."

### Break and Return Model
The core market premise of the Lipstick system. The theory that algorithmic price action follows a pattern of breaking range boundaries and returning to True Opens in a specific sequence.

---

## C

### Class 1 Swing
A 3-bar pivot. The most basic swing identification where a high is higher than the previous and next candle highs (or a low is lower than previous and next candle lows).

### Class 2 Swing
A Class 1 swing that has opposite-type Class 1 swings on both sides. For example, a Class 1 high with Class 1 lows before and after it.

### Class 3 Swing
A Class 2 swing that has same-type Class 2 swings on both sides. For example, a Class 2 high with Class 2 highs before and after it.

### Class 4 Swing
A Class 3 swing that has same-type Class 3 swings on both sides. The highest level of swing classification, representing major market structure.

### Confluence
The alignment of multiple factors or signals. In the Lipstick system, this might include: multiple sessions at the same status, Echo Chamber divergence, swing formation, and POI touches occurring simultaneously.

---

## D

### Double Sided Resolution
A resolution where the two breaks occurred on opposite sides of the range. For example: first break at PoC, second break at RPP (or vice versa).

### Divergence (Echo Chamber)
When ES and NQ have different session statuses or touch POI levels at different times. These discrepancies create trading opportunities as the market works to synchronize the instruments.

---

## E

### Echo Chamber
The correlative analysis methodology between ES and NQ. Based on the principle that the market desires to synchronize all assets, creating opportunities when divergences occur.

### ES
S&P 500 futures contract. One of the two primary instruments tracked in the Lipstick system.

### Expires At
The timestamp when a Minor session stops being tracked, set to TO time + 24 hours. Major, Weekly, and Monthly sessions never expire (expires_at = NULL).

---

## F

### First Break
The initial touch of either PoC or RPP after a range is established. Records: `first_break_time` and `first_break_side`.

### First Return
The first touch of the True Open after the first break. Records: `first_return_time`. Marks transition from 'break' to 'return' status.

---

## H

### Highest High
The highest price point reached during the PoC calculation window. Used to determine if PoC is on the high side.

---

## L

### Leader
In Echo Chamber analysis, the instrument that touches a POI level first. Can be 'ES', 'NQ', or 'simultaneous' (if within 60 seconds).

### Lowest Low
The lowest price point reached during the PoC calculation window. Used to determine if PoC is on the low side.

---

## M

### Major Session
One of five large intraday time segments: Asia, London, NY AM, NY PM, Afternoon. Used for trade setups and building narrative. Track indefinitely until resolved.

### Minor Session
One of sixteen 90-minute segments per trading day (m1800 through m1630). Used for trade execution and confluence. Track for 24 hours after TO, then expire.

### Monthly Session
The longest timeframe session, calculated monthly. Provides highest significance levels. Tracks indefinitely until resolved.

---

## N

### NQ
Nasdaq 100 futures contract. One of the two primary instruments tracked in the Lipstick system.

---

## O

### OOO / 3o's / Order of Operations
The narrative theory of the market. The concept that the market operates with a checklist of events or steps, moving from one task to the next after returns or resolutions.

---

## P

### PoC / Point of Control
One boundary of a session range. The price level with the highest variance from the True Open during the PoC calculation window. Can be either the highest high or lowest low of that window.

### PoC Calculation Window
The time period during which we track price action to determine the Point of Control. Starts at "Start Looking for PoC" time and ends at TO time (exclusive of TO candle).

### POI / Point of Interest
Any of the three critical price levels in a range: PoC, TO, or RPP. Points where we expect price reactions.

### POI Event
A recorded instance of price touching a POI level. Events are categorized as 'break', 'return', or 'resolution' based on the session's state at the time of the touch.

---

## R

### Range
A symmetrical boundary identified by three price levels: PoC (one boundary), TO (center), and RPP (opposite boundary). Extended in time for the duration of session tracking.

### Range Projection Point / RPP
The opposite boundary from the PoC, calculated as a mirror projection: RPP = 2 * TO - PoC. Creates a symmetrical range with TO in the center.

### Resolution
The final state of a session. Occurs when price completes a full cycle: break → return → break → return. Can be single-sided or double-sided.

### Resolution Type
Classification of how a session resolved. 'Single_sided' means both breaks were on the same side (PoC→PoC or RPP→RPP). 'Double_sided' means breaks were on opposite sides (PoC→RPP or RPP→PoC).

### Return
The second state in the session lifecycle. Occurs when price touches the True Open after the first break. Also refers to the fourth state when waiting for final resolution.

---

## S

### Second Break
The second touch of either PoC or RPP, occurring after the first return. Records: `second_break_time` and `second_break_side`.

### Session
A defined time segment used to calculate ranges and track price behavior. Four types: Major, Minor, Weekly, Monthly.

### Session Context
A JSON snapshot of all active session statuses at a specific moment in time. Captured for each swing to enable analysis of market conditions when the swing occurred.

### Single Sided Resolution
A resolution where both breaks occurred on the same side of the range (PoC→PoC or RPP→RPP).

### Status
The current state of a session in the state machine: 'unbroken', 'break', 'return', or 'resolved'.

### Swing
A price pivot point identified using hierarchical classification. Swings are classified from Class 1 (simple 3-bar pivot) to Class 4 (major market structure).

---

## T

### Time Delta
In Echo Chamber analysis, the time difference in seconds between when ES and NQ touched the same POI level.

### TO / True Open
The center point of a range. A critical time and price point that serves as a magnet for price and a checkpoint for Order of Operations. Can be calculated from open price, close price, or previous day close depending on session type.

### Touch
When a price level falls within a candle's high-low range. Formula: `(candle.low <= level <= candle.high)`

### Trading Day
The 24-hour period from 18:00 to 16:59 (next calendar day). Follows traditional indices futures trading hours. Stored in YYYY-MM-DD format (e.g., '2025-12-16'). Used in poi_events table for easy date-based filtering.

**Calculation:** If candle time is 00:00-16:59, trading_day equals calendar date. If candle time is 18:00-23:59, trading_day equals next calendar date.

---

## U

### Unbroken
The initial state of a session after its range is calculated. Indicates no touches of PoC or RPP have occurred yet.

---

## V

### Variance
The absolute distance between a price level and the True Open. Used to determine which extreme (highest high or lowest low) becomes the PoC.

---

## W

### Weekly Session
A session calculated weekly, starting Sunday 18:00. Provides multi-day context and higher timeframe structure. Tracks indefinitely until resolved.

---

## Session Status Values

| Status | Meaning |
|--------|---------|
| **unbroken** | Range established, no touches yet |
| **break** | First boundary (PoC or RPP) touched, waiting for TO return |
| **return** | Returned to TO after first break, waiting for second break and final return |
| **resolved** | Complete cycle finished, session done |

---

## Session Types

| Type | Count | Tracking Duration | Primary Use |
|------|-------|-------------------|-------------|
| **Major** | 5 per day | Indefinite | Trade setups, narrative |
| **Minor** | 16 per day | 24 hours | Execution, confluence |
| **Weekly** | 1 per week | Indefinite | Multi-day context |
| **Monthly** | 1 per month | Indefinite | Highest timeframe context |

---

## POI Event Types

| Event Type | When Created | Meaning |
|------------|--------------|---------|
| **break** | unbroken → break | First touch of PoC or RPP |
| **return** | break → return | First touch of TO after break |
| **resolution** | return → resolved | Final touch of TO completing cycle |

---

## Swing Classifications

| Class | Definition | Significance |
|-------|------------|--------------|
| **Class 1** | 3-bar pivot | Basic market noise |
| **Class 2** | Class 1 with opposite Class 1s on both sides | Minor structure |
| **Class 3** | Class 2 with same Class 2s on both sides | Significant structure |
| **Class 4** | Class 3 with same Class 3s on both sides | Major market structure |

---

## Related Documentation

- [User Guide](../user-guide/01-introduction.md) - Conceptual overview
- [Session Tables](session-tables.md) - All session timings
- [Formulas](formulas.md) - All calculation formulas
- [State Machine](state-machine.md) - Status transitions
