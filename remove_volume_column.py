import sqlite3

DB_PATH = 'data/ohlc_data.db'

print("\nRemoving volume column from ohlc_1m table...")
print("=" * 80)

# Connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Enable foreign key constraints
cursor.execute("PRAGMA foreign_keys = OFF")

try:
    # Step 1: Create new table without volume column
    print("1. Creating new table structure without volume column...")
    cursor.execute("""
    CREATE TABLE ohlc_1m_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        time TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        UNIQUE(symbol, time)
    )
    """)
    print("   [OK] New table created")

    # Step 2: Copy data from old table to new table
    print("\n2. Copying data from old table to new table...")
    cursor.execute("""
    INSERT INTO ohlc_1m_new (id, symbol, time, open, high, low, close)
    SELECT id, symbol, time, open, high, low, close
    FROM ohlc_1m
    """)
    rows_copied = cursor.rowcount
    print(f"   [OK] Copied {rows_copied} rows")

    # Step 3: Drop old table
    print("\n3. Dropping old table...")
    cursor.execute("DROP TABLE ohlc_1m")
    print("   [OK] Old table dropped")

    # Step 4: Rename new table to original name
    print("\n4. Renaming new table to 'ohlc_1m'...")
    cursor.execute("ALTER TABLE ohlc_1m_new RENAME TO ohlc_1m")
    print("   [OK] Table renamed")

    # Step 5: Recreate index
    print("\n5. Recreating index...")
    cursor.execute("CREATE INDEX idx_ohlc_symbol_time ON ohlc_1m(symbol, time)")
    print("   [OK] Index created")

    # Commit changes
    conn.commit()
    print("\n" + "=" * 80)
    print("[OK] Volume column successfully removed")
    print("=" * 80)

except Exception as e:
    print(f"\n[ERROR] Failed to remove column: {e}")
    conn.rollback()
    raise

finally:
    cursor.execute("PRAGMA foreign_keys = ON")

# Verify the new schema
print("\n" + "=" * 80)
print("UPDATED SCHEMA")
print("=" * 80)

cursor.execute("PRAGMA table_info(ohlc_1m)")
columns = cursor.fetchall()

print(f"\n{'Column':<20} {'Type':<15} {'Not Null':<10} {'Default':<10} {'PK'}")
print("-" * 80)
for col in columns:
    col_name = col[1]
    col_type = col[2]
    not_null = 'YES' if col[3] else 'NO'
    default = col[4] if col[4] else ''
    pk = 'YES' if col[5] else 'NO'
    print(f"{col_name:<20} {col_type:<15} {not_null:<10} {default:<10} {pk}")

# Verify data integrity
print("\n" + "=" * 80)
print("DATA VERIFICATION")
print("=" * 80)

cursor.execute("SELECT COUNT(*) FROM ohlc_1m")
total = cursor.fetchone()[0]
print(f"Total records: {total}")

cursor.execute("SELECT symbol, COUNT(*) FROM ohlc_1m GROUP BY symbol")
print("\nRecords by symbol:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Show sample data
print("\nSample record (ES):")
cursor.execute("SELECT * FROM ohlc_1m WHERE symbol = 'ES' LIMIT 1")
sample = cursor.fetchone()
if sample:
    print(f"  ID: {sample[0]}")
    print(f"  Symbol: {sample[1]}")
    print(f"  Time: {sample[2]}")
    print(f"  Open: {sample[3]}")
    print(f"  High: {sample[4]}")
    print(f"  Low: {sample[5]}")
    print(f"  Close: {sample[6]}")

print("=" * 80)

conn.close()
