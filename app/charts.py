"""
Functions that turn query DataFrames (from app/queries.py) into Plotly
Figure objects. Kept separate from layout.py and callbacks.py so chart
styling logic is easy to find and tweak in one place.
"""

import plotly.graph_objects as go

# Matches the Bootstrap "Flatly" theme used in main.py, so charts feel
# like part of the same design instead of a generic default Plotly look.
TEAL = "#18BC9C"
ORANGE = "#F39C12"
GRID_COLOR = "#ecf0f1"

CHART_LAYOUT_DEFAULTS = dict(
    margin=dict(l=40, r=20, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Lato, sans-serif", size=12, color="#2c3e50"),
    hovermode="x unified",
)


def build_mrr_chart(mrr_df):
    """Area chart of MRR over time."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=mrr_df["month"],
            y=mrr_df["mrr"],
            mode="lines",
            line=dict(color=TEAL, width=3),
            fill="tozeroy",
            fillcolor="rgba(24, 188, 156, 0.15)",
            hovertemplate="%{x|%b %Y}<br>MRR: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT_DEFAULTS,
        yaxis=dict(title="MRR ($)", gridcolor=GRID_COLOR, tickprefix="$", tickformat=",.0f"),
        xaxis=dict(title=None, gridcolor=GRID_COLOR),
    )
    return fig


def build_churn_chart(churn_df):
    """Line chart of monthly churn rate over time."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=churn_df["month"],
            y=churn_df["churn_rate_pct"],
            mode="lines+markers",
            line=dict(color=ORANGE, width=3),
            marker=dict(size=5),
            hovertemplate="%{x|%b %Y}<br>Churn rate: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        **CHART_LAYOUT_DEFAULTS,
        yaxis=dict(title="Churn rate (%)", gridcolor=GRID_COLOR, ticksuffix="%"),
        xaxis=dict(title=None, gridcolor=GRID_COLOR),
    )
    return fig
