"""
Callback functions: the interactivity layer. Each callback watches one or
more Input components and updates one or more Output components whenever
those inputs change.

Step 5 only wires up the KPI cards (as plain numbers) to prove the filter
pipeline works end to end. Step 6 adds callbacks for the actual charts.
"""

from dash import Input, Output, callback, html

from app.queries import get_kpi_summary, get_mrr_by_month, get_churn_by_month
from app.charts import build_mrr_chart, build_churn_chart

GREEN = "#18BC9C"
RED = "#E74C3C"


def _delta_badge(text, is_good):
    """Small colored text, used under each KPI card to show a month-over-month delta."""
    color = GREEN if is_good else RED
    return html.Span(text, style={"color": color, "fontWeight": "600"})


def register_callbacks(app):
    @callback(
        Output("kpi-mrr", "children"),
        Output("kpi-mrr-delta", "children"),
        Output("kpi-churn", "children"),
        Output("kpi-churn-delta", "children"),
        Output("kpi-ltv", "children"),
        Output("kpi-ltv-delta", "children"),
        Output("kpi-customers", "children"),
        Output("kpi-customers-delta", "children"),
        Output("mrr-chart", "figure"),
        Output("churn-chart", "figure"),
        Input("plan-filter", "value"),
    )
    def update_dashboard(selected_plan_ids):
        summary = get_kpi_summary()

        mrr_df = get_mrr_by_month(plan_ids=selected_plan_ids)
        current_mrr = mrr_df["mrr"].iloc[-1] if len(mrr_df) else 0

        mrr_text = f"${current_mrr:,.0f}"
        mrr_delta_pct = summary["mrr_delta_pct"]
        mrr_arrow = "\u2191" if mrr_delta_pct >= 0 else "\u2193"
        mrr_delta_text = _delta_badge(
            f"{mrr_arrow} {abs(mrr_delta_pct):.1f}% vs last month",
            is_good=mrr_delta_pct >= 0,
        )

        churn_text = f"{summary['current_churn_pct']:.1f}%"
        churn_delta_pts = summary["churn_delta_pts"]
        churn_arrow = "\u2191" if churn_delta_pts >= 0 else "\u2193"
        # For churn, a DECREASE is good, so the "good" flag is inverted vs MRR.
        churn_delta_text = _delta_badge(
            f"{churn_arrow} {abs(churn_delta_pts):.1f} pts vs last month",
            is_good=churn_delta_pts < 0,
        )

        ltv_text = f"${summary['avg_ltv']:,.0f}"
        ltv_delta_text = html.Span("across all customers", className="text-muted")

        customers_text = f"{summary['active_customers']:,}"
        net_new = summary["net_new_customers"]
        customers_arrow = "\u2191" if net_new >= 0 else "\u2193"
        customers_delta_text = _delta_badge(
            f"{customers_arrow} {abs(net_new)} net new this month",
            is_good=net_new >= 0,
        )

        mrr_fig = build_mrr_chart(mrr_df)
        churn_df = get_churn_by_month()  # churn isn't plan-filtered (whole-customer event)
        churn_fig = build_churn_chart(churn_df)

        return (
            mrr_text, mrr_delta_text,
            churn_text, churn_delta_text,
            ltv_text, ltv_delta_text,
            customers_text, customers_delta_text,
            mrr_fig, churn_fig,
        )
