"""
Entry point for the SaaS Metrics Dashboard.

Run from the project root:
    python app/main.py

Then open the URL it prints (usually http://127.0.0.1:8050) in your browser.
"""

import dash
import dash_bootstrap_components as dbc

from app.layout import build_layout
from app.callbacks import register_callbacks

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="SaaS Metrics Dashboard",
)

app.layout = build_layout()
register_callbacks(app)

# Exposed for WSGI servers (e.g. gunicorn) if you deploy this later
server = app.server

if __name__ == "__main__":
    app.run(debug=True)
