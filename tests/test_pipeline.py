"""Run: python -m unittest discover -s tests -v"""
import unittest
import pandas as pd
from sqlalchemy import text
from src.generate_data import generate, RAW
from src.load_data import load, database_engine


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate()
        cls.audit = load()

    def test_quality_reconciliation(self):
        self.assertTrue(self.audit['reconciles'])
        self.assertEqual(self.audit['raw_rows'], 15050)
        self.assertEqual(self.audit['valid_rows_loaded'], 15000)
        self.assertEqual(self.audit['duplicate_ids_removed'], 10)
        self.assertEqual(self.audit['rejected_after_dedup'], 40)

    def test_database_integrity(self):
        engine = database_engine()
        with engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM fact_sales')).scalar_one(), 15000)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM dim_product')).scalar_one(), 10)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM dim_territory')).scalar_one(), 20)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM fact_targets')).scalar_one(), 240)
        engine.dispose()

    def test_sales_revenue_reconciles(self):
        source = pd.read_csv(RAW / 'sales.csv')
        source = source.drop_duplicates('sale_id', keep='first')
        source = source.loc[(source['sale_id'] <= 15000)]
        expected = round((source.quantity * source.unit_price).sum(), 2)
        engine = database_engine()
        with engine.connect() as conn:
            observed = float(conn.execute(text('SELECT SUM(revenue) FROM fact_sales')).scalar_one())
        engine.dispose()
        self.assertAlmostEqual(observed, expected, places=2)


if __name__ == '__main__':
    unittest.main()
