
import re
import sqlite3
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import DB_PATH, SQL_DIR, OUT_TABLES, OUT_CHARTS, OUT_DASH, REPORTS, STATE_NAMES

NAVY, TEAL, RED, GREY, AMBER = "#1f3a5f", "#2a9d8f", "#d1495b", "#9aa5b1", "#edae49"
plt.rcParams.update({"figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 12, "font.size": 9})



def run_sql_file(conn, path):
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.MULTILINE)
    results = {}
    for name, sql in zip(parts[1::2], parts[2::2]):
        results[name] = pd.read_sql(sql, conn)
    return results


def money(x):
    return f"R${x:,.0f}"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT_CHARTS / f"{name}.png")
    plt.close(fig)


def make_charts(T):
    m = T["monthly_revenue"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(m["order_month"], m["revenue"] / 1e3, color=TEAL, alpha=.85, label="Monthly revenue")
    ax.plot(m["order_month"], m["revenue_3m_avg"] / 1e3, color=NAVY, lw=2.2, marker="o", ms=3, label="3-month average")
    ax.set_title("Monthly revenue (R$ thousands), Jan 2017 - Aug 2018")
    ax.set_ylabel("R$ thousands")
    ax.set_xticks(range(len(m)))
    ax.set_xticklabels(m["order_month"], rotation=60, ha="right")
    ax.legend(frameon=False)
    save(fig, "01_revenue_trend")

    c = T["top_categories"].head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(c["category"], c["revenue"] / 1e3, color=NAVY)
    for y, (rev, sh) in enumerate(zip(c["revenue"], c["revenue_share_pct"])):
        ax.text(rev / 1e3, y, f"  {sh:.1f}%", va="center", fontsize=8)
    ax.set_title("Top 10 categories by revenue (R$ thousands, % of total)")
    save(fig, "02_top_categories")

    d = T["review_by_delay_bucket"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    colors = [TEAL if "Late" not in b else RED for b in d["delay_bucket"]]
    ax.bar(d["delay_bucket"].str[3:], d["avg_review"], color=colors)
    for i, v in enumerate(d["avg_review"]):
        ax.text(i, v + .03, f"{v:.2f}", ha="center", fontsize=9, fontweight="bold")
    ax.set_ylim(1, 5)
    ax.set_title("Average review score by delivery vs promised date")
    ax.set_ylabel("Avg review (1-5)")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    save(fig, "03_review_by_delay_bucket")

    r = T["review_distribution_by_delivery"].pivot(index="review_score", columns="delivery_status",
                                                  values="pct_within_group").fillna(0)
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(r))
    ax.bar(x - .2, r.get("On time / early", 0), .4, color=TEAL, label="On time / early")
    ax.bar(x + .2, r.get("Late", 0), .4, color=RED, label="Late")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s} star" for s in r.index])
    ax.set_ylabel("% of orders in group")
    ax.set_title("Review score distribution: late vs on-time orders")
    ax.legend(frameon=False)
    save(fig, "04_review_distribution_late_vs_ontime")

    s = T["state_performance"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
    top = s.head(10).iloc[::-1]
    a1.barh(top["customer_state"], top["revenue"] / 1e3, color=NAVY)
    a1.set_title("Top 10 states by revenue (R$ thousands)")
    big = s[s["orders"] >= max(30, 0.003 * s["orders"].sum())]
    a2.scatter(big["late_rate_pct"], big["avg_review"], s=big["orders"] / big["orders"].max() * 900 + 30,
               color=TEAL, alpha=.6, edgecolor="white")
    for _, row in big.iterrows():
        a2.annotate(row["customer_state"], (row["late_rate_pct"], row["avg_review"]), ha="center", va="center", fontsize=7)
    a2.set_xlabel("Late delivery rate (%)")
    a2.set_ylabel("Avg review")
    a2.set_title("States: lateness vs satisfaction (bubble = orders)")
    save(fig, "05_state_performance")

    dc = T["seller_revenue_deciles"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(dc["decile"].astype(str), dc["revenue_share_pct"], color=AMBER)
    for i, v in enumerate(dc["revenue_share_pct"]):
        ax.text(i, v + .5, f"{v:.0f}%", ha="center", fontsize=8)
    ax.set_xlabel("Seller decile (1 = top 10% of sellers by revenue)")
    ax.set_ylabel("% of total revenue")
    ax.set_title("Seller revenue concentration")
    save(fig, "06_seller_revenue_concentration")

    rp = T["repeat_rate_by_first_experience"]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.bar(rp["first_order_experience"].str[3:], rp["repeat_rate_pct"], color=[RED, GREY, TEAL])
    for i, v in enumerate(rp["repeat_rate_pct"]):
        ax.text(i, v + .05, f"{v:.2f}%", ha="center", fontweight="bold")
    ax.set_title("Repeat-purchase rate by first-order review")
    ax.set_ylabel("% of customers who ordered again")
    save(fig, "07_repeat_rate_by_first_experience")

    w = T["worst_rated_categories"].iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(w["category"], w["avg_review"], color=RED)
    ax.set_xlim(1, 5)
    for y, v in enumerate(w["avg_review"]):
        ax.text(v + .03, y, f"{v:.2f}", va="center", fontsize=8)
    ax.set_title("10 lowest-rated categories (min 300 orders)")
    save(fig, "08_worst_rated_categories")


def build_report(T, od):
    dl = od[(od.order_status == "delivered") & od.review_score.notna() & od.is_late.notna()]
    ok = od[~od.order_status.isin(["canceled", "unavailable"]) & od.items_revenue.notna()]
    late, ont = dl[dl.is_late == 1], dl[dl.is_late == 0]
    bad = dl[dl.review_score <= 2]

    k = dict(
        revenue=ok.items_revenue.sum(), orders=len(ok), aov=ok.items_revenue.mean(),
        avg_review=dl.review_score.mean(), late_rate=100 * dl.is_late.mean(),
        bad_pct=100 * (dl.review_score <= 2).mean(),
        late_avg=late.review_score.mean(), ont_avg=ont.review_score.mean(),
        late_bad=100 * (late.review_score <= 2).mean(), ont_bad=100 * (ont.review_score <= 2).mean(),
        bad_from_late=100 * (bad.is_late == 1).mean(),
        late_rev=late.items_revenue.sum(), late_rev_share=100 * late.items_revenue.sum() / dl.items_revenue.sum(),
    )
    rep = T["overall_repeat_rate"].iloc[0]
    rp = T["repeat_rate_by_first_experience"].set_index("first_order_experience")["repeat_rate_pct"]
    k["repeat"] = rep.repeat_rate_pct
    k["rep_bad"], k["rep_good"] = rp.iloc[0], rp.iloc[-1]

    st = T["state_performance"]
    big = st[st.orders >= max(30, 0.003 * st.orders.sum())]
    worst_late = big.sort_values("late_rate_pct", ascending=False).head(3)
    worst_days = big.sort_values("avg_delivery_days", ascending=False).head(3)
    top_freight = big.sort_values("freight_pct_of_revenue", ascending=False).head(3)
    top_state = st.iloc[0]
    top3_share = st.head(3).revenue_share_pct.sum()
    fmt_states = lambda df, col, suf: ", ".join(f"{r.customer_state} ({r[col]:.1f}{suf})" for _, r in df.iterrows())

    sc = T["seller_scorecard"]
    weak = sc[sc.avg_review < 3.5]
    dec = T["seller_revenue_deciles"]
    top_dec = dec.iloc[0].revenue_share_pct
    cats = T["top_categories"]
    top5 = cats.iloc[4].cumulative_share_pct
    worst_cats = T["worst_rated_categories"].head(3)
    lane = T["same_state_vs_cross_state"].set_index("lane")
    est = T["estimate_accuracy"].iloc[0]
    status = T["order_status_breakdown"].set_index("order_status")
    lost = status.loc[status.index.isin(["canceled", "unavailable"])]
    mrev = T["monthly_revenue"]
    peak = mrev.loc[mrev.revenue.idxmax()]
    first, last = mrev.iloc[0], mrev.iloc[-1]
    yoy = mrev.dropna(subset=["yoy_growth_pct"])
    yoy_txt = f"{yoy.yoy_growth_pct.mean():.0f}% average year-over-year growth in {yoy.order_month.iloc[0]} to {yoy.order_month.iloc[-1]}" if len(yoy) else "n/a"
    lane_txt = ""
    if {"Same state", "Cross-state"} <= set(lane.index):
        lane_txt = (f"Cross-state orders are late {lane.loc['Cross-state','late_rate_pct']:.1f}% of the time vs "
                    f"{lane.loc['Same state','late_rate_pct']:.1f}% for same-state orders "
                    f"(avg {lane.loc['Cross-state','avg_delivery_days']:.1f} vs {lane.loc['Same state','avg_delivery_days']:.1f} days).")

    R = []
    R.append("# Olist E-Commerce Analysis - Insights Report\n")
    R.append("_Auto-generated by `src/run_analysis.py` from the data in the database. Revenue = item price excluding freight, "
             "cancelled/unavailable orders excluded unless stated._\n")
    R.append("## 1. Headline KPIs\n")
    R.append("| KPI | Value |\n|---|---|")
    for a, b in [("Revenue (excl. freight)", money(k["revenue"])), ("Orders", f"{k['orders']:,}"),
                 ("Average order value", f"R${k['aov']:,.2f}"), ("Average review score", f"{k['avg_review']:.2f} / 5"),
                 ("Late delivery rate", f"{k['late_rate']:.1f}%"), ("Bad reviews (1-2 stars)", f"{k['bad_pct']:.1f}%"),
                 ("Repeat-customer rate", f"{k['repeat']:.2f}%"), ("Growth", yoy_txt)]:
        R.append(f"| {a} | {b} |")

    R.append("\n## 2. Key findings\n")
    R.append(f"1. **Late delivery is the clearest driver of bad reviews.** Late orders average {k['late_avg']:.2f} stars vs "
             f"{k['ont_avg']:.2f} for on-time orders; {k['late_bad']:.0f}% of late orders get a 1-2 star review vs {k['ont_bad']:.0f}% of on-time orders.")
    R.append(f"2. **Late orders punch above their weight:** they are only "
             f"{k['late_rate']:.1f}% of deliveries but account for {k['bad_from_late']:.0f}% of all 1-2 star reviews.")
    R.append(f"3. **Revenue is concentrated geographically:** {top_state.customer_state} alone brings {top_state.revenue_share_pct:.0f}% of revenue; "
             f"the top 3 states bring {top3_share:.0f}%. Highest late rates (states with meaningful volume): {fmt_states(worst_late,'late_rate_pct','%')}.")
    R.append(f"4. **Category concentration:** the top 5 categories generate {top5:.0f}% of revenue "
             f"(#1: {cats.iloc[0].category}, {cats.iloc[0].revenue_share_pct:.1f}%). Lowest-rated large categories: "
             + ", ".join(f"{r.category} ({r.avg_review:.2f})" for _, r in worst_cats.iterrows()) + ".")
    R.append(f"5. **Seller concentration:** the top 10% of sellers generate {top_dec:.0f}% of revenue. {len(weak)} scored sellers "
             f"(20+ orders) average below 3.5 stars and hold {money(weak.revenue.sum())} of revenue.")
    ret_txt = ("a bad first experience lowers the repeat rate" if k["rep_bad"] < k["rep_good"]
               else "a bad first experience shows no clear drop in repeat rate in this data (retention is low either way)")
    R.append(f"6. **Retention is weak:** only {k['repeat']:.2f}% of customers ordered again. Repeat rate after a bad first-order review is "
             f"{k['rep_bad']:.2f}% vs {k['rep_good']:.2f}% after a good one - {ret_txt}.")
    R.append(f"7. **Revenue leakage:** {int(lost.orders.sum()):,} orders ({lost.share_of_orders_pct.sum():.1f}%) were cancelled/unavailable, "
             f"worth {money(lost.order_value.sum())}. Revenue attached to late deliveries is {money(k['late_rev'])} ({k['late_rev_share']:.1f}% of delivered revenue).")
    R.append(f"8. **Delivery promises:** average actual delivery {est.avg_actual_days:.1f} days vs {est.avg_promised_days:.1f} days promised "
             f"(buffer {est.avg_buffer_days:.1f} days on average, but the late tail is what customers punish). {lane_txt}")

    R.append("\n## 3. Business recommendations\n")
    R.append(f"\n**1. Make on-time delivery the top operating KPI.** Late orders cost {k['ont_avg']-k['late_avg']:.1f} review points. "
             f"Set a target to cut the {k['late_rate']:.1f}% late rate, track it weekly by seller and carrier lane, and alert before a package passes its promised date.")
    R.append(f"\n**2. Recalibrate delivery promises by region.** Show realistic dates for the slowest destinations ({fmt_states(worst_days,'avg_delivery_days',' days')}). "
             "A slightly longer but honest promise is cheaper than a 1-star review - 'late' is measured against the promise, not against speed.")
    R.append(f"\n**3. Launch a seller scorecard with consequences.** Rank sellers on late rate and review score; coach or restrict the {len(weak)} sellers averaging under 3.5 stars "
             f"({money(weak.revenue.sum())} of revenue) and reward top-quartile sellers with search visibility. Review the top-decile sellers monthly because they carry {top_dec:.0f}% of revenue.")
    R.append(f"\n**4. Shorten the cross-state lanes.** {lane_txt or 'Cross-state shipping is slower than same-state shipping.'} "
             f"Recruit sellers or add fulfilment/cross-dock capacity near high-demand, high-lateness states; review freight where it is heaviest ({fmt_states(top_freight,'freight_pct_of_revenue','% of revenue')}).")
    R.append(f"\n**5. Protect revenue categories and fix low-rated ones.** The top 5 categories drive {top5:.0f}% of revenue - protect their stock and delivery performance. "
             f"For the weakest-rated categories ({', '.join(worst_cats.category)}) audit product-quality and description issues, not only logistics.")
    R.append(f"\n**6. Recover unhappy customers and plan for peak demand.** Only {k['repeat']:.2f}% of customers return and a bad first order lowers that further "
             f"({k['rep_bad']:.2f}% vs {k['rep_good']:.2f}%). Trigger an apology/voucher flow for late orders and low reviews. "
             f"Peak month was {peak.order_month} ({money(peak.revenue)}); add seller and carrier capacity before peak periods, and reduce the {lost.share_of_orders_pct.sum():.1f}% cancellation/unavailable leakage with stock-sync checks.")

    R.append("\n## 4. Method notes and caveats\n")
    R.append("- Findings show association, not proven causation: other factors (product quality, seller communication) also drive reviews.")
    R.append("- Reviews with multiple submissions per order use the most recent one; payments and items are aggregated per order before joining to avoid double counting.")
    R.append("- Trend charts use Jan 2017 - Aug 2018 only; the first and last months of the dataset are incomplete.")
    R.append("- Currency is Brazilian Real (R$); the dataset is a historical sample (2016-2018).")
    (REPORTS / "insights_report.md").write_text("\n".join(R), encoding="utf-8")
    return k


def export_dashboard_data(conn, T):
    od = pd.read_sql("SELECT * FROM v_orders_enriched", conn)
    od["state_name"] = od.customer_state.map(STATE_NAMES)
    od.to_csv(OUT_DASH / "dashboard_orders.csv", index=False)
    it = pd.read_sql("SELECT * FROM v_items_enriched", conn)
    it["customer_state_name"] = it.customer_state.map(STATE_NAMES)
    it.to_csv(OUT_DASH / "dashboard_items.csv", index=False)
    st = T["state_performance"].copy()
    st["state_name"] = st.customer_state.map(STATE_NAMES)
    st.to_csv(OUT_DASH / "dashboard_state_summary.csv", index=False)
    T["monthly_revenue"].to_csv(OUT_DASH / "dashboard_monthly_kpis.csv", index=False)
    return od


def main():
    if not DB_PATH.exists():
        sys.exit("Database not found. Run:  python src/build_database.py")
    for d in (OUT_TABLES, OUT_CHARTS, OUT_DASH, REPORTS):
        d.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    T = {}
    for f in sorted(SQL_DIR.glob("0[2-9]_*.sql")):
        res = run_sql_file(conn, f)
        for name, df in res.items():
            df.to_csv(OUT_TABLES / f"{name}.csv", index=False)
            print(f"  {f.name:<28} {name:<38} {len(df):>5} rows")
        T.update(res)
    od = export_dashboard_data(conn, T)
    make_charts(T)
    k = build_report(T, od)
    conn.close()
    print("\nDone. Outputs:")
    print("  outputs/tables/            one CSV per SQL query")
    print("  outputs/charts/            8 PNG charts")
    print("  outputs/dashboard_data/    CSVs for Tableau / Power BI")
    print("  reports/insights_report.md findings + 6 recommendations")
    print(f"\nHeadline: revenue R${k['revenue']:,.0f} | late rate {k['late_rate']:.1f}% | "
          f"review late {k['late_avg']:.2f} vs on-time {k['ont_avg']:.2f}")


if __name__ == "__main__":
    main()
