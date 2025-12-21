# Session Tables Quick Reference

Complete timing reference for all session types in the Lipstick Trading System.

---

## Major Sessions (5 per trading day)

| Session Title | Start Looking for PoC | True Open Time | Start Time | End Time |
| --- | --- | --- | --- | --- |
| Asia | Closing Price of previous Day | Open of 19:30 | 18:00 | 23:59 |
| London | Opening of 00:00 candle | Open of 01:30 | 00:00 | 05:59 |
| NY AM | Opening of 06:00 candle | Open of 07:30 | 06:00 | 11:59 |
| NY PM | Opening of 12:00 candle | Open of 13:30 | 12:00 | 16:59 |
| Afternoon | Opening of 13:30 candle | Open of 15:00 | 13:30 | 16:59 |

**Tracking Duration:** Indefinite (until resolved)
**Expiry:** None (expires_at = NULL)
**All times in Eastern Time (ET)**

---

## Minor Sessions (16 per trading day)

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
**Tracking Duration:** 24 hours from TO time
**Expiry:** to_time + 24 hours
**All times in Eastern Time (ET)**

---

## Weekly Session (1 per week)

| Property | Value |
|----------|-------|
| **PoC Tracking Begins** | Sunday 18:00 |
| **True Open Time** | Monday 18:00 (open price) |
| **PoC Calculation Window** | Sunday 18:00 through Monday 17:59 |
| **Tracking Duration** | Indefinite (until resolved) |
| **Expiry** | None (expires_at = NULL) |

**Note:** Weekly session does not have a defined range until Monday 18:00 candle opens.

---

## Monthly Session (1 per month)

| Property | Value |
|----------|-------|
| **PoC Tracking Begins** | First full trading day at 18:00 |
| **True Open Time** | Second full week Sunday 18:00 (open price) |
| **Tracking Duration** | Indefinite (until resolved) |
| **Expiry** | None (expires_at = NULL) |

### Determining First Full Trading Day

The key rule: **We need Monday's trading session (Sunday 18:00) to be included.**

- If 1st = **Monday**: First trading day is **Sunday** (the day before) at 18:00
- If 1st = **Tuesday**: First trading day is **Monday** (the day before) at 18:00
- If 1st = **Wednesday**: First trading day is **Tuesday** (the day before) at 18:00
- If 1st = **Thursday**: First trading day is **Wednesday** (the day before) at 18:00
- If 1st = **Friday**: First trading day is **Thursday** (the day before) at 18:00
- If 1st = **Saturday**: First trading day is **Sunday** (the next day) at 18:00
- If 1st = **Sunday**: First trading day is **Sunday** (same day) at 18:00

### Determining Second Full Week

- If the 1st falls on **Saturday, Sunday, or Monday** → that week is the first full week
- If the 1st falls on **Tuesday, Wednesday, Thursday, or Friday** → that is NOT a full week; the following week is the first full week
- The TO is set at the Sunday 18:00 candle that begins the week **AFTER** the first full week

**Note:** Monthly session does not have a defined range until the second full week Sunday 18:00 candle opens.

---

## Yearly Session (1 per year)

| Property | Value |
|----------|-------|
| **PoC Tracking Begins** | First full trading day of January at 18:00 |
| **True Open Time** | First Sunday 18:00 of April (open price) |
| **Range Window** | First trading day of year through end of March (Q1) |
| **Tracking Duration** | Indefinite (until resolved) |
| **Expiry** | None (expires_at = NULL) |

### Determining First Full Trading Day of the Year

The key rule: **We need Monday's trading session (Sunday 18:00) to be included in January.**

- If Jan 1st = **Monday**: First trading day is **Sunday** (the day before) at 18:00
- If Jan 1st = **Tuesday**: First trading day is **Monday** (the day before) at 18:00
- If Jan 1st = **Wednesday**: First trading day is **Tuesday** (the day before) at 18:00
- If Jan 1st = **Thursday**: First trading day is **Wednesday** (the day before) at 18:00
- If Jan 1st = **Friday**: First trading day is **Thursday** (the day before) at 18:00
- If Jan 1st = **Saturday**: First trading day is **Sunday** (the next day) at 18:00
- If Jan 1st = **Sunday**: First trading day is **Sunday** (same day) at 18:00

### True Open Timing

The TO is set at the **first Sunday 18:00 of April**, which begins the Monday trading day.

This provides:
- Entire first quarter - Q1 (~66 trading days across January, February, March) to establish the PoC
- TO set at the beginning of Q2 (April)
- Tracking for the remainder of the year (Q2, Q3, Q4)

**Note:** Yearly session does not have a defined range until the first Sunday 18:00 of April.

---

## Session Hierarchy

### By Significance (highest to lowest)

1. **Monthly** - Longest timeframe, highest significance
2. **Weekly** - Multi-day timeframe, high significance
3. **Major** - Single to multi-day timeframe, significant
4. **Minor** - Intraday execution timeframe

### By Count Per Day

- **Major:** 5 sessions
- **Minor:** 16 sessions
- **Weekly:** 1 session per week
- **Monthly:** 1 session per month

**Total per trading day:** 21 sessions (5 Major + 16 Minor) + Weekly + Monthly

---

## Trading Day Definition

**Trading Day Boundaries:** 18:00 → 16:59 (next calendar day)

**Examples:**
- Candle: 2025-11-27T18:00:00 → trading_day = 2025-11-28
- Candle: 2025-11-28T09:00:00 → trading_day = 2025-11-28
- Candle: 2025-11-28T18:00:00 → trading_day = 2025-11-29

---

## Session Tracking Duration Summary

| Session Type | Tracking Duration | Expiry Logic |
|--------------|-------------------|--------------|
| Major | Indefinite | expires_at = NULL |
| Minor | 24 hours from TO | expires_at = to_time + 24h |
| Weekly | Indefinite | expires_at = NULL |
| Monthly | Indefinite | expires_at = NULL |

---

## Related Documentation

- [Sessions User Guide](../user-guide/02-sessions.md) - Detailed session explanations
- [Calculation Logic](../technical/calculation-logic.md) - How ranges are calculated
- [Formulas Reference](formulas.md) - All calculation formulas
