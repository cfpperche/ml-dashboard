"""
ML Dashboard — Mercado Livre Competitor Intelligence
Rode com: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio, json, os
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
from src.ml_api import MLClient
from src.ai_insights import analyze_with_claude, format_products_for_analysis

st.set_page_config(page_title="ML Competitor Intelligence", page_icon="🔍", layout="wide")

st.markdown("""<style>
.main-header{font-size:2rem;font-weight:700;background:linear-gradient(90deg,#1a1a2e,#0f3460);
-webkit-background-clip:text;-webkit-text-fill-color:transparent}
</style>""", unsafe_allow_html=True)

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

if "ml" not in st.session_state:
    st.session_state.ml = MLClient()
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "competitor_results" not in st.session_state:
    st.session_state.competitor_results = []
if "analyses" not in st.session_state:
    st.session_state.analyses = []

ml = st.session_state.ml

# ── SIDEBAR ───────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Config")
    ml_token = st.text_input("ML Access Token", value=os.getenv("ML_ACCESS_TOKEN",""), type="password")
    if ml_token and ml_token != ml.token:
        st.session_state.ml = MLClient(ml_token)
        ml = st.session_state.ml
        st.success("Token atualizado!")
    st.divider()
    if os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        st.success("Claude OAuth ✅")
    else:
        st.warning("Defina CLAUDE_CODE_OAUTH_TOKEN no .env")
    if st.button("🔌 Testar ML"):
        r = run_async(ml.me())
        if "error" not in (r or {}):
            st.success(f"Conectado: {r.get('nickname')}")
        else:
            st.error(str(r))

# ── HEADER ────────────────────────────────────────────
st.markdown('<p class="main-header">🔍 ML Competitor Intelligence</p>', unsafe_allow_html=True)
st.caption("Peças de Servidor · Mercado Livre API + Claude AI")

tab1, tab2, tab3, tab4 = st.tabs(["🔎 Busca","👥 Concorrentes","🤖 Insights IA","📥 Exportar"])

# ══════════════════════════════════════════════════════
# TAB 1 — BUSCA
# ══════════════════════════════════════════════════════
with tab1:
    c1, c2 = st.columns([3,1])
    query = c1.text_input("🔍 Buscar", placeholder="Ex: memoria 16GB DDR4 ECC RDIMM servidor")
    limit = c2.selectbox("Qtd", [10,25,50], index=1)

    qcols = st.columns(4)
    for i, qs in enumerate(["8GB DDR4 ECC UDIMM","16GB DDR4 ECC RDIMM","32GB DDR4 ECC RDIMM","16GB DDR5 ECC RDIMM"]):
        if qcols[i].button(qs, key=f"q{i}"):
            query = f"memoria {qs} servidor"

    if query:
        with st.spinner("Buscando..."):
            data = run_async(ml.search(query, limit=limit))
        if data and "results" in data:
            results = data["results"]
            st.session_state.search_results = results
            total = data.get("paging",{}).get("total",0)
            st.success(f"**{total:,}** resultados (mostrando {len(results)})")

            prices = [r["price"] for r in results if r.get("price")]
            if prices:
                m1,m2,m3,m4 = st.columns(4)
                m1.metric("Menor", f"R$ {min(prices):,.2f}")
                m2.metric("Maior", f"R$ {max(prices):,.2f}")
                m3.metric("Média", f"R$ {sum(prices)/len(prices):,.2f}")
                m4.metric("Mediana", f"R$ {sorted(prices)[len(prices)//2]:,.2f}")

                fig = px.histogram(x=prices, nbins=20, labels={"x":"Preço (R$)","y":"Qtd"},
                                   title="Distribuição de Preços", color_discrete_sequence=["#0f3460"])
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)

            df = pd.DataFrame([{
                "Título": r.get("title",""), "Preço": r.get("price",0),
                "Vendedor": r.get("seller",{}).get("nickname","?"),
                "Frete Grátis": "✅" if r.get("shipping",{}).get("free_shipping") else "❌",
                "Condição": r.get("condition",""), "Link": r.get("permalink",""),
            } for r in results])
            st.dataframe(df, column_config={
                "Preço": st.column_config.NumberColumn(format="R$ %.2f"),
                "Link": st.column_config.LinkColumn("Link"),
            }, hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════
# TAB 2 — CONCORRENTES
# ══════════════════════════════════════════════════════
with tab2:
    st.subheader("Análise de Concorrentes")
    comp_input = st.text_area("Nicknames (um por linha)", value="REDDAPPLE1\nELETROCHEAP", height=100)
    competitors = [c.strip() for c in comp_input.split("\n") if c.strip()]

    if st.button("🔍 Analisar", type="primary", key="analyze_comp"):
        all_prods = []
        prog = st.progress(0)
        for i, nick in enumerate(competitors):
            with st.spinner(f"Buscando {nick}..."):
                data = run_async(ml.search_seller(nickname=nick))
                if data and "results" in data:
                    for item in data["results"]:
                        item["_seller_nick"] = nick
                    all_prods.extend(data["results"])
                    st.toast(f"✅ {nick}: {len(data['results'])} produtos")
            prog.progress((i+1)/len(competitors))

        st.session_state.competitor_results = all_prods
        if all_prods:
            st.success(f"**{len(all_prods)}** produtos de {len(competitors)} concorrentes")
            df = pd.DataFrame([{
                "Vendedor": p.get("_seller_nick","?"), "Título": p.get("title",""),
                "Preço": p.get("price",0),
                "Frete Grátis": p.get("shipping",{}).get("free_shipping",False),
            } for p in all_prods])

            fig1 = px.bar(df.groupby("Vendedor").size().reset_index(name="Qtd"),
                          x="Vendedor", y="Qtd", title="Anúncios por Concorrente", color="Vendedor")
            st.plotly_chart(fig1, use_container_width=True)

            if df["Preço"].sum() > 0:
                fig2 = px.box(df[df["Preço"]>0], x="Vendedor", y="Preço",
                              title="Faixa de Preço por Concorrente", color="Vendedor")
                st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(df.sort_values("Preço", ascending=False),
                         column_config={"Preço": st.column_config.NumberColumn(format="R$ %.2f")},
                         hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════
# TAB 3 — INSIGHTS IA
# ══════════════════════════════════════════════════════
with tab3:
    st.subheader("🤖 Insights com Claude AI")
    st.caption("Usa assinatura Claude Max via OAuth")

    src = st.radio("Dados:", ["Última busca","Concorrentes","Prompt livre"], horizontal=True)
    prompt = st.text_area("Prompt", value=(
        "Analise os produtos e me dê:\n"
        "1. Top 5 oportunidades de margem\n"
        "2. Faixa de preço ideal por categoria\n"
        "3. Vendedores mais competitivos\n"
        "4. Recomendações estratégicas"
    ), height=120)

    if st.button("🧠 Gerar Insights", type="primary", key="gen_insights"):
        if src == "Última busca":
            ctx = format_products_for_analysis(st.session_state.search_results)
        elif src == "Concorrentes":
            ctx = format_products_for_analysis(st.session_state.competitor_results)
        else:
            ctx = ""

        if not ctx and src != "Prompt livre":
            st.warning("Faça uma busca primeiro.")
        else:
            with st.spinner("🧠 Claude analisando..."):
                resp = run_async(analyze_with_claude(prompt, ctx))
            st.markdown("### 📊 Análise")
            st.markdown(resp)
            st.session_state.analyses.append({
                "timestamp": datetime.now().isoformat(), "prompt": prompt, "response": resp,
            })

# ══════════════════════════════════════════════════════
# TAB 4 — EXPORTAR
# ══════════════════════════════════════════════════════
with tab4:
    st.subheader("📥 Exportar")
    c1, c2 = st.columns(2)
    with c1:
        if st.session_state.search_results:
            df_s = pd.DataFrame([{
                "Título": r.get("title",""), "Preço": r.get("price",0),
                "Vendedor": r.get("seller",{}).get("nickname","?"),
                "Item ID": r.get("id",""), "Link": r.get("permalink",""),
            } for r in st.session_state.search_results])
            buf = BytesIO(); df_s.to_excel(buf, index=False)
            st.download_button("⬇️ Excel (Busca)", buf.getvalue(),
                               f"ml_busca_{datetime.now():%Y%m%d_%H%M}.xlsx")
        else:
            st.info("Faça uma busca primeiro")
    with c2:
        if st.session_state.competitor_results:
            df_c = pd.DataFrame([{
                "Vendedor": p.get("_seller_nick","?"), "Título": p.get("title",""),
                "Preço": p.get("price",0), "Item ID": p.get("id",""),
            } for p in st.session_state.competitor_results])
            buf2 = BytesIO(); df_c.to_excel(buf2, index=False)
            st.download_button("⬇️ Excel (Concorrentes)", buf2.getvalue(),
                               f"ml_concorrentes_{datetime.now():%Y%m%d_%H%M}.xlsx")
        else:
            st.info("Analise concorrentes primeiro")

    if st.session_state.analyses:
        st.divider()
        st.download_button("⬇️ Análises IA (JSON)",
                           json.dumps(st.session_state.analyses, ensure_ascii=False, indent=2),
                           f"ml_insights_{datetime.now():%Y%m%d_%H%M}.json")

st.divider()
st.caption("ML Competitor Intelligence v0.1 · Claude Max + ML API")
