-- Queries are separated by "-- name: <query_name>" markers; run_analysis.py
-- executes each one and saves the result as outputs/tables/<query_name>.csv

-- name: monthly_revenue
-- Monthly revenue with MoM growth (LAG), 3-month moving average, cumulative total and YoY growth.
WITH monthly AS (
    SELECT order_month,
           COUNT(*)                                   AS orders,
           ROUND(SUM(items_revenue), 2)               AS revenue,
           ROUND(SUM(items_revenue) / COUNT(*), 2)    AS avg_order_value
    FROM v_orders_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND items_revenue IS NOT NULL
      AND order_month BETWEEN '2017-01' AND '2018-08'
    GROUP BY order_month
)
SELECT order_month, orders, revenue, avg_order_value,
       ROUND(100.0 * (revenue - LAG(revenue)     OVER w) / LAG(revenue)     OVER w, 1) AS mom_growth_pct,
       ROUND(100.0 * (revenue - LAG(revenue, 12) OVER w) / LAG(revenue, 12) OVER w, 1) AS yoy_growth_pct,
       ROUND(AVG(revenue) OVER (ORDER BY order_month
                                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)            AS revenue_3m_avg,
       ROUND(SUM(revenue) OVER (ORDER BY order_month), 2)                                AS cumulative_revenue
FROM monthly
WINDOW w AS (ORDER BY order_month)
ORDER BY order_month;

-- name: orders_by_weekday
SELECT CASE strftime('%w', order_purchase_timestamp)
            WHEN '0' THEN '7 Sun' WHEN '1' THEN '1 Mon' WHEN '2' THEN '2 Tue'
            WHEN '3' THEN '3 Wed' WHEN '4' THEN '4 Thu' WHEN '5' THEN '5 Fri' ELSE '6 Sat' END AS weekday,
       COUNT(*)                                                                                  AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                                        AS share_pct
FROM v_orders_enriched
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY weekday
ORDER BY weekday;

-- name: payment_mix
SELECT main_payment_type                                                   AS payment_type,
       COUNT(*)                                                            AS orders,
       ROUND(SUM(payment_total), 2)                                        AS paid_value,
       ROUND(100.0 * SUM(payment_total) / SUM(SUM(payment_total)) OVER (), 1) AS value_share_pct,
       ROUND(AVG(max_installments), 1)                                     AS avg_installments
FROM v_orders_enriched
WHERE order_status NOT IN ('canceled', 'unavailable') AND payment_total IS NOT NULL
GROUP BY main_payment_type
ORDER BY paid_value DESC;
