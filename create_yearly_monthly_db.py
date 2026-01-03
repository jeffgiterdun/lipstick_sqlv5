#!/usr/bin/env python3
"""
Create yearly_monthly.db with the exact V5 schema.

This database will store:
- 4-hour OHLC candles (instead of 1-minute)
- Yearly and Monthly sessions (no Weekly, Major, or Minor)
- Same 5-table structure as ohlc_data.db
"""

import sqlite3
import os
from datetime import datetime


def create_database():
    """Create yearly_monthly.db with all 5 tables, indexes, and constraints."""

    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    db_path = 'data/yearly_monthly.db'

    # Remove existing database if present
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)

    print(f"Creating new database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # -------------------------------------------------------------------------
    # TABLE 1: ohlc_4h (stores 4-hour candles)
    # -------------------------------------------------------------------------
    print("Creating ohlc_4h table...")
    cursor.execute("""
        CREATE TABLE ohlc_4h (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            time TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            UNIQUE(symbol, time)
        );
    """)

    cursor.execute("CREATE INDEX idx_ohlc_symbol_time ON ohlc_4h(symbol, time);")

    # -------------------------------------------------------------------------
    # TABLE 2: sessions (tracks Yearly and Monthly sessions only)
    # -------------------------------------------------------------------------
    print("Creating sessions table...")
    cursor.execute("""
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            session_type TEXT NOT NULL,  -- 'Yearly', 'Monthly'
            session_name TEXT NOT NULL,  -- 'Yearly', 'Monthly'

            -- Time boundaries
            session_start_time TEXT NOT NULL,  -- ISO timestamp when session begins
            to_time TEXT NOT NULL,  -- True Open time (when range is set)

            -- Range values
            true_open REAL,
            poc REAL,
            rpp REAL,

            -- Status tracking
            status TEXT NOT NULL,  -- 'unbroken', 'break', 'return', 'resolved'
            first_break_time TEXT,
            first_break_side TEXT,  -- 'PoC' or 'RPP'
            first_return_time TEXT,
            second_break_time TEXT,
            second_break_side TEXT,
            resolution_time TEXT,
            resolution_type TEXT,  -- 'single_sided' or 'double_sided'

            -- Expiry tracking (NULL for Yearly/Monthly)
            expires_at TEXT,  -- NULL for Yearly/Monthly

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            UNIQUE(symbol, session_type, session_name, session_start_time)
        );
    """)

    cursor.execute("CREATE INDEX idx_sessions_symbol_status ON sessions(symbol, status);")
    cursor.execute("CREATE INDEX idx_sessions_active ON sessions(symbol, status) WHERE status != 'resolved';")
    cursor.execute("CREATE INDEX idx_sessions_unexpired ON sessions(symbol, expires_at) WHERE expires_at IS NULL OR expires_at > datetime('now');")

    # -------------------------------------------------------------------------
    # TABLE 3: poi_events
    # -------------------------------------------------------------------------
    print("Creating poi_events table...")
    cursor.execute("""
        CREATE TABLE poi_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Foreign keys to BOTH ES and NQ sessions
            es_session_id INTEGER NOT NULL,  -- FK to ES session
            nq_session_id INTEGER NOT NULL,  -- FK to NQ session

            -- Denormalized session context (for easy querying)
            trading_day TEXT NOT NULL,  -- YYYY-MM-DD format (e.g., '2025-12-16') - based on first touch
            session_type TEXT NOT NULL,  -- 'Yearly', 'Monthly'
            session_name TEXT NOT NULL,  -- 'Yearly', 'Monthly'

            poi_type TEXT NOT NULL,  -- 'PoC', 'RPP', 'TO'
            event_type TEXT NOT NULL,  -- 'break', 'return', 'resolution'

            -- ES timing
            es_event_time TEXT,  -- NULL if ES hasn't touched yet

            -- NQ timing
            nq_event_time TEXT,  -- NULL if NQ hasn't touched yet

            -- Echo Chamber metrics (auto-calculated)
            time_delta_minutes INTEGER,  -- abs(es_time - nq_time) in minutes, NULL if only one touched
            leader TEXT,  -- 'ES', 'NQ', or 'simultaneous' (< 1 min)

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY (es_session_id) REFERENCES sessions(id),
            FOREIGN KEY (nq_session_id) REFERENCES sessions(id)
        );
    """)

    cursor.execute("CREATE INDEX idx_poi_events_es_session ON poi_events(es_session_id);")
    cursor.execute("CREATE INDEX idx_poi_events_nq_session ON poi_events(nq_session_id);")
    cursor.execute("CREATE INDEX idx_poi_events_trading_day ON poi_events(trading_day);")
    cursor.execute("CREATE INDEX idx_poi_events_session_name ON poi_events(session_name);")
    cursor.execute("CREATE INDEX idx_poi_events_es_time ON poi_events(es_event_time);")
    cursor.execute("CREATE INDEX idx_poi_events_nq_time ON poi_events(nq_event_time);")

    # -------------------------------------------------------------------------
    # TABLE 4: swings
    # -------------------------------------------------------------------------
    print("Creating swings table...")
    cursor.execute("""
        CREATE TABLE swings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            swing_time TEXT NOT NULL,
            swing_price REAL NOT NULL,
            swing_type TEXT NOT NULL,  -- 'high' or 'low'
            swing_class INTEGER NOT NULL,  -- 1, 2, 3, or 4 (final classification)

            -- Movement context
            prior_opposite_swing_id INTEGER,  -- Previous swing of opposite type
            points_from_prior REAL,
            candles_from_prior INTEGER,

            -- POI linkage
            nearest_poi_event_id INTEGER,  -- Closest POI event in time/price

            -- Session context snapshot (JSON)
            active_sessions_snapshot TEXT,  -- JSON: session statuses at this moment

            created_at TEXT NOT NULL,
            FOREIGN KEY (prior_opposite_swing_id) REFERENCES swings(id),
            FOREIGN KEY (nearest_poi_event_id) REFERENCES poi_events(id)
        );
    """)

    cursor.execute("CREATE INDEX idx_swings_symbol_time ON swings(symbol, swing_time);")
    cursor.execute("CREATE INDEX idx_swings_class ON swings(swing_class);")
    cursor.execute("CREATE INDEX idx_swings_major ON swings(swing_class) WHERE swing_class >= 3;")
    cursor.execute("CREATE INDEX idx_swings_poi_link ON swings(nearest_poi_event_id);")

    # -------------------------------------------------------------------------
    # TABLE 5: insights
    # -------------------------------------------------------------------------
    print("Creating insights table...")
    cursor.execute("""
        CREATE TABLE insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Temporal context
            observation_date TEXT NOT NULL,  -- When you recorded this (ISO format)
            market_date_start TEXT,  -- Start of date range (YYYY-MM-DD)
            market_date_end TEXT,    -- End of date range (YYYY-MM-DD), NULL if single day

            -- Session context
            sessions_involved TEXT,  -- Comma-separated or JSON (e.g., "Yearly,Monthly")

            -- Classification/tags for searching
            confluence_factors TEXT,  -- Comma-separated tags
            outcome_type TEXT,  -- Comma-separated tags
            symbols TEXT,  -- "ES", "NQ", or "ES,NQ"

            -- The insight content
            title TEXT,  -- Short description
            insight_markdown TEXT NOT NULL,  -- Full narrative in markdown

            -- Query hints (optional)
            suggested_query TEXT,  -- SQL or description for auto-generating queries

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    cursor.execute("CREATE INDEX idx_insights_market_date_start ON insights(market_date_start);")
    cursor.execute("CREATE INDEX idx_insights_market_date_end ON insights(market_date_end);")
    cursor.execute("CREATE INDEX idx_insights_sessions ON insights(sessions_involved);")
    cursor.execute("CREATE INDEX idx_insights_confluence ON insights(confluence_factors);")
    cursor.execute("CREATE INDEX idx_insights_outcome ON insights(outcome_type);")
    cursor.execute("CREATE INDEX idx_insights_symbols ON insights(symbols);")

    # Full-text search on title and markdown content
    print("Creating insights_fts virtual table...")
    cursor.execute("""
        CREATE VIRTUAL TABLE insights_fts USING fts5(
            title,
            insight_markdown,
            content=insights
        );
    """)

    # -------------------------------------------------------------------------
    # Commit and verify
    # -------------------------------------------------------------------------
    conn.commit()

    # Verify tables were created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()

    print("\n[OK] Database created successfully!")
    print(f"[OK] Location: {db_path}")
    print(f"[OK] Tables created: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")

    # Verify indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name;")
    indexes = cursor.fetchall()
    print(f"\n[OK] Indexes created: {len(indexes)}")
    for index in indexes:
        if not index[0].startswith('sqlite_'):  # Skip auto-created indexes
            print(f"  - {index[0]}")

    conn.close()
    print("\nDatabase ready for 4-hour OHLC data and Yearly/Monthly session tracking.")


if __name__ == '__main__':
    create_database()
