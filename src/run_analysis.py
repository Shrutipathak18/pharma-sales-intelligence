"""Execute reusable SQL for KPIs and export Power BI-ready aggregate CSVs."""
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from src.load_data import database_engine

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'processed'
SQL_FILE = ROOT / 'sql' / 'analysis.sql'


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    blocks = [b.strip() for b in SQL_FILE.read_text(encoding='utf-8').split(';') if b.strip()]
    names = ['sales_by_territory', 'product_performance', 'territory_target_attainment', 'monthly_growth']
    engine = database_engine()
    with engine.connect() as conn:
        for name, sql in zip(names, blocks):
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            outfile = OUTPUT / f'{name}.csv'
            df.to_csv(outfile, index=False)
            print(f'{name}: {len(df)} rows -> {outfile.relative_to(ROOT)}')
        result = conn.execute(text('SELECT COUNT(*) AS n, ROUND(SUM(revenue),2) AS revenue FROM fact_sales')).one()
        print(f'Quality checkpoint: {result.n:,} clean transactions; total synthetic revenue ₹{float(result.revenue):,.2f}')
    engine.dispose()


if __name__ == '__main__':
    run()
