-- Gross merchandise orders in the inclusive date window and selected market.
-- Anonymous purchases remain in revenue; only identified buyers enter repeat rate.
WITH o AS (
  SELECT * FROM orders WHERE date BETWEEN :start AND :end
  AND (:country = 'All markets' OR country = :country)
), buyers AS (
  SELECT customer_id, COUNT(*) AS n FROM o
  WHERE customer_id IS NOT NULL GROUP BY customer_id
), r AS (
  SELECT COALESCE(SUM(-value_mills),0)/1000.0 AS reversed_gbp
  FROM returns WHERE date BETWEEN :start AND :end
  AND (:country = 'All markets' OR country = :country)
)
SELECT COALESCE(SUM(value_mills),0)/1000.0 AS gross_sales_gbp,
  COUNT(*) AS orders, COALESCE(SUM(units),0) AS units,
  SUM(value_mills)/1000.0/NULLIF(COUNT(*),0) AS aov_gbp,
  (SELECT COUNT(*) FROM buyers) AS identified_customers,
  (SELECT COUNT(*) FROM buyers WHERE n >= 2)*1.0/
    NULLIF((SELECT COUNT(*) FROM buyers),0) AS repeat_purchase_rate,
  SUM(CASE WHEN customer_id IS NOT NULL THEN value_mills ELSE 0 END)*1.0/
    NULLIF(SUM(value_mills),0) AS identified_revenue_share,
  (SELECT reversed_gbp FROM r) AS reversed_gbp,
  COALESCE(SUM(value_mills),0)/1000.0-(SELECT reversed_gbp FROM r) AS net_recorded_value_gbp
FROM o;
