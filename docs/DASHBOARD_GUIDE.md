# Dashboard Guide: Tableau Public or Power BI (pick ONE, build it in ~2 hours)

After `python run_all.py` the folder `outputs/dashboard_data/` contains the files you need:

| File | Grain | Use it for |
|---|---|---|
| `dashboard_orders.csv` | 1 row per order | revenue, orders, reviews, late delivery, states |
| `dashboard_items.csv` | 1 row per order line | categories and sellers |
| `dashboard_state_summary.csv` | 1 row per state | map and state table |
| `dashboard_monthly_kpis.csv` | 1 row per month | trend with MoM / YoY growth |

> **Important rule:** do not mix `dashboard_orders` and `dashboard_items` in one chart (order revenue repeats on every item row and would be double counted). Use them as **separate data sources**.

Which tool? **Tableau Public** is free and works on Windows and Mac, and gives you a public link for your resume. **Power BI Desktop** is free but Windows-only. You only need one.

---
## Option A: Tableau Public (recommended: easy public link)

**1. Install and connect**
1. Download Tableau Public (public.tableau.com) and sign up.
2. Connect -> *Text file* -> `dashboard_orders.csv`. Then add `dashboard_items.csv`, `dashboard_state_summary.csv` and `dashboard_monthly_kpis.csv` as **separate** data sources (Data -> New Data Source).
3. In `dashboard_orders`: set `order_purchase_timestamp` to *Date & Time*. Right-click `state_name` -> Geographic Role -> *State/Province*.

**2. Calculated fields (Analysis -> Create Calculated Field), on `dashboard_orders`**
```
Revenue            : IF [Order Status] != "canceled" AND [Order Status] != "unavailable" THEN [Items Revenue] END
Delivered Orders   : IF [Order Status] = "delivered" AND NOT ISNULL([Is Late]) THEN 1 ELSE 0 END
Late Orders        : IF [Order Status] = "delivered" AND [Is Late] = 1 THEN 1 ELSE 0 END
Late Rate          : SUM([Late Orders]) / SUM([Delivered Orders])          (format as %)
Avg Review         : AVG(IF [Order Status] = "delivered" THEN [Review Score] END)
Bad Review Rate    : SUM(IF [Order Status]="delivered" AND [Review Score] <= 2 THEN 1 ELSE 0 END)
                     / SUM(IF [Order Status]="delivered" AND NOT ISNULL([Review Score]) THEN 1 ELSE 0 END)
```
`dashboard_orders` already has `delay_bucket` (numbered so it sorts correctly) and `order_month`.

**3. Build 6 sheets**
| Sheet | How |
|---|---|
| KPI cards (4) | Revenue, Orders, Avg Review, Late Rate: drag one measure to Text, format big and bold |
| Revenue trend | Rows = SUM(Revenue), Columns = `Order Month` (discrete). Filter `Order Month` to 2017-01 ... 2018-08. Add a *Moving Average* table calc (Analysis -> Create Table Calc, 3 periods) |
| Review by delay bucket | Columns = `Delay Bucket`, Rows = Avg Review. Colour late buckets red. Reference line at the overall average |
| State map | Columns/Rows auto from `State Name`, Colour = Late Rate (red = worse), Size = SUM(Revenue). Tooltip: avg review, orders |
| Top categories (`dashboard_items`) | Rows = `Category`, Columns = SUM(`Price`), top 10 filter (Filter -> Top -> By field). Colour by Avg of `Review Score` |
| Seller table (`dashboard_items`) | Rows = `Seller Id`, columns = SUM(Price), AVG(Review Score), then sort and show bottom 10 by review with a *Number of orders >= 20* filter (COUNTD of `Order Id`) |

**4. Dashboard layout (Dashboard -> New, size: Automatic or 1300x800)**
- Top row: title + 4 KPI cards
- Middle: revenue trend (left) | state map (right)
- Bottom: review-by-delay-bucket | top categories | seller table
- Add filters (apply to all sheets using the same data source): *Order Month*, *State Name*. Use *Dashboard -> Actions -> Filter* so clicking a state filters the other charts.
- Add a text box titled **"Key insight"**: "Late orders average X stars vs Y for on-time orders" (use the numbers from `reports/insights_report.md`).

**5. Publish**
File -> Save to Tableau Public. Put the link on your resume and in the GitHub README.

---
## Option B: Power BI Desktop

**1. Load**: Home -> Get Data -> Text/CSV -> load the 4 files (**Load**, not Transform, unless you want to rename columns). In *Data view*, set `order_purchase_timestamp` to Date/Time and `is_late` to Whole number. Set `state_name` -> Data category: *State or Province*.

**2. DAX measures** (Modeling -> New Measure; table name `dashboard_orders` shown as `orders` below, rename the table to keep formulas short)
```DAX
Revenue = CALCULATE ( SUM ( orders[items_revenue] ),
                      NOT ( orders[order_status] IN { "canceled", "unavailable" } ) )

Orders = CALCULATE ( COUNTROWS ( orders ),
                     NOT ( orders[order_status] IN { "canceled", "unavailable" } ),
                     NOT ( ISBLANK ( orders[items_revenue] ) ) )

Avg Order Value = DIVIDE ( [Revenue], [Orders] )

Delivered Scored Orders = CALCULATE ( COUNTROWS ( orders ),
                          orders[order_status] = "delivered", NOT ( ISBLANK ( orders[is_late] ) ) )

Late Rate = DIVIDE ( CALCULATE ( COUNTROWS ( orders ), orders[order_status] = "delivered", orders[is_late] = 1 ),
                     [Delivered Scored Orders] )

Avg Review = CALCULATE ( AVERAGE ( orders[review_score] ), orders[order_status] = "delivered" )

Bad Review Rate = DIVIDE (
    CALCULATE ( COUNTROWS ( orders ), orders[order_status] = "delivered", orders[review_score] <= 2 ),
    CALCULATE ( COUNTROWS ( orders ), orders[order_status] = "delivered", NOT ( ISBLANK ( orders[review_score] ) ) ) )

Avg Delivery Days = CALCULATE ( AVERAGE ( orders[delivery_days] ), orders[order_status] = "delivered" )
```
Do the same for items (`items` table): `Category Revenue = SUM ( items[price] )`.

**3. Visuals (Report view)**
| Visual | Fields |
|---|---|
| 4 KPI **Cards** | Revenue, Orders, Avg Review, Late Rate |
| **Line + clustered column** | X: `dashboard_monthly_kpis[order_month]`, columns: revenue, line: revenue_3m_avg |
| **Clustered column** | X: `delay_bucket`, Y: Avg Review (conditional colour: red for late buckets) |
| **Filled map** or **Map** | Location: `state_name`, Colour saturation: Late Rate, Size: Revenue |
| **Bar chart** | Axis: `items[category]`, Values: Category Revenue, Top N filter = 10 |
| **Table** | `seller_id`, orders, avg review, late rate (from `seller_scorecard.csv`, load it too) sorted by avg review ascending |
| **Slicers** | `order_month`, `state_name` |

**4. Polish**: consistent colour palette (navy `#1f3a5f`, teal `#2a9d8f`, red `#d1495b`), page title, a text box with the main insight, tooltips on, align everything on the grid.

**5. Share**: save the `.pbix` into the GitHub repo, export the report as PDF, take 2-3 screenshots for the README. (Public "Publish to web" is only available on some accounts.)

---
## What a recruiter looks for in the dashboard (checklist)
- [ ] A clear title that states the business question
- [ ] 4 KPI cards on top, filters on the side
- [ ] At least one chart that proves the story: **review score by delay bucket**
- [ ] A state map and a top-categories chart
- [ ] A short "Key insight" text box
- [ ] No more than 2 colours doing real work (red = bad, teal = good)
- [ ] Screenshot saved to `docs/dashboard_screenshot.png` and linked in the README
