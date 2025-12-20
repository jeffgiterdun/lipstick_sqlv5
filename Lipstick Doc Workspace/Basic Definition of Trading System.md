# Basic Definition of Trading System - READ ME

### Introduction:

What is the Lipstick trading system? The Lipstick system is a tool to observe price movements in the market referenced by price/time segments. The reason why this is relevant information is that it would appear that price action (driven by algorithms) references these price time levels and reacts somewhat predictably. Using the lipstick system and studying the patterns will provide beneficial anticipations in price action.

### Understanding Sessions:

Sessions are groups of time. We have four categories of sessions: **Major, Minor, Weekly, and Monthly**. Price is fractal, and we have layers of price segments. Each session segment of time is used to define ranges; the range is made up of three points: PoC's (Point of Control), RPP's (Range Projection Points), and TO's (True Opens).

1. **Major Ranges** are used for trade setups and building narrative
2. **Minor Ranges** are for trade execution and confluence
3. **Weekly Ranges** provide multi-day context and higher timeframe structure
4. **Monthly Ranges** provide the longest timeframe context and highest significance levels

### Session Tracking Duration:

- **Major sessions**: Track indefinitely until resolved (can remain active across multiple days)
- **Weekly sessions**: Track indefinitely until resolved (typically span multiple days)
- **Monthly sessions**: Track indefinitely until resolved (typically span multiple weeks)
- **Minor sessions**: Track for 24 hours after True Open is established, then expire

### Session Hierarchy and Importance:

The sessions follow a hierarchy of significance:
- **Monthly** (highest significance - longest timeframe)
- **Weekly** (high significance - multi-day timeframe)
- **Major** (significant - single to multi-day timeframe)
- **Minor** (execution timeframe - intraday)

Each session type serves a specific function. Major, Weekly, and Monthly sessions are the most important for Points of Interest and can remain active across multiple trading days until they reach "resolved" status. Minor sessions provide intraday execution context and confluence.

### Major Sessions (5 per trading day):

Major sessions are the largest intraday segments of time. There are 5 major sessions in a full trading day. Most commonly Asia, London, and New York AM are used for trade setups within the current trading day. New York PM and Afternoon sessions are used for setups in the next day. This is not a rule, however it is a common occurrence.

**Major Session Table:**

| Session Title | Start Looking for PoC | True Open Time | Start Time | End Time |
| --- | --- | --- | --- | --- |
| Asia | Closing Price of previous Day | Open of 19:30 | 18:00 | 23:59 |
| London | Opening of 00:00 candle | Open of 01:30 | 00:00 | 05:59 |
| NY AM | Opening of 06:00 candle | Open of 07:30 | 06:00 | 11:59 |
| NY PM | Opening of 12:00 candle | Open of 13:30 | 12:00 | 16:59 |
| Afternoon | Opening of 13:30 candle | Open of 15:00 | 13:30 | 16:59 |

### Minor Sessions (16 per trading day):

Minor sessions are 90-minute segments of the day. Every 90-minute segment is a Minor session. We start the day at 18:00 and the day ends at 16:59 the next day. This follows the traditional indices futures trading day.

**Minor Session Table:**

| Session Title | Start Looking for PoC | True Open Time | Start Time | End Time |
| --- | --- | --- | --- | --- |
| m1800 | Closing price of previous day | Close of 18:22 candle | 18:00 | 19:29 |
| m1930 | Opening of 19:30 candle | Close of 19:52 candle | 19:30 | 20:59 |
| m2100 | Opening of 21:00 candle | Close of 21:22 candle | 21:00 | 22:29 |
| m2230 | Opening of 22:30 candle | Close of 22:52 candle | 22:30 | 23:59 |
| m0000 | Opening of 00:00 candle | Close of 00:22 candle | 00:00 | 01:29 |
| m0130 | Opening of 01:30 candle | Close of 01:52 candle | 01:30 | 02:59 |
| m0300 | Opening of 03:00 candle | Close of 03:22 candle | 03:00 | 04:29 |
| m0430 | Opening of 04:30 candle | Close of 04:52 candle | 04:30 | 05:59 |
| m0600 | Opening of 06:00 candle | Close of 06:22 candle | 06:00 | 07:29 |
| m0730 | Opening of 07:30 candle | Close of 07:52 candle | 07:30 | 08:59 |
| m0900 | Opening of 09:00 candle | Close of 09:22 candle | 09:00 | 10:29 |
| m1030 | Opening of 10:30 candle | Close of 10:52 candle | 10:30 | 11:59 |
| m1200 | Opening of 12:00 candle | Close of 12:22 candle | 12:00 | 13:29 |
| m1330 | Opening of 13:30 candle | Close of 13:52 candle | 13:30 | 14:59 |
| m1500 | Opening of 15:00 candle | Close of 15:22 candle | 15:00 | 16:29 |
| m1630 | Opening of 16:30 candle | Close of 16:52 candle | 16:30 | 16:59 |

**Note:** m1630 is only 30 minutes duration (not the standard 90 minutes).

### Weekly Session:

The Weekly session provides multi-day structure and context. There is one active Weekly session at any given time.

**Weekly Session Calculation:**

- **PoC Tracking Begins:** Sunday 18:00 (the first candle of the Monday trading day)
- **True Open (TO):** Opening price of the Monday 18:00 candle (the first candle of the Tuesday trading day)
- **Range Calculation:** We look for the highest high or lowest low from Sunday 18:00 until the Monday 18:00 candle (exclusive) that gives the greatest variance from the TO price. This point is the PoC.
- **Duration:** Tracks indefinitely until the session reaches "resolved" status

**Important:** Until the Monday 18:00 candle opens, the Weekly session does not have a defined range (TO, PoC, RPP are not yet calculable).

### Monthly Session:

The Monthly session provides the longest timeframe context and highest significance levels. There is one active Monthly session at any given time.

**Monthly Session Calculation:**

- **PoC Tracking Begins:** First full trading day of the month (Sunday evening 18:00 is included if it falls within the first trading day)
- **True Open (TO):** Opening price of the Sunday 18:00 candle that begins the second full week of the month
- **Range Calculation:** We look for the highest high or lowest low from the first full trading day until the TO candle (exclusive) that gives the greatest variance from the TO price. This point is the PoC.
- **Duration:** Tracks indefinitely until the session reaches "resolved" status

**Determining the "Second Full Week":**
- If the 1st of the month falls on Saturday, Sunday, or Monday → that week is the first full week
- If the 1st of the month falls on Tuesday, Wednesday, Thursday, or Friday → that is NOT a full week; the following week is the first full week
- The TO is set at the Sunday 18:00 candle that begins the week AFTER the first full week

**Important:** Until the second full week begins, the Monthly session does not have a defined range (TO, PoC, RPP are not yet calculable).

---

## Definition of Terms:

### 1. True Opens (TO)

True opens are very important time and price points that we use to evaluate and create session ranges. We look for price action to return to True Open as they serve as magnets for price. They are believed to be specific time/price/asset alignment tools and work hand in hand with OOO's (order of operations, 3o's) instructions.

- **Major True Opens:** Extended from the inception point throughout the trading day and beyond until resolved
- **Weekly True Opens:** Extended from inception indefinitely until resolved
- **Monthly True Opens:** Extended from inception indefinitely until resolved
- **Minor True Opens:** Extended from inception for 24 hours
- In some cases, a return to a True Open represents a completion of a task or set of instructions in the OOO's

### 2. Ranges

A range is a boundary identified by a symmetrical horizontal plane. Ranges are made of 3 price points extended in time:
- **True Open (TO)** - the middle
- **Point of Control (PoC)** - one boundary
- **Range Projection Point (RPP)** - opposite boundary

The price action range established from the identified time segments is where we look for reactions at these levels. We track touch points and set session status based on the touches and breaks throughout the tracking period.

**Range Calculation Process:**

1. **PoC Tracking Window:** From the "Start Looking for PoC" time until the True Open time (exclusive of TO candle), we record the highest high and lowest low.

2. **Point of Control (PoC) Determination:** At the True Open time, we can set our range. The PoC is set using whichever extreme (highest high OR lowest low) has the largest variance from the TO price.
   - Calculate: `variance_high = abs(highest_high - TO)`
   - Calculate: `variance_low = abs(lowest_low - TO)`
   - If `variance_high > variance_low`: PoC = highest_high
   - If `variance_low >= variance_high`: PoC = lowest_low

3. **Range Projection Point (RPP) Calculation:** Once we know the PoC and TO, we extend the range to project the RPP. The RPP is a mirror of the range (distance between PoC and TO) projected on the opposite side of TO.
   - Formula: `RPP = 2 * TO - PoC`
   - Or using Fibonacci: 0% anchored on PoC, 50% on TO, 100% is the RPP
   - This creates a symmetrical range with TO in the center

### 3. Tracking Session Status

Our market premise is based on a **break and return model**. A range is established at the True Open time with an "unbroken" status—this is the default status. At that point in time we begin watching for a break of either the PoC or RPP of that range.

**Status Progression:**

**Unbroken → Break:**
- With a simple touch of any kind on the price levels identified as PoC or RPP, the status advances to "break"
- We record which side was broken first (PoC or RPP)

**Break → Return:**
- Only after a break of the RPP or PoC do we begin looking for a touch of the True Open price level
- A single break of the range boundary and touch of the True Open is classified as "return" status

**Return → Resolved:**
- After reaching return status, we watch for a second break (can be same side or opposite side)
- Once the second break occurs and price returns to TO again, the session reaches "resolved" status

**Resolution Types:**
- **Single Sided Resolution:** Both breaks occurred on the same side (PoC→PoC or RPP→RPP)
- **Double Sided Resolution:** Breaks occurred on opposite sides (PoC→RPP or RPP→PoC)

**Critical Rule:** Major, Weekly, and Monthly sessions track indefinitely until reaching "resolved" status. Minor sessions track for 24 hours after TO is established.

### 4. Order of Operations (3o's, OOO's)

Order of Operations is the term used to describe the narrative theory of the market. The market operates with a checklist of events or steps. We move from one step to the next after a return or resolution. A resolution is the return to a True Open after a break of the range associated with that True Open.

**Key Concepts:**
- Order of Operations moves are very specific to the day's events and are the hardest part to document and understand
- They happen all day long every day but need a clever way to simplify and keep track of
- The theory is that a resolution of one event will then trigger a resolution of an event previous
- There is a checklist of unreturned or unresolved ranges that were created as a result of the attack of an older session resolution
- Once one event is resolved, we look back to see what the next logical session chronologically needs attending to

**Hierarchy Consideration:**
- Monthly session resolutions are the most significant events
- Weekly session resolutions are highly significant
- Major session resolutions provide daily structure
- Minor session resolutions provide intraday execution context

### 5. "The Echo Chamber"

Correlative analysis between ES and NQ. Although ES and NQ appear to be highly correlated assets, we look for session status discrepancies that tip the hand of the algorithm. By following the status of both assets we can use this information to frame trades.

**The Core Principle:** The market has a desire to synchronize all assets—this is the secret to why markets move.

**Echo Chamber Analysis:**
- Track the same session across both ES and NQ simultaneously
- Identify when one instrument breaks a level while the other remains unbroken
- Identify when one instrument returns to TO while the other hasn't
- These divergences create high-probability opportunities as the instruments eventually realign
- The instrument that moves first often "leads" the other to follow

**Example Divergence Scenario:**
- ES breaks London PoC at 09:15 (status: break)
- NQ doesn't break London PoC until 09:45 (status: unbroken for 30 minutes)
- This 30-minute divergence represents an opportunity
- Once NQ finally breaks, we expect both instruments to move toward synchronization

---

## Summary

The Lipstick Trading System tracks four timeframes of sessions:
- **Monthly:** Longest timeframe, highest significance, tracks until resolved
- **Weekly:** Multi-day timeframe, high significance, tracks until resolved  
- **Major:** Daily timeframe (5 sessions per day), tracks until resolved
- **Minor:** Intraday timeframe (16 sessions per day), tracks for 24 hours

Each session defines a range with three critical price levels (PoC, TO, RPP) and progresses through status states (unbroken → break → return → resolved) based on price interaction with those levels. The Echo Chamber methodology compares ES and NQ session statuses simultaneously to identify divergences that create trading opportunities.