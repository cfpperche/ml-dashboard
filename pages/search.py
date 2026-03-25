import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import callback, dcc, html, dash_table, Input, Output, State, no_update, ctx, ALL

from src.ml_api import MLClient
from src.async_helper import run_async
from src.database import create_competitor, get_competitors
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
        html.Div(id="search-feedback"),
        dbc.Row(id="search-metrics", className="mb-3"),
        dcc.Graph(id="search-chart", style={"display": "none"}),
        html.Div(id="search-results-container"),
    ]),

    # Store para resultados raw
    dcc.Store(id="search-raw-results"),

    # Feedback de ação
    html.Div(id="search-action-feedback"),
])


def _build_results_table(results: list) -> html.Div:
    """Constrói tabela HTML com botão de ação por linha."""
    if not results:
        return html.Div()

    # Pegar seller_ids já cadastrados
    existing = {c["seller_id"] for c in get_competitors(active_only=False) if c["seller_id"]}

    status_icons = {"active": "🟢", "inactive": "🔴", "catalog_only": "📦"}
    rows = []
    for i, r in enumerate(results):
        seller_id = str(r.get("seller", {}).get("id", ""))
        seller_nick = r.get("seller", {}).get("nickname", "")
        already_added = seller_id in existing

        action_btn = html.Td(
            dbc.Button(
                "Já cadastrado" if already_added else "+ Concorrente",
                id={"type": "btn-add-seller", "index": i},
                color="secondary" if already_added else "success",
                size="sm", outline=True,
                disabled=already_added or not seller_id,
            )
        )

        rows.append(html.Tr([
            html.Td(status_icons.get(r.get("status", ""), "❓")),
            html.Td(r.get("title", "")[:60]),
            html.Td(f"R$ {r['price']:,.2f}" if r.get("price") else "—",
                     style={"textAlign": "right", "fontFamily": "monospace"}),
            html.Td(r.get("brand", "")),
            html.Td(r.get("model", "")),
            html.Td(seller_id or "—"),
            html.Td(seller_nick or "—"),
            html.Td("✅" if r.get("shipping", {}).get("free_shipping") else "❌"),
            html.Td(html.A("ver", href=r.get("permalink", "#"), target="_blank")
                     if r.get("permalink") else ""),
            action_btn,
        ]))

    return dbc.Table([
        html.Thead(html.Tr([
            html.Th(""), html.Th("Título"), html.Th("Preço"),
            html.Th("Marca"), html.Th("Modelo"),
            html.Th("Seller ID"), html.Th("Vendedor"),
            html.Th("Frete"), html.Th("Link"), html.Th("Ação"),
        ])),
        html.Tbody(rows),
    ], bordered=True, hover=True, responsive=True, size="sm", striped=True)


@callback(
    Output("search-feedback", "children"),
    Output("search-metrics", "children"),
    Output("search-chart", "figure"),
    Output("search-chart", "style"),
    Output("search-results-container", "children"),
    Output("search-raw-results", "data"),
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
            [], {}, {"display": "none"}, html.Div(), no_update, no_update,
        )

    per_page = int(per_page)
    ml = MLClient()
    data = run_async(ml.search(query, limit=per_page, status=status))

    if not data or "error" in data:
        detail = data.get("detail", data.get("error", "")) if data else "Sem resposta"
        return (
            dbc.Alert(f"Erro: {detail}", color="danger"),
            [], {}, {"display": "none"}, html.Div(), no_update, no_update,
        )

    results = data.get("results", [])
    total = data.get("paging", {}).get("total", 0)

    if not results:
        return (
            dbc.Alert("Nenhum resultado encontrado.", color="info"),
            [], {}, {"display": "none"}, html.Div(), no_update, no_update,
        )

    feedback = dbc.Alert(f"{total:,} produtos no catálogo · {len(results)} anúncios encontrados", color="success")

    prices = [r["price"] for r in results if r.get("price")]
    metrics = []
    if prices:
        metrics = [
            dbc.Col(metric_card("Menor", f"R$ {min(prices):,.2f}", "card-min"), width=3),
            dbc.Col(metric_card("Maior", f"R$ {max(prices):,.2f}", "card-max"), width=3),
            dbc.Col(metric_card("Média", f"R$ {sum(prices)/len(prices):,.2f}", "card-avg"), width=3),
            dbc.Col(metric_card("Mediana", f"R$ {sorted(prices)[len(prices)//2]:,.2f}", "card-med"), width=3),
        ]

    if prices:
        fig = px.histogram(x=prices, nbins=20, labels={"x": "Preço (R$)", "y": "Qtd"},
                           title="Distribuição de Preços", color_discrete_sequence=["#0f3460"])
        fig.update_layout(showlegend=False, height=300, margin=dict(t=40, b=30))
        chart_style = {}
    else:
        fig = {}
        chart_style = {"display": "none"}

    table = _build_results_table(results)
    return feedback, metrics, fig, chart_style, table, results, results


@callback(
    Output("search-action-feedback", "children"),
    Output("search-results-container", "children", allow_duplicate=True),
    Input({"type": "btn-add-seller", "index": ALL}, "n_clicks"),
    State("search-raw-results", "data"),
    prevent_initial_call=True,
)
def add_seller_as_competitor(n_clicks_list, results):
    if not any(n_clicks_list) or not results:
        return no_update, no_update

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update

    idx = triggered["index"]
    if idx >= len(results):
        return no_update, no_update

    item = results[idx]
    seller_id = str(item.get("seller", {}).get("id", ""))
    seller_nick = item.get("seller", {}).get("nickname", "")

    if not seller_id:
        return dbc.Alert("Seller ID não disponível.", color="warning"), no_update

    # Verifica se já existe
    existing = {c["seller_id"] for c in get_competitors(active_only=False) if c["seller_id"]}
    if seller_id in existing:
        return dbc.Alert("Concorrente já cadastrado.", color="info"), no_update

    create_competitor(
        nickname=seller_nick,
        seller_id=seller_id,
        name=seller_nick or f"Seller {seller_id}",
    )

    # Rebuild table para atualizar botões
    table = _build_results_table(results)
    return (
        dbc.Alert(f"Concorrente adicionado: {seller_nick or seller_id}", color="success"),
        table,
    )
