import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import callback, dcc, html, dash_table, Input, Output, State, no_update, ctx, ALL

from src.ml_api import MLClient
from src.async_helper import run_async
from src.database import create_competitor, get_competitors, save_search_results
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

    # Paginação
    dbc.Row([
        dbc.Col(dbc.Button("⬅️ Anterior", id="btn-prev-page", color="secondary", size="sm", outline=True), width="auto"),
        dbc.Col(html.Span(id="search-page-info", className="text-muted small align-self-center"), width="auto"),
        dbc.Col(dbc.Button("Próxima ➡️", id="btn-next-page", color="secondary", size="sm", outline=True), width="auto"),
    ], className="mt-2 mb-3 g-2", justify="center", align="center"),

    # Store para resultados raw e página
    dcc.Store(id="search-raw-results"),
    dcc.Store(id="search-current-page", data=0),

    # Feedback de ação
    html.Div(id="search-action-feedback"),
])


PAGE_SIZE = 25


def _build_results_table(results: list, page: int = 0) -> html.Div:
    """Constrói tabela HTML paginada com botão de ação por linha."""
    if not results:
        return html.Div()

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_results = results[start:end]

    existing = {c["seller_id"] for c in get_competitors(active_only=False) if c["seller_id"]}
    status_icons = {"active": "🟢", "inactive": "🔴", "catalog_only": "📦"}

    rows = []
    for i, r in enumerate(page_results):
        real_idx = start + i
        seller_id = str(r.get("seller", {}).get("id", ""))
        seller_nick = r.get("seller", {}).get("nickname", "")
        already_added = seller_id in existing

        action_btn = html.Td(
            dbc.Button(
                "Já cadastrado" if already_added else "+ Concorrente",
                id={"type": "btn-add-seller", "index": real_idx},
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
    Output("search-page-info", "children"),
    Output("btn-prev-page", "disabled"),
    Output("btn-next-page", "disabled"),
    Output("search-raw-results", "data"),
    Output("search-current-page", "data"),
    Output("store-search-results", "data"),
    Input("btn-search", "n_clicks"),
    State("search-input", "value"),
    State("search-status", "value"),
    State("search-per-page", "value"),
    prevent_initial_call=True,
)
def do_search(n_clicks, query, status, per_page):
    empty = (no_update,) * 11
    if not query:
        return (
            dbc.Alert("Digite um termo de busca.", color="warning"),
            [], {}, {"display": "none"}, html.Div(), "", True, True,
            no_update, 0, no_update,
        )

    per_page = int(per_page)
    ml = MLClient()
    data = run_async(ml.search(query, limit=per_page, status=status))

    if not data or "error" in data:
        detail = data.get("detail", data.get("error", "")) if data else "Sem resposta"
        return (
            dbc.Alert(f"Erro: {detail}", color="danger"),
            [], {}, {"display": "none"}, html.Div(), "", True, True,
            no_update, 0, no_update,
        )

    results = data.get("results", [])
    total = data.get("paging", {}).get("total", 0)

    if not results:
        return (
            dbc.Alert("Nenhum resultado encontrado.", color="info"),
            [], {}, {"display": "none"}, html.Div(), "", True, True,
            no_update, 0, no_update,
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

    # Salvar no histórico
    save_search_results(query, results)

    total_pages = max(1, (len(results) + PAGE_SIZE - 1) // PAGE_SIZE)
    page_info = f"Página 1 de {total_pages}"
    table = _build_results_table(results, page=0)
    return (feedback, metrics, fig, chart_style, table, page_info,
            True, total_pages <= 1, results, 0, results)


@callback(
    Output("search-results-container", "children", allow_duplicate=True),
    Output("search-page-info", "children", allow_duplicate=True),
    Output("btn-prev-page", "disabled", allow_duplicate=True),
    Output("btn-next-page", "disabled", allow_duplicate=True),
    Output("search-current-page", "data", allow_duplicate=True),
    Input("btn-prev-page", "n_clicks"),
    Input("btn-next-page", "n_clicks"),
    State("search-raw-results", "data"),
    State("search-current-page", "data"),
    prevent_initial_call=True,
)
def paginate(prev_clicks, next_clicks, results, current_page):
    if not results:
        return no_update, no_update, True, True, 0

    total_pages = max(1, (len(results) + PAGE_SIZE - 1) // PAGE_SIZE)
    trigger = ctx.triggered_id
    page = current_page or 0

    if trigger == "btn-next-page":
        page = min(page + 1, total_pages - 1)
    elif trigger == "btn-prev-page":
        page = max(page - 1, 0)

    table = _build_results_table(results, page=page)
    page_info = f"Página {page + 1} de {total_pages}"
    return table, page_info, page <= 0, page >= total_pages - 1, page


@callback(
    Output("search-action-feedback", "children"),
    Output("search-results-container", "children", allow_duplicate=True),
    Input({"type": "btn-add-seller", "index": ALL}, "n_clicks"),
    State("search-raw-results", "data"),
    State("search-current-page", "data"),
    prevent_initial_call=True,
)
def add_seller_as_competitor(n_clicks_list, results, current_page):
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

    table = _build_results_table(results, page=current_page or 0)
    return (
        dbc.Alert(f"Concorrente adicionado: {seller_nick or seller_id}", color="success"),
        table,
    )
