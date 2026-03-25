# CLAUDE.md — ML Competitor Intelligence Dashboard

## Visão Geral do Projeto

Dashboard local (Streamlit) para análise de concorrentes de **peças de servidor** no Mercado Livre, com insights de IA via Claude. Projeto pessoal, roda 100% local no PC do desenvolvedor.

### Problema que resolve
O usuário importa peças de servidor (RAM ECC, HDD SAS, SSD Enterprise, NICs, RAID controllers) e revende no Mercado Livre. Precisa monitorar preços de concorrentes, identificar oportunidades de margem, e tomar decisões de compra/cotação baseadas em dados reais de mercado.

### Público-alvo
Um único usuário (o desenvolvedor), uso pessoal e local.

---

## Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|------------|---------------|
| UI/Dashboard | **Streamlit** | Roda local no browser, rápido de prototipar, Python nativo |
| API ML | **httpx** (async) | Cliente HTTP async, melhor que requests para múltiplas chamadas |
| IA/Insights | **Claude Agent SDK** + OAuth | Usa assinatura Max ($200/mês) via `CLAUDE_CODE_OAUTH_TOKEN`, sem custo extra de API |
| IA fallback | **claude CLI** subprocess | `claude -p` como fallback se o SDK falhar — sempre funciona com sessão OAuth |
| Dados | **pandas** | Manipulação de dados tabulares |
| Gráficos | **plotly** | Gráficos interativos |
| Export | **openpyxl** | Exportar para Excel |
| Persistência | **SQLite** (futuro) | Para histórico de preços e tracking ao longo do tempo |
| Config | **python-dotenv** | Variáveis de ambiente via `.env` |

---

## Estrutura do Projeto

```
ml-dashboard/
├── CLAUDE.md              ← ESTE ARQUIVO (contexto para o Claude Code)
├── app.py                 ← Dashboard Streamlit principal (entrypoint)
├── src/
│   ├── __init__.py
│   ├── ml_api.py          ← Cliente async da API do Mercado Livre (MLClient)
│   └── ai_insights.py     ← Módulo de IA (Claude Agent SDK + CLI fallback)
├── .env                   ← Tokens (NÃO committar, está no .gitignore)
├── .env.example           ← Template de configuração
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Autenticação e Tokens

### Mercado Livre API
- **Token**: `ML_ACCESS_TOKEN` no `.env`
- **APP ID**: `4724076426479961`
- **Site**: `MLB` (Brasil)
- **Base URL**: `https://api.mercadolibre.com`
- **Redirect URI**: `https://github.com/cfpperche/redirect`
- **Token expira em 6h** — renovar com `ML_REFRESH_TOKEN` via POST para `/oauth/token`
- **Rate limit**: 0.4s delay entre requests (implementado no `MLClient._get()`)
- **Endpoints usados**:
  - `GET /sites/MLB/search?q={query}` — busca por termo
  - `GET /sites/MLB/search?nickname={nick}` — produtos de vendedor
  - `GET /sites/MLB/search?seller_id={id}` — produtos por seller ID
  - `GET /items/{item_id}` — detalhes do item
  - `GET /users/me` — verificar conexão
  - `GET /users/{user_id}` — info de vendedor
- **Todas as chamadas requerem header**: `Authorization: Bearer {token}`

### Claude AI (via OAuth da assinatura Max)
- **Plano**: Claude Max $200/mês
- **Token**: `CLAUDE_CODE_OAUTH_TOKEN` no `.env` (formato `sk-ant-oat01-XXXXX`)
- **Gerar token**: `claude setup-token` no terminal
- **Método primário**: Claude Agent SDK Python (`claude_agent_sdk.query()`)
- **Método fallback**: `claude -p "prompt" --output-format text` como subprocesso
- **System prompt da IA**: "analista especialista em e-commerce e peças de servidor, insights acionáveis em português"
- **IMPORTANTE**: O Agent SDK com OAuth funciona para uso pessoal/local. NÃO é para redistribuição como produto para terceiros (ToS da Anthropic).

---

## Funcionalidades Implementadas (v0.1)

### Tab 1: 🔎 Busca de Produtos
- Input de texto para busca livre no ML
- 4 botões de busca rápida (8GB DDR4 UDIMM, 16GB DDR4 RDIMM, 32GB DDR4 RDIMM, 16GB DDR5 RDIMM)
- Métricas: menor/maior/média/mediana de preços
- Histograma de distribuição de preços (Plotly)
- Tabela de resultados com título, preço, vendedor, frete, link

### Tab 2: 👥 Análise de Concorrentes
- Input de nicknames de vendedores (um por linha)
- Pré-configurados: REDDAPPLE1, ELETROCHEAP
- Busca todos os produtos de cada vendedor
- Gráfico de barras: qtd de anúncios por concorrente
- Box plot: distribuição de preços por concorrente
- Tabela detalhada com todos os produtos

### Tab 3: 🤖 Insights IA
- Escolha de fonte de dados (busca, concorrentes, ou prompt livre)
- Prompt editável pelo usuário
- Claude analisa os dados e retorna insights estratégicos
- Histórico de análises salvo no session_state

### Tab 4: 📥 Exportar
- Download Excel dos resultados de busca
- Download Excel dos dados de concorrentes
- Download JSON das análises IA

---

## Funcionalidades Planejadas (Roadmap)

### v0.2 — Persistência e Histórico
- [ ] SQLite para salvar resultados de busca com timestamp
- [ ] Gráfico de evolução de preços ao longo do tempo
- [ ] Dashboard de tendências (preço subiu/desceu por part number)
- [ ] Auto-refresh do ML token via refresh_token

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
- [ ] Multi-page Streamlit (páginas separadas em vez de tabs)
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
- `run_async()` wrapper para rodar coroutines no Streamlit (que é sync)
- Imports agrupados: stdlib → third-party → local
- Docstrings em português para módulos e funções públicas
- f-strings para formatação
- Formatação de moeda: `f"R$ {valor:,.2f}"`

### Streamlit
- `st.session_state` para persistir dados entre reruns
- `st.spinner()` durante chamadas à API
- `st.toast()` para feedback rápido
- `st.columns()` para layout
- `st.tabs()` para organizar funcionalidades
- `st.dataframe()` com `column_config` para formatação
- `st.plotly_chart()` para gráficos interativos

### Mercado Livre API
- Sempre enviar `Authorization: Bearer` no header
- Rate limit de 0.4s entre requests
- Tratar erros 401 (token expirado), 429 (rate limit), e exceções de rede
- Resultados paginados: ML retorna max 50 por request, usar offset para mais
- Campos referenciáveis: `sold_quantity` e `available_quantity` são referenciais (não exatos)

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
# Copiar o token para CLAUDE_CODE_OAUTH_TOKEN no .env

# Rodar dashboard
streamlit run app.py
# Abre em http://localhost:8501
```

---

## Decisões Técnicas

1. **Streamlit vs FastAPI+React**: Streamlit escolhido por ser protótipo local — menor complexidade, tudo em Python, sem build frontend separado. Migrar para FastAPI+React se virar multi-usuário.

2. **httpx vs requests**: httpx por ser async e suportar o event loop do Streamlit sem conflitos.

3. **Claude Agent SDK + CLI fallback**: SDK é o caminho mais limpo, mas pode ter issues com OAuth. CLI (`claude -p`) é infalível como backup porque usa a sessão OAuth logada diretamente.

4. **Sem banco de dados na v0.1**: Session state do Streamlit é suficiente para protótipo. SQLite planejado para v0.2 para persistir histórico de preços.

5. **Planilha de cotação separada**: Já existe uma planilha Excel completa (top10_ram_cotacao.xlsx) com 5 abas — DDR4, DDR5, concorrentes, RFQ, e catálogo completo de 47 modelos. Integrar com o dashboard na v0.3.
