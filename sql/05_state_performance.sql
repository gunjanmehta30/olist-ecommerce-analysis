-- name: state_performance
WITH st AS (
    SELECT customer_state,
           COUNT(*)                          AS orders,
           COUNT(DISTINCT customer_unique_id) AS customers,
           SUM(items_revenue)                AS revenue,
           SUM(freight_total)                AS freight,
           AVG(delivery_days)                AS avg_delivery_days,
           AVG(is_late)                      AS late_rate,
           AVG(review_score)                 AS avg_review
    FROM v_orders_enriched
    WHERE order_status = 'delivered' AND items_revenue IS NOT NULL
    GROUP BY customer_state
)
SELECT RANK() OVER (ORDER BY revenue DESC)                          AS revenue_rank,
       customer_state, orders, customers,
       ROUND(revenue, 2)                                            AS revenue,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 1)             AS revenue_share_pct,
       ROUND(revenue / orders, 2)                                   AS avg_order_value,
       ROUND(avg_delivery_days, 1)                                  AS avg_delivery_days,
       ROUND(avg_delivery_days - AVG(avg_delivery_days) OVER (), 1) AS days_vs_state_avg,
       ROUND(100.0 * late_rate, 1)                                  AS late_rate_pct,
       ROUND(avg_review, 2)                                         AS avg_review,
       RANK() OVER (ORDER BY avg_review DESC)                       AS review_rank,
       ROUND(100.0 * freight / revenue, 1)                          AS freight_pct_of_revenue
FROM st
ORDER BY revenue DESC;

-- name: same_state_vs_cross_state
-- Seller-to-customer lanes: is cross-state shipping the root of late deliveries?
WITH lane_orders AS (
    SELECT order_id, lane,
           MAX(is_late) AS is_late, MAX(review_score) AS review_score, MAX(delivery_days) AS delivery_days
    FROM v_items_enriched
    WHERE order_status = 'delivered' AND is_late IS NOT NULL
    GROUP BY order_id, lane
)
SELECT lane,
       COUNT(*)                          AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_of_orders_pct,
       ROUND(AVG(delivery_days), 1)      AS avg_delivery_days,
       ROUND(100.0 * AVG(is_late), 1)    AS late_rate_pct,
       ROUND(AVG(review_score), 2)       AS avg_review
FROM lane_orders
GROUP BY lane;
