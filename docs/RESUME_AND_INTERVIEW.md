# Resume Bullets and Interview Prep

## Resume entry (fill the [brackets] with YOUR numbers from `reports/insights_report.md`)

**E-Commerce Sales, Delivery & Customer Satisfaction Analysis** | SQL (SQLite), Python (pandas, matplotlib), Tableau / Power BI
*Dataset: Olist Brazilian E-Commerce (~100K orders, 9 relational tables)*

- Joined 9 relational tables with SQL (CTEs, window functions: `LAG`, `RANK`, `NTILE`, `ROW_NUMBER`, running totals) and built fan-out-safe order-level views, reconciling revenue to the source table to zero variance.
- Quantified that late deliveries ([X]% of orders) average [A] stars vs [B] for on-time orders and drive [Y]% of all 1-2 star reviews.
- Analysed revenue trends, category Pareto ([N] categories = [P]% of revenue), seller concentration and state-wise performance; found [STATE] has the highest late rate ([Z]%).
- Built an interactive Tableau / Power BI dashboard (KPI cards, state map, delivery-vs-review view) and delivered 6 data-backed recommendations targeting late delivery, seller quality, regional logistics and retention.

(Keep 3 or 4 bullets. Only use numbers that your own run produced.)

## 60-second project pitch
"Olist is a Brazilian marketplace. The business asked why some orders get bad reviews and where revenue is lost. I loaded the 9 tables into SQLite, built order-level views so joins don't double-count, and used window functions for growth, rankings and seller quartiles. The clearest finding was that delivery lateness against the promised date is the strongest driver of bad reviews: late orders score about [A] vs [B] stars. I then looked at where it happens by state and by seller, and built a dashboard and six recommendations."

## Questions you should be ready for
1. **Why did you aggregate before joining?** An order can have many items, payments and reviews. Joining raw tables multiplies rows and inflates revenue. I aggregated each table to one row per order and added a check that revenue reconciles to `order_items`.
2. **How did you define "late"?** Delivered date later than the estimated date, compared at calendar-date level. Delivering on the promised day is not late.
3. **How did you handle multiple reviews per order?** `ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC)` and kept the latest.
4. **Is lateness causing bad reviews?** The data shows a strong association with a consistent dose-response (longer delay -> lower score). It isn't proof of causation: product quality and seller communication also matter. An A/B test on delivery promises would be the next step.
5. **Why exclude some months from trends?** The first and last months of the dataset are incomplete and would fake a growth/decline.
6. **Why SQLite?** Zero setup and supports window functions; the SQL is standard and ports to PostgreSQL/MySQL with small date-function changes (`julianday`/`strftime`).
7. **What would you do next?** Predict late delivery risk with a model, add seller-level churn analysis, and test voucher recovery for late orders.
