"""
Callback functions: the interactivity layer. Each callback watches one or
more Input components and updates one or more Output components whenever
those inputs change.

Step 5 only wires up the KPI cards (as plain numbers) to prove the filter
pipeline works end to end. Step 6 adds callbacks for the actual charts.
"""

from dash import Input, Output, callback

from app.queries import get_kpi_summary, get_mrr_by_month


def register_callbacks(app):
    @callback(
        Output("kpi-mrr", "children"),
        Output("kpi-churn", "children"),
        Output("kpi-ltv", "children"),
        Output("kpi-customers", "children"),
        Input("plan-filter", "value"),
    )
    def update_kpis(selected_plan_ids):
        # KPI cards use whole-business numbers (not plan-filtered) except MRR,
        # which respects the plan filter so you can see e.g. "Enterprise-only MRR".
        summary = get_kpi_summary()

        mrr_df = get_mrr_by_month(plan_ids=selected_plan_ids)
        current_mrr = mrr_df["mrr"].iloc[-1] if len(mrr_df) else 0

        mrr_text = f"${current_mrr:,.0f}"
        churn_text = f"{summary['current_churn_pct']:.1f}%"
        ltv_text = f"${summary['avg_ltv']:,.0f}"
        customers_text = f"{summary['active_customers']:,}"

        return mrr_text, churn_text, ltv_text, customers_text
