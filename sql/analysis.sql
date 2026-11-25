-- Works in PostgreSQL and SQLite. Values reflect SYNTHETIC data, not real pharma sales.
-- 1) Sales by territory - LEFT JOIN keeps territories with zero sales.
SELECT t.region, t.city,
       ROUND(COALESCE(SUM(s.revenue), 0), 2) AS total_revenue,
       COUNT(s.sale_id) AS transactions
FROM dim_territory t
LEFT JOIN fact_sales s ON s.territory_id = t.territory_id
GROUP BY t.region, t.city
ORDER BY total_revenue DESC;

-- 2) Revenue by brand and therapeutic category.
SELECT p.therapeutic_category, p.brand,
       ROUND(SUM(s.revenue), 2) AS total_revenue,
       SUM(s.quantity) AS units_sold
FROM fact_sales s
JOIN dim_product p ON p.product_id = s.product_id
GROUP BY p.therapeutic_category, p.brand
ORDER BY total_revenue DESC;

-- 3) Correct target attainment - aggregate actual and targets separately BEFORE joining.
WITH actuals AS (
  SELECT month, territory_id, SUM(revenue) AS actual_revenue
  FROM fact_sales GROUP BY month, territory_id
)
SELECT t.month, d.region, d.city,
       ROUND(COALESCE(a.actual_revenue, 0), 2) AS actual_revenue,
       ROUND(t.target_revenue, 2) AS target_revenue,
       ROUND(100.0 * COALESCE(a.actual_revenue, 0) / NULLIF(t.target_revenue, 0), 1) AS attainment_pct
FROM fact_targets t
JOIN dim_territory d ON d.territory_id = t.territory_id
LEFT JOIN actuals a ON a.month = t.month AND a.territory_id = t.territory_id
ORDER BY t.month, attainment_pct;

-- 4) Monthly growth: demonstrates CTE + window function.
WITH monthly AS (
    SELECT month, SUM(revenue) AS monthly_revenue
    FROM fact_sales GROUP BY month
), growth AS (
    SELECT month, monthly_revenue,
           LAG(monthly_revenue) OVER (ORDER BY month) AS previous_month
    FROM monthly
)
SELECT month, ROUND(monthly_revenue, 2) AS revenue,
       ROUND(100.0 * (monthly_revenue - previous_month) / NULLIF(previous_month, 0), 2) AS mom_growth_pct
FROM growth
ORDER BY month;
