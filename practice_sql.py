
import sqlite3

conn = sqlite3.connect("pharma_sales.db")

query = """
WITH actual_sales AS (
    SELECT
        territory_id,
        SUM(revenue) AS actual_revenue
    FROM fact_sales
    GROUP BY territory_id
),

sales_targets AS (
    SELECT
        territory_id,
        SUM(target_revenue) AS target_revenue
    FROM fact_targets
    GROUP BY territory_id
)

SELECT
    t.city,
    t.region,
    ROUND(COALESCE(a.actual_revenue, 0), 2),
    ROUND(st.target_revenue, 2),
    ROUND(
        100.0 * COALESCE(a.actual_revenue, 0)
        / NULLIF(st.target_revenue, 0), 2
    ) AS achievement_pct
FROM dim_territory t
LEFT JOIN actual_sales a
    ON t.territory_id = a.territory_id
LEFT JOIN sales_targets st
    ON t.territory_id = st.territory_id
ORDER BY achievement_pct ASC;
"""

rows = conn.execute(query).fetchall()

print("\nTOTAL TERRITORIES:", len(rows))
print("-" * 80)

for row in rows:
    print(row)

print("-" * 80)

territory_revenue = sum(row[2] for row in rows)

database_revenue = conn.execute(
    "SELECT SUM(revenue) FROM fact_sales"
).fetchone()[0]

print(f"Territory revenue: INR {territory_revenue:,.2f}")
print(f"Database revenue:  INR {database_revenue:,.2f}")

print(
    "Reconciliation:",
    "PASS" if abs(territory_revenue - database_revenue) < 0.11
    else "FAIL"
)

conn.close()
