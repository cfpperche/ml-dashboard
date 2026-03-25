import dash
import dash_bootstrap_components as dbc
from datetime import datetime
from dash import callback, dcc, html, Input, Output, State, no_update

from src.ai_insights import analyze_with_claude, format_products_for_analysis
from src.async_helper import run_async

dash.register_page(__name__, path="/insights", name="Insights IA")

layout = dbc.Container([
    html.H4("Insights com Claude AI", className="mb-1"),
    html.P("Usa assinatura Claude Max via OAuth", className="text-muted small mb-3"),

    dbc.Row([
        dbc.Col([
            dbc.Label("Fonte de dados"),
            dbc.RadioItems(
                id="insights-source",
                options=[
                    {"label": "Última busca", "value": "search"},
                    {"label": "Concorrentes", "value": "competitors"},
                    {"label": "Prompt livre", "value": "free"},
                ],
                value="search",
                inline=True,
            ),
        ], className="mb-3"),
    ]),

    dbc.Textarea(
        id="insights-prompt",
        value=(
            "Analise os produtos e me dê:\n"
            "1. Top 5 oportunidades de margem\n"
            "2. Faixa de preço ideal por categoria\n"
            "3. Vendedores mais competitivos\n"
            "4. Recomendações estratégicas"
        ),
        rows=5, className="mb-3",
    ),

    dbc.Button("Gerar Insights", id="btn-insights", color="primary", className="mb-3"),

    dcc.Loading(id="insights-loading", type="default", children=[
        html.Div(id="insights-feedback"),
        html.Div(id="insights-response"),
    ]),

    html.Hr(),
    html.H5("Histórico de Análises"),
    html.Div(id="insights-history"),
])


@callback(
    Output("insights-feedback", "children"),
    Output("insights-response", "children"),
    Output("store-analyses", "data"),
    Input("btn-insights", "n_clicks"),
    State("insights-source", "value"),
    State("insights-prompt", "value"),
    State("store-search-results", "data"),
    State("store-competitor-results", "data"),
    State("store-analyses", "data"),
    prevent_initial_call=True,
)
def generate_insights(n_clicks, source, prompt, search_data, comp_data, analyses):
    if source == "search":
        ctx = format_products_for_analysis(search_data or [])
    elif source == "competitors":
        ctx = format_products_for_analysis(comp_data or [])
    else:
        ctx = ""

    if not ctx and source != "free":
        return dbc.Alert("Faça uma busca primeiro.", color="warning"), no_update, no_update

    if not prompt:
        return dbc.Alert("Digite um prompt.", color="warning"), no_update, no_update

    try:
        resp = run_async(analyze_with_claude(prompt, ctx))
    except Exception as e:
        return dbc.Alert(f"Erro: {e}", color="danger"), no_update, no_update

    response_card = dbc.Card(
        dbc.CardBody([
            html.H5("Análise", className="card-title"),
            dcc.Markdown(resp),
        ]),
        className="mb-3",
    )

    analyses = analyses or []
    analyses.append({
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "response": resp,
    })

    return None, response_card, analyses


@callback(
    Output("insights-history", "children"),
    Input("store-analyses", "data"),
)
def update_history(analyses):
    if not analyses:
        return html.P("Nenhuma análise ainda.", className="text-muted")

    items = []
    for a in reversed(analyses):
        items.append(dbc.Accordion(
            dbc.AccordionItem(
                dcc.Markdown(a["response"]),
                title=f"{a['timestamp'][:16]} — {a['prompt'][:60]}...",
            ),
            start_collapsed=True, className="mb-2",
        ))
    return items
