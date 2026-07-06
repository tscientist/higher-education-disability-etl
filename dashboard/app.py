import json

import pandas as pd
import plotly.express as px
import streamlit as st

import consultas as q
from db import collection_counts, get_database_name, ping


st.set_page_config(
    page_title="Educacao Superior PcD",
    layout="wide",
)


def df_from(records):
    return pd.DataFrame(records or [])


def filter_region(df, regiao):
    if df.empty or not regiao or regiao == "Todas" or "regiao" not in df.columns:
        return df
    return df[df["regiao"] == regiao]


def moneyless_int(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def pct(value):
    if value is None:
        return "0,00%"
    try:
        return f"{float(value):.2f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "0,00%"


@st.cache_data(ttl=300)
def load_options():
    anos = q.listar_anos()
    ufs = q.listar_ufs()
    modalidades = q.listar_modalidades()
    categorias = q.listar_categorias()
    return anos, ufs, modalidades, categorias


@st.cache_data(ttl=180)
def cached_resumo(ano, uf, modalidade, categoria):
    return q.get_resumo_geral(ano, uf, modalidade, categoria)


@st.cache_data(ttl=180)
def cached_evolucao(ano_inicio, ano_fim):
    return q.get_evolucao_matriculas_pcd(ano_inicio, ano_fim)


@st.cache_data(ttl=180)
def cached_uf(ano):
    return q.get_matriculas_pcd_por_uf(ano)


@st.cache_data(ttl=180)
def cached_regiao(ano):
    return q.get_matriculas_pcd_por_regiao(ano)


@st.cache_data(ttl=180)
def cached_modalidade_categoria(ano):
    return q.get_distribuicao_pcd_modalidade_categoria(ano)


@st.cache_data(ttl=180)
def cached_categoria(ano):
    return q.get_ranking_categoria_administrativa(ano)


@st.cache_data(ttl=180)
def cached_conclusao_regiao(ano):
    return q.get_taxa_conclusao_por_regiao(ano)


@st.cache_data(ttl=180)
def cached_perda_uf(ano):
    return q.get_taxa_perda_por_uf(ano)


@st.cache_data(ttl=180)
def cached_funil(ano):
    return q.get_funil_sisu_pcd(ano)


@st.cache_data(ttl=180)
def cached_demanda(ano, uf):
    return q.get_demanda_sisu_vs_matriculas_censo(ano, uf)


@st.cache_data(ttl=180)
def cached_lookup(ano, uf):
    return q.get_demanda_sisu_vs_censo_lookup(ano, uf)


@st.cache_data(ttl=180)
def cached_cursos(ano, uf):
    return q.get_cursos_por_uf(ano, uf, limit=100)


@st.cache_data(ttl=180)
def cached_elem_match(ano, sexo):
    return q.get_sisu_por_demografia_sexo(ano, sexo)


try:
    ping()
except Exception as exc:
    st.error(f"Nao foi possivel conectar ao MongoDB: {exc}")
    st.stop()


anos, ufs, modalidades, categorias = load_options()
if not anos:
    st.warning("Nenhum ano encontrado em gold_course_indicators.")
    st.stop()

st.sidebar.title("Filtros")
ano = st.sidebar.selectbox("Ano", ["Todos"] + anos, index=1 if len(anos) else 0)
ano_query = None if ano == "Todos" else int(ano)
ano_inicio, ano_fim = st.sidebar.select_slider(
    "Intervalo de anos",
    options=anos,
    value=(min(anos), max(anos)),
)
uf = st.sidebar.selectbox("UF", ["Todos"] + ufs)
regiao = st.sidebar.selectbox("Regiao", ["Todas", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"])
modalidade = st.sidebar.selectbox("Modalidade", ["Todas"] + modalidades)
categoria = st.sidebar.selectbox("Categoria administrativa", ["Todas"] + categorias)

st.title("Educacao Superior PcD")
st.caption(f"Banco: {get_database_name()} | Colecoes: gold_course_indicators e sisu_aggregated")

PERGUNTAS = {
    "visao_geral": "Visao geral dos indicadores carregados no MongoDB para os filtros selecionados.",
    1: "Pergunta 1: Como evoluiu o numero de matriculas de estudantes com deficiencia no ensino superior brasileiro ao longo dos anos?",
    2: "Pergunta 2: Quais regioes e UFs concentram maior quantidade de matriculas PcD?",
    3: "Pergunta 3: A distribuicao de estudantes PcD muda entre cursos presenciais e cursos EAD?",
    4: "Pergunta 4: Quais categorias administrativas de IES apresentam maior participacao de estudantes PcD?",
    5: "Pergunta 5: Como se compara a taxa de conclusao geral com a taxa de conclusao PcD por regiao?",
    6: "Pergunta 6: Em quais UFs a taxa de perda PcD e maior em comparacao com a taxa de perda geral?",
    7: "Pergunta 7: Como o funil de acesso pelo SISU se comporta para candidatos PcD?",
    8: "Pergunta 8: Existe relacao entre a demanda por vagas PcD no SISU e as matriculas PcD registradas no Censo?",
    "tecnico": "Tecnico / Indices: validacao de colecoes, indices, explain, $elemMatch e $lookup.",
}


def mostrar_pergunta(chave):
    st.info(PERGUNTAS[chave])

tabs = st.tabs(
    [
        "Visao geral",
        "Pergunta 1 - Evolucao anual",
        "Pergunta 2 - Regioes e UFs",
        "Pergunta 3 - Modalidade x Categoria",
        "Pergunta 4 - Categoria administrativa",
        "Pergunta 5 - Conclusao por regiao",
        "Pergunta 6 - Taxa de perda por UF",
        "Pergunta 7 - Funil SISU PcD",
        "Pergunta 8 - SISU x Censo",
        "Tecnico / Indices",
    ]
)

with tabs[0]:
    mostrar_pergunta("visao_geral")
    resumo = cached_resumo(ano_query, uf, modalidade, categoria)
    cols = st.columns(5)
    cols[0].metric("Cursos", moneyless_int(resumo.get("cursos")))
    cols[1].metric("IES", moneyless_int(resumo.get("instituicoes")))
    cols[2].metric("Matriculas", moneyless_int(resumo.get("matriculas")))
    cols[3].metric("Matriculas PcD", moneyless_int(resumo.get("matriculasPcd")))
    cols[4].metric("% PcD", pct(resumo.get("percentualPcd")))

    df_cursos = df_from(cached_cursos(ano_query, uf))
    st.dataframe(df_cursos, use_container_width=True, hide_index=True)

with tabs[1]:
    mostrar_pergunta(1)
    df = df_from(cached_evolucao(ano_inicio, ano_fim))
    if df.empty:
        st.info("Sem resultados para o intervalo selecionado.")
    else:
        fig = px.line(
            df,
            x="ano",
            y="matriculasPcd",
            markers=True,
            labels={"ano": "Ano", "matriculasPcd": "Matriculas PcD"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tabs[2]:
    mostrar_pergunta(2)
    df_uf = filter_region(df_from(cached_uf(ano_query)), regiao)
    df_regiao = df_from(cached_regiao(ano_query))
    left, right = st.columns(2)
    with left:
        if not df_uf.empty:
            fig = px.bar(
                df_uf.head(15),
                x="uf",
                y="matriculasPcd",
                color="regiao",
                labels={"uf": "UF", "matriculasPcd": "Matriculas PcD"},
            )
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_uf, use_container_width=True, hide_index=True)
    with right:
        if not df_regiao.empty:
            fig = px.bar(
                df_regiao,
                x="regiao",
                y="matriculasPcd",
                color="regiao",
                labels={"regiao": "Regiao", "matriculasPcd": "Matriculas PcD"},
            )
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_regiao, use_container_width=True, hide_index=True)

with tabs[3]:
    mostrar_pergunta(3)
    df = df_from(cached_modalidade_categoria(ano_query))
    if modalidade != "Todas" and not df.empty:
        df = df[df["modalidade"] == modalidade]
    if categoria != "Todas" and not df.empty:
        df = df[df["categoria"] == categoria]
    if df.empty:
        st.info("Sem resultados para os filtros selecionados.")
    else:
        fig = px.bar(
            df,
            x="modalidade",
            y="percentualPcd",
            color="categoria",
            barmode="group",
            labels={"modalidade": "Modalidade", "percentualPcd": "% PcD"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tabs[4]:
    mostrar_pergunta(4)
    df = df_from(cached_categoria(ano_query))
    if categoria != "Todas" and not df.empty:
        df = df[df["categoria"] == categoria]
    if df.empty:
        st.info("Sem resultados para os filtros selecionados.")
    else:
        fig = px.bar(
            df,
            x="categoria",
            y="percentualPcd",
            color="matriculasPcd",
            labels={"categoria": "Categoria", "percentualPcd": "% PcD"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tabs[5]:
    mostrar_pergunta(5)
    df = filter_region(df_from(cached_conclusao_regiao(ano_query)), regiao)
    if df.empty:
        st.info("Sem resultados para os filtros selecionados.")
    else:
        melted = df.melt(
            id_vars=["regiao"],
            value_vars=["taxaConclusaoGeral", "taxaConclusaoPcd"],
            var_name="tipo",
            value_name="taxa",
        )
        fig = px.bar(
            melted,
            x="regiao",
            y="taxa",
            color="tipo",
            barmode="group",
            labels={"regiao": "Regiao", "taxa": "Taxa de conclusao (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tabs[6]:
    mostrar_pergunta(6)
    df = df_from(cached_perda_uf(ano_query))
    if not df.empty:
        df["regiao"] = df["uf"].map(q.UF_REGIAO)
        df = filter_region(df, regiao)
    if df.empty:
        st.info("Sem resultados para os filtros selecionados.")
    else:
        fig = px.bar(
            df.head(20),
            x="uf",
            y="diferencaPerdas",
            color="regiao",
            labels={"uf": "UF", "diferencaPerdas": "Diferenca de perdas PcD - geral (p.p.)"},
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tabs[7]:
    mostrar_pergunta(7)
    df = df_from(cached_funil(ano_query))
    if df.empty:
        st.info("Sem dados SISU para os filtros selecionados.")
    else:
        row = df.iloc[-1]
        funnel = pd.DataFrame(
            {
                "etapa": ["Inscricoes PcD", "Aprovados PcD", "Matriculados PcD"],
                "quantidade": [
                    row.get("inscricoesPcd", 0),
                    row.get("aprovadosPcd", 0),
                    row.get("matriculadosPcd", 0),
                ],
            }
        )
        fig = px.funnel(funnel, x="quantidade", y="etapa")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

with tabs[8]:
    mostrar_pergunta(8)
    df = df_from(cached_demanda(ano_query, uf))
    if not df.empty:
        df["regiao"] = df["uf"].map(q.UF_REGIAO)
        df = filter_region(df, regiao)
    if df.empty:
        st.info("Sem resultados com match SISU e matriculas PcD no Censo.")
    else:
        fig = px.scatter(
            df,
            x="demandaPcd",
            y="matriculasPcdCenso",
            color="uf",
            hover_data=["siglaIes", "curso"],
            labels={
                "demandaPcd": "Inscricoes PcD no SISU",
                "matriculasPcdCenso": "Matriculas PcD no Censo",
            },
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

    lookup_df = df_from(cached_lookup(ano_query, uf))
    st.subheader("$lookup: gold_course_indicators -> sisu_aggregated")
    st.dataframe(lookup_df, use_container_width=True, hide_index=True)

with tabs[9]:
    mostrar_pergunta("tecnico")
    counts = collection_counts()
    col_a, col_b = st.columns(2)
    col_a.metric("gold_course_indicators", moneyless_int(counts.get("gold_course_indicators")))
    col_b.metric("sisu_aggregated", moneyless_int(counts.get("sisu_aggregated")))

    if st.button("Criar indices"):
        created = q.create_indexes()
        st.success("Indices prontos: " + ", ".join(created))
        st.cache_data.clear()

    explain_ano = ano_query or int(anos[-1])
    explain_uf = uf if uf != "Todos" else (ufs[0] if ufs else "SP")
    explain = q.get_explain_consulta_indexada(explain_ano, explain_uf)
    stages = q.detectar_estagios_explain(explain)
    cols = st.columns(2)
    cols[0].metric("IXSCAN", "Sim" if stages["usa_ixscan"] else "Nao")
    cols[1].metric("COLLSCAN", "Sim" if stages["usa_collscan"] else "Nao")
    st.json(explain)

    st.subheader("$elemMatch")
    sexo = st.selectbox("Sexo SISU", ["Todos", "F", "M", "Feminino", "Masculino"])
    st.dataframe(df_from(cached_elem_match(ano_query, sexo)), use_container_width=True, hide_index=True)

    st.subheader("Pipeline $lookup")
    st.code(json.dumps(q.sample_pipeline_lookup(), indent=2, ensure_ascii=False), language="json")
