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


def build_kpi_card(title, value_id, delta_id, subtitle=""):
    return dbc.Card(
        dbc.CardBody(
            [
                html.P(title, className="text-muted mb-1 small text-uppercase"),
                html.H3(id=value_id, children="--", className="mb-1"),
                html.P(id=delta_id, children="", className="small mb-0"),
            ]
        ),
        className="text-center h-100",
    )


def build_kpi_row():
    return dbc.Row(
        [
            dbc.Col(build_kpi_card("Current MRR", "kpi-mrr", "kpi-mrr-delta"), xs=12, sm=6, md=3),
            dbc.Col(build_kpi_card("Churn Rate", "kpi-churn", "kpi-churn-delta"), xs=12, sm=6, md=3),
            dbc.Col(build_kpi_card("Avg LTV", "kpi-ltv", "kpi-ltv-delta"), xs=12, sm=6, md=3),
            dbc.Col(build_kpi_card("Active Customers", "kpi-customers", "kpi-customers-delta"), xs=12, sm=6, md=3),
        ],
        className="mb-2 g-3",
    )


def build_data_note():
    """Small disclosure that the most recent month is partial -- avoids a confusing dip."""
    return html.P(
        "Note: the most recent month is partial, so its MRR/churn delta may look artificially small.",
        className="text-muted small fst-italic mb-4",
    )


def build_charts_row():
    """
    Row containing the two live charts, each wrapped in dcc.Loading so a
    subtle spinner shows while the callback recalculates (e.g. right after
    toggling a plan filter), rather than the chart looking frozen/stale.
    """
    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        html.H6("Monthly Recurring Revenue", className="mb-2"),
                        dcc.Loading(
                            dcc.Graph(id="mrr-chart", config={"displayModeBar": False}),
                            type="dot",
                        ),
                    ],
                    body=True,
                ),
                xs=12, md=6,
            ),
            dbc.Col(
                dbc.Card(
                    [
                        html.H6("Churn Rate", className="mb-2"),
                        dcc.Loading(
                            dcc.Graph(id="churn-chart", config={"displayModeBar": False}),
                            type="dot",
                        ),
                    ],
                    body=True,
                ),
                xs=12, md=6,
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
                            dbc.Col(build_sidebar(), xs=12, md=3),
                            dbc.Col(
                                [
                                    build_kpi_row(),
                                    build_data_note(),
                                    build_charts_row(),
                                ],
                                xs=12, md=9,
                            ),
                        ]
                    ),
                ],
                fluid=True,
            ),
        ]
    )
