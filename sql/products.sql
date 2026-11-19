-- Product net value is an accounting-period view. Reversals may refer to prior sales.
WITH s AS (
  SELECT sku, MAX(description) AS description, SUM(quantity) AS units,
    SUM(value_mills)/1000.0 AS gross_sales_gbp, COUNT(DISTINCT invoice) AS orders
  FROM sales WHERE date BETWEEN :start AND :end
    AND (:country = 'All markets' OR country = :country) GROUP BY sku
), r AS (
  SELECT sku, SUM(-value_mills)/1000.0 AS reversed_gbp
  FROM returns WHERE date BETWEEN :start AND :end
    AND (:country = 'All markets' OR country = :country) GROUP BY sku
), all_skus AS (SELECT sku FROM s UNION SELECT sku FROM r)
SELECT a.sku, COALESCE(s.description, a.sku) AS description,
  COALESCE(s.units,0) AS units, COALESCE(s.orders,0) AS orders,
  COALESCE(s.gross_sales_gbp,0) AS gross_sales_gbp,
  COALESCE(r.reversed_gbp,0) AS reversed_gbp,
  COALESCE(s.gross_sales_gbp,0)-COALESCE(r.reversed_gbp,0) AS net_recorded_value_gbp,
  SUM(COALESCE(s.gross_sales_gbp,0)) OVER (ORDER BY COALESCE(s.gross_sales_gbp,0) DESC, a.sku
    ROWS UNBOUNDED PRECEDING)/NULLIF(SUM(COALESCE(s.gross_sales_gbp,0)) OVER (),0) AS cumulative_sales_share
FROM all_skus a LEFT JOIN s ON a.sku=s.sku LEFT JOIN r ON a.sku=r.sku
ORDER BY gross_sales_gbp DESC, a.sku;
