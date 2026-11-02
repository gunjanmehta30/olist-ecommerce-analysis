# E-Commerce Sales, Delivery & Customer Satisfaction Analysis

**Dataset:** Olist Brazilian E-Commerce (Kaggle) | ~100K orders, 9 related tables (2016-2018)
**Stack:** SQL (SQLite) | Python (pandas, matplotlib, Plotly) | Tableau Public or Power BI
**Business question:** *"Why do some orders get bad reviews, and where is the company losing revenue?"*

## What this project delivers
| Requirement | Where it lives |
|---|---|
| SQL joins and window functions across multiple tables | `sql/01_views.sql` ... `sql/06_revenue_leakage.sql` |
| Revenue trends, top categories, top and bottom sellers | `sql/02_*`, `sql/03_*` |
| Late delivery vs review score | `sql/04_delivery_vs_reviews.sql` |
| State-wise performance | `sql/05_state_performance.sql` |
| Dashboard | `outputs/dashboard.html` (instant) + Tableau / Power BI build steps in `docs/DASHBOARD_GUIDE.md` |
| 5-6 business recommendations | `reports/insights_report.md` (auto-written with numbers from your run) |

## Quick start
```bash
# 1. Install
pip install -r requirements.txt

# 2. Get the data: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
#    Unzip all 9 CSVs into  data/raw/
#    (or: kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip)

# 3. Run everything
python run_all.py
```
Want to test the code before downloading? `python run_all.py --sample` uses a tiny **synthetic** dataset. Those numbers are fake: never put them on a resume.

Outputs after a run:
```
outputs/tables/          one CSV per SQL query (18 tables)
outputs/charts/          8 PNG charts for README / slides
outputs/dashboard.html   interactive dashboard, open in any browser
outputs/dashboard_data/  clean CSVs to load into Tableau / Power BI
reports/insights_report.md   KPIs, findings and 6 recommendations
```

## Project structure
```
olist-ecommerce-analysis/
|-- run_all.py                 one-command pipeline
|-- sql/
|   |-- 01_views.sql           fan-out-safe order- and item-level views
|   |-- 02_revenue_trends.sql  MoM / YoY (LAG), moving average, cumulative revenue, payments
|   |-- 03_categories_sellers.sql  Pareto, RANK, NTILE seller quartiles and deciles, scorecard
|   |-- 04_delivery_vs_reviews.sql delay buckets, late vs on-time, share of bad reviews
|   |-- 05_state_performance.sql   state KPIs, same-state vs cross-state lanes
|   `-- 06_revenue_leakage.sql     cancellations, revenue at risk, repeat rate (ROW_NUMBER)
|-- src/
|   |-- config.py   build_database.py   run_analysis.py
|   |-- build_dashboard.py   generate_sample_data.py
|-- docs/  DASHBOARD_GUIDE.md   RESUME_AND_INTERVIEW.md
|-- data/raw/   (put Kaggle CSVs here)   database/   outputs/   reports/
```

## Data model (simplified)
```
customers --< orders >-- order_items >-- products >-- category_translation
                |             `-------- sellers
                |--< order_payments
                `--< order_reviews        geolocation (zip prefix lookup)
```

## Method highlights
- **No double counting.** An order has many items, payments and reviews, so each is aggregated to one row per order before joining. `build_database.py` asserts one row per order and that revenue reconciles with `order_items`.
- **Duplicate reviews** are resolved with `ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC)`.
- **Late** = delivered calendar date after the estimated delivery date; delay is bucketed (early, on the day, late 1-3, 4-7, 8-14, 15+ days).
- **Revenue** = item price excluding freight; cancelled and unavailable orders excluded; trend charts use Jan 2017 - Aug 2018 (edge months are incomplete).
- Window functions used: `LAG`, `RANK`, `NTILE`, `ROW_NUMBER`, running `SUM`/`AVG`, `SUM() OVER ()` for shares, `PARTITION BY` percentages.

## Findings
Run the project, then open `reports/insights_report.md`. It contains your KPI table, 8 findings and 6 recommendations with the exact numbers from your data. Add a screenshot of your Tableau / Power BI dashboard at `docs/dashboard_screenshot.png`.

From the public Olist dataset you should expect a story along these lines (verify against your own output before claiming anything): late orders are a small share of deliveries but score far lower than on-time orders, São Paulo dominates revenue, a handful of categories make most of the money, and repeat purchase is very low.

## Business recommendations (summary; full version with numbers in the report)
1. Make on-time delivery the top operating KPI and alert before promised dates are missed.
2. Recalibrate delivery promises for the slowest regions.
3. Launch a seller scorecard with consequences for persistently low-rated sellers.
4. Shorten cross-state lanes with local sellers / fulfilment capacity; review freight-heavy regions.
5. Protect top-revenue categories and fix the lowest-rated ones.
6. Recover unhappy customers (voucher / apology flow) and prepare capacity for peak months.

## Limitations
Association, not proof of causation; one marketplace, 2016-2018; reviews are voluntary (selection bias); geolocation is a zip-prefix lookup and was not used for distance calculation (a natural next step: seller-to-customer distance vs delay).

## Author
Gunjan Mehta | MCA | Data Analytics / Data Science
