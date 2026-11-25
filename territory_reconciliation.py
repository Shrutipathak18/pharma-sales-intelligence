"""Validate the 2025 territory results and export a Power BI-ready CSV.
Run from the pharma_sales_btsa_starter project after src.load_data.
Requires only the Python standard library.
"""
from pathlib import Path
import csv
import sqlite3

ROOT = Path(__file__).resolve().parent
DB = ROOT / "pharma_sales.db"
OUTPUT = ROOT / "data" / "processed" / "territory_performance_2025.csv"

if not DB.exists():
    raise SystemExit(f"Database not found: {DB}. Run: python -m src.load_data")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

try:
    def scalar(sql):
        return conn.execute(sql).fetchone()[0]

    master_count = scalar("SELECT COUNT(*) FROM dim_territory")
    sales_territories = scalar("SELECT COUNT(DISTINCT territory_id) FROM fact_sales")
    target_territories = scalar("SELECT COUNT(DISTINCT territory_id) FROM fact_targets")
    transactions = scalar("SELECT COUNT(*) FROM fact_sales")
    target_rows = scalar("SELECT COUNT(*) FROM fact_targets")
    db_revenue = float(scalar("SELECT COALESCE(SUM(revenue), 0) FROM fact_sales"))
    db_target = float(scalar("SELECT COALESCE(SUM(target_revenue), 0) FROM fact_targets"))
    orphan_sales = scalar("""
        SELECT COUNT(*) FROM fact_sales s
        LEFT JOIN dim_territory t ON s.territory_id = t.territory_id
        WHERE t.territory_id IS NULL
    """)
    orphan_targets = scalar("""
        SELECT COUNT(*) FROM fact_targets f
        LEFT JOIN dim_territory t ON f.territory_id = t.territory_id
        WHERE t.territory_id IS NULL
    """)
    incomplete_targets = scalar("""
        SELECT COUNT(*) FROM (
            SELECT territory_id FROM fact_targets
            GROUP BY territory_id HAVING COUNT(DISTINCT month) <> 12
        )
    """)

    sql = """
    WITH sales AS (
        SELECT territory_id, SUM(revenue) AS actual_revenue,
               COUNT(*) AS transactions
        FROM fact_sales
        GROUP BY territory_id
    ),
    targets AS (
        SELECT territory_id, SUM(target_revenue) AS target_revenue
        FROM fact_targets
        GROUP BY territory_id
    )
    SELECT t.territory_id, t.region, t.city,
           COALESCE(s.actual_revenue, 0) AS actual_revenue,
           COALESCE(g.target_revenue, 0) AS target_revenue,
           COALESCE(s.transactions, 0) AS transactions
    FROM dim_territory t
    LEFT JOIN sales s ON t.territory_id = s.territory_id
    LEFT JOIN targets g ON t.territory_id = g.territory_id
    ORDER BY t.territory_id
    """
    results = conn.execute(sql).fetchall()
    summed_revenue = sum(float(r["actual_revenue"]) for r in results)
    summed_target = sum(float(r["target_revenue"]) for r in results)
    summed_transactions = sum(int(r["transactions"]) for r in results)

    checks = {
        "20 master territories": master_count == 20,
        "20 territories with sales": sales_territories == 20,
        "20 territories with targets": target_territories == 20,
        "20 territory output rows": len(results) == 20,
        "15,000 valid sales transactions": transactions == 15000,
        "240 monthly target records": target_rows == 240,
        "12 target months per territory": incomplete_targets == 0,
        "No orphan territory IDs": orphan_sales == 0 and orphan_targets == 0,
        "All transactions represented": summed_transactions == transactions,
        "Territory revenue equals database revenue": abs(summed_revenue - db_revenue) < 0.01,
        "Territory targets equal database targets": abs(summed_target - db_target) < 0.01,
    }

    print("\nTERRITORY DATA RECONCILIATION — SYNTHETIC 2025 DATA")
    print("-" * 65)
    for label, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'} | {label}")
    print(f"\nDatabase revenue:  INR {db_revenue:,.2f}")
    print(f"Territory revenue: INR {summed_revenue:,.2f}")
    print(f"Total targets:     INR {db_target:,.2f}")
    print(f"Overall attainment: {100 * db_revenue / db_target:.2f}%" if db_target else "No targets")

    if not all(checks.values()):
        raise SystemExit("\nCHECKS FAILED. Review the database before exporting.")

    rows = []
    for r in results:
        actual = float(r["actual_revenue"])
        target = float(r["target_revenue"])
        attainment = 100 * actual / target if target else None
        rows.append({
            "territory_id": r["territory_id"],
            "region": r["region"],
            "city": r["city"],
            "transactions": r["transactions"],
            "actual_revenue": f"{actual:.2f}",
            "target_revenue": f"{target:.2f}",
            "variance_inr": f"{actual - target:.2f}",
            "attainment_pct": f"{attainment:.2f}" if attainment is not None else "",
            "performance_status": "Target Achieved" if target and actual >= target else "Below Target",
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    
    below = [r for r in rows if r["performance_status"] == "Below Target"]
    achieved = len(rows) - len(below)

    print(f"\nTerritories achieving target: {achieved}/20")
    print(f"Territories below target: {len(below)}/20")

    print("\nBOTTOM 5 TERRITORIES (BY TARGET ATTAINMENT)")

    for r in sorted(below, key=lambda x: float(x["attainment_pct"]))[:5]:
        print(
            f"{r['city']:<14} "
            f"{r['attainment_pct']:>6}% "
            f"Shortfall INR {abs(float(r['variance_inr'])):,.2f}"
        )

    print(f"\nCSV successfully exported to: {OUTPUT}")

finally:
    conn.close()
