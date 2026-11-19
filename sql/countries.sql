SELECT country, COUNT(*) AS orders, COUNT(DISTINCT customer_id) AS identified_customers,
 SUM(value_mills)/1000.0 AS gross_sales_gbp,
 SUM(value_mills)*1.0/SUM(SUM(value_mills)) OVER () AS sales_share
FROM orders WHERE date BETWEEN :start AND :end
 AND (:country = 'All markets' OR country = :country)
GROUP BY country ORDER BY gross_sales_gbp DESC;
