import dash_bootstrap_components as dbc
from dash import html


def metric_card(label: str, value: str, card_id: str = ""):
    return dbc.Card(
        dbc.CardBody([
            html.P(label, className="metric-label mb-1"),
            html.P(value, className="metric-value mb-0"),
        ]),
        className="metric-card",
        id=card_id or f"card-{label}",
    )
