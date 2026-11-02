-- =====================================================================
-- 01_views.sql : clean, fan-out-safe building blocks
-- Raw tables are one-to-many (an order has many items / payments / reviews),
-- so we aggregate each to ONE ROW PER ORDER before joining. Joining the raw
-- tables directly would silently double-count revenue.
-- Revenue definition used everywhere: SUM(item price), excluding freight.
-- =====================================================================

DROP VIEW IF EXISTS v_order_payments;
CREATE VIEW v_order_payments AS
SELECT order_id,
       SUM(payment_value)            AS payment_total,
       MAX(payment_installments)     AS max_installments,
       MIN(payment_type)             AS main_payment_type
FROM order_payments
GROUP BY order_id;

DROP VIEW IF EXISTS v_order_items_agg;
CREATE VIEW v_order_items_agg AS
SELECT order_id,
       COUNT(*)                      AS n_items,
       COUNT(DISTINCT seller_id)     AS n_sellers,
       SUM(price)                    AS items_revenue,
       SUM(freight_value)            AS freight_total
FROM order_items
GROUP BY order_id;

-- Some orders have several reviews: keep the most recent one (window function).
DROP VIEW IF EXISTS v_order_reviews;
CREATE VIEW v_order_reviews AS
SELECT order_id, review_score
FROM (
    SELECT order_id, review_score,
           ROW_NUMBER() OVER (PARTITION BY order_id
                              ORDER BY review_answer_timestamp DESC, review_id) AS rn
    FROM order_reviews
)
WHERE rn = 1;

-- One row per order with every metric the analysis needs.
DROP VIEW IF EXISTS v_orders_enriched;
CREATE VIEW v_orders_enriched AS
SELECT o.order_id,
       o.customer_id,
       c.customer_unique_id,
       c.customer_state,
       c.customer_city,
       o.order_status,
       o.order_purchase_timestamp,
       strftime('%Y-%m', o.order_purchase_timestamp)                         AS order_month,
       o.order_delivered_customer_date,
       o.order_estimated_delivery_date,
       i.n_items, i.n_sellers, i.items_revenue, i.freight_total,
       p.payment_total, p.max_installments, p.main_payment_type,
       r.review_score,
       julianday(o.order_delivered_customer_date)
         - julianday(o.order_purchase_timestamp)                             AS delivery_days,
       julianday(o.order_estimated_delivery_date)
         - julianday(o.order_purchase_timestamp)                             AS estimated_days,
       -- compare calendar dates so "delivered on the promised day" is NOT late
       julianday(date(o.order_delivered_customer_date))
         - julianday(date(o.order_estimated_delivery_date))                  AS delay_days,
       CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL
            WHEN date(o.order_delivered_customer_date) > date(o.order_estimated_delivery_date)
            THEN 1 ELSE 0 END                                                AS is_late,
       CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL
            WHEN julianday(date(o.order_delivered_customer_date))
                 - julianday(date(o.order_estimated_delivery_date)) <= -7    THEN '1. Early 7+ days'
            WHEN julianday(date(o.order_delivered_customer_date))
                 - julianday(date(o.order_estimated_delivery_date)) <= -1    THEN '2. Early 1-6 days'
            WHEN julianday(date(o.order_delivered_customer_date))
                 - julianday(date(o.order_estimated_delivery_date)) = 0      THEN '3. On the day'
            WHEN julianday(date(o.order_delivered_customer_date))
                 - julianday(date(o.order_estimated_delivery_date)) <= 3     THEN '4. Late 1-3 days'
            WHEN julianday(date(o.order_delivered_customer_date))
                 - julianday(date(o.order_estimated_delivery_date)) <= 7     THEN '5. Late 4-7 days'
            WHEN julianday(date(o.order_delivered_customer_date))
                 - julianday(date(o.order_estimated_delivery_date)) <= 14    THEN '6. Late 8-14 days'
            ELSE '7. Late 15+ days' END                                      AS delay_bucket
FROM orders o
JOIN customers c               ON c.customer_id = o.customer_id
LEFT JOIN v_order_items_agg i  ON i.order_id    = o.order_id
LEFT JOIN v_order_payments  p  ON p.order_id    = o.order_id
LEFT JOIN v_order_reviews   r  ON r.order_id    = o.order_id;

-- One row per order line, with category (English), seller and order context.
DROP VIEW IF EXISTS v_items_enriched;
CREATE VIEW v_items_enriched AS
SELECT oi.order_id, oi.order_item_id, oi.product_id, oi.seller_id,
       oi.price, oi.freight_value,
       COALESCE(t.product_category_name_english, pr.product_category_name, 'unknown') AS category,
       s.seller_state, s.seller_city,
       e.customer_state, e.customer_unique_id, e.order_status, e.order_month,
       e.review_score, e.is_late, e.delay_days, e.delivery_days,
       CASE WHEN s.seller_state = e.customer_state THEN 'Same state' ELSE 'Cross-state' END AS lane
FROM order_items oi
JOIN v_orders_enriched e            ON e.order_id = oi.order_id
LEFT JOIN products pr               ON pr.product_id = oi.product_id
LEFT JOIN category_translation t    ON t.product_category_name = pr.product_category_name
LEFT JOIN sellers s                 ON s.seller_id = oi.seller_id;
