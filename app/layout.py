"""
Defines the visual structure of the dashboard:
  - a top navbar with the project title
  - a sidebar with filters (plan selector)
  - a main content area with KPI cards and placeholder chart slots

No chart-drawing logic lives here -- that's added in Step 6.
This step just gets a real, styled, navigable page on screen.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc

from app.queries import get_plans


def build_navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("SaaS Metrics Dashboard", className="fw-bold"),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        className="mb-4",
    )


def build_sidebar():
    plans_df = get_plans()
    plan_options = [{"label": row.plan_name, "value": row.plan_id} for row in plans_df.itertuples()]

    return dbc.Card(
        [
            html.H5("Filters", className="mb-3"),
            html.Label("Plan", className="fw-semibold"),
            dcc.Checklist(
                id="plan-filter",
                options=plan_options,
                value=[p["value"] for p in plan_options],  # all selected by default
                inputClassName="me-2",
                labelClassName="d-block mb-1",
            ),
        ],
        body=True,
        className="mb-4",
    )


def build_kpi_card(title, value_id, subtitle=""):
    return dbc.Card(
        dbc.CardBody(
            [
                html.P(title, className="text-muted mb-1 small text-uppercase"),
                html.H3(id=value_id, children="--", className="mb-0"),
                html.P(subtitle, className="text-muted small mb-0"),
            ]
        ),
        className="text-center",
    )


def build_kpi_row():
    return dbc.Row(
        [
            dbc.Col(build_kpi_card("Current MRR", "kpi-mrr"), width=3),
            dbc.Col(build_kpi_card("Churn Rate", "kpi-churn"), width=3),
            dbc.Col(build_kpi_card("Avg LTV", "kpi-ltv"), width=3),
            dbc.Col(build_kpi_card("Active Customers", "kpi-customers"), width=3),
        ],
        className="mb-4 g-3",
    )


def build_chart_placeholders():
    """
    Empty bordered boxes where Step 6 will insert dcc.Graph components.
    Having named placeholders now means callbacks can already reference
    these ids before the real charts exist.
    """
    placeholder_style = {
        "height": "320px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "border": "1px dashed #ccc",
        "borderRadius": "8px",
        "color": "#999",
    }
    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(html.Div("MRR chart coming in Step 6", style=placeholder_style), body=True),
                width=6,
            ),
            dbc.Col(
                dbc.Card(html.Div("Churn chart coming in Step 6", style=placeholder_style), body=True),
                width=6,
            ),
        ],
        className="mb-4 g-3",
    )


def build_layout():
    return html.Div(
        [
            build_navbar(),
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(build_sidebar(), width=3),
                            dbc.Col(
                                [
                                    build_kpi_row(),
                                    build_chart_placeholders(),
                                ],
                                width=9,
                            ),
                        ]
                    ),
                ],
                fluid=True,
            ),
        ]
    )
