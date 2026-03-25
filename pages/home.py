import dash
from dash import html

dash.register_page(__name__, path="/", name="Home")

layout = html.Div([
    html.Meta(httpEquiv="refresh", content="0; url=/search"),
])
