# Power BI dashboard build guide

**Important:** No `.pbix` dashboard is included. You will create it yourself so you can explain every chart in interviews.

## Quickest method (no PostgreSQL connector required)

1. Run the project scripts to generate the `data/processed/` folder.
2. Open **Power BI Desktop** > **Home** > **Get data** > **Text/CSV**.
3. Load:
   - `sales_by_territory.csv`
   - `product_performance.csv`
   - `territory_target_attainment.csv`
   - `monthly_growth.csv`
4. In Power Query, set currency values to **Decimal number** and `month` to Text.
5. Add the following three report pages:

### Page 1 — Executive overview
- KPI card: `SUM(revenue)` from `monthly_growth` (period total)
- Line chart: `month` vs `revenue`
- Bar chart: `region` / `city` vs `total_revenue` (from sales_by_territory)
- Matrix: regions/cities and revenue

### Page 2 — Territory performance
- Table: `month`, `region`, `city`, `actual_revenue`, `target_revenue`, `attainment_pct`
- Bar chart: actual vs target by city, filter by month
- Conditional formatting: attainment below 100% highlighted

### Page 3 — Product performance
- Bar chart: brand vs total_revenue
- Treemap: therapeutic_category vs total_revenue
- Table: brand, units_sold, total_revenue

## Better version (optional)
Connect Power BI directly to PostgreSQL using the PostgreSQL database connector. Load the five relational tables, create relationships, and build DAX measures for `Total Revenue`, `Total Target`, `Target Attainment %`, and `Transactions`. That approach demonstrates stronger data modeling skills than importing aggregate CSVs.

## Important analytical caveats
- CSV aggregates do not have shared row-level filter relationships, so **do not** claim that one date slicer filters every visual across these separate tables.
- If you need synchronized slicers, use the PostgreSQL relational model or export a joined row-level fact table.
- A sum of `attainment_pct` is meaningless; calculate overall attainment as `SUM(actual_revenue) / SUM(target_revenue) * 100`.
- All records and figures are synthetic examples, not actual pharmaceutical market statistics.
