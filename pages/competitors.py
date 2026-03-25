import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import callback, dcc, html, dash_table, Input, Output, State, no_update

from src.ml_api import MLClient
from src.async_helper import run_async

dash.register_page(__name__, path="/competitors", name="Concorrentes")

layout = dbc.Container([
    html.H4("Análise de Concorrentes", className="mb-3"),

    dbc.Row([
        dbc.Col([
            dbc.Label("Nicknames (um por linha)"),
            dbc.Textarea(id="comp-nicknames", value="REDDAPPLE1\nELETROCHEAP", rows=4),
        ], width=6),
        dbc.Col([
            dbc.Label("Ou Seller IDs (um por linha)"),
            dbc.Textarea(id="comp-seller-ids", placeholder="Ex: 123456789", rows=4),
        ], width=6),
    ], className="mb-3"),

    dbc.Button("Analisar Concorrentes", id="btn-analyze-comp", color="primary", className="mb-3"),

    dcc.Loading(id="comp-loading", type="default", children=[
        html.Div(id="comp-feedback"),
        dcc.Graph(id="comp-chart-bar", style={"display": "none"}),
        dcc.Graph(id="comp-chart-box", style={"display": "none"}),
        dash_table.DataTable(
            id="comp-table",
            data=[], columns=[],
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "14px"},
            style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_size=25,
            style_table={"overflowX": "auto"},
        ),
    ]),
])


@callback(
    Output("comp-feedback", "children"),
    Output("comp-chart-bar", "figure"),
    Output("comp-chart-bar", "style"),
    Output("comp-chart-box", "figure"),
    Output("comp-chart-box", "style"),
    Output("comp-table", "data"),
    Output("comp-table", "columns"),
    Output("store-competitor-results", "data"),
    Input("btn-analyze-comp", "n_clicks"),
    State("comp-nicknames", "value"),
    State("comp-seller-ids", "value"),
    prevent_initial_call=True,
)
def analyze_competitors(n_clicks, nicknames_text, seller_ids_text):
    nicknames = [n.strip() for n in (nicknames_text or "").split("\n") if n.strip()]
    seller_ids = [s.strip() for s in (seller_ids_text or "").split("\n") if s.strip()]

    if not nicknames and not seller_ids:
        return (
            dbc.Alert("Preencha nicknames ou seller IDs.", color="warning"),
            {}, {"display": "none"}, {}, {"display": "none"}, [], [], no_update,
        )

    ml = MLClient()
    all_prods = []

    for nick in nicknames:
        data = run_async(ml.search_seller(nickname=nick))
        if data and "results" in data:
            for item in data["results"]:
                item["_seller_nick"] = nick
            all_prods.extend(data["results"])

    for sid in seller_ids:
        data = run_async(ml.search_seller(seller_id=sid))
        if data and "results" in data:
            for item in data["results"]:
                item["_seller_nick"] = f"ID:{sid}"
            all_prods.extend(data["results"])

    if not all_prods:
        return (
            dbc.Alert("Nenhum produto encontrado. A busca por vendedor pode estar bloqueada pela API.", color="warning"),
            {}, {"display": "none"}, {}, {"display": "none"}, [], [], [],
        )

    feedback = dbc.Alert(f"{len(all_prods)} produtos de {len(nicknames) + len(seller_ids)} concorrentes", color="success")

    df = pd.DataFrame([{
        "Vendedor": p.get("_seller_nick", "?"),
        "Título": p.get("title", ""),
        "Preço": p.get("price", 0),
        "Frete Grátis": p.get("shipping", {}).get("free_shipping", False),
    } for p in all_prods])

    # Bar chart
    fig_bar = px.bar(
        df.groupby("Vendedor").size().reset_index(name="Qtd"),
        x="Vendedor", y="Qtd", title="Anúncios por Concorrente", color="Vendedor",
    )
    fig_bar.update_layout(height=300, margin=dict(t=40, b=30))

    # Box plot
    df_prices = df[df["Preço"] > 0]
    if not df_prices.empty:
        fig_box = px.box(df_prices, x="Vendedor", y="Preço",
                         title="Faixa de Preço por Concorrente", color="Vendedor")
        fig_box.update_layout(height=300, margin=dict(t=40, b=30))
        box_style = {}
    else:
        fig_box = {}
        box_style = {"display": "none"}

    columns = [{"name": c, "id": c} for c in df.columns]

    return feedback, fig_bar, {}, fig_box, box_style, df.to_dict("records"), columns, all_prods
