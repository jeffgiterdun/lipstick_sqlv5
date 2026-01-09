-- Update December 2025 Monthly Sessions with Correct Values
-- Run this file: sqlite3 data/ohlc_data.db < update_december_sessions.sql

-- First, let's see what we're updating
SELECT 'BEFORE UPDATE:' as status;
SELECT id, symbol, session_name, session_type,
       true_open as TO, poc as PoC, rpp as RPP,
       status, to_time, session_start_time
FROM sessions
WHERE session_type = 'Monthly'
AND (session_name LIKE '%December 2025%' OR session_name LIKE '2025-12%');

-- Update ES December 2025
UPDATE sessions
SET true_open = 6940.25,
    poc = 6859.25,
    rpp = 7021.00,
    updated_at = datetime('now')
WHERE session_type = 'Monthly'
AND symbol = 'ES'
AND (session_name LIKE '%December 2025%' OR session_name LIKE '2025-12%');

-- Update NQ December 2025
UPDATE sessions
SET true_open = 25997.25,
    poc = 25440.50,
    rpp = 26553.75,
    updated_at = datetime('now')
WHERE session_type = 'Monthly'
AND symbol = 'NQ'
AND (session_name LIKE '%December 2025%' OR session_name LIKE '2025-12%');

-- Verify the updates
SELECT 'AFTER UPDATE:' as status;
SELECT id, symbol, session_name, session_type,
       true_open as TO, poc as PoC, rpp as RPP,
       status, to_time, session_start_time
FROM sessions
WHERE session_type = 'Monthly'
AND (session_name LIKE '%December 2025%' OR session_name LIKE '2025-12%');

-- Show how many rows were updated
SELECT changes() as 'Rows Updated';
