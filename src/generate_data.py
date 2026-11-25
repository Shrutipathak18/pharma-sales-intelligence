"""Generate reproducible SYNTHETIC data. All brands, reps, and transactions are fictional."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
SEED = 42


def generate(n_sales: int = 15_000) -> dict[str, int]:
    RAW.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    products = pd.DataFrame([
        (101, 'Cardiora-A', 'Cardiovascular', 450),
        (102, 'Cardiora-B', 'Cardiovascular', 620),
        (103, 'Glycora-A', 'Diabetes', 320),
        (104, 'Glycora-B', 'Diabetes', 510),
        (105, 'Respira-A', 'Respiratory', 280),
        (106, 'Respira-B', 'Respiratory', 390),
        (107, 'Neurovia-A', 'Neurology', 710),
        (108, 'Neurovia-B', 'Neurology', 830),
        (109, 'Immunora-A', 'Immunology', 560),
        (110, 'Immunora-B', 'Immunology', 770),
    ], columns=['product_id', 'brand', 'therapeutic_category', 'list_price'])
    territory_specs = [
        ('North', 'Delhi'), ('North', 'Chandigarh'), ('North', 'Jaipur'), ('North', 'Lucknow'), ('North', 'Dehradun'),
        ('West', 'Mumbai'), ('West', 'Pune'), ('West', 'Ahmedabad'), ('West', 'Surat'), ('West', 'Nagpur'),
        ('South', 'Bengaluru'), ('South', 'Chennai'), ('South', 'Hyderabad'), ('South', 'Kochi'), ('South', 'Coimbatore'),
        ('East', 'Kolkata'), ('East', 'Patna'), ('East', 'Ranchi'), ('East', 'Bhubaneswar'), ('East', 'Guwahati'),
    ]
    territories = pd.DataFrame([
        (idx + 1, region, city) for idx, (region, city) in enumerate(territory_specs)
    ], columns=['territory_id', 'region', 'city'])
    reps = pd.DataFrame([
        (2 * territory_id - 1 + j, f'Rep-{2 * territory_id - 1 + j:03d}', territory_id)
        for territory_id in territories['territory_id'] for j in (0, 1)
    ], columns=['sales_rep_id', 'rep_name', 'territory_id'])

    product_idxs = rng.integers(0, len(products), n_sales)
    territory_ids = rng.choice(territories.territory_id.to_numpy(), n_sales)
    sales_rep_ids = (2 * territory_ids - 1) + rng.integers(0, 2, n_sales)
    day_offsets = rng.integers(0, 365, n_sales)
    dates = pd.Timestamp('2025-01-01') + pd.to_timedelta(day_offsets, unit='D')
    quantities = rng.integers(1, 18, n_sales)
    unit_prices = np.round(products.list_price.to_numpy()[product_idxs] * rng.uniform(0.88, 1.12, n_sales), 2)
    sales = pd.DataFrame({
        'sale_id': np.arange(1, n_sales + 1),
        'sale_date': dates.strftime('%Y-%m-%d'),
        'product_id': products.product_id.to_numpy()[product_idxs],
        'territory_id': territory_ids,
        'sales_rep_id': sales_rep_ids,
        'quantity': quantities,
        'unit_price': unit_prices,
    })
    # Monthly targets use real synthetic revenue, plus variable challenge levels.
    clean = sales.assign(month=sales.sale_date.str[:7], revenue=sales.quantity * sales.unit_price)
    totals = clean.groupby(['month', 'territory_id'], as_index=False)['revenue'].sum()
    targets = totals.rename(columns={'revenue': 'target_revenue'})
    targets['target_revenue'] = (targets.target_revenue * rng.uniform(0.90, 1.15, len(targets))).round(2)

    # Inject data-quality errors. ETL will identify and reject these rows.
    mistakes = sales.sample(n=40, random_state=SEED).copy().reset_index(drop=True)
    mistakes['sale_id'] = np.arange(n_sales + 1, n_sales + 41)
    mistakes.loc[0:9, 'quantity'] = 0
    mistakes.loc[10:19, 'unit_price'] = -20
    mistakes.loc[20:29, 'product_id'] = 9999
    mistakes.loc[30:34, 'sale_date'] = 'not-a-date'
    mistakes.loc[35:39, 'sales_rep_id'] = 9999
    # Ten duplicate transaction IDs should also be removed.
    dupes = sales.iloc[:10].copy()
    raw_sales = pd.concat([sales, mistakes, dupes], ignore_index=True)
    raw_sales = raw_sales.sample(frac=1, random_state=SEED).reset_index(drop=True)

    products.to_csv(RAW / 'products.csv', index=False)
    territories.to_csv(RAW / 'territories.csv', index=False)
    reps.to_csv(RAW / 'sales_reps.csv', index=False)
    raw_sales.to_csv(RAW / 'sales.csv', index=False)
    targets.to_csv(RAW / 'targets.csv', index=False)
    return {'valid_transactions': n_sales, 'raw_transactions': len(raw_sales),
            'products': len(products), 'territories': len(territories), 'reps': len(reps)}


if __name__ == '__main__':
    print('Generated synthetic datasets:', generate())
