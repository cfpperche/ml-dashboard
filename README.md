# 🔍 ML Competitor Intelligence Dashboard

Dashboard local para análise de concorrentes no Mercado Livre, com insights de IA via Claude.

## Stack
- **Dashboard**: Streamlit (roda local no browser)
- **IA**: Claude Agent SDK + OAuth (usa sua assinatura Max, sem custo extra)
- **API ML**: httpx async
- **Gráficos**: Plotly
- **Export**: openpyxl (Excel)

## Setup

### 1. Instalar
```bash
cd ml-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar tokens
```bash
cp .env.example .env
```

Edite o `.env`:
```env
# Claude OAuth (rode: claude setup-token)
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-XXXXX

# Mercado Livre
ML_ACCESS_TOKEN=APP_USR-4724076426479961-032512-XXXXX
```

### 3. Rodar
```bash
streamlit run app.py
```

Abre em http://localhost:8501

## Funcionalidades

| Tab | O que faz |
|-----|-----------|
| 🔎 Busca | Busca produtos no ML com métricas de preço e gráficos |
| 👥 Concorrentes | Analisa produtos de vendedores específicos |
| 🤖 Insights IA | Claude analisa os dados e dá recomendações |
| 📥 Exportar | Baixa tudo em Excel ou JSON |

## Renovar tokens

**ML (expira em 6h):**
```bash
curl -X POST 'https://api.mercadolibre.com/oauth/token' \
  -d 'grant_type=refresh_token&client_id=SEU_APP_ID&client_secret=SEU_SECRET&refresh_token=SEU_REFRESH_TOKEN'
```

**Claude OAuth:**
```bash
claude setup-token
```
