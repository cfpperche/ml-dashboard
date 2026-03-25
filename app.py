"""
ML Dashboard — Mercado Livre Competitor Intelligence
Rode com: python app.py
"""
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dotenv import load_dotenv

load_dotenv()

from components.navbar import navbar

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="ML Competitor Intelligence",
)

app.layout = dbc.Container([
    # Stores globais
    dcc.Store(id="store-search-results", storage_type="memory"),
    dcc.Store(id="store-competitor-results", storage_type="memory"),
    dcc.Store(id="store-analyses", storage_type="memory", data=[]),

    # Downloads
    dcc.Download(id="download-search-excel"),
    dcc.Download(id="download-competitors-excel"),
    dcc.Download(id="download-insights-json"),

    # Layout
    navbar,
    dash.page_container,

    # Footer
    html.Hr(className="mt-4"),
    html.P("ML Competitor Intelligence v0.2 · Dash + Claude Max + ML API",
           className="text-muted text-center small mb-3"),
], fluid=True)

server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8050)
