import json
import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import callback, dcc, html, Input, Output, State, no_update

dash.register_page(__name__, path="/export", name="Exportar")

layout = dbc.Container([
    html.H4("Exportar Dados", className="mb-3"),

    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Busca"),
            html.P("Exportar resultados da última busca.", className="text-muted"),
            dbc.Button("Excel (Busca)", id="btn-export-search", color="primary", outline=True),
        ])), width=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Concorrentes"),
            html.P("Exportar dados de concorrentes.", className="text-muted"),
            dbc.Button("Excel (Concorrentes)", id="btn-export-comp", color="primary", outline=True),
        ])), width=4),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("Insights IA"),
            html.P("Exportar análises em JSON.", className="text-muted"),
            dbc.Button("JSON (Insights)", id="btn-export-insights", color="primary", outline=True),
        ])), width=4),
    ]),

    html.Div(id="export-feedback", className="mt-3"),
])


@callback(
    Output("download-search-excel", "data"),
    Input("btn-export-search", "n_clicks"),
    State("store-search-results", "data"),
    prevent_initial_call=True,
)
def export_search(n_clicks, data):
    if not data:
        return no_update
    df = pd.DataFrame([{
        "Título": r.get("title", ""), "Preço": r.get("price", 0),
        "Marca": r.get("brand", ""), "Modelo": r.get("model", ""),
        "Item ID": r.get("id", ""), "Link": r.get("permalink", ""),
    } for r in data])
    return dcc.send_data_frame(df.to_excel, "ml_busca.xlsx", index=False)


@callback(
    Output("download-competitors-excel", "data"),
    Input("btn-export-comp", "n_clicks"),
    State("store-competitor-results", "data"),
    prevent_initial_call=True,
)
def export_competitors(n_clicks, data):
    if not data:
        return no_update
    df = pd.DataFrame([{
        "Vendedor": p.get("_seller_nick", "?"), "Título": p.get("title", ""),
        "Preço": p.get("price", 0), "Item ID": p.get("id", ""),
    } for p in data])
    return dcc.send_data_frame(df.to_excel, "ml_concorrentes.xlsx", index=False)


@callback(
    Output("download-insights-json", "data"),
    Input("btn-export-insights", "n_clicks"),
    State("store-analyses", "data"),
    prevent_initial_call=True,
)
def export_insights(n_clicks, data):
    if not data:
        return no_update
    return dict(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        filename="ml_insights.json",
    )
