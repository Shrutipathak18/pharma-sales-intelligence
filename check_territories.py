
import sqlite3

conn = sqlite3.connect("pharma_sales.db")

checks = {
    "Territories in master": """
        SELECT COUNT(*) FROM dim_territory
    """,

    "Territories with sales": """
        SELECT COUNT(DISTINCT territory_id)
        FROM fact_sales
    """,

    "Territories with targets": """
        SELECT COUNT(DISTINCT territory_id)
        FROM fact_targets
    """
}

for label, query in checks.items():
    result = conn.execute(query).fetchone()[0]
    print(f"{label}: {result}")

print("\nTerritories without targets:")

query = """
SELECT
    t.territory_id,
    t.city,
    t.region
FROM dim_territory t
LEFT JOIN fact_targets ft
    ON t.territory_id = ft.territory_id
WHERE ft.territory_id IS NULL
ORDER BY t.city;
"""

for row in conn.execute(query):
    print(row)

conn.close()
