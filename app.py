"""Dashboard — Mobilidade Urbana e Transporte Público no Brasil (2015–2024)."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
import streamlit as st
from sqlalchemy import create_engine

BASE = Path(__file__).parent
CSV = BASE / "dados" / "simulacao_mobilidade_urbana_brasil.csv"
DB = BASE / "database" / "mobilidade.db"
ORDEM = ["Baixo", "Médio", "Alto", "Crítico"]

st.set_page_config(page_title="Mobilidade Urbana no Brasil", page_icon="🚌", layout="wide")


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    """Lê do SQLite (SQLAlchemy). Se o banco não existir, cria a partir do CSV."""
    engine = create_engine(f"sqlite:///{DB}")
    if not DB.exists():
        DB.parent.mkdir(exist_ok=True)
        pd.read_csv(CSV, encoding="utf-8-sig").to_sql("mobilidade", engine, index=False, if_exists="replace")
    df = pd.read_sql("SELECT * FROM mobilidade", engine)
    df["data"] = pd.to_datetime(df["data"])
    df["nivel_congestionamento"] = pd.Categorical(df["nivel_congestionamento"], categories=ORDEM, ordered=True)
    df["nivel_num"] = df["nivel_congestionamento"].cat.codes + 1
    df["co2_por_1000_pass"] = df["emissao_co2"] / df["passageiros"] * 1000
    return df


def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


df = carregar_dados()

# ---------------------------------------------------------------- Cabeçalho
st.title("🚌 Mobilidade Urbana e Transporte Público no Brasil")
st.caption("Avaliação G1 — Análise e Visualização de Dados com Python · Período 2015–2024 · Dados simulados")
st.markdown(
    "**Problema:** a mobilidade urbana influencia qualidade de vida, produtividade e meio ambiente. "
    "Este painel investiga fluxo de passageiros, tempo de deslocamento, congestionamento e emissões "
    "em cidades brasileiras, para identificar gargalos e comparar regiões e meios de transporte."
)

# ---------------------------------------------------------------- Filtros
st.sidebar.header("Filtros")
anos = st.sidebar.slider("Ano", int(df.ano.min()), int(df.ano.max()), (int(df.ano.min()), int(df.ano.max())))
meses = st.sidebar.multiselect("Mês", sorted(df.mes.unique()), default=sorted(df.mes.unique()))
regioes = st.sidebar.multiselect("Região", sorted(df.regiao.unique()), default=sorted(df.regiao.unique()))
base_uf = df[df.regiao.isin(regioes)]
ufs = st.sidebar.multiselect("Estado (UF)", sorted(base_uf.uf.unique()), default=sorted(base_uf.uf.unique()))
base_cid = base_uf[base_uf.uf.isin(ufs)]
cidades = st.sidebar.multiselect("Cidade", sorted(base_cid.cidade.unique()), default=sorted(base_cid.cidade.unique()))
modais = st.sidebar.multiselect("Meio de transporte", sorted(df.meio_transporte.unique()), default=sorted(df.meio_transporte.unique()))
niveis = st.sidebar.multiselect("Nível de congestionamento", ORDEM, default=ORDEM)

f = df[
    df.ano.between(*anos) & df.mes.isin(meses) & df.regiao.isin(regioes) & df.uf.isin(ufs)
    & df.cidade.isin(cidades) & df.meio_transporte.isin(modais) & df.nivel_congestionamento.isin(niveis)
]
if f.empty:
    st.warning("Nenhum registro para os filtros selecionados. Ajuste os filtros na barra lateral.")
    st.stop()

# ---------------------------------------------------------------- KPIs
por_cidade = f.groupby("cidade").passageiros.sum()
por_modal = f.groupby("meio_transporte").passageiros.sum()
c1, c2, c3 = st.columns(3)
c1.metric("Total de passageiros", fmt(f.passageiros.sum()))
c2.metric("Cidade mais movimentada", por_cidade.idxmax())
c3.metric("Meio de transporte predominante", por_modal.idxmax())
c4, c5, c6 = st.columns(3)
c4.metric("Tempo médio de deslocamento", f"{f.tempo_medio_deslocamento.mean():.1f} min")
c5.metric("Tarifa média", f"R$ {f.tarifa_media.mean():.2f}".replace(".", ","))
c6.metric("Nível médio de congestionamento", f"{f.nivel_num.mean():.2f} / 4")
st.divider()

# ---------------------------------------------------------------- Seções
t1, t2, t3, t4, t5, t6 = st.tabs(
    ["📈 Evolução temporal", "🗺️ Regiões e cidades", "🚇 Meios de transporte",
     "🚦 Congestionamento", "🔗 Correlações e ambiente", "📋 Tabela e conclusão"]
)

with t1:
    mensal = f.groupby("data").agg(passageiros=("passageiros", "sum"), tempo=("tempo_medio_deslocamento", "mean")).reset_index()
    mensal["media_movel_12m"] = mensal.passageiros.rolling(12, min_periods=1).mean()
    fig = px.line(mensal, x="data", y=["passageiros", "media_movel_12m"], title="Passageiros por mês e média móvel de 12 meses",
                  labels={"value": "Passageiros", "data": "", "variable": ""})
    st.plotly_chart(fig, use_container_width=True)
    anual = f.groupby("ano").tempo_medio_deslocamento.mean().reset_index()
    fig = px.line(anual, x="ano", y="tempo_medio_deslocamento", markers=True, title="Tempo médio de deslocamento por ano (min)")
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
    var = anual.tempo_medio_deslocamento.iloc[-1] - anual.tempo_medio_deslocamento.iloc[0]
    inclinacao = np.polyfit(anual.ano, anual.tempo_medio_deslocamento, 1)[0] if len(anual) > 1 else 0.0
    st.info(f"**Interpretação:** entre {int(anual.ano.iloc[0])} e {int(anual.ano.iloc[-1])}, o tempo médio de deslocamento "
            f"variou {var:+.1f} min e a tendência linear (NumPy) é de {inclinacao:+.2f} min por ano. "
            "Valores próximos de zero indicam estabilidade, não piora estrutural.")

with t2:
    col_a, col_b = st.columns(2)
    reg = f.groupby("regiao").agg(passageiros=("passageiros", "sum"), cidades=("cidade", "nunique"),
                                  tempo=("tempo_medio_deslocamento", "mean"), cong=("nivel_num", "mean")).reset_index()
    reg["passageiros_por_cidade"] = reg.passageiros / reg.cidades
    col_a.plotly_chart(px.bar(reg, x="regiao", y="passageiros", title="Passageiros por região (total)"), use_container_width=True)
    col_b.plotly_chart(px.bar(reg, x="regiao", y="passageiros_por_cidade", title="Passageiros por cidade (média regional)"),
                       use_container_width=True)
    n = st.slider("Quantidade de cidades no ranking", 5, 20, 10)
    top = por_cidade.sort_values(ascending=False).head(n).reset_index().sort_values("passageiros")
    st.plotly_chart(px.bar(top, x="passageiros", y="cidade", orientation="h", title=f"Top {n} cidades por passageiros"),
                    use_container_width=True)
    pressao = reg.sort_values("cong", ascending=False).iloc[0]
    st.info(f"**Interpretação:** o total por região depende do número de cidades na base; a média por cidade permite comparação mais justa. "
            f"Maior congestionamento médio no recorte: **{pressao.regiao}** ({pressao.cong:.2f}/4). Diferenças regionais são pequenas.")

with t3:
    modal = f.groupby("meio_transporte").agg(passageiros=("passageiros", "sum"), tempo=("tempo_medio_deslocamento", "mean"),
                                             lotacao=("lotacao_media", "mean"), velocidade=("velocidade_media", "mean"),
                                             tarifa=("tarifa_media", "mean")).reset_index()
    col_a, col_b = st.columns(2)
    col_a.plotly_chart(px.bar(modal.sort_values("passageiros"), x="passageiros", y="meio_transporte", orientation="h",
                              title="Passageiros por meio de transporte"), use_container_width=True)
    col_b.plotly_chart(px.pie(modal, names="meio_transporte", values="passageiros", title="Participação modal"), use_container_width=True)
    metrica = st.selectbox("Comparar meios de transporte por", ["tempo", "lotacao", "velocidade", "tarifa"])
    st.plotly_chart(px.bar(modal, x="meio_transporte", y=metrica, title=f"Média de {metrica} por meio de transporte"), use_container_width=True)
    st.info(f"**Interpretação:** **{por_modal.idxmax()}** lidera em passageiros, mas a diferença para os demais modais é pequena. "
            "Isso sugere uso equilibrado entre os modais na base simulada.")

with t4:
    col_a, col_b = st.columns(2)
    dist = f.nivel_congestionamento.value_counts().reindex(ORDEM).reset_index()
    dist.columns = ["nivel", "registros"]
    col_a.plotly_chart(px.bar(dist, x="nivel", y="registros", color="nivel", title="Registros por nível de congestionamento"),
                       use_container_width=True)
    mix = f.groupby(["meio_transporte", "nivel_congestionamento"], observed=True).size().reset_index(name="n")
    col_b.plotly_chart(px.bar(mix, x="meio_transporte", y="n", color="nivel_congestionamento", barmode="stack",
                              category_orders={"nivel_congestionamento": ORDEM}, title="Congestionamento por meio de transporte"),
                       use_container_width=True)
    st.subheader("Períodos críticos (ano × mês)")
    st.caption("A base não possui hora do dia; o mapa de calor usa o período mensal como proxy de horários críticos.")
    heat = f.pivot_table(index="ano", columns="mes", values="nivel_num", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.heatmap(heat, annot=True, fmt=".1f", cmap="rocket_r", ax=ax, cbar_kws={"label": "1=Baixo … 4=Crítico"})
    ax.set(xlabel="Mês", ylabel="")
    st.pyplot(fig)
    st.info("**Interpretação:** níveis de congestionamento aparecem em proporções semelhantes e sem sazonalidade marcante.")

with t5:
    st.subheader("Passageiros × tempo de deslocamento")
    amostra = f.sample(min(len(f), 1500), random_state=1)
    st.plotly_chart(px.scatter(amostra, x="passageiros", y="tempo_medio_deslocamento", color="meio_transporte", opacity=.6,
                               trendline=None, title="Dispersão (amostra de até 1.500 registros)"), use_container_width=True)
    r = f.passageiros.corr(f.tempo_medio_deslocamento)
    st.metric("Correlação de Pearson (passageiros × tempo)", f"{r:.3f}")
    cols = ["passageiros", "tempo_medio_deslocamento", "lotacao_media", "velocidade_media", "emissao_co2", "tarifa_media", "nivel_num"]
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(f[cols].corr(), annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, ax=ax)
    st.pyplot(fig)
    st.subheader("Análise ambiental")
    em = f.groupby("meio_transporte").agg(emissao_total=("emissao_co2", "sum"), co2_por_1000=("co2_por_1000_pass", "mean")).reset_index()
    col_a, col_b = st.columns(2)
    col_a.plotly_chart(px.bar(em, x="meio_transporte", y="emissao_total", title="Emissão total de CO₂ (estimada)"), use_container_width=True)
    col_b.plotly_chart(px.bar(em, x="meio_transporte", y="co2_por_1000", title="CO₂ por 1.000 passageiros"), use_container_width=True)
    forca = "desprezível" if abs(r) < 0.1 else "fraca" if abs(r) < 0.3 else "moderada ou forte"
    st.info(f"**Interpretação:** correlação {forca} (r = {r:.3f}). Mais passageiros não implicam maior tempo de deslocamento nesta base; "
            "em dados reais, esperaríamos relações mais claras entre lotação, velocidade e congestionamento.")

with t6:
    st.subheader("Tabela dinâmica")
    dim = st.selectbox("Linhas", ["cidade", "regiao", "uf", "meio_transporte", "ano"])
    tabela = f.pivot_table(index=dim, columns="nivel_congestionamento", values="passageiros", aggfunc="count", observed=True, fill_value=0)
    tabela.columns = tabela.columns.astype(str)
    tabela["passageiros_total"] = f.groupby(dim).passageiros.sum()
    tabela["tempo_medio"] = f.groupby(dim).tempo_medio_deslocamento.mean().round(1)
    st.dataframe(tabela, use_container_width=True)
    st.subheader("Dados filtrados")
    st.dataframe(f.drop(columns=["nivel_num"]), use_container_width=True, height=300)
    st.download_button("⬇️ Baixar dados filtrados (CSV)", f.to_csv(index=False).encode("utf-8-sig"), "mobilidade_filtrada.csv", "text/csv")

    st.subheader("Conclusão executiva")
    st.success(
        f"No recorte selecionado ({fmt(len(f))} registros), foram transportados **{fmt(f.passageiros.sum())} passageiros**. "
        f"**{por_cidade.idxmax()}** é a cidade mais movimentada e **{por_modal.idxmax()}** o meio predominante, "
        f"com tempo médio de deslocamento de **{f.tempo_medio_deslocamento.mean():.1f} min** e nível médio de congestionamento de "
        f"**{f.nivel_num.mean():.2f}/4**. As diferenças entre cidades, regiões e modais são pequenas e as correlações próximas de zero, "
        "o que é característico de dados simulados. **Recomendação:** incorporar população, horário e dados oficiais (IBGE/ANTP) "
        "para identificar gargalos reais e priorizar investimentos."
    )
