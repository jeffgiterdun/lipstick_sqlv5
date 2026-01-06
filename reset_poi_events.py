#!/usr/bin/env python3
"""
Reset POI events and session status for reprocessing.
"""

import sqlite3

DB_PATH = 'data/ohlc_data.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Resetting POI events and session status...")
print()

# Clear POI events
cursor.execute("DELETE FROM poi_events")
deleted_events = cursor.rowcount
print(f"Deleted {deleted_events} POI events")

# Reset session status fields
cursor.execute("""
    UPDATE sessions
    SET status = 'unbroken',
        first_break_time = NULL,
        first_break_side = NULL,
        first_return_time = NULL,
        second_break_time = NULL,
        second_break_side = NULL,
        resolution_time = NULL,
        resolution_type = NULL,
        last_poi_check_time = NULL
""")
updated_sessions = cursor.rowcount
print(f"Reset {updated_sessions} sessions to unbroken status")

conn.commit()
print()
print("Done! Ready to reprocess POI events.")

conn.close()
