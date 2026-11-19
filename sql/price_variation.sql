-- OBSERVATIONAL price dispersion. Promotions, costs, and exposure are not observed.
-- No causal uplift or margin is computed from this dataset.
SELECT sku, MAX(description) AS description, COUNT(DISTINCT invoice) AS orders,
 COUNT(DISTINCT unit_price_mills) AS observed_price_points,
 MIN(unit_price_mills)/1000.0 AS min_unit_price_gbp,
 MAX(unit_price_mills)/1000.0 AS max_unit_price_gbp,
 SUM(value_mills)/1000.0/SUM(quantity) AS weighted_unit_price_gbp,
 SUM(value_mills)/1000.0 AS gross_sales_gbp
FROM sales WHERE date BETWEEN :start AND :end
 AND (:country = 'All markets' OR country = :country)
GROUP BY sku HAVING COUNT(DISTINCT invoice) >= 30 AND COUNT(DISTINCT unit_price_mills) > 1
ORDER BY gross_sales_gbp DESC;
