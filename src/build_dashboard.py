import sys
import pandas as pd
import plotly.graph_objects as go
from config import OUT_TABLES, OUT_DASH, ROOT

NAVY, TEAL, RED, AMBER = "#1f3a5f", "#2a9d8f", "#d1495b", "#edae49"


def fig_html(fig, first=False):
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=40, r=20, t=50, b=40),
        height=380,
        font=dict(family="Segoe UI, Arial, sans-serif", size=12),
    )
    return fig.to_html(full_html=False, include_plotlyjs=True if first else False)


def main():
    if not (OUT_TABLES / "monthly_revenue.csv").exists():
        sys.exit("Run python src/run_analysis.py first.")
    rd = lambda n: pd.read_csv(OUT_TABLES / f"{n}.csv")
    m, cat, bucket = (
        rd("monthly_revenue"),
        rd("top_categories"),
        rd("review_by_delay_bucket"),
    )
    st, dist, dec = (
        rd("state_performance"),
        rd("review_distribution_by_delivery"),
        rd("seller_revenue_deciles"),
    )
    rep, worst = rd("repeat_rate_by_first_experience"), rd("worst_rated_categories")
    orders = pd.read_csv(
        OUT_DASH / "dashboard_orders.csv",
        usecols=["order_status", "items_revenue", "review_score", "is_late"],
    )

    ok = orders[
        ~orders.order_status.isin(["canceled", "unavailable"])
        & orders.items_revenue.notna()
    ]
    dl = orders[
        (orders.order_status == "delivered")
        & orders.review_score.notna()
        & orders.is_late.notna()
    ]
    kpis = [
        ("Revenue", f"R${ok.items_revenue.sum()/1e6:,.2f}M"),
        ("Orders", f"{len(ok):,}"),
        ("Avg order value", f"R${ok.items_revenue.mean():,.0f}"),
        ("Avg review", f"{dl.review_score.mean():.2f} / 5"),
        ("Late deliveries", f"{100*dl.is_late.mean():.1f}%"),
        ("Bad reviews (1-2*)", f"{100*(dl.review_score<=2).mean():.1f}%"),
    ]

    figs = []
    f = go.Figure()
    f.add_bar(x=m.order_month, y=m.revenue, name="Revenue", marker_color=TEAL)
    f.add_scatter(
        x=m.order_month,
        y=m.revenue_3m_avg,
        name="3-month avg",
        line=dict(color=NAVY, width=3),
    )
    f.update_layout(title="Monthly revenue (R$)")
    figs.append(f)

    f = go.Figure(
        go.Bar(
            x=cat.revenue[:10][::-1],
            y=cat.category[:10][::-1],
            orientation="h",
            marker_color=NAVY,
            text=cat.revenue_share_pct[:10][::-1].map("{:.1f}%".format),
            textposition="outside",
        )
    )
    f.update_layout(title="Top 10 categories by revenue")
    figs.append(f)

    f = go.Figure(
        go.Bar(
            x=bucket.delay_bucket.str[3:],
            y=bucket.avg_review,
            marker_color=[RED if "Late" in b else TEAL for b in bucket.delay_bucket],
            text=bucket.avg_review.map("{:.2f}".format),
            textposition="outside",
        )
    )
    f.update_layout(
        title="Avg review score by delivery vs promised date", yaxis=dict(range=[1, 5])
    )
    figs.append(f)

    f = go.Figure()
    for status, color in [("On time / early", TEAL), ("Late", RED)]:
        d = dist[dist.delivery_status == status]
        f.add_bar(
            x=d.review_score.astype(str) + " star",
            y=d.pct_within_group,
            name=status,
            marker_color=color,
        )
    f.update_layout(
        title="Review distribution: late vs on-time (% of group)", barmode="group"
    )
    figs.append(f)

    big = st[st.orders >= max(30, 0.003 * st.orders.sum())]
    f = go.Figure(
        go.Scatter(
            x=big.late_rate_pct,
            y=big.avg_review,
            mode="markers+text",
            text=big.customer_state,
            textposition="middle center",
            marker=dict(
                size=big.orders / big.orders.max() * 60 + 14, color=TEAL, opacity=0.6
            ),
            customdata=big[["revenue", "avg_delivery_days"]],
            hovertemplate="%{text}<br>Late: %{x}%<br>Review: %{y}<br>Revenue: R$%{customdata[0]:,.0f}"
            "<br>Avg days: %{customdata[1]}<extra></extra>",
        )
    )
    f.update_layout(
        title="States: late rate vs avg review (bubble = orders)",
        xaxis_title="Late rate (%)",
        yaxis_title="Avg review",
    )
    figs.append(f)

    f = go.Figure(go.Bar(x=st.customer_state[:12], y=st.revenue, marker_color=NAVY))
    f.update_layout(title="Revenue by state (top 12)")
    figs.append(f)

    f = go.Figure(
        go.Bar(x=dec.decile.astype(str), y=dec.revenue_share_pct, marker_color=AMBER)
    )
    f.update_layout(
        title="Seller revenue concentration (decile 1 = top 10%)",
        xaxis_title="Seller decile",
        yaxis_title="% of revenue",
    )
    figs.append(f)

    f = go.Figure(
        go.Bar(
            x=rep.first_order_experience.str[3:],
            y=rep.repeat_rate_pct,
            marker_color=[RED, "#9aa5b1", TEAL],
            text=rep.repeat_rate_pct.map("{:.2f}%".format),
            textposition="outside",
        )
    )
    f.update_layout(title="Repeat-purchase rate by first-order review")
    figs.append(f)

    kpi_html = "".join(
        f'<div class="kpi"><div class="v">{v}</div><div class="l">{k}</div></div>'
        for k, v in kpis
    )
    grid = "".join(
        f'<div class="card">{fig_html(f, first=(i == 0))}</div>'
        for i, f in enumerate(figs)
    )
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Olist E-Commerce Dashboard</title>
<style>body{{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#f4f6f8;color:#1f3a5f}}
header{{background:#1f3a5f;color:#fff;padding:18px 28px}}header h1{{margin:0;font-size:22px}}header p{{margin:4px 0 0;opacity:.8;font-size:13px}}
.kpis{{display:flex;gap:14px;padding:18px 28px;flex-wrap:wrap}}.kpi{{background:#fff;border-radius:10px;padding:14px 20px;min-width:140px;box-shadow:0 1px 3px #0002}}
.kpi .v{{font-size:24px;font-weight:700}}.kpi .l{{font-size:12px;color:#667}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:16px;padding:0 28px 28px}}
.card{{background:#fff;border-radius:10px;box-shadow:0 1px 3px #0002;padding:6px}}</style></head><body>
<header><h1>Olist E-Commerce: Sales, Delivery &amp; Customer Satisfaction</h1>
<p>Why do some orders get bad reviews, and where is the company losing revenue?</p></header>
<div class="kpis">{kpi_html}</div><div class="grid">{grid}</div></body></html>"""
    out = ROOT / "outputs" / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard written: {out}")


if __name__ == "__main__":
    main()
