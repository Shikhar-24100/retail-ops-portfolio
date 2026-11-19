-- Partial months are retained and visibly marked by the dashboard.
SELECT substr(date,1,7) AS month, SUM(value_mills)/1000.0 AS gross_sales_gbp,
  COUNT(*) AS orders, SUM(value_mills)/1000.0/COUNT(*) AS aov_gbp,
  COUNT(DISTINCT customer_id) AS identified_customers
FROM orders WHERE date BETWEEN :start AND :end
  AND (:country = 'All markets' OR country = :country)
GROUP BY month ORDER BY month;
