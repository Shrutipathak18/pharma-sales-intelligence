# Pharma Sales Intelligence & ETL Analytics System



> **All data is SYNTHETIC** and reproducibly generated. There are no real pharma-company sales records and no confidential information.

## What the pipeline does

1. **Generate** 15,000 valid mock transactions plus 50 intentionally defective/duplicate rows.
2. **Clean and validate** records (dates, quantities, prices, foreign keys, duplicates, rep/territory consistency).
3. **Load** five relational tables with primary keys, foreign keys, and indexes.
4. **Analyze** territories, products, target attainment, and month-over-month growth in SQL.
5. **Export** Power BI-friendly CSVs so you can build your own dashboard.

```text
Synthetic source files -> Python + Pandas ETL -> SQLite/PostgreSQL
                                              -> SQL queries -> CSV -> Power BI
```

## Folder structure

```text
pharma_sales_starter/
  .env.example
  requirements.txt
  README.md
  src/
    generate_data.py
    load_data.py
    run_analysis.py
  sql/analysis.sql
  tests/test_pipeline.py
  docs/project_brief.md
  docs/power_bi_guide.md
  data/raw/                  # generated locally
  data/processed/            # generated locally
```

## Run locally (Windows PowerShell)

Use Python 3.10 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.generate_data
python -m src.load_data
python -m src.run_analysis
python -m unittest discover -s tests -v
```

If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process Bypass` in the current PowerShell session or run `.venv\Scripts\python.exe` directly.

### Database choice

**Beginner route:** no installation needed beyond Python: the code defaults to **SQLite** and creates `pharma_sales.db`. This teaches database fundamentals immediately.

**Preferred resume route:** to demonstrate **PostgreSQL**, install PostgreSQL locally, create a database named `pharma_sales`, copy `.env.example` to `.env`, and insert:

```text
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/pharma_sales
```

Rerun the `load_data` and `run_analysis` commands.

**Warning:** `load_data` DROPS and recreates all five project tables on every run. Use a dedicated practice database; never point it at a database containing valuable data.

## Expected output

- `data/processed/etl_quality_report.csv` — counts and QA reconciliation
- `data/processed/clean_sales.csv` — cleaned transactions
- `data/processed/sales_by_territory.csv`
- `data/processed/product_performance.csv`
- `data/processed/territory_target_attainment.csv`
- `data/processed/monthly_growth.csv`

The generator creates **15,050** raw rows; **15,000** valid transactions should be loaded. 10 repeated IDs and 40 bad transactions should be rejected.

## Build Power BI yourself

Follow [`docs/power_bi_guide.md`](docs/power_bi_guide.md) and create a three-page `.pbix` report. CSV import is quickest, but PostgreSQL direct connection is stronger for interviews.

## Project completion checklist

- [ ] Pipeline runs and quality tests pass
- [ ] You can explain each SQL JOIN, CTE and window function
- [ ] Power BI report has three pages
- [ ] You add actual screenshots under `docs/screenshots/`
- [ ] You publish to GitHub with a README and one justified business recommendation
- [ ] You only include resume bullets for work you actually completed

## Next enhancements (after V1)

- Add a CLI argument for alternative years and transaction counts.
- Add ETL logging and error quarantine files.
- Schedule the pipeline using Windows Task Scheduler/GitHub Actions.
- Deploy PostgreSQL/ETL to a suitable managed service.
