-- name: order_status_breakdown
-- Revenue lost to cancelled / unavailable orders and orders stuck in the pipeline.
SELECT order_status,
       COUNT(*)                                            AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS share_of_orders_pct,
       ROUND(COALESCE(SUM(items_revenue), 0), 2)           AS order_value
FROM v_orders_enriched
GROUP BY order_status
ORDER BY orders DESC;

-- name: revenue_by_review_segment
-- How much revenue is attached to unhappy customers ("revenue at risk")?
SELECT CASE WHEN review_score <= 2 THEN '1. Bad (1-2 stars)'
            WHEN review_score = 3  THEN '2. Neutral (3 stars)'
            ELSE '3. Good (4-5 stars)' END                                  AS review_segment,
       COUNT(*)                                                             AS orders,
       ROUND(SUM(items_revenue), 2)                                         AS revenue,
       ROUND(100.0 * SUM(items_revenue) / SUM(SUM(items_revenue)) OVER (), 1) AS revenue_share_pct,
       ROUND(100.0 * AVG(is_late), 1)                                       AS late_rate_pct
FROM v_orders_enriched
WHERE order_status = 'delivered' AND review_score IS NOT NULL AND items_revenue IS NOT NULL
GROUP BY review_segment
ORDER BY review_segment;

-- name: repeat_rate_by_first_experience
-- Window functions: first order per customer, then did the customer ever come back?
WITH o AS (
    SELECT customer_unique_id, review_score,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY order_purchase_timestamp) AS rn,
           COUNT(*)     OVER (PARTITION BY customer_unique_id)                                    AS n_orders
    FROM v_orders_enriched
    WHERE order_status = 'delivered' AND review_score IS NOT NULL
)
SELECT CASE WHEN review_score <= 2 THEN '1. Bad (1-2 stars)'
            WHEN review_score = 3  THEN '2. Neutral (3 stars)'
            ELSE '3. Good (4-5 stars)' END                                      AS first_order_experience,
       COUNT(*)                                                                 AS customers,
       ROUND(100.0 * AVG(CASE WHEN n_orders > 1 THEN 1.0 ELSE 0 END), 2)        AS repeat_rate_pct
FROM o
WHERE rn = 1
GROUP BY first_order_experience
ORDER BY first_order_experience;

-- name: overall_repeat_rate
WITH c AS (
    SELECT customer_unique_id, COUNT(*) AS n_orders
    FROM v_orders_enriched
    WHERE order_status = 'delivered'
    GROUP BY customer_unique_id
)
SELECT COUNT(*)                                                           AS customers,
       SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END)                      AS repeat_customers,
       ROUND(100.0 * AVG(CASE WHEN n_orders > 1 THEN 1.0 ELSE 0 END), 2)  AS repeat_rate_pct
FROM c;
