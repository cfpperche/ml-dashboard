import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import callback, dcc, html, dash_table, Input, Output, State, no_update, ctx, ALL

from src.ml_api import MLClient
from src.async_helper import run_async
from src.database import (
    get_competitors, get_competitor, create_competitor,
    update_competitor, delete_competitor,
)

dash.register_page(__name__, path="/competitors", name="Concorrentes")


def _reputation_badge(level: str, power: str) -> str:
    """Retorna emoji para nível de reputação."""
    badges = {
        "5_green": "🟢 Excelente",
        "4_light_green": "🟡 Boa",
        "3_yellow": "🟠 Regular",
        "2_orange": "🔴 Ruim",
        "1_red": "⛔ Muito ruim",
    }
    rep = badges.get(level, level or "—")
    if power:
        ps = {"platinum": "💎", "gold": "🥇", "silver": "🥈"}.get(power, "")
        rep += f" {ps} {power.title()}"
    return rep


def _competitors_table():
    """Gera a tabela de concorrentes do banco."""
    comps = get_competitors(active_only=False)
    if not comps:
        return html.P("Nenhum concorrente cadastrado.", className="text-muted")

    rows = []
    for c in comps:
        status = "🟢" if c["active"] else "🔴"
        rep = _reputation_badge(c.get("reputation_level", ""), c.get("power_seller", ""))
        transactions = c.get("total_transactions", 0)
        tx_str = f"{transactions:,}" if transactions else "—"

        rows.append(html.Tr([
            html.Td(status),
            html.Td(c["name"] or "—"),
            html.Td(c["nickname"] or "—"),
            html.Td(c["seller_id"] or "—"),
            html.Td(rep),
            html.Td(tx_str, style={"textAlign": "right"}),
            html.Td(c["notes"] or "—"),
            html.Td([
                dbc.ButtonGroup([
                    dbc.Button("Editar", id={"type": "btn-edit-comp", "index": c["id"]},
                               color="secondary", size="sm", outline=True),
                    dbc.Button("Excluir", id={"type": "btn-del-comp", "index": c["id"]},
                               color="danger", size="sm", outline=True),
                ], size="sm"),
            ]),
        ]))

    return dbc.Table([
        html.Thead(html.Tr([
            html.Th(""), html.Th("Nome"), html.Th("Nickname"),
            html.Th("Seller ID"), html.Th("Reputação"), html.Th("Vendas"),
            html.Th("Notas"), html.Th("Ações"),
        ])),
        html.Tbody(rows),
    ], bordered=True, hover=True, responsive=True, size="sm")


layout = dbc.Container([
    html.H4("Concorrentes", className="mb-3"),

    # ── CRUD ──
    dbc.Card(dbc.CardBody([
        html.H5("Cadastrar Concorrente", className="mb-3"),
        dbc.Row([
            dbc.Col(dbc.Input(id="comp-name", placeholder="Nome (ex: Eletrocheap)"), width=3),
            dbc.Col(dbc.Input(id="comp-nickname", placeholder="Nickname ML"), width=3),
            dbc.Col(dbc.Input(id="comp-seller-id", placeholder="Seller ID"), width=2),
            dbc.Col(dbc.Input(id="comp-notes", placeholder="Notas"), width=2),
            dbc.Col(dbc.Button("Adicionar", id="btn-add-comp", color="primary", className="w-100"), width=2),
        ]),
    ]), className="mb-3"),

    # Modal de edição
    dbc.Modal([
        dbc.ModalHeader("Editar Concorrente"),
        dbc.ModalBody([
            dcc.Store(id="edit-comp-id"),
            dbc.Label("Nome"), dbc.Input(id="edit-comp-name", className="mb-2"),
            dbc.Label("Nickname"), dbc.Input(id="edit-comp-nickname", className="mb-2"),
            dbc.Label("Seller ID"), dbc.Input(id="edit-comp-seller-id", className="mb-2"),
            dbc.Label("Notas"), dbc.Input(id="edit-comp-notes", className="mb-2"),
            dbc.Label("Ativo"),
            dbc.Switch(id="edit-comp-active", value=True, className="mb-2"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Salvar", id="btn-save-edit-comp", color="primary"),
            dbc.Button("Cancelar", id="btn-cancel-edit-comp", color="secondary"),
        ]),
    ], id="modal-edit-comp", is_open=False),

    # Tabela de concorrentes
    html.Div(id="comp-table-container", children=_competitors_table()),
    html.Div(id="comp-crud-feedback"),

    # Ações em massa
    dbc.Row([
        dbc.Col(dbc.Button("Atualizar Perfis", id="btn-update-profiles", color="info",
                           outline=True, size="sm"), width="auto"),
        dbc.Col(dbc.Button("Analisar Todos", id="btn-analyze-comp", color="primary",
                           size="sm"), width="auto"),
    ], className="mt-2 mb-3 g-2"),

    html.Div(id="comp-profile-feedback"),

    html.Hr(),

    # ── ANÁLISE ──
    dcc.Loading(id="comp-loading", type="default", children=[
        html.Div(id="comp-feedback"),
        dcc.Graph(id="comp-chart-bar", style={"display": "none"}),
        dcc.Graph(id="comp-chart-box", style={"display": "none"}),
        dash_table.DataTable(
            id="comp-results-table",
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


# ── CRUD Callbacks ──

@callback(
    Output("comp-table-container", "children", allow_duplicate=True),
    Output("comp-crud-feedback", "children", allow_duplicate=True),
    Output("comp-name", "value"),
    Output("comp-nickname", "value"),
    Output("comp-seller-id", "value"),
    Output("comp-notes", "value"),
    Input("btn-add-comp", "n_clicks"),
    State("comp-name", "value"),
    State("comp-nickname", "value"),
    State("comp-seller-id", "value"),
    State("comp-notes", "value"),
    prevent_initial_call=True,
)
def add_competitor(n_clicks, name, nickname, seller_id, notes):
    if not name and not nickname and not seller_id:
        return no_update, dbc.Alert("Preencha pelo menos nome, nickname ou seller ID.", color="warning"), no_update, no_update, no_update, no_update
    create_competitor(nickname=nickname or "", seller_id=seller_id or "",
                      name=name or "", notes=notes or "")
    return _competitors_table(), dbc.Alert("Concorrente adicionado!", color="success"), "", "", "", ""


@callback(
    Output("comp-table-container", "children", allow_duplicate=True),
    Output("comp-crud-feedback", "children", allow_duplicate=True),
    Input({"type": "btn-del-comp", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def del_competitor(n_clicks_list):
    if not any(n_clicks_list):
        return no_update, no_update
    triggered = ctx.triggered_id
    if triggered and isinstance(triggered, dict):
        comp_id = triggered["index"]
        delete_competitor(comp_id)
        return _competitors_table(), dbc.Alert("Concorrente excluído.", color="info")
    return no_update, no_update


@callback(
    Output("modal-edit-comp", "is_open"),
    Output("edit-comp-id", "data"),
    Output("edit-comp-name", "value"),
    Output("edit-comp-nickname", "value"),
    Output("edit-comp-seller-id", "value"),
    Output("edit-comp-notes", "value"),
    Output("edit-comp-active", "value"),
    Input({"type": "btn-edit-comp", "index": ALL}, "n_clicks"),
    Input("btn-cancel-edit-comp", "n_clicks"),
    prevent_initial_call=True,
)
def open_edit_modal(edit_clicks, cancel_click):
    trigger = ctx.triggered_id
    if trigger == "btn-cancel-edit-comp":
        return False, None, "", "", "", "", True
    if isinstance(trigger, dict) and any(edit_clicks):
        comp_id = trigger["index"]
        c = get_competitor(comp_id)
        if c:
            return True, c["id"], c["name"] or "", c["nickname"] or "", c["seller_id"] or "", c["notes"] or "", bool(c["active"])
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update


@callback(
    Output("modal-edit-comp", "is_open", allow_duplicate=True),
    Output("comp-table-container", "children", allow_duplicate=True),
    Output("comp-crud-feedback", "children"),
    Input("btn-save-edit-comp", "n_clicks"),
    State("edit-comp-id", "data"),
    State("edit-comp-name", "value"),
    State("edit-comp-nickname", "value"),
    State("edit-comp-seller-id", "value"),
    State("edit-comp-notes", "value"),
    State("edit-comp-active", "value"),
    prevent_initial_call=True,
)
def save_edit(n_clicks, comp_id, name, nickname, seller_id, notes, active):
    if not comp_id:
        return no_update, no_update, no_update
    update_competitor(comp_id, name=name, nickname=nickname,
                      seller_id=seller_id, notes=notes, active=1 if active else 0)
    return False, _competitors_table(), dbc.Alert("Concorrente atualizado!", color="success")


# ── Atualizar Perfis ──

@callback(
    Output("comp-profile-feedback", "children"),
    Output("comp-table-container", "children", allow_duplicate=True),
    Input("btn-update-profiles", "n_clicks"),
    prevent_initial_call=True,
)
def update_profiles(n_clicks):
    comps = get_competitors(active_only=False)
    comps_with_id = [c for c in comps if c.get("seller_id")]
    if not comps_with_id:
        return dbc.Alert("Nenhum concorrente com Seller ID cadastrado.", color="warning"), no_update

    ml = MLClient()
    updated = 0
    for c in comps_with_id:
        user_data = run_async(ml.get_user(c["seller_id"]))
        if user_data and "error" not in user_data:
            rep = user_data.get("seller_reputation", {})
            update_competitor(
                c["id"],
                nickname=user_data.get("nickname", c["nickname"]) or c["nickname"],
                reputation_level=rep.get("level_id", ""),
                power_seller=rep.get("power_seller_status", "") or "",
                total_transactions=rep.get("transactions", {}).get("total", 0) or 0,
                permalink=user_data.get("permalink", ""),
                profile_updated_at="CURRENT_TIMESTAMP",
            )
            updated += 1

    return (
        dbc.Alert(f"{updated} perfis atualizados de {len(comps_with_id)} concorrentes.", color="success"),
        _competitors_table(),
    )


# ── Análise Callback ──

@callback(
    Output("comp-feedback", "children"),
    Output("comp-chart-bar", "figure"),
    Output("comp-chart-bar", "style"),
    Output("comp-chart-box", "figure"),
    Output("comp-chart-box", "style"),
    Output("comp-results-table", "data"),
    Output("comp-results-table", "columns"),
    Output("store-competitor-results", "data"),
    Input("btn-analyze-comp", "n_clicks"),
    prevent_initial_call=True,
)
def analyze_competitors(n_clicks):
    comps = get_competitors(active_only=True)
    if not comps:
        return (
            dbc.Alert("Cadastre concorrentes primeiro.", color="warning"),
            {}, {"display": "none"}, {}, {"display": "none"}, [], [], no_update,
        )

    ml = MLClient()
    all_prods = []

    for c in comps:
        label = c["name"] or c["nickname"] or f"ID:{c['seller_id']}"
        if c["nickname"]:
            data = run_async(ml.search_seller(nickname=c["nickname"]))
        elif c["seller_id"]:
            data = run_async(ml.search_seller(seller_id=c["seller_id"]))
        else:
            continue
        if data and "results" in data:
            for item in data["results"]:
                item["_seller_nick"] = label
            all_prods.extend(data["results"])

    if not all_prods:
        return (
            dbc.Alert("Nenhum produto encontrado. A busca por vendedor pode estar bloqueada pela API.", color="warning"),
            {}, {"display": "none"}, {}, {"display": "none"}, [], [], [],
        )

    feedback = dbc.Alert(f"{len(all_prods)} produtos de {len(comps)} concorrentes", color="success")

    df = pd.DataFrame([{
        "Vendedor": p.get("_seller_nick", "?"),
        "Título": p.get("title", ""),
        "Preço": p.get("price", 0),
        "Frete Grátis": p.get("shipping", {}).get("free_shipping", False),
    } for p in all_prods])

    fig_bar = px.bar(
        df.groupby("Vendedor").size().reset_index(name="Qtd"),
        x="Vendedor", y="Qtd", title="Anúncios por Concorrente", color="Vendedor",
    )
    fig_bar.update_layout(height=300, margin=dict(t=40, b=30))

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
