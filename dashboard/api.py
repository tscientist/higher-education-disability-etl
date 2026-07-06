from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

import consultas as q
from db import collection_counts, get_database_name, ping


app = FastAPI(
    title="API Educacao Superior PcD",
    description=(
        "Endpoints para expor as consultas MongoDB do dashboard de educacao "
        "superior e estudantes com deficiencia."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _clean_filter(value):
    if value in (None, "", "Todos", "Todas"):
        return None
    return value


def _run_query(pergunta: int | str, descricao: str, fn: Callable[..., Any], **kwargs):
    try:
        data = fn(**kwargs)
        return {
            "pergunta": pergunta,
            "descricao": descricao,
            "filtros": kwargs,
            "total": len(data) if isinstance(data, list) else 1,
            "data": data,
        }
    except (PyMongoError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/", tags=["sistema"])
def root():
    return {
        "service": "API Educacao Superior PcD",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["sistema"])
def healthcheck():
    try:
        ping()
        counts = collection_counts()
        return {
            "status": "ok",
            "database": get_database_name(),
            "collections": counts,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "message": str(exc)},
        ) from exc


@app.get("/api/v1/opcoes", tags=["sistema"])
def get_opcoes():
    return {
        "anos": q.listar_anos(),
        "ufs": q.listar_ufs(),
        "regioes": sorted(set(q.UF_REGIAO.values())),
        "modalidades": q.listar_modalidades(),
        "categorias": q.listar_categorias(),
    }


@app.get("/api/v1/resumo", tags=["analises"])
def get_resumo(
    ano: int | None = Query(default=None),
    uf: str | None = Query(default=None),
    modalidade: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
):
    return _run_query(
        "resumo",
        "Indicadores gerais para os filtros informados.",
        q.get_resumo_geral,
        ano=ano,
        uf=_clean_filter(uf),
        modalidade=_clean_filter(modalidade),
        categoria=_clean_filter(categoria),
    )


@app.get(
    "/api/v1/perguntas/1",
    tags=["perguntas"],
    summary="Pergunta 1 - Evolucao anual",
    description="Como evoluiu o numero de matriculas de estudantes com deficiencia no ensino superior brasileiro ao longo dos anos?",
)
def pergunta_1(
    ano_inicio: int | None = Query(default=None),
    ano_fim: int | None = Query(default=None),
):
    return _run_query(
        1,
        "Como evoluiu o numero de matriculas de estudantes PcD ao longo dos anos?",
        q.get_evolucao_matriculas_pcd,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
    )


@app.get(
    "/api/v1/perguntas/2",
    tags=["perguntas"],
    summary="Pergunta 2 - Regioes e UFs",
    description="Quais regioes e UFs concentram maior quantidade de matriculas PcD?",
)
def pergunta_2(
    ano: int | None = Query(default=None),
    nivel: str = Query(default="uf", pattern="^(uf|regiao|ambos)$"),
):
    if nivel == "regiao":
        data = q.get_matriculas_pcd_por_regiao(ano=ano)
    elif nivel == "ambos":
        data = {
            "ufs": q.get_matriculas_pcd_por_uf(ano=ano),
            "regioes": q.get_matriculas_pcd_por_regiao(ano=ano),
        }
        return {
            "pergunta": 2,
            "descricao": "Quais regioes e UFs concentram mais matriculas PcD?",
            "filtros": {"ano": ano, "nivel": nivel},
            "total": {
                "ufs": len(data["ufs"]),
                "regioes": len(data["regioes"]),
            },
            "data": data,
        }
    else:
        data = q.get_matriculas_pcd_por_uf(ano=ano)

    return {
        "pergunta": 2,
        "descricao": "Quais regioes e UFs concentram mais matriculas PcD?",
        "filtros": {"ano": ano, "nivel": nivel},
        "total": len(data),
        "data": data,
    }


@app.get(
    "/api/v1/perguntas/3",
    tags=["perguntas"],
    summary="Pergunta 3 - Modalidade x categoria",
    description="A distribuicao de estudantes PcD muda entre cursos presenciais e cursos EAD?",
)
def pergunta_3(ano: int | None = Query(default=None)):
    return _run_query(
        3,
        "A distribuicao de estudantes PcD muda entre cursos presenciais e EAD?",
        q.get_distribuicao_pcd_modalidade_categoria,
        ano=ano,
    )


@app.get(
    "/api/v1/perguntas/4",
    tags=["perguntas"],
    summary="Pergunta 4 - Categoria administrativa",
    description="Quais categorias administrativas de IES apresentam maior participacao de estudantes PcD?",
)
def pergunta_4(ano: int | None = Query(default=None)):
    return _run_query(
        4,
        "Quais categorias administrativas apresentam maior participacao PcD?",
        q.get_ranking_categoria_administrativa,
        ano=ano,
    )


@app.get(
    "/api/v1/perguntas/5",
    tags=["perguntas"],
    summary="Pergunta 5 - Conclusao por regiao",
    description="Como se compara a taxa de conclusao geral com a taxa de conclusao PcD por regiao?",
)
def pergunta_5(ano: int | None = Query(default=None)):
    return _run_query(
        5,
        "Comparacao entre taxa de conclusao geral e taxa de conclusao PcD por regiao.",
        q.get_taxa_conclusao_por_regiao,
        ano=ano,
    )


@app.get(
    "/api/v1/perguntas/6",
    tags=["perguntas"],
    summary="Pergunta 6 - Taxa de perda por UF",
    description="Em quais UFs a taxa de perda PcD e maior em comparacao com a taxa de perda geral?",
)
def pergunta_6(ano: int | None = Query(default=None)):
    return _run_query(
        6,
        "UFs onde a taxa de perda PcD e maior em comparacao com a taxa geral.",
        q.get_taxa_perda_por_uf,
        ano=ano,
    )


@app.get(
    "/api/v1/perguntas/7",
    tags=["perguntas"],
    summary="Pergunta 7 - Funil SISU PcD",
    description="Como o funil de acesso pelo SISU se comporta para candidatos PcD?",
)
def pergunta_7(ano: int | None = Query(default=None)):
    return _run_query(
        7,
        "Funil de acesso SISU para candidatos PcD.",
        q.get_funil_sisu_pcd,
        ano=ano,
    )


@app.get(
    "/api/v1/perguntas/8",
    tags=["perguntas"],
    summary="Pergunta 8 - SISU x Censo",
    description="Existe relacao entre a demanda por vagas PcD no SISU e as matriculas PcD registradas no Censo?",
)
def pergunta_8(
    ano: int | None = Query(default=None),
    uf: str | None = Query(default=None),
    usar_lookup: bool = Query(
        default=False,
        description="Quando true, usa $lookup com a colecao sisu_aggregated.",
    ),
):
    fn = q.get_demanda_sisu_vs_censo_lookup if usar_lookup else q.get_demanda_sisu_vs_matriculas_censo
    return _run_query(
        8,
        "Relacao entre demanda PcD no SISU e matriculas PcD registradas no Censo.",
        fn,
        ano=ano,
        uf=_clean_filter(uf),
    )


@app.get("/api/v1/cursos", tags=["consultas tecnicas"])
def get_cursos(
    ano: int | None = Query(default=None),
    uf: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
):
    return _run_query(
        "find",
        "Exemplo de find com filtros e projecao por UF.",
        q.get_cursos_por_uf,
        ano=ano,
        uf=_clean_filter(uf),
        limit=limit,
    )


@app.get("/api/v1/sisu/demografia/sexo", tags=["consultas tecnicas"])
def get_sisu_por_sexo(
    ano: int | None = Query(default=None),
    sexo: str | None = Query(default=None),
):
    return _run_query(
        "elemMatch",
        "Exemplo de consulta com $elemMatch em sisu.demografia.porSexo.",
        q.get_sisu_por_demografia_sexo,
        ano=ano,
        sexo=_clean_filter(sexo),
    )


@app.post("/api/v1/indices", tags=["consultas tecnicas"])
def criar_indices():
    try:
        created = q.create_indexes()
        return {"status": "ok", "indices": created}
    except PyMongoError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/explain", tags=["consultas tecnicas"])
def get_explain(
    ano: int = Query(...),
    uf: str = Query(..., min_length=2, max_length=2),
):
    try:
        explain = q.get_explain_consulta_indexada(ano, uf.upper())
        stages = q.detectar_estagios_explain(explain)
        return {
            "status": "ok",
            "filtros": {"ano": ano, "uf": uf.upper()},
            "usaIXSCAN": stages["usa_ixscan"],
            "usaCOLLSCAN": stages["usa_collscan"],
            "explain": explain,
        }
    except (PyMongoError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
