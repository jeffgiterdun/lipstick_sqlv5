# Lipstick Trading System Documentation

Complete documentation for the Lipstick Analytical Tool V5 - a hindsight analysis system for ES/NQ futures tracking algorithmic price behavior through time-segmented sessions.

---

## Quick Links

- **New to Lipstick?** Start with the [Introduction](user-guide/01-introduction.md)
- **Building the system?** See [Setup Guide](development/setup-guide.md) and [Implementation Phases](development/implementation-phases.md)
- **Need a quick reference?** Check [Session Tables](reference/session-tables.md) or [Formulas](reference/formulas.md)

---

## Documentation Structure

### For Traders & Users

Learn the Lipstick trading methodology and how to interpret session data.

**User Guide**
1. [Introduction](user-guide/01-introduction.md) - What is the Lipstick Trading System?
2. [Sessions](user-guide/02-sessions.md) - Session types and timing
3. [Ranges and Terms](user-guide/03-ranges-and-terms.md) - PoC, TO, RPP definitions
4. [Order of Operations](user-guide/04-order-of-operations.md) - Market narrative theory
5. [Echo Chamber](user-guide/05-echo-chamber.md) - ES/NQ correlation analysis

### For Developers & Implementers

Technical specifications for building and maintaining the analytical system.

**Technical Documentation**
- [Architecture Overview](technical/architecture-overview.md) - System design and data flow
- [Database Schema](technical/database-schema.md) - Tables, relationships, and constraints
- [Calculation Logic](technical/calculation-logic.md) - Range calculations, state machine, touch detection
- [Processing Algorithm](technical/processing-algorithm.md) - Step-by-step implementation
- [Edge Cases](technical/edge-cases.md) - Missing data, gaps, special scenarios

### Quick Reference

Fast lookup for common information.

**Reference Materials**
- [Session Tables](reference/session-tables.md) - All session timing tables in one place
- [State Machine](reference/state-machine.md) - Status transitions and diagrams
- [Formulas](reference/formulas.md) - All calculation formulas
- [Glossary](reference/glossary.md) - Complete term definitions

### Development Resources

Guides for setting up and building the system.

**Development Guides**
- [Setup Guide](development/setup-guide.md) - Getting started
- [Implementation Phases](development/implementation-phases.md) - Build process and verification
- [Changelog](development/changelog.md) - Version history and upgrade guide

---

## What is the Lipstick System?

The Lipstick Trading System tracks algorithmic price behavior through time-segmented sessions. By calculating ranges (PoC, TO, RPP) and monitoring how price interacts with these levels, traders can anticipate price action and identify high-probability setups.

### Core Concepts

- **Sessions**: Time segments (Major, Minor, Weekly, Monthly, Yearly) that define when to measure price action
- **Ranges**: Symmetrical boundaries (PoC ← TO → RPP) where price is expected to react
- **Status Tracking**: State machine that monitors price progression (unbroken → break → return → resolved)
- **Echo Chamber**: ES/NQ correlation analysis exploiting synchronization divergences
- **Order of Operations**: Market narrative theory - the algorithmic "checklist" driving price

### Key Features (V5)

- **Indefinite Session Tracking** - Major/Weekly/Monthly sessions track across multiple days until resolved
- **Built-in Echo Chamber** - ES/NQ timing captured in single database row for direct divergence analysis
- **Hierarchical Swing Detection** - Class 1-4 classification with POI linkage
- **Session Context Snapshots** - JSON capture of all active sessions at each significant price swing
- **Research Journal** - Insights table with full-text search for pattern discovery

---

## Quick Start

### For Traders

1. Start with [Introduction](user-guide/01-introduction.md) to understand the methodology
2. Learn about [Sessions](user-guide/02-sessions.md) and their hierarchy
3. Study [Ranges and Terms](user-guide/03-ranges-and-terms.md) to understand PoC, TO, RPP
4. Read [Echo Chamber](user-guide/05-echo-chamber.md) for ES/NQ trading strategies
5. Use [Reference Materials](#quick-reference) for quick lookups

### For Developers

1. Review [Architecture Overview](technical/architecture-overview.md) for system design
2. Follow [Setup Guide](development/setup-guide.md) to configure environment
3. Build the system using [Implementation Phases](development/implementation-phases.md)
4. Reference [Database Schema](technical/database-schema.md) for data structures
5. Handle special cases with [Edge Cases](technical/edge-cases.md) guide

---

## System Overview

### Database Tables

| Table | Purpose | Records per Day |
|-------|---------|-----------------|
| **sessions** | Session ranges and status tracking | 21 per symbol (~42 total) |
| **poi_events** | POI touches with Echo Chamber data | 50-200 (variable) |
| **swings** | Hierarchical swing classification | 100-500 (variable) |
| **insights** | Research journal entries | Manual (as needed) |

### Session Types

| Type | Count | Tracking Duration | Primary Use |
|------|-------|-------------------|-------------|
| **Yearly** | 1 per year | Indefinite | Absolute highest timeframe context |
| **Monthly** | 1 per month | Indefinite | Highest monthly timeframe context |
| **Weekly** | 1 per week | Indefinite | Multi-day context |
| **Major** | 5 per day | Indefinite | Trade setups, narrative |
| **Minor** | 16 per day | 24 hours | Execution, confluence |

### Processing Flow

```
OHLC Data (1-minute bars)
       ↓
[Phase 1: Range Calculation]
   → sessions table populated
       ↓
[Phase 2: POI Event Detection]
   → sessions status updated
   → poi_events table populated
       ↓
[Phase 3: Swing Detection]
   → swings table populated
       ↓
[Phase 4: Analysis]
   → Query patterns
   → Record insights
```

---

## Session Hierarchy

### By Significance

1. **Yearly** (absolute highest)
   - Longest timeframe - full year
   - Absolute most significant levels
   - Tracks indefinitely

2. **Monthly** (highest)
   - Longest monthly timeframe
   - Most significant monthly levels
   - Tracks indefinitely

3. **Weekly** (high)
   - Multi-day structure
   - High significance levels
   - Tracks indefinitely

4. **Major** (significant)
   - Daily structure
   - Trade setup levels
   - Tracks indefinitely

5. **Minor** (execution)
   - Intraday context
   - Execution and confluence
   - Tracks 24 hours, then expires

---

## State Machine

All sessions progress through states based on price interaction:

```
unbroken → break → return → resolved
```

- **unbroken**: Range set, no touches yet
- **break**: First boundary (PoC/RPP) touched
- **return**: Touched TO after first break
- **resolved**: Complete cycle finished

See [State Machine Reference](reference/state-machine.md) for detailed transitions.

---

## Common Queries

### Find Active Sessions

```sql
SELECT * FROM sessions
WHERE status != 'resolved'
AND to_time <= datetime('now')
AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY session_type, to_time;
```

### Find Echo Chamber Divergences

```sql
SELECT * FROM poi_events
WHERE time_delta_seconds > 300  -- >5 minute divergence
ORDER BY time_delta_seconds DESC;
```

### Find London PoC First Breaks on Specific Date

```sql
SELECT * FROM poi_events
WHERE trading_day = '2025-12-16'
AND session_name LIKE 'London%'
AND poi_type = 'PoC'
AND event_type = 'first_break';
```

### Find Major Swings Near POI Events

```sql
SELECT s.*, p.poi_type, p.event_type
FROM swings s
JOIN poi_events p ON s.nearest_poi_event_id = p.id
WHERE s.swing_class >= 3
ORDER BY s.swing_time DESC;
```

---

## Version Information

**Current Version:** 5.0.0
**Release Date:** November 28, 2025

### V5 Major Changes

- ✅ Indefinite session tracking (Major/Weekly/Monthly)
- ✅ Echo Chamber built into poi_events
- ✅ Hierarchical swing detection (Class 1-4)
- ✅ Session context JSON snapshots
- ✅ Merged sessions table
- ❌ Removed Quartile sessions
- ❌ Removed trading_day constraint

See [Changelog](development/changelog.md) for complete version history.

---

## Learning Paths

### Path 1: Trader (Methodology Focus)

```
Introduction → Sessions → Ranges & Terms → Echo Chamber → Order of Operations
          ↓
    Practice with queries
          ↓
    Record insights
```

**Time:** 4-6 hours reading + practice

### Path 2: Developer (Implementation Focus)

```
Architecture Overview → Database Schema → Calculation Logic → Processing Algorithm
          ↓
    Setup Guide → Implementation Phases
          ↓
    Build and verify
```

**Time:** 1-2 days setup + implementation

### Path 3: Analyst (Data Focus)

```
Introduction → Technical Overview → Database Schema → Reference Materials
          ↓
    Write queries and analyze patterns
          ↓
    Use insights table for research journal
```

**Time:** 2-3 hours reading + ongoing analysis

---

## Support and Resources

### Documentation Sections

- **User Guide** - Trading methodology and concepts
- **Technical** - System architecture and implementation
- **Reference** - Quick lookup for formulas, tables, terms
- **Development** - Setup, build process, changelog

### External Resources

- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **Python datetime**: https://docs.python.org/3/library/datetime.html
- **Pandas Documentation**: https://pandas.pydata.org/docs/

---

## Contributing

### Documentation Improvements

If you find errors or want to improve documentation:

1. Note the file location (e.g., `docs/user-guide/02-sessions.md`)
2. Describe the issue or improvement
3. Submit via project repository

### Code Contributions

See [Setup Guide](development/setup-guide.md) for development environment setup.

---

## License

[Add license information here]

---

## Acknowledgments

The Lipstick Trading System is the result of extensive market observation and pattern recognition focused on algorithmic price behavior in ES and NQ futures markets.

---

**Last Updated:** November 28, 2025
**Version:** 5.0.0
