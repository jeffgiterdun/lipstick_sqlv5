# Changelog

All notable changes to the Lipstick Analytical Tool.

---

## [5.0.0] - 2025-11-28

### Major Release: V5 Complete Rewrite

**Focus:** Indefinite session tracking, Echo Chamber analysis, and hierarchical swing detection.

### Added

#### Session Types
- **Yearly sessions** - Absolute highest significance timeframe tracking (full calendar year)
- **Monthly sessions** - Highest monthly significance timeframe tracking
- **Weekly sessions** - Multi-day timeframe tracking
- **Indefinite tracking** for Major, Weekly, Monthly, and Yearly sessions (no expiry)
- **24-hour expiry** for Minor sessions only

#### Database Schema
- **Merged sessions table** - Combines time_groups and session_status from V4 into single table
- **Enhanced poi_events table** - Built-in Echo Chamber with ES/NQ timing in single row
- **New swings table** - Hierarchical swing classification (Class 1-4)
- **New insights table** - Research journal with full-text search

#### Features
- **Echo Chamber metrics** - Automatic calculation of time_delta_seconds and leader
- **Session context snapshots** - JSON capture of active sessions at each swing
- **POI event linkage** - Swings linked to nearest POI events
- **Swing movement metrics** - Points and candles from prior opposite swing

### Changed

#### Session Tracking
- Removed `trading_day` constraint - sessions track across multiple days
- Sessions now identified by (symbol, session_type, session_name, session_start_time)
- Active sessions can persist for weeks until resolution

#### Database Structure
- **Removed:** Quartile sessions (64 per day)
- **Removed:** Separate time_groups and session_status tables
- **Removed:** context_snapshot table
- Reduced from 85 to 21 sessions per trading day (more efficient)

#### Performance
- Optimized indexes for indefinite session tracking
- Added partial indexes for active/unexpired sessions
- Reduced database size while adding functionality

### Performance Impact

**Database Size per Day:**
- V4: 85 sessions × 2 symbols = 170 session records
- V5: 21 sessions × 2 symbols = 42 session records
- **Reduction:** 75% fewer session records per day

**Additional Tables:**
- swings: ~100-500 records per day
- poi_events: ~50-200 records per day
- insights: manual entries only

---

## [4.0.0] - 2024

### V4 Features (For Reference)

#### Session Types
- Major sessions (5 per day)
- Minor sessions (16 per day)
- Quartile sessions (64 per day)
- **Total:** 85 sessions per trading day

#### Database Schema
- Separate time_groups table for ranges
- Separate session_status table for tracking
- context_snapshot table for market state
- All sessions constrained by trading_day

#### Limitations
- Sessions expired at end of trading day
- Echo Chamber analysis required post-processing
- No Weekly, Monthly, or Yearly timeframes
- No hierarchical swing classification

---

## Upgrade Guide: V4 → V5

### Breaking Changes

1. **Database schema completely redesigned**
   - Cannot migrate existing V4 databases
   - Must rebuild from OHLC data

2. **Session tracking model changed**
   - V4: All sessions expire at day end
   - V5: Major/Weekly/Monthly/Yearly track indefinitely

3. **Removed features**
   - Quartile sessions (use Minor sessions instead)
   - trading_day field (sessions span multiple days)

### Migration Steps

1. **Backup V4 database**
   ```bash
   cp data/ohlc_data_v4.db data/ohlc_data_v4_backup.db
   ```

2. **Export insights/notes from V4** (if applicable)

3. **Create new V5 database**
   ```bash
   sqlite3 data/ohlc_data.db < schema_v5.sql
   ```

4. **Copy OHLC data from V4**
   ```bash
   sqlite3 data/ohlc_data_v4.db ".dump ohlc_1m" | sqlite3 data/ohlc_data.db
   ```

5. **Run V5 processing**
   ```bash
   python calculate_ranges_v5.py
   python process_poi_events_v5.py
   python detect_swings_v5.py
   ```

---

## Roadmap

### Planned for V5.1

- [ ] API endpoint for real-time session status queries
- [ ] Automated insight generation from swing patterns
- [ ] Enhanced visualization export (TradingView format)
- [ ] Performance optimization for multi-year datasets

### Under Consideration

- [ ] Intraday session patterns (sub-Minor timeframes)
- [ ] Volume profile integration
- [ ] Additional instruments (Russell, Dow futures)
- [ ] Machine learning pattern recognition

---

## Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **Major version** (X.0.0): Breaking changes, incompatible API changes
- **Minor version** (0.X.0): New features, backward compatible
- **Patch version** (0.0.X): Bug fixes, backward compatible

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| **5.0.0** | 2025-11-28 | Complete rewrite with indefinite tracking and Echo Chamber |
| **4.0.0** | 2024 | Quartile sessions, separate tables, trading_day constraint |
| **3.x** | 2023 | (Historical versions not documented) |

---

## Related Documentation

- [Implementation Phases](implementation-phases.md) - Build V5 from scratch
- [Architecture Overview](../technical/architecture-overview.md) - V5 design philosophy
- [Setup Guide](setup-guide.md) - Development environment setup
