-- name: review_by_delay_bucket
SELECT delay_bucket,
       COUNT(*)                                                                  AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                        AS share_of_orders_pct,
       ROUND(AVG(review_score), 2)                                               AS avg_review,
       ROUND(100.0 * AVG(CASE WHEN review_score = 1 THEN 1.0 ELSE 0 END), 1)     AS pct_1_star,
       ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0 END), 1)    AS pct_bad_reviews
FROM v_orders_enriched
WHERE order_status = 'delivered' AND review_score IS NOT NULL AND delay_bucket IS NOT NULL
GROUP BY delay_bucket
ORDER BY delay_bucket;

-- name: late_vs_ontime
SELECT CASE is_late WHEN 1 THEN 'Late' ELSE 'On time / early' END                AS delivery_status,
       COUNT(*)                                                                  AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                        AS share_of_orders_pct,
       ROUND(AVG(review_score), 2)                                               AS avg_review,
       ROUND(AVG(delivery_days), 1)                                              AS avg_delivery_days,
       ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0 END), 1)    AS pct_bad_reviews,
       ROUND(SUM(items_revenue), 2)                                              AS revenue
FROM v_orders_enriched
WHERE order_status = 'delivered' AND review_score IS NOT NULL AND is_late IS NOT NULL
GROUP BY is_late
ORDER BY is_late;

-- name: review_distribution_by_delivery
SELECT CASE is_late WHEN 1 THEN 'Late' ELSE 'On time / early' END                AS delivery_status,
       review_score,
       COUNT(*)                                                                  AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY is_late), 1)    AS pct_within_group
FROM v_orders_enriched
WHERE order_status = 'delivered' AND review_score IS NOT NULL AND is_late IS NOT NULL
GROUP BY is_late, review_score
ORDER BY is_late, review_score;

-- name: bad_reviews_explained_by_lateness
-- Of all 1-2 star reviews, how many came from late orders?
SELECT CASE is_late WHEN 1 THEN 'Late' ELSE 'On time / early' END                AS delivery_status,
       COUNT(*)                                                                  AS bad_reviews,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                        AS share_of_bad_reviews_pct
FROM v_orders_enriched
WHERE order_status = 'delivered' AND review_score <= 2 AND is_late IS NOT NULL
GROUP BY is_late;

-- name: estimate_accuracy
-- Does the promised delivery date leave enough buffer? Actual vs estimated days.
SELECT ROUND(AVG(delivery_days), 1)                      AS avg_actual_days,
       ROUND(AVG(estimated_days), 1)                     AS avg_promised_days,
       ROUND(AVG(estimated_days - delivery_days), 1)     AS avg_buffer_days
FROM v_orders_enriched
WHERE order_status = 'delivered' AND delivery_days IS NOT NULL;
