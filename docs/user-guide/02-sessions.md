# Session Types and Timing

## Understanding Sessions

Sessions are groups of time. We have five categories of sessions: **Major, Minor, Weekly, Monthly, and Yearly**. Each session segment of time is used to define ranges; the range is made up of three points: PoC's (Point of Control), RPP's (Range Projection Points), and TO's (True Opens).

## Session Functions

1. **Major Ranges** are used for trade setups and building narrative
2. **Minor Ranges** are for trade execution and confluence
3. **Weekly Ranges** provide multi-day context and higher timeframe structure
4. **Monthly Ranges** provide the longest timeframe context and highest significance levels
5. **Yearly Ranges** provide the absolute highest timeframe context across the entire year

## Session Tracking Duration

- **Major sessions**: Track indefinitely until resolved (can remain active across multiple days)
- **Weekly sessions**: Track indefinitely until resolved (typically span multiple days)
- **Monthly sessions**: Track indefinitely until resolved (typically span multiple weeks)
- **Yearly sessions**: Track indefinitely until resolved (typically span multiple months)
- **Minor sessions**: Track for 24 hours after True Open is established, then expire

## Session Hierarchy and Importance

The sessions follow a hierarchy of significance:
- **Yearly** (absolute highest significance - full year timeframe)
- **Monthly** (highest significance - longest monthly timeframe)
- **Weekly** (high significance - multi-day timeframe)
- **Major** (significant - single to multi-day timeframe)
- **Minor** (execution timeframe - intraday)

Each session type serves a specific function. Major, Weekly, Monthly, and Yearly sessions are the most important for Points of Interest and can remain active across multiple trading days until they reach "resolved" status. Minor sessions provide intraday execution context and confluence.

---

## Major Sessions (5 per trading day)

Major sessions are the largest intraday segments of time. There are 5 major sessions in a full trading day. Most commonly Asia, London, and New York AM are used for trade setups within the current trading day. New York PM and Afternoon sessions are used for setups in the next day. This is not a rule, however it is a common occurrence.

### Major Session Table

| Session Title | Start Looking for PoC | True Open Time | Start Time | End Time |
| --- | --- | --- | --- | --- |
| Asia | Closing Price of previous Day | Open of 19:30 | 18:00 | 23:59 |
| London | Opening of 00:00 candle | Open of 01:30 | 00:00 | 05:59 |
| NY AM | Opening of 06:00 candle | Open of 07:30 | 06:00 | 11:59 |
| NY PM | Opening of 12:00 candle | Open of 13:30 | 12:00 | 16:59 |
| Afternoon | Opening of 13:30 candle | Open of 15:00 | 13:30 | 16:59 |

**Note**: All times are in Eastern Time (ET).

---

## Minor Sessions (16 per trading day)

Minor sessions are 90-minute segments of the day. Every 90-minute segment is a Minor session. We start the day at 18:00 and the day ends at 16:59 the next day. This follows the traditional indices futures trading day.

### Minor Session Table

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

**Note**: m1630 is only 30 minutes duration (not the standard 90 minutes).

---

## Weekly Session

The Weekly session provides multi-day structure and context. There is one active Weekly session at any given time.

### Weekly Session Calculation

- **PoC Tracking Begins:** Sunday 18:00 (the first candle of the Monday trading day)
- **True Open (TO):** Opening price of the Monday 18:00 candle (the first candle of the Tuesday trading day)
- **Range Calculation:** We look for the highest high or lowest low from Sunday 18:00 until the Monday 18:00 candle (exclusive) that gives the greatest variance from the TO price. This point is the PoC.
- **Duration:** Tracks indefinitely until the session reaches "resolved" status

**Important:** Until the Monday 18:00 candle opens, the Weekly session does not have a defined range (TO, PoC, RPP are not yet calculable).

---

## Monthly Session

The Monthly session provides the longest timeframe context and highest significance levels. There is one active Monthly session at any given time.

### Monthly Session Calculation

- **PoC Tracking Begins:** First full trading day of the month (Sunday evening 18:00 is included if it falls within the first trading day)
- **True Open (TO):** Opening price of the Sunday 18:00 candle that begins the second full week of the month
- **Range Calculation:** We look for the highest high or lowest low from the first full trading day until the TO candle (exclusive) that gives the greatest variance from the TO price. This point is the PoC.
- **Duration:** Tracks indefinitely until the session reaches "resolved" status

### Determining the "Second Full Week"

- If the 1st of the month falls on Saturday, Sunday, or Monday → that week is the first full week
- If the 1st of the month falls on Tuesday, Wednesday, Thursday, or Friday → that is NOT a full week; the following week is the first full week
- The TO is set at the Sunday 18:00 candle that begins the week AFTER the first full week

**Important:** Until the second full week begins, the Monthly session does not have a defined range (TO, PoC, RPP are not yet calculable).

---

## Yearly Session

The Yearly session provides the absolute highest timeframe context and most significant price levels across an entire calendar year. There is one active Yearly session at any given time.

### Yearly Session Calculation

- **PoC Tracking Begins:** First full trading day of the calendar year
- **True Open (TO):** Opening price of the first Sunday 18:00 of April
- **Range Calculation:** We look for the highest high or lowest low from the first full trading day of January through the end of March (entire Q1) (until TO candle, exclusive) that gives the greatest variance from the TO price. This point is the PoC.
- **Duration:** Tracks indefinitely until the session reaches "resolved" status

### First Full Trading Day of the Year

Following the same logic as Monthly sessions, we need to ensure Monday's trading session (Sunday 18:00) is included in January:

- If Jan 1st falls on Saturday, Sunday, or Monday → trading begins Sunday Jan 1st at 18:00 (or late Sunday from previous year)
- If Jan 1st falls on Tuesday through Friday → trading begins on the prior Sunday/Monday transition from December

### True Open Timing

The TO is set at the **first Sunday 18:00 of April**, which begins the Monday trading day.

This provides:
- Entire first quarter - Q1 (~66 trading days across January, February, March) to establish the PoC
- TO set at the beginning of Q2 (April)
- Tracking of these critical levels for the remainder of the year (Q2, Q3, Q4)

**Important:** Until the first Sunday 18:00 of April, the Yearly session does not have a defined range (TO, PoC, RPP are not yet calculable).

### Example: 2025 Yearly Session

- Jan 1, 2025 = Wednesday
- First full trading day: Dec 31, 2024 (Tuesday) at 18:00
- PoC Tracking Window: Dec 31, 2024 18:00 through March 31, 2025 23:59 (entire Q1)
- TO Time: April 6, 2025 (Sunday) at 18:00
- Range Active: April 6, 2025 through Dec 31, 2025 (or until resolved)

---

## Trading Day Definition

**Trading Day Boundaries:** 18:00 → 16:59 (next calendar day)

This follows the traditional indices futures trading day structure.

**Example:**
- Candle: 2025-11-27T18:00:00 → trading_day = 2025-11-28
- Candle: 2025-11-28T09:00:00 → trading_day = 2025-11-28
- Candle: 2025-11-28T18:00:00 → trading_day = 2025-11-29

---

## Next Steps

- [Ranges and Terms](03-ranges-and-terms.md) - Learn about PoC, TO, and RPP
- [Order of Operations](04-order-of-operations.md) - Understanding market narrative
- [Echo Chamber Analysis](05-echo-chamber.md) - ES/NQ correlation strategies
