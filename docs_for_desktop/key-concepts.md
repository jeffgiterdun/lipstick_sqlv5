# Key Concepts - Trading Terminology

Essential concepts for understanding the Lipstick Trading System.

---

## Session Range Components

### PoC (Point of Control)
**Definition:** The highest high OR lowest low within the PoC window that has the **greatest variance from True Open**.

**Calculation:**
1. Find highest high in PoC window
2. Find lowest low in PoC window
3. Calculate variance from TO for each: `abs(price - TO)`
4. PoC = whichever has greater variance

**Purpose:** Identifies the extreme price level that defines one side of the session range.

### TO (True Open)
**Definition:** The **open price** of the candle at TO time. This is the anchor point of the session range.

**Key Points:**
- TO time is calculated based on session type
- Major sessions: Specific time per session (varies by session)
- Minor sessions: 22 minutes after session start
- Weekly/Monthly/Yearly: Specific calculation rules per type
- TO price = candle open at that exact time

**Purpose:** Provides the reference point from which PoC and RPP are measured.

### RPP (Range Projection Point)
**Definition:** Mirror projection of PoC across TO. The "opposite side" of the range.

**Formula:**
```
RPP = 2 × TO - PoC
```

**Purpose:** Projects an equal distance on the opposite side of TO, creating a symmetric range.

**Visual:**
```
PoC <-------- TO --------> RPP
     (distance)   (equal distance)
```

---

## Session State Machine

Sessions progress through 4 states based on POI touches:

### 1. unbroken
- **Definition:** No PoC or RPP touched yet
- **Next State:** Break (when PoC or RPP touched)
- **Fields:** status = 'unbroken'

### 2. break
- **Definition:** First PoC or RPP touch occurred
- **Fields Set:**
  - `status` = 'break'
  - `first_break_time`: Timestamp of touch
  - `first_break_side`: 'PoC' or 'RPP'
- **Next State:** Return (when TO touched)

### 3. return
- **Definition:** Price returned to TO after first break
- **Fields Set:**
  - `status` = 'return'
  - `first_return_time`: Timestamp of TO touch
- **Next States:**
  - Back to Break: Second PoC/RPP touch (records second_break_time)
  - Resolution: Second TO touch (after second break)

### 4. resolved
- **Definition:** Second return to TO after second break
- **Fields Set:**
  - `status` = 'resolved'
  - `resolution_time`: Timestamp of second TO return
  - `resolution_type`: 'single_sided' or 'double_sided'
- **Resolution Types:**
  - **single_sided:** Both breaks on same side (PoC+PoC or RPP+RPP)
  - **double_sided:** One PoC break, one RPP break

### State Diagram
```
unbroken
   │
   ├─ PoC/RPP touch ──→ break
   │                      │
   │                      ├─ TO touch ──→ return
   │                      │                 │
   │                      │                 ├─ PoC/RPP touch ──→ (second break)
   │                      │                 │                      │
   │                      │                 │                      ├─ TO touch ──→ resolved
```

---

## Echo Chamber Analysis

**Definition:** Timing divergence between ES and NQ when they touch the same POI level.

### Components

#### time_delta_minutes
**Definition:** Absolute time difference (in minutes) between ES and NQ touches of the same POI.

**Calculation:**
```
time_delta_minutes = abs(es_event_time - nq_event_time) / 60
```

**NULL When:** Only one instrument has touched the POI level

#### leader
**Definition:** Which instrument touched first.

**Values:**
- **'ES'** - ES touched first
- **'NQ'** - NQ touched first
- **'simultaneous'** - Within 60 seconds (<1 minute apart)

**NULL When:** Only one instrument has touched the POI level

### Significance Interpretation

**Small Divergence (<60 minutes):**
- Normal market behavior
- Instruments moving relatively in sync

**Medium Divergence (60-360 minutes / 1-6 hours):**
- One instrument showing relative strength/weakness
- Monitor for additional confluence

**Large Divergence (>360 minutes / >6 hours):**
- Significant leader/lagger relationship
- One instrument telegraphing direction
- Higher probability for continued divergence

**Extreme Divergence (>1440 minutes / >1 day):**
- Major structural divergence
- Very strong leader signal
- Indicates significant market imbalance

---

## Swing Classification

Hierarchical fractal swing detection with 6 classes (higher = more significant).

### Class 1 (Most Common)
- **Definition:** Basic 3-bar pivot
- **Pattern:** Lower high (for swing high) or higher low (for swing low) between two opposite extremes
- **Significance:** Smallest structural unit, noise level

### Class 2
- **Definition:** Breaks prior Class 1 extreme
- **Significance:** Confirms directional move beyond noise

### Class 3
- **Definition:** Breaks prior Class 2 extreme
- **Significance:** **Structural swing** - marks significant support/resistance
- **Note:** Class 3+ are considered "major" or "structural" swings

### Class 4
- **Definition:** Breaks prior Class 3 extreme
- **Significance:** Major structural shift in market

### Class 5
- **Definition:** Breaks prior Class 4 extreme
- **Significance:** Rare, very significant structural event

### Class 6 (Most Rare)
- **Definition:** Breaks prior Class 5 extreme
- **Significance:** **Extreme structural event** - multi-day or multi-week impact

### Key Metrics

**points_from_prior:**
- Distance in points from prior opposite swing
- Measures move magnitude

**candles_from_prior:**
- Number of candles between this swing and prior opposite swing
- Measures move duration/time

**candles_from_poi_event:**
- Number of candles since the nearest POI event
- Links swing formation timing to POI touches

---

## Session Expiration

### Minor Sessions
- **Expire:** 24 hours after TO time
- **Field:** `expires_at = to_time + 24 hours`
- **Reason:** Too numerous to track indefinitely (16 per day)
- **Behavior:** POI processing ignores expired sessions

### Major/Weekly/Monthly/Yearly Sessions
- **Expire:** Never (expires_at = NULL)
- **Track:** Until resolved
- **Reason:** Critical structural levels with lasting significance

---

## Trading Day

**Definition:** A trading day runs from 18:00 to 16:59 next calendar day.

**Purpose:** Aligns with futures market trading hours (Sunday evening through Friday afternoon).

**Calculation Logic:**
```
if hour < 18:
    trading_day = current_calendar_date
else:  # hour >= 18
    trading_day = next_calendar_date
```

**Format:** YYYY-MM-DD

**Usage:** All POI events tagged with trading_day for easy daily filtering.

---

## Order of Operations (OOO)

**Definition:** The theory that the market follows a sequential checklist of tasks, resolving sessions in order.

### Core Concept
When a session resolves:
1. Market "checks off" that task as complete
2. Looks backward chronologically
3. Identifies next unresolved session
4. Price gravitates toward that session's key levels (PoC, TO, RPP)

### Session Hierarchy (by structural significance)
1. **Yearly** - Most significant, multi-month impact
2. **Monthly** - Very significant, multi-week impact
3. **Weekly** - Significant, week-to-week structure
4. **Major** - Daily structure, intraday reference
5. **Minor** - Intraday execution, short-term targets

**Principle:** Higher timeframe sessions take precedence in the OOO checklist.

---

## Confluence

**Definition:** Multiple factors aligning at the same price level or time, creating higher-probability trade setups.

### Common Confluence Factors
1. **POI Touch** - Price testing PoC, TO, or RPP level
2. **Echo Chamber Divergence** - Large time_delta with clear leader
3. **Major Swing Formation** - Class 3+ swing at or near POI
4. **Session Status Alignment** - Multiple sessions in similar states
5. **Multi-Timeframe Alignment** - Different session types at same price level
6. **Resolution Timing** - Session resolution triggering next OOO task

### Principle
More confluence factors = Higher probability setup

---

## Key Design Principles

### 1. Dual-Asset Tracking
Both ES and NQ tracked in single database with:
- Paired sessions (ES and NQ sessions at same time)
- Echo Chamber analysis (timing divergence)
- Comparative analysis capabilities

### 2. Hierarchical Structure
Multiple timeframes tracked simultaneously:
- Minor (16/day) → Major (5/day) → Weekly (1/week) → Monthly (1/month) → Yearly (1/year)
- Higher timeframes provide context for lower timeframes

### 3. State Machine Progression
Sessions follow defined lifecycle:
- unbroken → break → return → resolved
- Clear, predictable progression
- Trackable at any point in time

### 4. POI Event Linkage
Swings linked to POI events:
- Provides context for swing formation
- Identifies which POI levels drive significant swings
- Enables pattern recognition over time

### 5. Research Journal
insights table provides:
- Permanent archive of discoveries
- Full-text searchable patterns
- Tagged for filtering and analysis
- SQL query preservation for reproducibility

---

## Next Steps

- See `database-schema.md` for table structures and fields
- See `system-overview.md` for overall architecture
- See `custom-instructions.md` for Claude Desktop analysis workflow
- See `discoveries.md` for your own research findings
