# Setup Guide

Getting started with the Lipstick Analytical Tool V5 development environment.

---

## Prerequisites

### Required Software

- **Python 3.8+**
- **SQLite 3.35+**
- **Git** (for version control)

### Optional Tools

- **DB Browser for SQLite** - GUI for database exploration
- **Visual Studio Code** - Recommended IDE
- **Jupyter Notebook** - For analysis and querying

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Lipstick_SQLV5
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected requirements.txt:**
```
pandas>=1.5.0
numpy>=1.23.0
python-dateutil>=2.8.0
```

### 4. Verify SQLite Installation

```bash
sqlite3 --version
# Expected: 3.35.0 or higher
```

---

## Project Structure

```
Lipstick_SQLV5/
├── data/
│   └── ohlc_data.db          # SQLite database
├── docs/                     # Documentation
│   ├── user-guide/
│   ├── technical/
│   ├── reference/
│   └── development/
├── src/                      # Source code
│   ├── calculate_ranges_v5.py
│   ├── process_poi_events_v5.py
│   ├── detect_swings_v5.py
│   └── verify_v5.py
├── schema_v5.sql            # Database schema
├── requirements.txt
└── README.md
```

---

## Database Setup

### Create Database Directory

```bash
mkdir -p data
```

### Initialize Database Schema

```bash
sqlite3 data/ohlc_data.db < schema_v5.sql
```

### Verify Tables Created

```bash
sqlite3 data/ohlc_data.db ".tables"
```

**Expected output:**
```
insights    ohlc_1m     poi_events  sessions    swings
```

---

## Load OHLC Data

### Data Requirements

- **Format:** 1-minute OHLC bars
- **Symbols:** ES, NQ
- **Time Format:** ISO 8601 with timezone (e.g., `2025-11-27T18:00:00-05:00`)
- **Time Zone:** Eastern Time (ET)

### Sample Data Loading Script

```python
import sqlite3
import pandas as pd

# Read CSV data
df = pd.read_csv('historical_data.csv')

# Connect to database
conn = sqlite3.connect('data/ohlc_data.db')

# Insert data
df.to_sql('ohlc_1m', conn, if_exists='append', index=False)

# Verify
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM ohlc_1m")
print(f"Total rows: {cursor.fetchone()[0]}")

conn.close()
```

### Verify Data Loaded

```sql
SELECT symbol, COUNT(*) as count, MIN(time), MAX(time)
FROM ohlc_1m
GROUP BY symbol;
```

---

## Configuration

### Environment Variables (Optional)

Create `.env` file:

```env
DB_PATH=data/ohlc_data.db
LOG_LEVEL=INFO
TIMEZONE=America/New_York
```

### Python Configuration

```python
# config.py
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'ohlc_data.db'

# Settings
TIMEZONE = 'America/New_York'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
```

---

## Running the System

### Phase 1: Calculate Ranges

```bash
python src/calculate_ranges_v5.py
```

### Phase 2: Process POI Events

```bash
python src/process_poi_events_v5.py
```

### Phase 3: Detect Swings

```bash
python src/detect_swings_v5.py
```

### Phase 4: Verify Data

```bash
python src/verify_v5.py
```

---

## Development Tools

### DB Browser for SQLite

Download from: https://sqlitebrowser.org/

**Useful for:**
- Browsing tables and data
- Running ad-hoc queries
- Inspecting schema
- Viewing query execution plans

### Jupyter Notebook Setup

```bash
pip install jupyter

# Start Jupyter
jupyter notebook
```

**Sample Analysis Notebook:**

```python
import sqlite3
import pandas as pd

# Connect
conn = sqlite3.connect('data/ohlc_data.db')

# Query sessions
sessions_df = pd.read_sql("""
    SELECT * FROM sessions
    WHERE symbol = 'ES'
    AND status = 'resolved'
    LIMIT 10
""", conn)

print(sessions_df)
```

---

## Troubleshooting

### Database Locked Error

**Symptom:** `sqlite3.OperationalError: database is locked`

**Solutions:**
1. Close all connections to the database
2. Use `conn.commit()` before closing connections
3. Use `PRAGMA busy_timeout = 5000` for retries

### Missing Data in ohlc_1m

**Symptom:** Sessions have NULL ranges

**Solutions:**
1. Verify data completeness: `SELECT COUNT(*) FROM ohlc_1m WHERE symbol = 'ES' AND time BETWEEN ? AND ?`
2. Check for gaps in minute data
3. See [Edge Cases](../technical/edge-cases.md) for handling missing data

### Import Errors

**Symptom:** `ModuleNotFoundError`

**Solutions:**
1. Ensure virtual environment is activated
2. Run `pip install -r requirements.txt`
3. Check Python version (`python --version`)

---

## Best Practices

### Version Control

```bash
# Initialize git repository
git init

# Create .gitignore
echo "venv/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".env" >> .gitignore
echo "data/*.db-journal" >> .gitignore

# First commit
git add .
git commit -m "Initial commit: Lipstick V5 setup"
```

### Database Backups

```bash
# Backup database
sqlite3 data/ohlc_data.db ".backup data/ohlc_data_backup.db"

# Or use copy
cp data/ohlc_data.db data/ohlc_data_backup_$(date +%Y%m%d).db
```

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lipstick_v5.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Processing started")
```

---

## Next Steps

1. Review [Implementation Phases](implementation-phases.md) for build process
2. Explore [Technical Documentation](../technical/architecture-overview.md) for system architecture
3. Read [User Guide](../user-guide/01-introduction.md) for trading methodology

---

## Support and Resources

- **Documentation:** `/docs/`
- **Issues:** Report at project repository
- **Questions:** See [User Guide](../user-guide/01-introduction.md) for methodology questions
