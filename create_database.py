import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = 'data/ohlc_data.db'

# Remove existing database if it exists
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"Removed existing database at {DB_PATH}")

# Create database connection
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Enable foreign key constraints
cursor.execute("PRAGMA foreign_keys = ON")

print(f"\nCreating Lipstick Trading System V5 database at: {DB_PATH}")
print("=" * 80)

# =============================================================================
# 1. OHLC_1M TABLE - Raw OHLC Data
# =============================================================================
print("\n1. Creating ohlc_1m table...")

cursor.execute("""
CREATE TABLE ohlc_1m (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    time TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER,
    UNIQUE(symbol, time)
)
""")

cursor.execute("CREATE INDEX idx_ohlc_symbol_time ON ohlc_1m(symbol, time)")
print("   [OK] ohlc_1m table created")
print("   [OK] Index: idx_ohlc_symbol_time")

# =============================================================================
# 2. SESSIONS TABLE - Range Values & Status Tracking
# =============================================================================
print("\n2. Creating sessions table...")

cursor.execute("""
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    session_type TEXT NOT NULL,
    session_name TEXT NOT NULL,

    -- Time boundaries
    session_start_time TEXT NOT NULL,
    to_time TEXT NOT NULL,

    -- Range values
    true_open REAL,
    poc REAL,
    rpp REAL,

    -- Status tracking
    status TEXT NOT NULL,
    first_break_time TEXT,
    first_break_side TEXT,
    first_return_time TEXT,
    second_break_time TEXT,
    second_break_side TEXT,
    resolution_time TEXT,
    resolution_type TEXT,

    -- Expiry tracking
    expires_at TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE(symbol, session_type, session_name, session_start_time)
)
""")

cursor.execute("CREATE INDEX idx_sessions_symbol_status ON sessions(symbol, status)")
cursor.execute("CREATE INDEX idx_sessions_active ON sessions(symbol, status) WHERE status != 'resolved'")
cursor.execute("CREATE INDEX idx_sessions_unexpired ON sessions(symbol, expires_at) WHERE expires_at IS NULL OR expires_at > datetime('now')")
print("   [OK] sessions table created")
print("   [OK] Index: idx_sessions_symbol_status")
print("   [OK] Index: idx_sessions_active (partial)")
print("   [OK] Index: idx_sessions_unexpired (partial)")

# =============================================================================
# 3. POI_EVENTS TABLE - POI Touches with Echo Chamber
# =============================================================================
print("\n3. Creating poi_events table...")

cursor.execute("""
CREATE TABLE poi_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,

    -- Denormalized session context
    trading_day TEXT NOT NULL,
    symbol TEXT NOT NULL,
    session_type TEXT NOT NULL,
    session_name TEXT NOT NULL,

    poi_type TEXT NOT NULL,
    event_type TEXT NOT NULL,

    -- ES timing
    es_event_time TEXT,

    -- NQ timing
    nq_event_time TEXT,

    -- Echo Chamber metrics
    time_delta_seconds INTEGER,
    leader TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (session_id) REFERENCES sessions(id)
)
""")

cursor.execute("CREATE INDEX idx_poi_events_session ON poi_events(session_id)")
cursor.execute("CREATE INDEX idx_poi_events_trading_day ON poi_events(trading_day)")
cursor.execute("CREATE INDEX idx_poi_events_symbol_session ON poi_events(symbol, session_name)")
cursor.execute("CREATE INDEX idx_poi_events_es_time ON poi_events(es_event_time)")
cursor.execute("CREATE INDEX idx_poi_events_nq_time ON poi_events(nq_event_time)")
print("   [OK] poi_events table created")
print("   [OK] Index: idx_poi_events_session")
print("   [OK] Index: idx_poi_events_trading_day")
print("   [OK] Index: idx_poi_events_symbol_session")
print("   [OK] Index: idx_poi_events_es_time")
print("   [OK] Index: idx_poi_events_nq_time")

# =============================================================================
# 4. SWINGS TABLE - Hierarchical Swing Detection
# =============================================================================
print("\n4. Creating swings table...")

cursor.execute("""
CREATE TABLE swings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    swing_time TEXT NOT NULL,
    swing_price REAL NOT NULL,
    swing_type TEXT NOT NULL,
    swing_class INTEGER NOT NULL,

    -- Movement context
    prior_opposite_swing_id INTEGER,
    points_from_prior REAL,
    candles_from_prior INTEGER,

    -- POI linkage
    nearest_poi_event_id INTEGER,

    -- Session context snapshot
    active_sessions_snapshot TEXT,

    created_at TEXT NOT NULL,
    FOREIGN KEY (prior_opposite_swing_id) REFERENCES swings(id),
    FOREIGN KEY (nearest_poi_event_id) REFERENCES poi_events(id)
)
""")

cursor.execute("CREATE INDEX idx_swings_symbol_time ON swings(symbol, swing_time)")
cursor.execute("CREATE INDEX idx_swings_class ON swings(swing_class)")
cursor.execute("CREATE INDEX idx_swings_major ON swings(swing_class) WHERE swing_class >= 3")
cursor.execute("CREATE INDEX idx_swings_poi_link ON swings(nearest_poi_event_id)")
print("   [OK] swings table created")
print("   [OK] Index: idx_swings_symbol_time")
print("   [OK] Index: idx_swings_class")
print("   [OK] Index: idx_swings_major (partial)")
print("   [OK] Index: idx_swings_poi_link")

# =============================================================================
# 5. INSIGHTS TABLE - Research Journal
# =============================================================================
print("\n5. Creating insights table...")

cursor.execute("""
CREATE TABLE insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Temporal context
    observation_date TEXT NOT NULL,
    market_date_start TEXT,
    market_date_end TEXT,

    -- Session context
    sessions_involved TEXT,

    -- Classification/tags
    confluence_factors TEXT,
    outcome_type TEXT,
    symbols TEXT,

    -- Content
    title TEXT,
    insight_markdown TEXT NOT NULL,

    -- Query hints
    suggested_query TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
""")

cursor.execute("CREATE INDEX idx_insights_market_date_start ON insights(market_date_start)")
cursor.execute("CREATE INDEX idx_insights_market_date_end ON insights(market_date_end)")
cursor.execute("CREATE INDEX idx_insights_sessions ON insights(sessions_involved)")
cursor.execute("CREATE INDEX idx_insights_confluence ON insights(confluence_factors)")
cursor.execute("CREATE INDEX idx_insights_outcome ON insights(outcome_type)")
cursor.execute("CREATE INDEX idx_insights_symbols ON insights(symbols)")
print("   [OK] insights table created")
print("   [OK] Index: idx_insights_market_date_start")
print("   [OK] Index: idx_insights_market_date_end")
print("   [OK] Index: idx_insights_sessions")
print("   [OK] Index: idx_insights_confluence")
print("   [OK] Index: idx_insights_outcome")
print("   [OK] Index: idx_insights_symbols")

# =============================================================================
# 6. INSIGHTS FTS5 TABLE - Full-Text Search
# =============================================================================
print("\n6. Creating insights_fts virtual table...")

cursor.execute("""
CREATE VIRTUAL TABLE insights_fts USING fts5(
    title,
    insight_markdown,
    content=insights
)
""")
print("   [OK] insights_fts virtual table created (FTS5)")

# =============================================================================
# Commit and Close
# =============================================================================
conn.commit()
print("\n" + "=" * 80)
print("[OK] Database created successfully!")
print("=" * 80)

# =============================================================================
# VERIFICATION
# =============================================================================
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

# Check foreign keys
cursor.execute("PRAGMA foreign_keys")
fk_status = cursor.fetchone()[0]
print(f"\nForeign Keys Enabled: {'YES' if fk_status else 'NO'}")

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print(f"\nTotal Tables: {len(tables)}")
for table in tables:
    print(f"  - {table[0]}")

# Get virtual tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%VIRTUAL%' ORDER BY name")
virtual_tables = cursor.fetchall()
print(f"\nVirtual Tables (FTS5): {len(virtual_tables)}")
for table in virtual_tables:
    print(f"  - {table[0]}")

# Get all indexes
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name")
indexes = cursor.fetchall()
print(f"\nTotal Indexes: {len(indexes)}")
for idx in indexes:
    print(f"  - {idx[0]}")

print("\n" + "=" * 80)
print("DETAILED SCHEMAS")
print("=" * 80)

# Show schema for each table
for table in ['ohlc_1m', 'sessions', 'poi_events', 'swings', 'insights']:
    print(f"\n{table.upper()} TABLE:")
    print("-" * 80)
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print(f"{'Column':<30} {'Type':<15} {'Not Null':<10} {'Default'}")
    print("-" * 80)
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        not_null = 'YES' if col[3] else 'NO'
        default = col[4] if col[4] else ''
        print(f"{col_name:<30} {col_type:<15} {not_null:<10} {default}")

# Show foreign keys
print("\n" + "=" * 80)
print("FOREIGN KEY CONSTRAINTS")
print("=" * 80)

for table in ['poi_events', 'swings']:
    cursor.execute(f"PRAGMA foreign_key_list({table})")
    fks = cursor.fetchall()
    if fks:
        print(f"\n{table.upper()}:")
        for fk in fks:
            print(f"  {fk[3]} -> {fk[2]}({fk[4]})")

conn.close()
print("\n" + "=" * 80)
print("Database connection closed.")
print("=" * 80)
