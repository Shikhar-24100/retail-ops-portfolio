-- Transparent RFM-inspired rules; no claim of a trained customer model.
-- R: days since last order at :end. F/M: orders/gross spend in selected period.
WITH rfm AS (
 SELECT customer_id, CAST(julianday(:end)-julianday(MAX(date)) AS INTEGER) AS recency_days,
 COUNT(*) AS frequency, SUM(value_mills)/1000.0 AS monetary_gbp
 FROM orders WHERE customer_id IS NOT NULL AND date BETWEEN :start AND :end
 AND (:country = 'All markets' OR country = :country) GROUP BY customer_id
), classified AS (
 SELECT *, CASE WHEN recency_days > 90 THEN 'Lapsed >90 days'
 WHEN frequency >= 3 THEN 'Frequent recent buyers'
 WHEN frequency = 2 THEN 'Repeat recent buyers'
 ELSE 'Recent one-time buyers' END AS segment FROM rfm
)
SELECT segment, COUNT(*) AS customers, SUM(frequency) AS orders,
 SUM(monetary_gbp) AS gross_sales_gbp, AVG(recency_days) AS avg_recency_days,
 AVG(frequency) AS avg_frequency, AVG(monetary_gbp) AS avg_customer_spend_gbp
FROM classified GROUP BY segment ORDER BY gross_sales_gbp DESC;
