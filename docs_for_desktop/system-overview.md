# Lipstick Trading System V5 - System Overview

## Purpose
Systematic analysis of ES and NQ futures using hierarchical session ranges and Point of Interest (POI) tracking with Echo Chamber divergence analysis.

---

## Database: ohlc_data.db

**Type:** SQLite database
**Symbols:** ES, NQ futures
**Timeframe:** 1-minute OHLC candle data

---

## Core Tables

### 1. **ohlc_1m**
Raw 1-minute OHLC candle data for ES and NQ.

### 2. **sessions**
Session ranges and status tracking.

**Session Types:**
- **Major:** 5 per trading day (Asia, London, NY_AM, NY_PM, Afternoon)
- **Minor:** 16 per trading day at 90-minute intervals
- **Weekly:** 1 per week
- **Monthly:** 1 per month
- **Yearly:** 1 per year

**Status Tracking:** Each session progresses through states:
- unbroken → break → return → resolved

### 3. **poi_events**
POI (Point of Interest) touch events with Echo Chamber analysis.

**Tracks:**
- When ES and NQ touch PoC, TO, or RPP levels
- Time delta between ES and NQ touches
- Which instrument led (ES, NQ, or simultaneous)

### 4. **swings**
Hierarchical swing classification (Class 1-6) with POI linkage.

**Links:**
- Prior opposite swings for movement metrics
- Nearest POI events for context

### 5. **insights**
Research journal for recording discoveries, patterns, and observations.

**Searchable by:**
- Date range
- Sessions involved
- Confluence factors
- Outcome types
- Full-text search

---

## Session Range Components

Each session has three key price levels:

### PoC (Point of Control)
The highest high or lowest low within the PoC window with the greatest variance from True Open.

### TO (True Open)
The open price at TO time. This anchors the session range.

### RPP (Range Projection Point)
Mirror projection of PoC across TO:
```
RPP = 2 × TO - PoC
```

---

## Session Status States

Sessions progress through a state machine based on POI touches:

1. **unbroken** - No POI touches yet
2. **break** - First PoC or RPP touch
3. **return** - First TO touch after break
4. **resolved** - Second TO touch after second break

---

## Echo Chamber Analysis

Tracks timing divergence between ES and NQ when touching the same POI level.

**Key Metrics:**
- **time_delta_minutes:** Absolute time difference between touches
- **leader:** Which instrument touched first (ES, NQ, or simultaneous)

**Significance:** Large divergences indicate one instrument leading price action.

---

## Swing Classification

Hierarchical fractal swing detection with 6 classes:

- **Class 1:** Basic 3-bar pivots (most common)
- **Class 2:** Breaks prior Class 1 extreme
- **Class 3:** Breaks prior Class 2 extreme (structural)
- **Class 4:** Breaks prior Class 3 extreme (major structural)
- **Class 5:** Breaks prior Class 4 extreme (rare)
- **Class 6:** Breaks prior Class 5 extreme (extreme events)

**Note:** Class 3+ swings are considered structurally significant.

---

## Session Expiration

- **Minor sessions:** Expire 24 hours after TO time
- **Major/Weekly/Monthly/Yearly:** Track until resolved (never expire)

---

## Trading Day

Trading day runs 18:00 → 16:59 next calendar day.

All POI events are tagged with trading_day for easy filtering.

---

## Data Processing Pipeline

1. **load_1m_csv.py** - Load raw CSV data into ohlc_1m
2. **calculate_daily_sessions.py** - Calculate session ranges (PoC, TO, RPP)
3. **process_poi_events_1m.py** - Detect POI touches, create events, update statuses
4. **detect_swings_1m.py** - Classify swings, link to POI events

---

## Foreign Key Relationships

```
sessions (id) ←─── poi_events (es_session_id, nq_session_id)
                         ↑
                         │
                    swings (nearest_poi_event_id)
```

---

## Key Design Principles

- **Dual-asset tracking:** Both ES and NQ in single database with paired analysis
- **Hierarchical sessions:** Multiple timeframes (Minor → Major → Weekly → Monthly → Yearly)
- **State machine:** Sessions progress through defined states
- **Echo Chamber:** Built-in ES/NQ divergence analysis
- **Fractal swings:** Hierarchical classification with structural significance
- **Research journal:** insights table for permanent discovery archive

---

## Next Steps

See the other documentation files for:
- `database-schema.md` - Detailed table structures
- `key-concepts.md` - Trading terminology and concepts
- `custom-instructions.md` - Instructions for Claude Desktop analysis
- `discoveries.md` - Your working memory for recent findings
