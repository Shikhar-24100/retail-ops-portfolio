-- First OBSERVED order in selected market, looking back before the report window.
-- Give each eligible customer exactly 90 days of follow-up to avoid right censoring.
WITH history AS (
 SELECT * FROM orders WHERE customer_id IS NOT NULL AND date <= :end
 AND (:country = 'All markets' OR country = :country)
), firsts AS (
 SELECT customer_id, MIN(date) AS first_date FROM history GROUP BY customer_id
), eligible AS (
 SELECT * FROM firsts WHERE first_date BETWEEN :start AND :end
 AND julianday(:end)-julianday(first_date) >= 90
), customer_outcome AS (
 SELECT e.customer_id, e.first_date,
 COUNT(h.invoice) >= 2 AS repeated_90d
 FROM eligible e JOIN history h ON e.customer_id=h.customer_id
 AND julianday(h.date)-julianday(e.first_date) BETWEEN 0 AND 90
 GROUP BY e.customer_id, e.first_date
)
SELECT substr(first_date,1,7) AS cohort, COUNT(*) AS eligible_customers,
 SUM(repeated_90d) AS repeat_customers_90d,
 AVG(repeated_90d) AS repeat_rate_90d
FROM customer_outcome GROUP BY cohort ORDER BY cohort;
