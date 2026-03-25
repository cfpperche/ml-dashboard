# CLAUDE.md — ML Competitor Intelligence Dashboard

## Visão Geral do Projeto

Dashboard local (Dash/Plotly) para análise de concorrentes de **peças de servidor** no Mercado Livre, com insights de IA via Claude. Projeto pessoal, roda 100% local no PC do desenvolvedor (WSL2 Ubuntu).

### Problema que resolve
O usuário importa peças de servidor (RAM ECC, HDD SAS, SSD Enterprise, NICs, RAID controllers) e revende no Mercado Livre. Precisa monitorar preços de concorrentes, identificar oportunidades de margem, e tomar decisões de compra/cotação baseadas em dados reais de mercado.

### Público-alvo
Um único usuário (o desenvolvedor), uso pessoal e local.

---

## Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|------------|---------------|
| UI/Dashboard | **Dash (Plotly)** + **dash-bootstrap-components** | Multi-page, callbacks explícitos, production-ready |
| API ML | **httpx** (async) | Cliente HTTP async para múltiplas chamadas concorrentes |
| IA/Insights | **Claude Agent SDK** + OAuth | Usa assinatura Max ($200/mês) via `CLAUDE_CODE_OAUTH_TOKEN`, sem custo extra de API |
| IA fallback | **claude CLI** subprocess | `claude -p` como fallback se o SDK falhar — sempre funciona com sessão OAuth |
| Dados | **pandas** | Manipulação de dados tabulares |
| Gráficos | **plotly** | Gráficos interativos (nativo no Dash) |
| Export | **openpyxl** | Exportar para Excel |
| Persistência | **SQLite** | Banco local para concorrentes e histórico de preços |
| Config | **python-dotenv** | Variáveis de ambiente via `.env` |

---

## Estrutura do Projeto

```
ml-dashboard/
├── CLAUDE.md                  ← ESTE ARQUIVO (contexto para o Claude Code)
├── app.py                     ← Inicialização Dash + layout base + navbar
├── pages/
│   ├── search.py              ← Busca de produtos no catálogo ML
│   ├── competitors.py         ← CRUD + análise de concorrentes
│   ├── insights.py            ← Insights IA com Claude
│   ├── export.py              ← Download Excel/JSON
│   ├── settings.py            ← OAuth tokens (Claude + ML)
│   └── home.py                ← Redirect para /search
├── components/
│   ├── __init__.py
│   ├── navbar.py              ← Barra de navegação (dbc.Navbar)
│   └── cards.py               ← Cards de métricas reutilizáveis
├── src/
│   ├── __init__.py
│   ├── ml_api.py              ← Cliente async da API do Mercado Livre (MLClient)
│   ├── ai_insights.py         ← Módulo de IA (Claude Agent SDK + CLI fallback)
│   ├── auth.py                ← OAuth handlers (Claude + ML)
│   ├── database.py            ← SQLite — persistência local
│   └── async_helper.py        ← Wrapper run_async() para callbacks Dash
├── assets/
│   └── style.css              ← CSS custom (Dash auto-carrega)
├── data/
│   └── ml_dashboard.db        ← Banco SQLite (gitignored)
├── .env                       ← Tokens (NÃO committar, está no .gitignore)
├── .env.example               ← Template de configuração
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Autenticação e Tokens

### Mercado Livre API
- **Token**: `ML_ACCESS_TOKEN` no `.env`
- **APP ID**: `ML_APP_ID` no `.env` (default: `4724076426479961`)
- **Site**: `MLB` (Brasil)
- **Base URL**: `https://api.mercadolibre.com`
- **Redirect URI**: `ML_REDIRECT_URI` no `.env` (`https://github.com/cfpperche/redirect`)
- **Token expira em 6h** — renovar com `ML_REFRESH_TOKEN` via POST para `/oauth/token`
- **Rate limit**: 0.4s delay entre requests (implementado no `MLClient._get()`)
- **IMPORTANTE**: O endpoint `/sites/MLB/search` está bloqueado por policy do ML para este app. A busca usa `/products/search` (catálogo) + `/products/{id}/items` (anúncios ativos/inativos).
- **Endpoints usados**:
  - `GET /products/search?site_id=MLB&q={query}` — busca no catálogo
  - `GET /products/{id}/items?status={active|inactive}` — anúncios de um produto
  - `GET /users/me` — verificar conexão
  - `GET /users/{user_id}` — info de vendedor
  - `GET /users/{user_id}/items/search` — items do próprio vendedor
  - `POST /oauth/token` — trocar code por token ou refresh
- **Todas as chamadas requerem header**: `Authorization: Bearer {token}`

### Claude AI (via OAuth da assinatura Max)
- **Plano**: Claude Max $200/mês
- **Token**: `CLAUDE_CODE_OAUTH_TOKEN` no `.env` (formato `sk-ant-oat01-XXXXX`)
- **Gerar token**: `claude setup-token` no terminal, ou sincronizar via Settings no dashboard
- **Credenciais**: lidas de `~/.claude/.credentials.json`
- **Método primário**: Claude Agent SDK Python (`claude_agent_sdk.query()`)
- **Método fallback**: `claude -p "prompt" --output-format text` como subprocesso
- **System prompt da IA**: "analista especialista em e-commerce e peças de servidor, insights acionáveis em português"
- **IMPORTANTE**: O Agent SDK com OAuth funciona para uso pessoal/local. NÃO é para redistribuição como produto para terceiros (ToS da Anthropic).

---

## Funcionalidades Implementadas (v0.2)

### /search — Busca de Produtos
- Search bar + botão Buscar
- Filtros: status (Todos/Ativos/Inativos) e itens por página
- Métricas: menor/maior/média/mediana de preços
- Histograma de distribuição de preços (Plotly)
- Tabela HTML com colunas: Status, Título, Preço, Marca, Modelo, Seller ID, Vendedor, Frete, Link
- Botão "+ Concorrente" por linha para auto-cadastrar seller no banco
- Paginação com botões Anterior/Próxima

### /competitors — Concorrentes (CRUD)
- Formulário para cadastrar concorrente (nome, nickname, seller ID, notas)
- Tabela com todos os concorrentes (ativos e inativos)
- Editar via modal (todos os campos + toggle ativo/inativo)
- Excluir concorrente
- Botão "Analisar Todos" busca produtos de todos os concorrentes ativos
- Gráfico de barras (qtd anúncios) + box plot (faixa de preços)

### /insights — Insights IA
- Escolha de fonte de dados (busca, concorrentes, ou prompt livre)
- Prompt editável pelo usuário
- Claude analisa os dados e retorna insights estratégicos em markdown
- Histórico de análises com accordion expansível

### /export — Exportar
- Download Excel dos resultados de busca
- Download Excel dos dados de concorrentes
- Download JSON das análises IA
- Usa `dcc.Download` com callbacks

### /settings — Configuração de Tokens
- **Claude**: detecta token de `~/.claude/.credentials.json`, mostra plano e expiração, botão sincronizar
- **ML**: status de Access Token e Client Secret, input para secret, botão "Autorizar Mercado Livre" (abre Chrome no Windows via WSL), campo para colar URL de callback, botão refresh token
- **Testar Conexão**: verifica se o token ML está válido

---

## Funcionalidades Planejadas (Roadmap)

### v0.2 — Persistência e Histórico (em progresso)
- [x] SQLite para concorrentes (CRUD completo)
- [ ] Salvar resultados de busca no SQLite com timestamp (histórico de preços)
- [ ] Gráfico de evolução de preços ao longo do tempo
- [ ] Dashboard de tendências (preço subiu/desceu por part number)
- [ ] Auto-refresh do ML token via refresh_token (quando dá 401)

### v0.3 — Análise Avançada
- [ ] Busca por Part Number específico com comparação entre vendedores
- [ ] Detecção automática de oportunidades (preço abaixo da média)
- [ ] Cálculo de margem estimada (preço ML vs custo importação)
- [ ] Integração com a planilha de cotação (importar custos do Excel)
- [ ] Alertas de preço (notificar quando um concorrente baixar preço)

### v0.4 — Concorrentes Aprofundado
- [ ] Perfil detalhado de cada concorrente (reputação, tempo de atividade, volume)
- [ ] Tracking de novos produtos adicionados por concorrentes
- [ ] Comparação side-by-side de catálogos
- [ ] Heatmap de categorias mais vendidas por concorrente

### v0.5 — IA Avançada
- [ ] Claude gera relatório semanal automático
- [ ] Sugestão automática de preço de venda baseada no mercado
- [ ] Análise de sentimento de avaliações de produtos
- [ ] Predição de demanda baseada em sazonalidade

### v1.0 — Produção Local
- [ ] Autenticação local (senha simples para proteger dashboard)
- [ ] Scheduler para coleta automática de dados (cron + script)
- [ ] Backup automático do SQLite
- [ ] Docker compose para facilitar setup

---

## Contexto de Negócio

### Produtos Comercializados
- **RAM DDR4 ECC**: UDIMM (4/8/16/32GB) e RDIMM (8/16/32/64GB)
- **RAM DDR5 ECC**: UDIMM (8/16/32/48GB) e RDIMM (16/32/48/64/96/128GB)
- **Frequências DDR4**: 2133, 2400, 2666, 2933, 3200 MHz
- **Frequências DDR5**: 4800, 5600 MHz
- **Fabricantes**: Samsung, SK Hynix, Micron, Kingston
- **Também vende**: HDD SAS, SSD Enterprise (Intel D3-S4510/S4610), Network Cards (X520, X540, X550, X710, I350), RAID Controllers, Cooler Fans, GBICs/SFPs, CPUs Xeon
- **Servidores compatíveis**: Dell PowerEdge (R640/R740/R660/R760), HPE ProLiant (DL360/DL380 G9/G10/G11), Lenovo ThinkSystem (SR630/SR650)

### Concorrentes Mapeados
- **REDDAPPLE1** — vendedor referência do usuário
- **Eletrocheap** — MercadoLíder, foco em RAM ECC
- **Memórias Online (Laggo)** — 25 anos, price setter, DDR3→DDR5
- **Performance Solutions** — posicionamento premium, workstations
- **Sinergia TI** — autorizada Dell, RAM OEM
- **SpeedRam** — alto volume (+1000 vendas), MercadoLíder Platinum
- **TI Server Store** — especializado em recondicionado
- **KingstonStore** — loja do fabricante, preço-teto

### Dados de Mercado (Março 2026)
- Faixa ML 8GB DDR4 ECC UDIMM: R$ 375 — R$ 799
- Faixa ML 16GB DDR4 ECC UDIMM: R$ 990 — R$ 1.799
- Faixa ML 32GB DDR4 ECC RDIMM: R$ 1.450 — R$ 2.890
- DDR5 ECC: mercado ainda imaturo no BR, poucos vendedores, margem alta
- Escassez global de DRAM por demanda IA — previsão de pico 2026, normalização 2027-2028
- Câmbio referência: USD→BRL ~R$ 5,80

---

## Convenções de Código

### Python
- Python 3.10+ (usa type hints modernas como `str | None`)
- Async/await para I/O (httpx, Agent SDK)
- `run_async()` wrapper em `src/async_helper.py` para rodar coroutines em callbacks Dash (que são sync)
- Imports agrupados: stdlib → third-party → local
- Docstrings em português para módulos e funções públicas
- f-strings para formatação
- Formatação de moeda: `f"R$ {valor:,.2f}"`

### Dash
- Multi-page com `pages/` directory e `dash.register_page()`
- Callbacks com `@callback` + `Input`, `Output`, `State`
- `prevent_initial_call=True` em callbacks de botão
- `dcc.Store` para estado compartilhado entre páginas (memory)
- `dcc.Loading` para feedback durante chamadas à API
- `dcc.Download` para exportação de arquivos
- `dbc.Alert` para feedback (success, danger, warning, info)
- Pattern-matching callbacks com `ALL` para botões dinâmicos em tabelas
- `allow_duplicate=True` quando múltiplos callbacks escrevem no mesmo Output

### Mercado Livre API
- Sempre enviar `Authorization: Bearer` no header
- Rate limit de 0.4s entre requests
- `/sites/MLB/search` bloqueado — usar `/products/search` + `/products/{id}/items`
- Items de terceiros via `/items/{id}` retornam 403 — só items próprios acessíveis
- Tratar erros 401 (token expirado), 403 (bloqueio policy), 429 (rate limit)
- Campos referenciáveis: `sold_quantity` e `available_quantity` são referenciais (não exatos)

### SQLite
- Banco em `data/ml_dashboard.db` (gitignored)
- Tabelas inicializadas automaticamente ao importar `src/database.py`
- `PRAGMA journal_mode=WAL` para performance
- `sqlite3.Row` para acessar colunas por nome

---

## Como Rodar

```bash
# Setup inicial
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env com os tokens

# Gerar OAuth token do Claude
claude setup-token
# Ou sincronizar via /settings no dashboard

# Rodar dashboard
python app.py
# Abre em http://localhost:8050
```

---

## Decisões Técnicas

1. **Dash vs Streamlit**: Migrado de Streamlit para Dash na v0.2. Streamlit reroda o script inteiro a cada interação, causava erros de "Event loop is closed" com async e não suportava callbacks reais. Dash tem callbacks explícitos, multi-page nativo, e arquitetura production-ready.

2. **httpx vs requests**: httpx por ser async e suportar chamadas concorrentes sem bloquear.

3. **Claude Agent SDK + CLI fallback**: SDK é o caminho mais limpo, mas pode ter issues com OAuth. CLI (`claude -p`) é infalível como backup porque usa a sessão OAuth logada diretamente.

4. **SQLite para persistência**: Banco local leve, sem setup de servidor. Usado para CRUD de concorrentes, planejado para histórico de preços.

5. **`/products/search` em vez de `/sites/MLB/search`**: A API do ML bloqueou o endpoint de busca padrão por policy (`PA_UNAUTHORIZED_RESULT_FROM_POLICIES`). A alternativa usa catálogo + items vinculados.

6. **WSL + Chrome**: Em WSL, abrir browser no Windows requer chamar `chrome.exe` diretamente via `/mnt/c/Program Files/Google/Chrome/Application/chrome.exe`.

7. **Tabela HTML vs DataTable**: A tabela de resultados de busca usa HTML (`dbc.Table`) em vez de `dash_table.DataTable` para suportar botões de ação ("+  Concorrente") por linha. DataTable não permite componentes Dash nas células.

8. **Planilha de cotação separada**: Já existe uma planilha Excel completa (top10_ram_cotacao.xlsx) com 5 abas — DDR4, DDR5, concorrentes, RFQ, e catálogo completo de 47 modelos. Integrar com o dashboard na v0.3.
