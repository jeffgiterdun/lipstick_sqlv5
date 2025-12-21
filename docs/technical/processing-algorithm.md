# Processing Algorithm

Step-by-step implementation guide for the Lipstick Analytical Tool V5 processing system.

---

## Processing Overview

V5 processing happens in three distinct phases:

1. **Phase 1: Range Calculation** - Calculate ranges for all sessions
2. **Phase 2: POI Event Detection** - Detect touches and update statuses
3. **Phase 3: Swing Detection** - Classify swings and link to POI events

---

## Phase 1: Range Calculation

Process each symbol (ES, NQ) independently.

### Daily Session Calculation

For each calendar day in the dataset:

```python
def calculate_daily_sessions(symbol, calendar_date):
    """
    Calculate all Major and Minor sessions for a given calendar day.

    Args:
        symbol: 'ES' or 'NQ'
        calendar_date: Date in YYYY-MM-DD format

    Creates:
        5 Major sessions (Asia, London, NY_AM, NY_PM, Afternoon)
        16 Minor sessions (m1800 through m1630)
    """

    # Major Sessions
    for major_session in ['Asia', 'London', 'NY_AM', 'NY_PM', 'Afternoon']:
        session_start_time = get_session_start_time(major_session, calendar_date)
        to_time = get_to_time(major_session, calendar_date)

        # Calculate range
        ranges = calculate_session_ranges(
            symbol,
            major_session,
            session_start_time,
            to_time
        )

        # Insert into sessions table
        insert_session(
            symbol=symbol,
            session_type='Major',
            session_name=major_session,
            session_start_time=session_start_time,
            to_time=to_time,
            true_open=ranges['true_open'],
            poc=ranges['poc'],
            rpp=ranges['rpp'],
            status='unbroken',
            expires_at=None  # Never expires
        )

    # Minor Sessions
    for minor_session in ['m1800', 'm1930', ..., 'm1630']:
        session_start_time = get_session_start_time(minor_session, calendar_date)
        to_time = get_to_time(minor_session, calendar_date)
        expires_at = to_time + timedelta(hours=24)

        # Calculate range
        ranges = calculate_session_ranges(
            symbol,
            minor_session,
            session_start_time,
            to_time
        )

        # Insert into sessions table
        insert_session(
            symbol=symbol,
            session_type='Minor',
            session_name=minor_session,
            session_start_time=session_start_time,
            to_time=to_time,
            true_open=ranges['true_open'],
            poc=ranges['poc'],
            rpp=ranges['rpp'],
            status='unbroken',
            expires_at=expires_at  # Expires after 24 hours
        )
```

### Weekly Session Calculation

For each Sunday in the dataset:

```python
def calculate_weekly_session(symbol, sunday_date):
    """
    Calculate Weekly session starting on a Sunday.

    Args:
        symbol: 'ES' or 'NQ'
        sunday_date: Date of Sunday in YYYY-MM-DD format

    Creates:
        1 Weekly session
    """
    session_start_time = f"{sunday_date}T18:00:00-05:00"  # Adjust for DST

    # Monday is next day
    monday_date = sunday_date + timedelta(days=1)
    to_time = f"{monday_date}T18:00:00-05:00"

    # Calculate range (Sunday 18:00 through Monday 17:59)
    ranges = calculate_session_ranges(
        symbol,
        'Weekly',
        session_start_time,
        to_time
    )

    # Insert into sessions table
    insert_session(
        symbol=symbol,
        session_type='Weekly',
        session_name='Weekly',
        session_start_time=session_start_time,
        to_time=to_time,
        true_open=ranges['true_open'],
        poc=ranges['poc'],
        rpp=ranges['rpp'],
        status='unbroken',
        expires_at=None  # Never expires
    )
```

### Monthly Session Calculation

For each month in the dataset:

```python
def calculate_monthly_session(symbol, year, month):
    """
    Calculate Monthly session for a given month.

    Args:
        symbol: 'ES' or 'NQ'
        year: Year (e.g., 2025)
        month: Month (1-12)

    Creates:
        1 Monthly session
    """
    # Determine first full trading day
    first_day = date(year, month, 1)
    first_trading_day = get_first_full_trading_day(first_day)

    session_start_time = f"{first_trading_day}T18:00:00-05:00"

    # Determine second full week Sunday
    second_full_week_sunday = get_second_full_week_sunday(first_day)
    to_time = f"{second_full_week_sunday}T18:00:00-05:00"

    # Calculate range
    ranges = calculate_session_ranges(
        symbol,
        'Monthly',
        session_start_time,
        to_time
    )

    # Insert into sessions table
    insert_session(
        symbol=symbol,
        session_type='Monthly',
        session_name='Monthly',
        session_start_time=session_start_time,
        to_time=to_time,
        true_open=ranges['true_open'],
        poc=ranges['poc'],
        rpp=ranges['rpp'],
        status='unbroken',
        expires_at=None  # Never expires
    )
```

### Yearly Session Calculation

For each year in the dataset:

```python
def calculate_yearly_session(symbol, year):
    """
    Calculate Yearly session for a given year.

    Args:
        symbol: 'ES' or 'NQ'
        year: Year (e.g., 2025)

    Creates:
        1 Yearly session
    """
    # Determine first full trading day of January
    jan_first = date(year, 1, 1)
    first_trading_day = get_first_full_trading_day_of_year(jan_first)

    session_start_time = f"{first_trading_day}T18:00:00-05:00"

    # TO is set at first Sunday 18:00 of April
    first_april_sunday = get_first_sunday_of_april(year)
    to_time = f"{first_april_sunday}T18:00:00-05:00"

    # Calculate range (Q1: first trading day through end of March)
    ranges = calculate_session_ranges(
        symbol,
        'Yearly',
        session_start_time,
        to_time
    )

    # Insert into sessions table
    insert_session(
        symbol=symbol,
        session_type='Yearly',
        session_name='Yearly',
        session_start_time=session_start_time,
        to_time=to_time,
        true_open=ranges['true_open'],
        poc=ranges['poc'],
        rpp=ranges['rpp'],
        status='unbroken',
        expires_at=None  # Never expires
    )
```

---

## Phase 2: POI Event Detection

Process ES and NQ simultaneously to build echo chamber data.

```python
def process_poi_events():
    """
    Process all candles chronologically, detecting POI touches
    and updating sessions + poi_events tables.

    Processes both ES and NQ together to capture echo chamber timing.
    """

    # Get all candles for both symbols, sorted chronologically
    all_candles = load_all_candles_sorted(['ES', 'NQ'])

    for candle in all_candles:
        symbol = candle['symbol']
        candle_time = candle['time']

        # Get all active sessions for this symbol
        active_sessions = get_active_sessions(symbol, candle_time)

        for session in active_sessions:
            # Detect touches
            touches = detect_touches(
                candle,
                true_open=session.true_open,
                poc=session.poc,
                rpp=session.rpp
            )

            # Process each touched level
            for poi_type in ['PoC', 'RPP', 'TO']:
                if touches[poi_type]:
                    process_poi_touch(
                        session=session,
                        symbol=symbol,
                        candle_time=candle_time,
                        poi_type=poi_type
                    )
```

### POI Touch Processing

```python
def process_poi_touch(session, symbol, candle_time, poi_type):
    """
    Handle a POI touch event.

    Steps:
    1. Apply state machine to determine event_type
    2. Update session status
    3. Create or update poi_event record with denormalized context
    """

    # Apply state machine
    current_status = get_session_status_dict(session)
    updated_status, event_type, should_record = apply_touch_event(
        current_status,
        poi_type,
        candle_time
    )

    # Update session
    update_session_status(session.id, updated_status)

    # Record POI event if state machine says to
    if should_record:
        # Calculate trading day for this event
        trading_day = get_trading_day(candle_time)

        # Check if poi_event already exists for this session+poi+event
        existing_event = query_poi_event(
            session_id=session.id,
            poi_type=poi_type,
            event_type=event_type
        )

        if existing_event is None:
            # First touch - create new poi_event with denormalized context
            if symbol == 'ES':
                insert_poi_event(
                    session_id=session.id,
                    trading_day=trading_day,
                    symbol=session.symbol,
                    session_type=session.session_type,
                    session_name=session.session_name,
                    poi_type=poi_type,
                    event_type=event_type,
                    es_event_time=candle_time,
                    nq_event_time=None
                )
            else:  # NQ
                insert_poi_event(
                    session_id=session.id,
                    trading_day=trading_day,
                    symbol=session.symbol,
                    session_type=session.session_type,
                    session_name=session.session_name,
                    poi_type=poi_type,
                    event_type=event_type,
                    es_event_time=None,
                    nq_event_time=candle_time
                )

        else:
            # Second touch - update existing poi_event
            if symbol == 'ES':
                update_poi_event(
                    event_id=existing_event.id,
                    es_event_time=candle_time,
                    nq_event_time=existing_event.nq_event_time
                )
            else:  # NQ
                update_poi_event(
                    event_id=existing_event.id,
                    es_event_time=existing_event.es_event_time,
                    nq_event_time=candle_time
                )

            # Calculate echo chamber metrics
            calculate_echo_chamber_metrics(existing_event.id)
```

### Trading Day Helper Function

```python
def get_trading_day(timestamp):
    """
    Calculate trading day from timestamp.

    Trading day runs 18:00 to 16:59 (next calendar day).

    Args:
        timestamp: ISO 8601 timestamp string

    Returns:
        Trading day in YYYY-MM-DD format
    """
    dt = parse_iso_timestamp(timestamp)

    # If time is 00:00 to 16:59, trading day is same calendar date
    if dt.hour < 18:
        return dt.date().isoformat()

    # If time is 18:00 to 23:59, trading day is next calendar date
    else:
        next_day = dt.date() + timedelta(days=1)
        return next_day.isoformat()
```

---

## Phase 3: Swing Detection

Executes AFTER Phase 2 (POI events) is complete.

### Overview of Swing Detection Process

```python
def build_swings_table():
    """
    Detect and classify all swings for both symbols.

    Process:
    1. Detect Class 1 swings (3-bar pivots)
    2. Promote Class 1 → Class 2
    3. Promote Class 2 → Class 3
    4. Promote Class 3 → Class 4
    5. Calculate movement metrics
    6. Link to POI events
    7. Capture session context
    """

    for symbol in ['ES', 'NQ']:
        print(f"Processing swings for {symbol}...")

        # Load all candles
        candles = load_all_candles(symbol)

        # Pass 1: Detect Class 1 swings
        swings = detect_class1_swings(candles)

        # Pass 2: Promote to Class 2
        swings = promote_to_class2(swings)

        # Pass 3: Promote to Class 3
        swings = promote_to_class3(swings)

        # Pass 4: Promote to Class 4
        swings = promote_to_class4(swings)

        # Pass 5: Calculate movement metrics
        swings = calculate_movement_metrics(swings)

        # Pass 6: Link to POI events
        swings = link_to_poi_events(symbol, swings)

        # Pass 7: Capture session context
        swings = capture_session_context(symbol, swings)

        # Insert all swings
        for swing in swings:
            insert_swing(swing)
```

### Pass 1: Detect Class 1 Swings

```python
def detect_class1_swings(candles):
    """
    Detect all Class 1 swings using 3-bar pivot logic.

    Class 1 High: high[i] > high[i-1] AND high[i] > high[i+1]
    Class 1 Low: low[i] < low[i-1] AND low[i] < low[i+1]

    Returns:
        List of swing dicts with keys: time, price, type, class
    """
    swings = []

    for i in range(1, len(candles) - 1):
        prev = candles[i-1]
        curr = candles[i]
        next = candles[i+1]

        # Class 1 High
        if curr['high'] > prev['high'] and curr['high'] > next['high']:
            swings.append({
                'time': curr['time'],
                'price': curr['high'],
                'type': 'high',
                'class': 1
            })

        # Class 1 Low
        if curr['low'] < prev['low'] and curr['low'] < next['low']:
            swings.append({
                'time': curr['time'],
                'price': curr['low'],
                'type': 'low',
                'class': 1
            })

    return swings
```

### Pass 2-4: Promotion Logic

```python
def promote_to_class2(swings):
    """
    Promote Class 1 swings to Class 2.

    Rule:
    - Class 1 HIGH → Class 2 if has Class 1 LOWs before AND after
    - Class 1 LOW → Class 2 if has Class 1 HIGHs before AND after
    """
    for i, swing in enumerate(swings):
        if swing['class'] != 1:
            continue

        if swing['type'] == 'high':
            # Need Class 1 lows before and after
            lows_before = [s for s in swings[:i] if s['type'] == 'low' and s['class'] == 1]
            lows_after = [s for s in swings[i+1:] if s['type'] == 'low' and s['class'] == 1]

            if lows_before and lows_after:
                swing['class'] = 2

        elif swing['type'] == 'low':
            # Need Class 1 highs before and after
            highs_before = [s for s in swings[:i] if s['type'] == 'high' and s['class'] == 1]
            highs_after = [s for s in swings[i+1:] if s['type'] == 'high' and s['class'] == 1]

            if highs_before and highs_after:
                swing['class'] = 2

    return swings

# Similar logic for promote_to_class3() and promote_to_class4()
```

### Pass 6: Link to POI Events

```python
def link_to_poi_events(symbol, swings):
    """
    Link each swing to nearest POI event (if any).

    Matching criteria:
    - Same symbol
    - POI event time within ±5 minutes of swing time
    - POI event price within ±5 ticks of swing price

    If multiple POI events match, choose closest in time.
    """
    for swing in swings:
        swing_time = parse_iso_timestamp(swing['time'])
        swing_price = swing['price']

        # Query POI events near this swing
        nearby_events = query_nearby_poi_events(
            symbol=symbol,
            center_time=swing_time,
            time_window_minutes=5,
            center_price=swing_price,
            price_window_ticks=5
        )

        if nearby_events:
            # Find closest in time
            closest = min(
                nearby_events,
                key=lambda e: abs((parse_iso_timestamp(e.es_event_time or e.nq_event_time) - swing_time).total_seconds())
            )
            swing['nearest_poi_event_id'] = closest.id
        else:
            swing['nearest_poi_event_id'] = None

    return swings
```

### Pass 7: Capture Session Context

```python
def capture_session_context(symbol, swings):
    """
    Capture active session statuses at the moment of each swing.

    Stores as JSON in active_sessions_snapshot field.
    """
    for swing in swings:
        swing_time = swing['time']

        # Get all active sessions at this moment
        active_sessions = get_active_sessions(symbol, swing_time)

        # Build snapshot JSON
        snapshot = {
            'major_sessions': {},
            'weekly_session': None,
            'monthly_session': None,
            'current_minor': None
        }

        for session in active_sessions:
            if session.session_type == 'Major':
                snapshot['major_sessions'][session.session_name] = {
                    'status': session.status,
                    'first_break_time': session.first_break_time,
                    'first_return_time': session.first_return_time,
                    'resolution_time': session.resolution_time
                }

            elif session.session_type == 'Weekly':
                snapshot['weekly_session'] = {
                    'status': session.status,
                    'first_break_time': session.first_break_time,
                    'first_return_time': session.first_return_time,
                    'resolution_time': session.resolution_time
                }

            elif session.session_type == 'Monthly':
                snapshot['monthly_session'] = {
                    'status': session.status,
                    'first_break_time': session.first_break_time,
                    'first_return_time': session.first_return_time,
                    'resolution_time': session.resolution_time
                }

            elif session.session_type == 'Yearly':
                snapshot['yearly_session'] = {
                    'status': session.status,
                    'first_break_time': session.first_break_time,
                    'first_return_time': session.first_return_time,
                    'resolution_time': session.resolution_time
                }

            elif session.session_type == 'Minor':
                # Determine if this is the "current" minor (the one the swing is in)
                if (session.session_start_time <= swing_time and
                    swing_time <= session.session_start_time + timedelta(minutes=90)):
                    snapshot['current_minor'] = {
                        'session': session.session_name,
                        'status': session.status
                    }

        # Convert to JSON string
        swing['active_sessions_snapshot'] = json.dumps(snapshot)

    return swings
```

---

## Implementation Phases

### Phase 1: Database Setup
```bash
# Create schema
sqlite3 data/ohlc_data.db < schema_v5.sql

# Verify tables
sqlite3 data/ohlc_data.db ".tables"
# Expected: ohlc_1m, sessions, poi_events, swings, insights
```

### Phase 2: Range Calculation
```bash
python calculate_ranges_v5.py

# Output:
# - Populates sessions table
# - All Major, Minor, Weekly, Monthly sessions
# - Sets expires_at for Minor sessions
# - Status = 'unbroken' for all
```

### Phase 3: POI Event Processing
```bash
python process_poi_events_v5.py

# Output:
# - Updates sessions table (status changes)
# - Populates poi_events table
# - Echo chamber metrics calculated
```

### Phase 4: Swing Detection
```bash
python detect_swings_v5.py

# Output:
# - Populates swings table
# - Links to poi_events
# - Captures session context
```

### Phase 5: Verification
```bash
python verify_v5.py

# Checks:
# - Session count (21 per trading day + Weekly/Monthly)
# - POI event echo chamber completeness
# - Swing classification distribution
# - Session context snapshot validity
```

---

## Next Steps

- [Calculation Logic](calculation-logic.md) - Detailed calculation algorithms
- [Edge Cases](edge-cases.md) - Handling special scenarios
- [Database Schema](database-schema.md) - Table structure reference
