"""
Quick POI Event Viewer

Display sample POI events with Echo Chamber data from yearly_monthly.db
"""

import sqlite3


def main():
    conn = sqlite3.connect('data/yearly_monthly.db')
    conn.row_factory = sqlite3.Row

    print("=" * 100)
    print("POI Event Viewer - Yearly and Monthly Sessions")
    print("=" * 100)

    # Summary statistics
    cursor = conn.cursor()

    print("\n[SESSION STATUS SUMMARY]")
    cursor.execute("""
        SELECT
            status,
            COUNT(*) as count
        FROM sessions
        GROUP BY status
        ORDER BY
            CASE status
                WHEN 'resolved' THEN 1
                WHEN 'return' THEN 2
                WHEN 'break' THEN 3
                WHEN 'unbroken' THEN 4
            END
    """)

    for row in cursor.fetchall():
        print(f"  {row['status']:12} {row['count']:3} sessions")

    # POI event summary
    print("\n[POI EVENT SUMMARY]")
    cursor.execute("SELECT COUNT(*) as count FROM poi_events")
    total_events = cursor.fetchone()['count']
    print(f"  Total POI Events: {total_events}")

    cursor.execute("""
        SELECT
            event_type,
            COUNT(*) as count
        FROM poi_events
        GROUP BY event_type
    """)

    for row in cursor.fetchall():
        print(f"    {row['event_type']:12} {row['count']:3} events")

    # Echo Chamber events (both ES and NQ touched)
    print("\n[ECHO CHAMBER EVENTS - Both ES and NQ Touched]")
    cursor.execute("""
        SELECT
            pe.session_name,
            pe.poi_type,
            pe.event_type,
            pe.es_event_time,
            pe.nq_event_time,
            pe.time_delta_minutes,
            pe.leader
        FROM poi_events pe
        WHERE pe.es_event_time IS NOT NULL
        AND pe.nq_event_time IS NOT NULL
        ORDER BY pe.time_delta_minutes ASC
        LIMIT 10
    """)

    print("\nTop 10 Most Synchronized (Smallest Time Delta):")
    print("-" * 100)

    for row in cursor.fetchall():
        row = dict(row)
        es_time = row['es_event_time'][-8:] if row['es_event_time'] else 'N/A'
        nq_time = row['nq_event_time'][-8:] if row['nq_event_time'] else 'N/A'

        print(f"{row['session_name']:20} | {row['poi_type']:3} {row['event_type']:10} | "
              f"ES: {es_time} | NQ: {nq_time} | "
              f"Leader: {row['leader']:12} | Delta: {row['time_delta_minutes']:6} min")

    # Resolved sessions
    print("\n[RESOLVED SESSIONS - Recent Completions]")
    cursor.execute("""
        SELECT
            s.symbol,
            s.session_name,
            s.first_break_side,
            s.second_break_side,
            s.resolution_type,
            s.resolution_time
        FROM sessions s
        WHERE s.status = 'resolved'
        ORDER BY s.resolution_time DESC
        LIMIT 15
    """)

    print("\nMost Recent 15 Resolutions:")
    print("-" * 100)

    for row in cursor.fetchall():
        row = dict(row)
        res_date = row['resolution_time'][:10] if row['resolution_time'] else 'N/A'

        print(f"{row['session_name']:20} ({row['symbol']}) | "
              f"{row['first_break_side']:3} -> {row['second_break_side']:3} | "
              f"{row['resolution_type']:13} | Resolved: {res_date}")

    # Active sessions waiting for resolution
    print("\n[ACTIVE SESSIONS - Waiting for Resolution]")
    cursor.execute("""
        SELECT
            s.symbol,
            s.session_name,
            s.status,
            s.first_break_side,
            s.second_break_side,
            s.first_break_time
        FROM sessions s
        WHERE s.status IN ('break', 'return')
        ORDER BY s.first_break_time DESC
        LIMIT 15
    """)

    print("\nMost Recent 15 Active Sessions:")
    print("-" * 100)

    for row in cursor.fetchall():
        row = dict(row)
        break_date = row['first_break_time'][:10] if row['first_break_time'] else 'N/A'
        second_break = row['second_break_side'] if row['second_break_side'] else '---'

        print(f"{row['session_name']:20} ({row['symbol']}) | "
              f"Status: {row['status']:8} | "
              f"{row['first_break_side']:3} -> {second_break:3} | "
              f"First Break: {break_date}")

    # Sample POI event sequence for a resolved session
    print("\n[SAMPLE POI EVENT SEQUENCE]")
    cursor.execute("""
        SELECT
            s.symbol,
            s.session_name,
            s.status
        FROM sessions s
        WHERE s.status = 'resolved'
        AND s.session_type = 'Yearly'
        ORDER BY s.session_start_time DESC
        LIMIT 1
    """)

    sample_session = cursor.fetchone()
    if sample_session:
        session_name = sample_session['session_name']
        symbol = sample_session['symbol']

        print(f"\n{session_name} ({symbol}) - Complete Event Sequence:")
        print("-" * 100)

        cursor.execute("""
            SELECT
                pe.poi_type,
                pe.event_type,
                COALESCE(pe.es_event_time, pe.nq_event_time) as event_time,
                pe.leader,
                pe.time_delta_minutes,
                pe.es_event_time,
                pe.nq_event_time
            FROM poi_events pe
            WHERE pe.session_name = ?
            ORDER BY event_time ASC
        """, (session_name,))

        for i, row in enumerate(cursor.fetchall(), 1):
            row = dict(row)
            event_date = row['event_time'][:19] if row['event_time'] else 'N/A'
            leader = f"Leader: {row['leader']}" if row['leader'] else ""
            delta = f"(Delta: {row['time_delta_minutes']} min)" if row['time_delta_minutes'] else ""

            print(f"  {i}. {row['poi_type']:3} {row['event_type']:10} | "
                  f"{event_date} | {leader} {delta}")

    conn.close()
    print("\n" + "=" * 100)


if __name__ == '__main__':
    main()
