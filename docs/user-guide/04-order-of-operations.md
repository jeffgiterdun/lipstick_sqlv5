# Order of Operations (OOO / 3o's)

## What is Order of Operations?

Order of Operations is the term used to describe the narrative theory of the market. The market operates with a checklist of events or steps. We move from one step to the next after a return or resolution. A resolution is the return to a True Open after a break of the range associated with that True Open.

## Core Concept

The theory is that the market follows a specific sequence of tasks, similar to how a computer program executes instructions. Each session resolution represents the completion of a task, which then triggers the next item on the algorithmic "checklist."

## Key Principles

### 1. Sequential Execution

Order of Operations moves are very specific to the day's events and are the hardest part to document and understand. They happen all day long every day but need a clever way to simplify and keep track of.

### 2. Cascading Resolutions

The theory is that a resolution of one event will then trigger a resolution of an event previous. There is a checklist of unreturned or unresolved ranges that were created as a result of the attack of an older session resolution.

### 3. Chronological Processing

Once one event is resolved, we look back to see what the next logical session chronologically needs attending to.

## Session Hierarchy in OOO

The sessions follow a hierarchy of significance for Order of Operations:

1. **Monthly session resolutions** - The most significant events
2. **Weekly session resolutions** - Highly significant
3. **Major session resolutions** - Provide daily structure
4. **Minor session resolutions** - Provide intraday execution context

## How OOO Works in Practice

### The Checklist Model

Think of the market as maintaining a list of unresolved tasks:

```
Current Session Status:
- Monthly: [break] - waiting for TO return
- Weekly: [return] - waiting for second break
- Asia: [resolved] - complete ✓
- London: [break] - waiting for TO return
- m0900: [return] - waiting for second break
- m0730: [resolved] - complete ✓
```

### Resolution Cascade Example

**Scenario:** London session resolves

1. **London Resolution** (return to TO after second break)
   - This completes London's task in the OOO

2. **Market Looks Backward**
   - What unresolved sessions came before London?
   - Asia is already resolved ✓
   - Weekly is in "return" status - needs second break

3. **Next Task Triggered**
   - Market now "attempts" to break Weekly PoC/RPP again
   - This creates a setup opportunity

4. **Continuation**
   - If Weekly breaks and returns again (resolves), market looks back further
   - Perhaps Monthly is in "break" status - needs TO return
   - Price gravitates toward Monthly TO

## Practical Trading Application

### Identifying the Next Move

When a session resolves, ask:
1. What is the current status of higher timeframe sessions?
2. What do they need to complete their cycle?
3. Where are their key levels (PoC, TO, RPP)?

### Example Setup

**Current State:**
- Monthly: Status = "return" (needs second break)
- Weekly: Status = "resolved" ✓
- London: Status = "break" (needs TO return)
- Current Price: Near London TO

**OOO Analysis:**
- London is the immediate task → expect return to London TO
- After London returns, watch for second break
- If London resolves → market may address Monthly's second break
- Monthly PoC/RPP become high-probability targets

## The Complexity Challenge

Order of Operations moves are very specific to the day's events and are the hardest part to document and understand. They require:

- Tracking multiple sessions simultaneously
- Understanding which sessions are "active" in the checklist
- Recognizing when a resolution triggers the next task
- Identifying which previous session needs attention

## Integration with Echo Chamber

OOO becomes even more powerful when combined with [Echo Chamber Analysis](05-echo-chamber.md). When ES and NQ have different session statuses, we can identify:

- Which instrument is ahead in its OOO checklist
- Divergences that signal which task will resolve first
- Leading indicators of the next OOO move

## Key Observations

### True Open as Task Completion

In some cases, a return to a True Open represents a completion of a task or set of instructions in the OOO's. The TO acts as a checkpoint that confirms "task complete" before the algorithm moves to the next instruction.

### Unresolved Ranges Build Up

Throughout the day, multiple sessions may be in various states of completion. These unresolved ranges don't disappear—they remain on the "checklist" until addressed. This creates:

- Multiple potential targets for price
- Confluence when multiple session levels align
- High-probability setups when OOO sequencing is clear

### Patience and Observation

Understanding OOO requires careful observation over time. Patterns emerge as you track:
- Which sessions resolve in sequence
- How price responds after major resolutions
- Which timeframes tend to cascade together

## Simplified Approach

While OOO is complex, a simplified approach:

1. **Track all session statuses** (use the analytical tool)
2. **When a session resolves** → note it
3. **Look backward chronologically** → what's unresolved?
4. **Identify the next likely target** → PoC/TO/RPP of unresolved session
5. **Wait for confluence** → Echo Chamber divergence, swing formation, etc.

---

## Next Steps

- [Echo Chamber Analysis](05-echo-chamber.md) - Combine OOO with ES/NQ correlation
- [State Machine (Reference)](../reference/state-machine.md) - Visual state transition diagrams
- [Session Tables (Reference)](../reference/session-tables.md) - Track session timings
