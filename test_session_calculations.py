#!/usr/bin/env python3
"""
Test session calculation logic to verify correctness.

This script tests the helper functions and verifies the session calculations
match the specifications in docs/reference/session-tables.md
"""

from datetime import datetime, time
import pytz
from calculate_daily_sessions import (
    get_first_full_trading_day_of_month,
    get_second_full_week_sunday,
    get_first_full_trading_day_of_year,
    get_first_sunday_of_april
)

ET = pytz.timezone('US/Eastern')


def test_monthly_session_january_2025():
    """Test January 2025 monthly session calculation."""
    print("\n" + "="*80)
    print("Test: January 2025 Monthly Session")
    print("="*80)

    # January 1, 2025 = Wednesday
    print("January 1, 2025 = Wednesday")

    # Expected: First full trading day is Tuesday Dec 31, 2024 at 18:00
    poc_start = get_first_full_trading_day_of_month(2025, 1)
    print(f"PoC Start (Begin Looking): {poc_start}")
    print(f"Expected: 2024-12-31 18:00:00 ET")

    # Expected: Second full week Sunday is Jan 12, 2025 at 18:00
    to_time = get_second_full_week_sunday(2025, 1)
    print(f"True Open: {to_time}")
    print(f"Expected: 2025-01-12 18:00:00 ET")

    # Verify
    expected_poc = ET.localize(datetime(2024, 12, 31, 18, 0))
    expected_to = ET.localize(datetime(2025, 1, 12, 18, 0))

    assert poc_start == expected_poc, f"PoC start mismatch! Got {poc_start}, expected {expected_poc}"
    assert to_time == expected_to, f"TO time mismatch! Got {to_time}, expected {expected_to}"

    print("[PASSED]")


def test_yearly_session_2025():
    """Test 2025 yearly session calculation."""
    print("\n" + "="*80)
    print("Test: 2025 Yearly Session")
    print("="*80)

    # January 1, 2025 = Wednesday
    print("January 1, 2025 = Wednesday")

    # Expected: First full trading day is Tuesday Dec 31, 2024 at 18:00
    poc_start = get_first_full_trading_day_of_year(2025)
    print(f"PoC Start (Begin Looking): {poc_start}")
    print(f"Expected: 2024-12-31 18:00:00 ET")

    # Expected: First Sunday of April 2025
    # April 1, 2025 = Tuesday, so first Sunday is April 6
    to_time = get_first_sunday_of_april(2025)
    print(f"True Open: {to_time}")
    print(f"Expected: 2025-04-06 18:00:00 ET")

    # Verify
    expected_poc = ET.localize(datetime(2024, 12, 31, 18, 0))
    expected_to = ET.localize(datetime(2025, 4, 6, 18, 0))

    assert poc_start == expected_poc, f"PoC start mismatch! Got {poc_start}, expected {expected_poc}"
    assert to_time == expected_to, f"TO time mismatch! Got {to_time}, expected {expected_to}"

    print("[PASSED]")


def test_monthly_various_scenarios():
    """Test monthly session calculation for various first-of-month scenarios."""
    print("\n" + "="*80)
    print("Test: Monthly Sessions - Various Scenarios")
    print("="*80)

    test_cases = [
        # (year, month, first_day_of_week, expected_poc_date, expected_to_date)
        (2025, 1, "Wednesday", "2024-12-31", "2025-01-12"),  # Jan 1 = Wed
        (2025, 2, "Saturday", "2025-02-02", "2025-02-09"),   # Feb 1 = Sat, TO = Sun before 2nd full week
        (2025, 3, "Saturday", "2025-03-02", "2025-03-09"),   # Mar 1 = Sat, TO = Sun before 2nd full week
    ]

    for year, month, dow, expected_poc, expected_to in test_cases:
        poc_start = get_first_full_trading_day_of_month(year, month)
        to_time = get_second_full_week_sunday(year, month)

        print(f"\n{year}-{month:02d} (1st = {dow}):")
        print(f"  PoC Start: {poc_start.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Expected:  {expected_poc} 18:00")
        print(f"  True Open: {to_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Expected:  {expected_to} 18:00")

        assert poc_start.strftime('%Y-%m-%d') == expected_poc, \
            f"PoC mismatch for {year}-{month}"
        assert to_time.strftime('%Y-%m-%d') == expected_to, \
            f"TO mismatch for {year}-{month}"

        print("  [PASSED]")


def test_major_session_times():
    """Verify Major session times are correct."""
    print("\n" + "="*80)
    print("Test: Major Session Time Definitions")
    print("="*80)

    from calculate_daily_sessions import MAJOR_SESSIONS

    expected = {
        'Asia': {'start': '18:00', 'end': '23:59', 'to': '19:30'},
        'London': {'start': '00:00', 'end': '05:59', 'to': '01:30'},
        'NY_AM': {'start': '06:00', 'end': '11:59', 'to': '07:30'},
        'NY_PM': {'start': '12:00', 'end': '16:59', 'to': '13:30'},
        'Afternoon': {'start': '13:30', 'end': '16:59', 'to': '15:00'},
    }

    for session_name, times in expected.items():
        actual = MAJOR_SESSIONS[session_name]
        print(f"\n{session_name}:")
        print(f"  Start: {actual['start']} (expected {times['start']})")
        print(f"  End: {actual['end']} (expected {times['end']})")
        print(f"  TO: {actual['to_time']} (expected {times['to']})")

        assert actual['start'].strftime('%H:%M') == times['start']
        assert actual['end'].strftime('%H:%M') == times['end']
        assert actual['to_time'].strftime('%H:%M') == times['to']

        print("  [PASSED]")


def test_minor_session_definitions():
    """Verify Minor session definitions are correct."""
    print("\n" + "="*80)
    print("Test: Minor Session Definitions")
    print("="*80)

    from calculate_daily_sessions import MINOR_SESSIONS

    expected_names = [
        'm1800', 'm1930', 'm2100', 'm2230',
        'm0000', 'm0130', 'm0300', 'm0430',
        'm0600', 'm0730', 'm0900', 'm1030',
        'm1200', 'm1330', 'm1500', 'm1630'
    ]

    print(f"\nExpected 16 sessions: {len(expected_names)}")
    print(f"Actual: {len(MINOR_SESSIONS)}")
    assert len(MINOR_SESSIONS) == 16, "Should have exactly 16 minor sessions"

    actual_names = [s[0] for s in MINOR_SESSIONS]
    print(f"\nSession names:")
    print(f"Expected: {expected_names}")
    print(f"Actual:   {actual_names}")
    assert actual_names == expected_names, "Minor session names don't match"

    # Verify first session (m1800)
    print(f"\nm1800 details:")
    print(f"  Start: {MINOR_SESSIONS[0][1]}")
    print(f"  TO offset: {MINOR_SESSIONS[0][2]} minutes")
    print(f"  Duration: {MINOR_SESSIONS[0][3]} minutes")
    print(f"  Begin looking: {MINOR_SESSIONS[0][4]}")

    assert MINOR_SESSIONS[0][2] == 22, "TO offset should be 22 minutes"
    assert MINOR_SESSIONS[0][3] == 89, "Duration should be 89 minutes"

    print("\n[PASSED]")


def main():
    """Run all tests."""
    print("="*80)
    print("Session Calculation Tests")
    print("="*80)

    try:
        test_major_session_times()
        test_minor_session_definitions()
        test_monthly_session_january_2025()
        test_yearly_session_2025()
        test_monthly_various_scenarios()

        print("\n" + "="*80)
        print("ALL TESTS PASSED")
        print("="*80)

    except AssertionError as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
