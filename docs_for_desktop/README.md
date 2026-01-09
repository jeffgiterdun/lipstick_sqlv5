# Claude Desktop Project Documentation

**Clean foundation documentation for SQL analysis work in Claude Desktop with MCP database access.**

---

## Quick Start

### 1. Create Desktop Project
1. Open Claude Desktop
2. Create new Project
3. Name it: "Lipstick Trading Analysis" (or your preference)

### 2. Add This Folder to Project
1. In Project Settings → Add Knowledge
2. Add the entire `docs_for_desktop/` folder
3. All `.md` files will be loaded as context (zero token cost)

### 3. Set Custom Instructions
1. In Project Settings → Custom Instructions
2. Open `custom-instructions.md`
3. Copy entire content
4. Paste into Custom Instructions field
5. Save

### 4. Verify MCP Database Connection
Your SQLite MCP should already be configured in Desktop. Verify Docker is running.

**Configuration location:** `%APPDATA%\Claude\claude_desktop_config.json`

### 5. Start Analyzing!
- Ask Claude to query sessions, POI events, swings
- Build your discoveries in `discoveries.md`
- Save detailed findings to `insights` table

---

## File Overview

### 📘 Core Documentation (Always Loaded - Zero Token Cost)

#### `system-overview.md`
**Purpose:** High-level system understanding

**Contains:**
- Database structure and tables
- Session types (Major, Minor, Weekly, Monthly, Yearly)
- Core concepts (PoC, TO, RPP, State Machine)
- Data processing pipeline
- Design principles

**Use When:** Understanding overall system architecture

---

#### `database-schema.md`
**Purpose:** Quick reference for table structures

**Contains:**
- All 5 tables with column definitions
- Indexes and foreign keys
- Data type standards
- Query best practices

**Use When:** Writing SQL queries or understanding relationships

---

#### `key-concepts.md`
**Purpose:** Trading terminology and system concepts

**Contains:**
- Session range components (PoC, TO, RPP formulas)
- State machine (unbroken → break → return → resolved)
- Echo Chamber analysis (time_delta, leader, significance)
- Swing classification (Class 1-6 definitions)
- Session expiration rules
- Trading day calculation
- Order of Operations theory
- Confluence definition

**Use When:** Understanding trading terms or system behavior

---

### 📝 Working Document (You Maintain)

#### `discoveries.md`
**Purpose:** Your working memory for recent findings

**Structure:**
- Discovery template (copy and fill for each finding)
- Discovery log table (quick reference)
- Active hypotheses (what you're testing)
- Patterns being tracked
- Questions to explore
- Working notes

**Update When:**
- You discover something significant
- You're testing a hypothesis
- You need quick reference during analysis

**Best Practice:**
- Keep recent only (last 2-4 weeks)
- Brief summaries
- Link to insights table for full details
- Clean out old entries regularly

---

### ⚙️ Setup File

#### `custom-instructions.md`
**Purpose:** Instructions for Claude's analysis behavior

**Contains:**
- Your role definition
- Analysis workflows
- Query best practices
- Response style guidelines
- Recording insights process

**Use:** Copy into Project Settings → Custom Instructions (one-time setup)

---

## Documentation Philosophy

This documentation provides:

✅ **System Knowledge** - How the system works
✅ **Terminology** - Trading concepts explained
✅ **Structure** - Database tables and relationships
✅ **Workflow** - How to analyze and record findings

❌ **NOT Included:**
- Specific market analysis (that's what you'll discover)
- Common queries (you'll build your own)
- Historical findings (use insights table)
- Today's specific work (keep it general)

---

## Typical Workflow

### Initial Setup (One Time)
1. Create Claude Desktop project
2. Add `docs_for_desktop/` folder as knowledge
3. Copy custom instructions
4. Verify MCP connection

### Daily Analysis
1. **Check current state:** Query session status, recent POI events
2. **Explore patterns:** Look for Echo Chamber divergences, Class 3+ swings
3. **Analyze confluence:** Multiple timeframes, POI types, swing formations
4. **Record findings:**
   - Detailed analysis → `insights` table (permanent archive)
   - Summary → `discoveries.md` (working memory)

### Pattern Research
1. Search `insights` table for historical patterns
2. Check `discoveries.md` for recent findings
3. Query database for similar setups
4. Document new patterns discovered

---

## Key Principles

### Session Hierarchy
Higher timeframes provide context for lower:
1. Yearly > 2. Monthly > 3. Weekly > 4. Major > 5. Minor

### Echo Chamber Significance
- <60 min = normal
- 60-360 min = medium
- >360 min = significant
- >1440 min = extreme (very strong signal)

### Swing Structural Importance
- Class 1-2 = noise
- Class 3+ = structural
- Class 5-6 = extreme events

### State Machine Progression
All sessions follow: unbroken → break → return → resolved

### Dual-Asset Analysis
Always compare ES and NQ for:
- Timing divergence (Echo Chamber)
- Status alignment/divergence
- Structural confirmation

---

## Maintaining Documentation

### This Folder (docs_for_desktop/)
- **Keep general** - No specific market analysis
- **System knowledge only** - How it works, not what happened
- **Update rarely** - Only when system changes

### discoveries.md
- **Keep current** - Last 2-4 weeks only
- **Update frequently** - After each analysis session
- **Move old entries** - To insights table after 1 month

### insights Table (SQL)
- **Permanent archive** - Never delete
- **Full details** - Complete analysis with SQL
- **Properly tagged** - For future searching
- **Searchable** - Use FTS5 full-text search

---

## Tips for Success

1. **Query both ES and NQ** for comparison always
2. **Check discoveries.md first** before asking questions
3. **Use proper tags** in insights table for future search
4. **Keep discoveries.md focused** on recent work
5. **Look for confluence** - multiple factors aligning
6. **Prioritize higher timeframes** in analysis
7. **Track hypotheses** in discoveries.md
8. **Document reproducible SQL** in insights table

---

## Two Claude Workflow

### Claude Code CLI (System Maintenance)
- Data processing (load CSV, calculate sessions, POI events, swings)
- Debugging code
- System updates
- Pipeline management

### Claude Desktop (Analysis & Discovery)
- SQL queries and analysis
- Pattern discovery
- Recording insights
- Hypothesis testing
- Research and exploration

**Both work together** - Use the right tool for the task!

---

## Getting Help

**For System Issues:**
- Check processing pipeline scripts
- Review error logs
- Use Claude Code CLI for debugging

**For Analysis Questions:**
- Reference `key-concepts.md` for terminology
- Check `database-schema.md` for structure
- Search `insights` table for patterns
- Review `discoveries.md` for recent findings

---

**You're ready to start!**

Open Claude Desktop, create your project, add this folder, set custom instructions, and begin discovering patterns in your trading data.
