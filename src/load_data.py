"""Validate input CSVs and load normalized relational tables into SQLite/PostgreSQL."""
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, Date,
    Numeric, ForeignKey, CheckConstraint, Index, event,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'data' / 'processed'
load_dotenv(ROOT / '.env')
DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{ROOT / "pharma_sales.db"}')
metadata = MetaData()

products = Table('dim_product', metadata,
    Column('product_id', Integer, primary_key=True),
    Column('brand', String(80), nullable=False),
    Column('therapeutic_category', String(50), nullable=False),
    Column('list_price', Numeric(12, 2), nullable=False),
)
territories = Table('dim_territory', metadata,
    Column('territory_id', Integer, primary_key=True),
    Column('region', String(40), nullable=False),
    Column('city', String(60), nullable=False),
)
reps = Table('dim_sales_rep', metadata,
    Column('sales_rep_id', Integer, primary_key=True),
    Column('rep_name', String(80), nullable=False),
    Column('territory_id', Integer, ForeignKey('dim_territory.territory_id'), nullable=False),
)
sales = Table('fact_sales', metadata,
    Column('sale_id', Integer, primary_key=True),
    Column('sale_date', Date, nullable=False),
    Column('month', String(7), nullable=False),
    Column('product_id', Integer, ForeignKey('dim_product.product_id'), nullable=False),
    Column('territory_id', Integer, ForeignKey('dim_territory.territory_id'), nullable=False),
    Column('sales_rep_id', Integer, ForeignKey('dim_sales_rep.sales_rep_id'), nullable=False),
    Column('quantity', Integer, CheckConstraint('quantity > 0'), nullable=False),
    Column('unit_price', Numeric(12, 2), CheckConstraint('unit_price > 0'), nullable=False),
    Column('revenue', Numeric(16, 2), nullable=False),
)
targets = Table('fact_targets', metadata,
    Column('month', String(7), primary_key=True),
    Column('territory_id', Integer, ForeignKey('dim_territory.territory_id'), primary_key=True),
    Column('target_revenue', Numeric(16, 2), nullable=False),
)
Index('ix_fact_sales_month_territory', sales.c.month, sales.c.territory_id)
Index('ix_fact_sales_product', sales.c.product_id)


def database_engine():
    engine = create_engine(DATABASE_URL, future=True)
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def set_foreign_keys(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.close()
    return engine


def clean_sales(raw, products_df, territories_df, reps_df):
    """Return (validated sales, QA counts). Keep first duplicate transaction ID."""
    report = {'raw_rows': len(raw)}
    # Strict typing first, so malformed strings are rejected rather than silently filled.
    for col in ['sale_id', 'product_id', 'territory_id', 'sales_rep_id', 'quantity', 'unit_price']:
        raw[col] = pd.to_numeric(raw[col], errors='coerce')
    raw['sale_date'] = pd.to_datetime(raw['sale_date'], errors='coerce')
    dups = raw.duplicated(subset=['sale_id'], keep='first')
    report['duplicate_ids_removed'] = int(dups.sum())
    df = raw.loc[~dups].copy()

    mapped_territories = reps_df.set_index('sales_rep_id')['territory_id'].to_dict()
    checks = {
        'missing_or_invalid_fields': df[['sale_id','sale_date','product_id','territory_id','sales_rep_id','quantity','unit_price']].isna().any(axis=1),
        'invalid_quantity_or_price': (df['quantity'] <= 0) | (df['unit_price'] <= 0),
        'unknown_product': ~df['product_id'].isin(products_df.product_id),
        'unknown_territory': ~df['territory_id'].isin(territories_df.territory_id),
        'unknown_rep_or_mismatch': df['territory_id'].ne(df['sales_rep_id'].map(mapped_territories)),
        'outside_2025': (df['sale_date'] < pd.Timestamp('2025-01-01')) | (df['sale_date'] > pd.Timestamp('2025-12-31')),
    }
    for name, mask in checks.items():
        report[name] = int(mask.sum())
    rejected = pd.concat(checks, axis=1).any(axis=1)
    report['rejected_after_dedup'] = int(rejected.sum())
    clean = df.loc[~rejected].copy()
    clean['month'] = clean['sale_date'].dt.strftime('%Y-%m')
    clean['revenue'] = (clean['quantity'] * clean['unit_price']).round(2)
    clean['sale_date'] = clean['sale_date'].dt.date
    report['valid_rows_loaded'] = len(clean)
    report['reconciles'] = report['raw_rows'] == report['duplicate_ids_removed'] + report['rejected_after_dedup'] + report['valid_rows_loaded']
    if not report['reconciles']:
        raise AssertionError('ETL reconciliation failed')
    return clean, report


def load():
    OUT.mkdir(parents=True, exist_ok=True)
    for filename in ('products.csv','territories.csv','sales_reps.csv','sales.csv','targets.csv'):
        if not (RAW / filename).exists():
            raise FileNotFoundError(f'Missing {RAW / filename}. First run: python -m src.generate_data')
    product_df = pd.read_csv(RAW / 'products.csv')
    territory_df = pd.read_csv(RAW / 'territories.csv')
    rep_df = pd.read_csv(RAW / 'sales_reps.csv')
    target_df = pd.read_csv(RAW / 'targets.csv')
    sales_df, report = clean_sales(pd.read_csv(RAW / 'sales.csv'), product_df, territory_df, rep_df)
    if target_df.duplicated(['month', 'territory_id']).any():
        raise ValueError('Duplicate target primary keys detected')
    if target_df.target_revenue.le(0).any():
        raise ValueError('Targets must be positive')
    sales_df.to_csv(OUT / 'clean_sales.csv', index=False)
    pd.DataFrame([report]).to_csv(OUT / 'etl_quality_report.csv', index=False)

    engine = database_engine()
    # Learning/demo behavior: rebuild the synthetic database on every run.
    with engine.begin() as conn:
        metadata.drop_all(conn)
        metadata.create_all(conn)
        for df, table in [(product_df, products), (territory_df, territories),
                          (rep_df, reps), (sales_df, sales), (target_df, targets)]:
            df.to_sql(table.name, conn, if_exists='append', index=False, chunksize=1000)
    engine.dispose()
    print('Database:', DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL)
    print('ETL quality report:', report)
    return report


if __name__ == '__main__':
    load()
