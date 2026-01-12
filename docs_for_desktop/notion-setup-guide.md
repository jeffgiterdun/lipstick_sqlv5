# Notion Setup Guide

Step-by-step guide to setting up your Notion workspace for systematic pattern discovery and validation.

---

## Overview

You'll create 4 linked databases to track your journey from hypothesis → testing → validation:

1. **Hypotheses** - What you're testing
2. **Tests** - Individual test runs with results
3. **Validated Setups** - Proven patterns (your tradable playbook)
4. **Insights Archive** - Long-form analysis and discoveries

---

## Database 1: Hypotheses

### Purpose
Track each testable idea about market patterns.

### Properties

| Property Name | Type | Options/Formula |
|---------------|------|-----------------|
| Name | Title | - |
| Status | Select | Active Testing / Validated / Failed / Insufficient Data / Paused |
| Setup Type | Select | Echo Chamber / OOO Sequence / Swing @ POI / Status Alignment / Multi-TF Confluence / Other |
| Entry Criteria | Text | - |
| Target Definition | Text | - |
| Invalidation Rules | Text | - |
| Confluence Factors | Multi-select | Swing Class / Echo Chamber / Session Status / Multi-TF / OOO / Session Type / POI Timing |
| Min Sample Target | Number | Default: 20 |
| Date Created | Date | - |
| Last Updated | Last edited time | - |
| Related Tests | Relation | → Tests database |
| Notes | Text | - |

### Example Entry

**Name:** Class 3+ Swing at Major PoC Break → TO Target

**Status:** Active Testing

**Setup Type:** Swing @ POI

**Entry Criteria:**
```
1. Major session status = 'break' (first PoC break occurred)
2. Class 3+ swing forms within 20 candles of PoC break event
3. Swing direction aligns with expected reversion to TO
```

**Target Definition:**
```
Price reaches session TO level before invalidation
```

**Invalidation Rules:**
```
1. Price moves 10+ points beyond PoC (wrong direction)
2. Session resolves without hitting TO
3. 4+ hours pass without TO touch
```

**Confluence Factors:** Swing Class, POI Timing, Session Type

---

## Database 2: Tests

### Purpose
Record each time you test a hypothesis with specific data.

### Properties

| Property Name | Type | Options/Formula |
|---------------|------|-----------------|
| Test Name | Title | - |
| Hypothesis | Relation | → Hypotheses database |
| Status | Select | Pass (>50%) / Fail (<50%) / Inconclusive / In Progress |
| Date Range Tested | Date | Start and end dates of data analyzed |
| Total Occurrences | Number | - |
| Wins | Number | - |
| Losses | Number | - |
| Incomplete | Number | Instances that haven't resolved yet |
| Win Rate | Formula | `prop("Wins") / (prop("Wins") + prop("Losses"))` |
| Win Rate % | Formula | `round(prop("Win Rate") * 100)` |
| Avg Time to Target | Number | Minutes |
| Avg Points (Win) | Number | - |
| Avg Points (Loss) | Number | - |
| Risk/Reward | Formula | `prop("Avg Points (Win)") / prop("Avg Points (Loss)")` |
| SQL Query | Text/Code | - |
| Key Findings | Text | - |
| Next Steps | Text | - |
| Test Date | Date | - |
| Tested By | Person | - |

### Example Entry

**Test Name:** Class 3+ @ Major PoC - December 2024

**Hypothesis:** [Link to hypothesis]

**Status:** Fail (<50%)

**Date Range Tested:** 2024-12-01 to 2024-12-31

**Total Occurrences:** 24

**Wins:** 11

**Losses:** 13

**Win Rate %:** 46%

**Avg Time to Target:** 87 minutes

**Avg Points (Win):** 8.3

**Avg Points (Loss):** 6.1

**Risk/Reward:** 1.36

**SQL Query:**
```sql
SELECT
    s.symbol,
    s.swing_time,
    s.swing_class,
    p.session_name,
    sess.true_open,
    sess.poc
FROM swings s
JOIN poi_events p ON s.nearest_poi_event_id = p.id
JOIN sessions sess ON (
    (s.symbol = 'ES' AND p.es_session_id = sess.id)
    OR (s.symbol = 'NQ' AND p.nq_session_id = sess.id)
)
WHERE s.swing_class >= 3
  AND s.candles_from_poi_event <= 20
  AND p.poi_type = 'PoC'
  AND p.event_type = 'first_break'
  AND sess.session_type = 'Major'
  AND s.swing_time BETWEEN '2024-12-01' AND '2024-12-31'
ORDER BY s.swing_time;
```

**Key Findings:**
```
- Win rate of 46% falls short of 50% threshold
- R/R of 1.36 is decent but not enough to compensate for sub-50% win rate
- Class 3 swings (n=18) had 44% win rate
- Class 4+ swings (n=6) had 50% win rate (small sample)
- Time to target highly variable (30-240 min range)
```

**Next Steps:**
```
1. Test with Class 4+ only (need more data - only 6 instances)
2. Test adding Echo Chamber divergence as additional filter
3. Test with Weekly/Monthly POIs instead of Major
```

---

## Database 3: Validated Setups

### Purpose
Your tradable playbook - only patterns that passed validation.

### Properties

| Property Name | Type | Options/Formula |
|---------------|------|-----------------|
| Setup Name | Title | - |
| Setup Type | Select | Echo Chamber / OOO Sequence / Swing @ POI / Status Alignment / Multi-TF Confluence / Other |
| Status | Select | Active / Under Review / Retired |
| Win Rate % | Number | - |
| Sample Size | Number | Total historical occurrences tested |
| Risk/Reward | Number | - |
| Avg Hold Time (min) | Number | - |
| Confluence Required | Multi-select | Swing Class / Echo Chamber / Session Status / Multi-TF / OOO / Session Type / POI Timing |
| Entry Checklist | Text | - |
| Target Levels | Text | - |
| Stop Rules | Text | - |
| Best Time of Day | Text | Optional - if pattern is time-dependent |
| Source Hypothesis | Relation | → Hypotheses database |
| Source Tests | Relation | → Tests database |
| Trade Plan | Text/Page | Full detailed plan |
| Last Validated | Date | Last time you re-tested with new data |
| Notes | Text | - |

### Example Entry

**Setup Name:** Echo Chamber 6h+ Divergence → Leader Follow-Through

**Setup Type:** Echo Chamber

**Status:** Active

**Win Rate %:** 58

**Sample Size:** 27

**Risk/Reward:** 1.8

**Avg Hold Time (min):** 145

**Confluence Required:** Echo Chamber, POI Timing, Session Type

**Entry Checklist:**
```
1. ✓ POI break event (PoC or RPP) on Major/Weekly/Monthly session
2. ✓ ES and NQ time_delta > 360 minutes (6+ hours)
3. ✓ Clear leader identified (ES or NQ)
4. ✓ Lagging instrument finally breaks the POI level
5. ✓ Enter on lagging instrument in direction of leader
```

**Target Levels:**
```
Primary: Session TO level
Secondary: If session in 'return' status, target opposite POI
```

**Stop Rules:**
```
1. Price moves 12 ES points / 35 NQ points against entry
2. 3 hours pass without progress toward target
3. Leader instrument reverses direction significantly
```

**Trade Plan:**
```
See full trade plan page [link to detailed Notion page]
```

**Last Validated:** 2025-01-09

---

## Database 4: Insights Archive

### Purpose
Long-form analysis, discoveries, and learning (replaces the SQL insights table or complements it).

### Properties

| Property Name | Type | Options/Formula |
|---------------|------|-----------------|
| Title | Title | - |
| Date | Date | - |
| Category | Select | Pattern Discovery / Validation Results / Market Observation / System Learning / Failed Hypothesis / Other |
| Sessions Involved | Text | - |
| Symbols | Multi-select | ES / NQ |
| Tags | Multi-select | Class 3 / Class 4 / Echo Chamber / Major Session / Weekly Session / Monthly Session / OOO / POI / Other |
| Key Finding | Text | One-sentence summary |
| Related Hypotheses | Relation | → Hypotheses database |
| Related Tests | Relation | → Tests database |
| Full Analysis | Text/Page | Detailed write-up |
| SQL Queries | Text/Code | For reproduction |
| Attachments | Files | Screenshots, charts, etc. |

---

## Recommended Notion Page Structure

```
📁 Lipstick Trading Analysis
├── 📊 Dashboard (overview with linked database views)
│   ├── Active Hypotheses (filtered view)
│   ├── Recent Tests (sorted by date)
│   ├── Validated Setups (active only)
│   └── Key Metrics (formulas, charts)
│
├── 🧪 Hypotheses (Database 1)
│
├── 📈 Tests (Database 2)
│   ├── View: Passing Tests (>50% win rate)
│   ├── View: Failed Tests (<50% win rate)
│   ├── View: By Date
│   └── View: By Hypothesis
│
├── ✅ Validated Setups (Database 3)
│   ├── View: Active Setups
│   ├── View: By Win Rate
│   └── View: By Setup Type
│
├── 📝 Insights Archive (Database 4)
│   ├── View: By Category
│   ├── View: By Date
│   └── View: By Tags
│
└── 📚 Resources
    ├── System Documentation (links to .md files)
    ├── Common SQL Queries
    └── Learning Notes
```

---

## Using Claude Desktop with Notion MCP

### Creating Entries

When Claude Desktop is connected to Notion via MCP, you can ask:

```
"Create a new hypothesis in Notion for testing Class 4+ swings at Weekly PoC levels"
```

Claude will use the Notion MCP to create the database entry with proper structure.

### Updating Entries

```
"Update hypothesis 'Class 3+ @ Major PoC' status to 'Failed' and link test results"
```

### Querying Notion

```
"Show me all validated setups with win rate >60%"
"What hypotheses are in 'Active Testing' status?"
"List all failed tests and their key findings"
```

---

## Workflow Integration

### Phase 1: Discovery (Weeks 1-2)

**In Claude Desktop:**
1. Query database for patterns
2. Identify potential setups
3. Form hypotheses

**In Notion:**
1. Create hypothesis entries as you form them
2. Document what you're looking for
3. Track questions and observations

### Phase 2: Testing (Weeks 3-4)

**In Claude Desktop:**
1. Run SQL queries for each hypothesis
2. Score instances (win/loss)
3. Calculate metrics

**In Notion:**
1. Create test entry for each hypothesis run
2. Record SQL query, results, win rate
3. Update hypothesis status based on results
4. Document key findings and next steps

### Phase 3: Validation (Ongoing)

**In Claude Desktop:**
1. Re-test passing patterns with new data
2. Refine entry criteria
3. Monitor live setups

**In Notion:**
1. Create validated setup entries for passing patterns
2. Build detailed trade plans
3. Track live performance (future: live trades database)
4. Archive insights

---

## Tips for Success

### Keep It Simple at Start
Don't create all databases at once if it feels overwhelming. Start with:
1. Hypotheses database
2. Tests database
3. Simple text page for notes

Add Validated Setups and Insights Archive as you progress.

### Link Everything
Use relations to connect:
- Tests → Hypotheses (every test links to parent hypothesis)
- Validated Setups → Hypotheses + Tests (show your validation path)
- Insights → Hypotheses/Tests (context for discoveries)

### Use Templates
Create Notion templates for:
- New Hypothesis (pre-filled fields)
- New Test (standard structure)
- New Validated Setup (complete checklist)

### Regular Reviews
Weekly review routine:
1. Check all "Active Testing" hypotheses - any ready to move to next phase?
2. Review failed tests - what did we learn?
3. Update validated setups with new data
4. Archive old insights

### Stay Honest
The value of this system is brutal honesty:
- If win rate is 48%, status = "Failed" (not "close to passing")
- If sample size is 15, status = "Insufficient Data" (not validated)
- Document failures prominently - they teach as much as successes

---

## Example Daily Log Entry (Optional)

Some traders like a daily log in addition to the databases:

**📅 2025-01-10 Analysis Log**

**Market State:**
- ES Major sessions: NY_AM (return), NY_PM (break), Afternoon (unbroken)
- NQ Major sessions: NY_AM (return), NY_PM (break), Afternoon (unbroken)
- ES Weekly: return status, awaiting resolution
- Key level: ES Weekly TO at 5985

**Analysis:**
- Tested "Class 3+ @ Major PoC" hypothesis on December data
- Results: 46% win rate on 24 instances → Failed
- Observation: Class 4+ subset showed 50% (n=6, insufficient data)

**Hypotheses Updated:**
- "Class 3+ @ Major PoC" → Status: Failed
- Created new: "Class 4+ @ Major PoC" → Status: Insufficient Data (collecting)

**Next Steps:**
- Continue collecting Class 4+ instances
- Test Echo Chamber divergence hypothesis next
- Review Weekly/Monthly POI significance

**Potential Setups Today:**
- ES Weekly TO at 5985 (watching for bounce)
- NQ NY_PM session PoC at 21,450 (watching for break)

---

## Getting Started Checklist

- [ ] Create Notion account (if needed)
- [ ] Set up Notion MCP in Claude Desktop config
- [ ] Create workspace "Lipstick Trading Analysis"
- [ ] Create Hypotheses database with properties listed above
- [ ] Create Tests database with properties listed above
- [ ] Link databases (Tests → Hypotheses relation)
- [ ] Test creating entry via Claude Desktop
- [ ] Add your first 3-5 hypotheses
- [ ] Begin testing

---

You're now ready to build a systematic knowledge base of what actually works in your trading data.

Stay rigorous. Stay objective. Let the data lead.
