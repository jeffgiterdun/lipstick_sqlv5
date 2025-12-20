# State Machine Reference

Complete reference for session status transitions in the Lipstick Trading System.

---

## Session States

### Four States

1. **unbroken** - Initial state, no touches yet
2. **break** - First boundary (PoC or RPP) has been touched
3. **return** - Returned to TO after first break
4. **resolved** - Second break + second TO return completed

---

## State Transitions

### Transition Table

| Current State | Event | What Gets Recorded | Next State |
|---------------|-------|-------------------|------------|
| **unbroken** | Touch PoC or RPP | `first_break_time`<br>`first_break_side` | **break** |
| **break** | Touch PoC or RPP (repeat) | Nothing (ignored) | **break** |
| **break** | Touch TO | `first_return_time` | **return** |
| **return** | Touch PoC or RPP | `second_break_time`<br>`second_break_side` | **return** |
| **return** | Touch PoC or RPP (repeat) | Nothing (ignored) | **return** |
| **return** | Touch TO | `resolution_time`<br>`resolution_type` | **resolved** |
| **resolved** | Any touch | Nothing (session complete) | **resolved** |

---

## State Diagram

```
┌──────────┐
│          │
│ unbroken │  Initial state when range is set
│          │
└────┬─────┘
     │
     │ Touch PoC or RPP
     │ Record: first_break_time, first_break_side
     ▼
┌──────────┐
│          │
│  break   │  Waiting for TO return
│          │
└────┬─────┘
     │
     │ Touch TO
     │ Record: first_return_time
     ▼
┌──────────┐
│          │
│  return  │  Waiting for second break
│          │
└────┬─────┘
     │
     │ Touch PoC or RPP
     │ Record: second_break_time, second_break_side
     │ (stay in return state)
     ▼
┌──────────┐
│          │
│  return  │  Waiting for second TO return
│          │
└────┬─────┘
     │
     │ Touch TO
     │ Record: resolution_time, resolution_type
     ▼
┌──────────┐
│          │
│ resolved │  Session complete
│          │
└──────────┘
```

---

## Resolution Types

### Single Sided Resolution

Both breaks occurred on the same side.

**Examples:**
- First break: PoC → Second break: PoC
- First break: RPP → Second break: RPP

**Formula:**
```python
if first_break_side == second_break_side:
    resolution_type = 'single_sided'
```

### Double Sided Resolution

Breaks occurred on opposite sides.

**Examples:**
- First break: PoC → Second break: RPP
- First break: RPP → Second break: PoC

**Formula:**
```python
if first_break_side != second_break_side:
    resolution_type = 'double_sided'
```

---

## Detailed State Behavior

### unbroken State

**Conditions:**
- Range has been calculated (TO time reached)
- No touches of PoC or RPP yet

**Waiting For:**
- First touch of PoC or RPP

**Ignores:**
- TO touches (not meaningful until after a break)

---

### break State

**Conditions:**
- PoC or RPP has been touched at least once
- TO has not been touched yet (after the break)

**Waiting For:**
- First touch of TO

**Ignores:**
- Additional touches of PoC or RPP (only first break counts)

**Records:**
- `first_break_side`: 'PoC' or 'RPP' (whichever was touched first)

---

### return State

**Conditions:**
- First break occurred
- Returned to TO at least once
- Possibly second break occurred
- Final TO return has NOT occurred yet

**Waiting For:**
- Second touch of TO (after second break)

**Records When Entering Return (first time):**
- `first_return_time`

**Records on Second Break:**
- `second_break_time`
- `second_break_side`: 'PoC' or 'RPP'

**Ignores:**
- Additional touches of PoC/RPP after second break (only first and second count)

---

### resolved State

**Conditions:**
- Complete cycle: break → return → break → return completed
- Session is "done"

**Waiting For:**
- Nothing (session complete)

**Ignores:**
- All touches (session no longer active for tracking)

**Records:**
- `resolution_type`: 'single_sided' or 'double_sided'

---

## Reset Logic

### After First Return

After `first_return_time` is recorded, the system "resets" for the second break:
- Next PoC/RPP touch becomes `second_break`
- Intermediate touches between first return and second break are ignored

**Example:**
```
09:00 - Break PoC (first_break)
09:15 - Touch TO (first_return) → status = 'return'
09:30 - Touch PoC (ignored, already in return)
10:00 - Touch RPP (second_break_time recorded, still status = 'return')
10:15 - Touch TO (resolution_time recorded) → status = 'resolved'
```

---

## POI Event Types

POI events are created based on state transitions:

### break Event Type

- Created when status changes: unbroken → break
- Records which level was broken (PoC or RPP)

### return Event Type

- Created when status changes: break → return
- Records TO touch after first break

### resolution Event Type

- Created when status changes: return → resolved
- Records final TO touch

**Note:** State can be 'return' with both break events AND return events recorded, while waiting for final resolution.

---

## Session Status Query Examples

### Find All Unbroken Sessions

```sql
SELECT * FROM sessions
WHERE status = 'unbroken'
AND to_time <= datetime('now')  -- Range is defined
ORDER BY to_time DESC;
```

### Find Sessions Waiting for Return

```sql
SELECT * FROM sessions
WHERE status = 'break'
AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY first_break_time DESC;
```

### Find Recently Resolved Sessions

```sql
SELECT * FROM sessions
WHERE status = 'resolved'
AND resolution_time >= datetime('now', '-1 day')
ORDER BY resolution_time DESC;
```

### Find Active Sessions (All Types)

```sql
SELECT * FROM sessions
WHERE status != 'resolved'
AND to_time <= datetime('now')
AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY session_type, to_time;
```

---

## Related Documentation

- [Ranges and Terms](../user-guide/03-ranges-and-terms.md) - Detailed explanation of status progression
- [Calculation Logic](../technical/calculation-logic.md) - State machine implementation
- [Database Schema](../technical/database-schema.md) - Sessions table structure
