"""
Autenticação OAuth — Claude + Mercado Livre.
Gerencia tokens, refresh automático, e persistência no .env.
"""
import json
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx
from dotenv import set_key, dotenv_values

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
CLAUDE_CREDS = Path.home() / ".claude" / ".credentials.json"

ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ML_AUTH_BASE = "https://auth.mercadolivre.com.br/authorization"


def _ensure_env():
    if not ENV_PATH.exists():
        ENV_PATH.touch()


def save_env(key: str, value: str):
    """Salva uma chave no .env."""
    _ensure_env()
    set_key(str(ENV_PATH), key, value)


def load_env() -> dict:
    """Lê o .env atual."""
    _ensure_env()
    return dotenv_values(str(ENV_PATH))


def _ml_config() -> dict:
    """Lê configuração ML do .env."""
    env = load_env()
    return {
        "app_id": env.get("ML_APP_ID", ""),
        "client_secret": env.get("ML_CLIENT_SECRET", ""),
        "redirect_uri": env.get("ML_REDIRECT_URI", ""),
        "access_token": env.get("ML_ACCESS_TOKEN", ""),
        "refresh_token": env.get("ML_REFRESH_TOKEN", ""),
    }


# ── CLAUDE ────────────────────────────────────────────

def get_claude_credentials() -> dict | None:
    """Lê credenciais do Claude de ~/.claude/.credentials.json."""
    if not CLAUDE_CREDS.exists():
        return None
    try:
        data = json.loads(CLAUDE_CREDS.read_text())
        oauth = data.get("claudeAiOauth", {})
        if oauth.get("accessToken"):
            return {
                "access_token": oauth["accessToken"],
                "refresh_token": oauth.get("refreshToken", ""),
                "expires_at": oauth.get("expiresAt", 0),
                "subscription": oauth.get("subscriptionType", ""),
            }
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def sync_claude_token() -> tuple[bool, str]:
    """Sincroniza o token do Claude de ~/.claude/.credentials.json para o .env."""
    creds = get_claude_credentials()
    if creds and creds["access_token"]:
        save_env("CLAUDE_CODE_OAUTH_TOKEN", creds["access_token"])
        return True, f"Token sincronizado (plano: {creds['subscription']})"
    return False, "Token não encontrado em ~/.claude/.credentials.json"


def run_claude_setup_token() -> tuple[bool, str]:
    """Roda 'claude setup-token' como subprocesso."""
    try:
        result = subprocess.run(
            ["claude", "setup-token"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return sync_claude_token()
        return False, f"Erro: {result.stderr[:200]}"
    except FileNotFoundError:
        return False, "CLI 'claude' não encontrado. Instale: npm install -g @anthropic-ai/claude-code"
    except subprocess.TimeoutExpired:
        return False, "Timeout — setup-token demorou mais de 2 min"


# ── MERCADO LIVRE ─────────────────────────────────────

def get_ml_auth_url() -> str:
    """Retorna a URL de autorização do Mercado Livre."""
    cfg = _ml_config()
    return (
        f"{ML_AUTH_BASE}?response_type=code"
        f"&client_id={cfg['app_id']}"
        f"&redirect_uri={cfg['redirect_uri']}"
    )


def is_localhost_redirect() -> bool:
    """Verifica se o redirect URI é localhost (permite captura automática)."""
    cfg = _ml_config()
    parsed = urlparse(cfg["redirect_uri"])
    return parsed.hostname in ("localhost", "127.0.0.1")


def get_localhost_port() -> int:
    """Extrai a porta do redirect URI localhost."""
    cfg = _ml_config()
    parsed = urlparse(cfg["redirect_uri"])
    return parsed.port or 80


class _CallbackHandler(BaseHTTPRequestHandler):
    """Servidor HTTP local para capturar o callback OAuth do ML."""
    auth_code = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            _CallbackHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                "<h2>Autorizado com sucesso!</h2>"
                "<p>Pode fechar esta aba e voltar ao dashboard.</p>"
                "</body></html>".encode()
            )
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Erro: parametro 'code' nao recebido")

    def log_message(self, format, *args):
        pass


def start_callback_server() -> HTTPServer:
    """Inicia servidor local para capturar o callback OAuth."""
    _CallbackHandler.auth_code = None
    port = get_localhost_port()
    server = HTTPServer(("localhost", port), _CallbackHandler)
    server.timeout = 120
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    return server


def get_captured_code() -> str | None:
    """Retorna o code capturado pelo callback server."""
    return _CallbackHandler.auth_code


def extract_code_from_url(url: str) -> str | None:
    """Extrai o parâmetro 'code' de uma URL de callback."""
    try:
        query = parse_qs(urlparse(url).query)
        return query.get("code", [None])[0]
    except Exception:
        return None


def exchange_ml_code(code: str) -> tuple[bool, str, dict]:
    """Troca authorization code por access_token + refresh_token."""
    cfg = _ml_config()
    resp = httpx.post(ML_TOKEN_URL, json={
        "grant_type": "authorization_code",
        "client_id": cfg["app_id"],
        "client_secret": cfg["client_secret"],
        "code": code,
        "redirect_uri": cfg["redirect_uri"],
    })
    if resp.status_code == 200:
        data = resp.json()
        save_env("ML_ACCESS_TOKEN", data["access_token"])
        save_env("ML_REFRESH_TOKEN", data["refresh_token"])
        return True, f"Tokens obtidos (expira em {data.get('expires_in', '?')}s)", data
    return False, f"Erro {resp.status_code}: {resp.text[:200]}", {}


def refresh_ml_token() -> tuple[bool, str]:
    """Renova ML access_token usando refresh_token."""
    cfg = _ml_config()
    if not cfg["refresh_token"] or not cfg["client_secret"]:
        return False, "ML_REFRESH_TOKEN ou ML_CLIENT_SECRET não configurados"

    resp = httpx.post(ML_TOKEN_URL, json={
        "grant_type": "refresh_token",
        "client_id": cfg["app_id"],
        "client_secret": cfg["client_secret"],
        "refresh_token": cfg["refresh_token"],
    })
    if resp.status_code == 200:
        data = resp.json()
        save_env("ML_ACCESS_TOKEN", data["access_token"])
        save_env("ML_REFRESH_TOKEN", data["refresh_token"])
        return True, f"Token renovado (expira em {data.get('expires_in', '?')}s)"
    return False, f"Erro {resp.status_code}: {resp.text[:200]}"


# ── OAUTH AUTOMÁTICO (Playwright) ─────────────────────

def open_ml_auth_in_browser():
    """Abre a URL de autorização do ML no browser do sistema (funciona em WSL)."""
    import webbrowser

    auth_url = get_ml_auth_url()
    explorer = Path("/mnt/c/Windows/explorer.exe")

    if explorer.exists():
        # WSL: abre no browser do Windows via explorer.exe
        subprocess.Popen(
            [str(explorer), auth_url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        webbrowser.open(auth_url)
