import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import callback, dcc, html, Input, Output, State, no_update

from src.database import get_tracked_queries, get_price_summary, get_price_history

dash.register_page(__name__, path="/history", name="Histórico")

layout = dbc.Container([
    html.H4("Histórico de Preços", className="mb-3"),

    dbc.Row([
        dbc.Col([
            dbc.Label("Busca"),
            dbc.Select(id="history-query", options=[], placeholder="Selecione uma busca..."),
        ], width=5),
        dbc.Col([
            dbc.Label("Período"),
            dbc.Select(id="history-days", options=[
                {"label": "7 dias", "value": "7"},
                {"label": "30 dias", "value": "30"},
                {"label": "90 dias", "value": "90"},
                {"label": "180 dias", "value": "180"},
                {"label": "1 ano", "value": "365"},
            ], value="90"),
        ], width=3),
        dbc.Col([
            dbc.Label("\u00a0"),  # spacer
            dbc.Button("Atualizar", id="btn-history", color="primary", className="w-100"),
        ], width=2),
        dbc.Col([
            dbc.Label("\u00a0"),
            dbc.Button("Recarregar buscas", id="btn-reload-queries", color="secondary",
                       outline=True, className="w-100", size="sm"),
        ], width=2),
    ], className="mb-3"),

    dcc.Loading([
        html.Div(id="history-feedback"),

        # Gráfico de evolução
        dcc.Graph(id="history-chart", style={"display": "none"}),

        # Tabela resumo por dia
        html.Div(id="history-table-container"),
    ]),
])


@callback(
    Output("history-query", "options"),
    Input("btn-reload-queries", "n_clicks"),
    Input("history-query", "id"),  # trigger on page load
)
def load_queries(n_clicks, _):
    queries = get_tracked_queries()
    return [{"label": q, "value": q} for q in queries]


@callback(
    Output("history-feedback", "children"),
    Output("history-chart", "figure"),
    Output("history-chart", "style"),
    Output("history-table-container", "children"),
    Input("btn-history", "n_clicks"),
    State("history-query", "value"),
    State("history-days", "value"),
    prevent_initial_call=True,
)
def show_history(n_clicks, query, days):
    if not query:
        return dbc.Alert("Selecione uma busca.", color="warning"), {}, {"display": "none"}, html.Div()

    days = int(days)
    summary = get_price_summary(query, days)

    if not summary:
        return (
            dbc.Alert(f"Sem dados de preço para '{query}' nos últimos {days} dias.", color="info"),
            {}, {"display": "none"}, html.Div(),
        )

    df = pd.DataFrame(summary)
    df["date"] = pd.to_datetime(df["date"])

    # Gráfico de evolução
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["avg_price"], mode="lines+markers",
        name="Preço Médio", line=dict(color="#0f3460", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["min_price"], mode="lines",
        name="Mínimo", line=dict(color="#28a745", width=1, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["max_price"], mode="lines",
        name="Máximo", line=dict(color="#dc3545", width=1, dash="dash"),
    ))
    fig.update_layout(
        title=f"Evolução de Preços — {query}",
        xaxis_title="Data", yaxis_title="Preço (R$)",
        height=400, margin=dict(t=40, b=30),
        yaxis_tickprefix="R$ ",
        hovermode="x unified",
    )

    feedback = dbc.Alert(
        f"{len(summary)} dias com dados · {df['count'].sum():.0f} registros no período",
        color="success",
    )

    # Tabela resumo
    table_df = df.copy()
    table_df["date"] = table_df["date"].dt.strftime("%d/%m/%Y")
    table_df = table_df.rename(columns={
        "date": "Data", "count": "Anúncios",
        "avg_price": "Média", "min_price": "Mínimo", "max_price": "Máximo",
    })
    for col in ["Média", "Mínimo", "Máximo"]:
        table_df[col] = table_df[col].apply(lambda x: f"R$ {x:,.2f}")

    rows = [html.Tr([html.Td(row[c]) for c in table_df.columns]) for _, row in table_df.iterrows()]
    table = dbc.Table([
        html.Thead(html.Tr([html.Th(c) for c in table_df.columns])),
        html.Tbody(rows),
    ], bordered=True, hover=True, responsive=True, size="sm", striped=True)

    return feedback, fig, {}, table
