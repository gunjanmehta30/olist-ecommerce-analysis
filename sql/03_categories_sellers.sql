-- name: top_categories
-- Pareto view: revenue share and cumulative share per category (window functions).
WITH cat AS (
    SELECT category,
           COUNT(DISTINCT order_id)  AS orders,
           SUM(price)                AS revenue,
           AVG(price)                AS avg_price,
           SUM(freight_value)        AS freight
    FROM v_items_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY category
)
SELECT RANK() OVER (ORDER BY revenue DESC)                                   AS revenue_rank,
       category, orders,
       ROUND(revenue, 2)                                                     AS revenue,
       ROUND(avg_price, 2)                                                   AS avg_price,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)                      AS revenue_share_pct,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(revenue) OVER (), 2)                                      AS cumulative_share_pct,
       ROUND(100.0 * freight / revenue, 1)                                   AS freight_pct_of_revenue
FROM cat
ORDER BY revenue DESC
LIMIT 15;

-- name: worst_rated_categories
-- Categories with >= 300 delivered orders, sorted by lowest average review.
WITH co AS (
    SELECT category, order_id,
           SUM(price)        AS rev,
           MAX(review_score) AS review_score,
           MAX(is_late)      AS is_late
    FROM v_items_enriched
    WHERE order_status = 'delivered' AND review_score IS NOT NULL
    GROUP BY category, order_id
)
SELECT category,
       COUNT(*)                                                       AS orders,
       ROUND(SUM(rev), 2)                                             AS revenue,
       ROUND(AVG(review_score), 2)                                    AS avg_review,
       ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0 END), 1) AS pct_bad_reviews,
       ROUND(100.0 * AVG(is_late), 1)                                 AS late_rate_pct
FROM co
GROUP BY category
HAVING COUNT(*) >= 300
ORDER BY avg_review ASC
LIMIT 10;

-- name: seller_scorecard
-- Every seller with >= 20 delivered orders: revenue rank, quartile, quality and lateness.
WITH so AS (
    SELECT seller_id, order_id,
           SUM(price)        AS rev,
           MAX(review_score) AS review_score,
           MAX(is_late)      AS is_late
    FROM v_items_enriched
    WHERE order_status = 'delivered'
    GROUP BY seller_id, order_id
),
sm AS (
    SELECT seller_id,
           COUNT(*)            AS orders,
           SUM(rev)            AS revenue,
           AVG(review_score)   AS avg_review,
           AVG(is_late)        AS late_rate
    FROM so
    GROUP BY seller_id
    HAVING COUNT(*) >= 20
)
SELECT sm.seller_id, s.seller_state, sm.orders,
       ROUND(sm.revenue, 2)                                           AS revenue,
       ROUND(sm.avg_review, 2)                                        AS avg_review,
       ROUND(100.0 * sm.late_rate, 1)                                 AS late_rate_pct,
       RANK()  OVER (ORDER BY sm.revenue DESC)                        AS revenue_rank,
       RANK()  OVER (ORDER BY sm.avg_review ASC)                      AS worst_review_rank,
       NTILE(4) OVER (ORDER BY sm.revenue DESC)                       AS revenue_quartile,
       ROUND(100.0 * sm.revenue / SUM(sm.revenue) OVER (), 2)         AS share_of_scored_revenue_pct
FROM sm
JOIN sellers s ON s.seller_id = sm.seller_id
ORDER BY sm.revenue DESC;

-- name: seller_revenue_deciles
-- How concentrated is revenue? Share of revenue held by each seller decile.
WITH sr AS (
    SELECT seller_id, SUM(price) AS revenue
    FROM v_items_enriched
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY seller_id
),
d AS (
    SELECT seller_id, revenue, NTILE(10) OVER (ORDER BY revenue DESC) AS decile FROM sr
)
SELECT decile,
       COUNT(*)                                                    AS sellers,
       ROUND(SUM(revenue), 2)                                      AS revenue,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1)  AS revenue_share_pct
FROM d
GROUP BY decile
ORDER BY decile;
