import dash
import dash_bootstrap_components as dbc
from datetime import datetime
from dash import callback, html, Input, Output, State, no_update

from src.auth import (
    get_claude_credentials, sync_claude_token,
    extract_code_from_url, exchange_ml_code,
    refresh_ml_token, load_env, save_env,
    open_ml_auth_in_browser,
)
from src.ml_api import MLClient
from src.async_helper import run_async

dash.register_page(__name__, path="/settings", name="Settings")


def _claude_section():
    creds = get_claude_credentials()
    if creds:
        exp = datetime.fromtimestamp(creds["expires_at"] / 1000)
        return [
            dbc.Alert(f"Token encontrado — plano {creds['subscription']}", color="success"),
            html.P(f"Expira em: {exp:%d/%m/%Y %H:%M}", className="text-muted small"),
            dbc.Button("Sincronizar token do Claude para .env", id="btn-sync-claude", color="secondary", size="sm"),
        ]
    return [
        dbc.Alert("Token Claude não encontrado.", color="warning"),
        html.P("Rode `claude setup-token` no terminal.", className="text-muted"),
        dbc.Button("Verificar novamente", id="btn-sync-claude", color="secondary", size="sm"),
    ]


def _ml_section():
    env = load_env()
    token_ok = env.get("ML_ACCESS_TOKEN", "").startswith("APP_USR-")
    secret_ok = env.get("ML_CLIENT_SECRET", "") not in ("", "SEU_SECRET_KEY")
    return token_ok, secret_ok


def layout():
    token_ok, secret_ok = _ml_section()

    return dbc.Container([
        html.H4("Configuração de Tokens", className="mb-3"),

        # Claude
        html.H5("Claude AI (OAuth)"),
        html.Div(id="claude-status", children=_claude_section()),
        html.Div(id="claude-feedback"),

        html.Hr(),

        # Mercado Livre
        html.H5("Mercado Livre (OAuth)"),
        dbc.Row([
            dbc.Col([
                html.P("Access Token", className="text-muted small mb-0"),
                html.P("Configurado" if token_ok else "Pendente",
                       className="fw-bold fs-5"),
            ], width=4),
            dbc.Col([
                html.P("Client Secret", className="text-muted small mb-0"),
                html.P("Configurado" if secret_ok else "Pendente",
                       className="fw-bold fs-5"),
            ], width=4),
        ], className="mb-3"),

        # Client Secret input (se não tiver)
        html.Div(id="ml-secret-section", children=[
            dbc.InputGroup([
                dbc.Input(id="ml-secret-input", placeholder="ML Client Secret", type="password"),
                dbc.Button("Salvar", id="btn-save-secret", color="secondary"),
            ], className="mb-3"),
        ] if not secret_ok else []),

        # OAuth flow
        html.Div([
            dbc.Button("Autorizar Mercado Livre", id="btn-auth-ml", color="warning", className="mb-2"),
            html.Div(id="ml-auth-section", children=[
                dbc.Input(id="ml-callback-url", placeholder="Cole a URL de callback aqui (contém ?code=TG-...)",
                          className="mb-2"),
                dbc.Button("Trocar code por tokens", id="btn-exchange-ml", color="success", size="sm"),
            ], style={"display": "none"}),
        ] if secret_ok else []),

        html.Div(id="ml-feedback", className="mt-2"),

        # Refresh
        html.Div([
            html.Hr(),
            dbc.Button("Renovar Token (refresh)", id="btn-refresh-ml", color="secondary", size="sm"),
        ] if token_ok else []),

        html.Div(id="ml-refresh-feedback", className="mt-2"),

        # Test connection
        html.Hr(),
        dbc.Button("Testar Conexão ML", id="btn-test-ml", color="info", size="sm"),
        html.Div(id="ml-test-feedback", className="mt-2"),
    ])


# ── Claude callbacks ──

@callback(
    Output("claude-feedback", "children"),
    Input("btn-sync-claude", "n_clicks"),
    prevent_initial_call=True,
)
def sync_claude(n_clicks):
    ok, msg = sync_claude_token()
    return dbc.Alert(msg, color="success" if ok else "danger")


# ── ML callbacks ──

@callback(
    Output("ml-auth-section", "style"),
    Input("btn-auth-ml", "n_clicks"),
    prevent_initial_call=True,
)
def open_auth(n_clicks):
    open_ml_auth_in_browser()
    return {"display": "block"}


@callback(
    Output("ml-feedback", "children"),
    Input("btn-exchange-ml", "n_clicks"),
    State("ml-callback-url", "value"),
    prevent_initial_call=True,
)
def exchange_token(n_clicks, url):
    if not url:
        return dbc.Alert("Cole a URL de callback.", color="warning")
    code = extract_code_from_url(url)
    if not code:
        return dbc.Alert("Parâmetro 'code' não encontrado na URL.", color="danger")
    ok, msg, data = exchange_ml_code(code)
    return dbc.Alert(msg, color="success" if ok else "danger")


@callback(
    Output("ml-refresh-feedback", "children"),
    Input("btn-refresh-ml", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_token(n_clicks):
    ok, msg = refresh_ml_token()
    return dbc.Alert(msg, color="success" if ok else "danger")


@callback(
    Output("ml-test-feedback", "children"),
    Input("btn-test-ml", "n_clicks"),
    prevent_initial_call=True,
)
def test_ml(n_clicks):
    ml = MLClient()
    r = run_async(ml.me())
    if r and "error" not in r:
        return dbc.Alert(f"Conectado: {r.get('nickname', '?')}", color="success")
    return dbc.Alert(f"Erro: {r}", color="danger")


@callback(
    Output("ml-secret-section", "children"),
    Input("btn-save-secret", "n_clicks"),
    State("ml-secret-input", "value"),
    prevent_initial_call=True,
)
def save_secret(n_clicks, secret):
    if not secret:
        return no_update
    save_env("ML_CLIENT_SECRET", secret)
    return [dbc.Alert("Client Secret salvo!", color="success")]
