import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import callback, dcc, html, dash_table, Input, Output, State, no_update

from src.ml_api import MLClient
from src.async_helper import run_async
from components.cards import metric_card

dash.register_page(__name__, path="/search", name="Busca")

layout = dbc.Container([
    html.H4("Busca de Produtos", className="mb-3"),

    # Search bar
    dbc.Row([
        dbc.Col(dbc.Input(id="search-input", placeholder="Ex: memoria 16GB DDR4 ECC RDIMM servidor", type="text"), width=9),
        dbc.Col(dbc.Button("Buscar", id="btn-search", color="primary", className="w-100"), width=3),
    ], className="mb-3"),

    # Filtros
    dbc.Row([
        dbc.Col([
            dbc.Label("Status", size="sm"),
            dbc.Select(id="search-status", options=[
                {"label": "Todos", "value": "all"},
                {"label": "Ativos", "value": "active"},
                {"label": "Inativos", "value": "inactive"},
            ], value="all"),
        ], width=3),
        dbc.Col([
            dbc.Label("Por página", size="sm"),
            dbc.Select(id="search-per-page", options=[
                {"label": "10", "value": "10"},
                {"label": "25", "value": "25"},
                {"label": "50", "value": "50"},
            ], value="25"),
        ], width=3),
    ], className="mb-3"),

    # Loading wrapper
    dcc.Loading(id="search-loading", type="default", children=[
        # Feedback
        html.Div(id="search-feedback"),

        # Métricas
        dbc.Row(id="search-metrics", className="mb-3"),

        # Gráfico
        dcc.Graph(id="search-chart", style={"display": "none"}),

        # Tabela
        dash_table.DataTable(
            id="search-table",
            data=[],
            columns=[],
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "14px"},
            style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_size=25,
            style_data_conditional=[
                {"if": {"column_id": "Preço"}, "textAlign": "right", "fontFamily": "monospace"},
            ],
            style_table={"overflowX": "auto"},
            markdown_options={"html": True},
        ),
    ]),
])


@callback(
    Output("search-feedback", "children"),
    Output("search-metrics", "children"),
    Output("search-chart", "figure"),
    Output("search-chart", "style"),
    Output("search-table", "data"),
    Output("search-table", "columns"),
    Output("search-table", "page_size"),
    Output("store-search-results", "data"),
    Input("btn-search", "n_clicks"),
    State("search-input", "value"),
    State("search-status", "value"),
    State("search-per-page", "value"),
    prevent_initial_call=True,
)
def do_search(n_clicks, query, status, per_page):
    if not query:
        return (
            dbc.Alert("Digite um termo de busca.", color="warning"),
            [], {}, {"display": "none"}, [], [], 25, no_update,
        )

    per_page = int(per_page)
    ml = MLClient()
    data = run_async(ml.search(query, limit=per_page, status=status))

    if not data or "error" in data:
        detail = data.get("detail", data.get("error", "")) if data else "Sem resposta"
        return (
            dbc.Alert(f"Erro: {detail}", color="danger"),
            [], {}, {"display": "none"}, [], [], per_page, no_update,
        )

    results = data.get("results", [])
    total = data.get("paging", {}).get("total", 0)

    if not results:
        return (
            dbc.Alert("Nenhum resultado encontrado.", color="info"),
            [], {}, {"display": "none"}, [], [], per_page, no_update,
        )

    # Feedback
    feedback = dbc.Alert(f"{total:,} produtos no catálogo · {len(results)} anúncios encontrados", color="success")

    # Métricas
    prices = [r["price"] for r in results if r.get("price")]
    metrics = []
    if prices:
        metrics = [
            dbc.Col(metric_card("Menor", f"R$ {min(prices):,.2f}", "card-min"), width=3),
            dbc.Col(metric_card("Maior", f"R$ {max(prices):,.2f}", "card-max"), width=3),
            dbc.Col(metric_card("Média", f"R$ {sum(prices)/len(prices):,.2f}", "card-avg"), width=3),
            dbc.Col(metric_card("Mediana", f"R$ {sorted(prices)[len(prices)//2]:,.2f}", "card-med"), width=3),
        ]

    # Gráfico
    if prices:
        fig = px.histogram(x=prices, nbins=20, labels={"x": "Preço (R$)", "y": "Qtd"},
                           title="Distribuição de Preços", color_discrete_sequence=["#0f3460"])
        fig.update_layout(showlegend=False, height=300, margin=dict(t=40, b=30))
        chart_style = {}
    else:
        fig = {}
        chart_style = {"display": "none"}

    # Tabela
    status_icons = {"active": "🟢", "inactive": "🔴", "catalog_only": "📦"}
    df = pd.DataFrame([{
        "Status": status_icons.get(r.get("status", ""), "❓"),
        "Título": r.get("title", ""),
        "Preço": f"R$ {r['price']:,.2f}" if r.get("price") else "—",
        "Marca": r.get("brand", ""),
        "Modelo": r.get("model", ""),
        "Frete": "✅" if r.get("shipping", {}).get("free_shipping") else "❌",
        "Link": f"[ver]({r.get('permalink', '')})" if r.get("permalink") else "",
    } for r in results])

    columns = [
        {"name": c, "id": c, "presentation": "markdown" if c == "Link" else "input"}
        for c in df.columns
    ]

    return feedback, metrics, fig, chart_style, df.to_dict("records"), columns, per_page, results
