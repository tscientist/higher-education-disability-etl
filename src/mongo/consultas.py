"""
consultas.py
============
Implementa as consultas MongoDB para gold_cursos_sisu cobrindo:

  Q1  — find + projeção: cursos PcD acima de limiar em SP
  Q2  — dot notation + $elemMatch: cursos com PcD feminina matriculada
  Q3  — aggregation: ranking de UF por matrícula PcD
  Q4  — aggregation: distribuição de modalidade de ensino por ano
  Q5  — $lookup: enriquecer gold com dados completos da IES
  Q6  — aggregation: top-10 cursos por taxa de conclusão PcD
  Q7  — explain COLLSCAN vs IXSCAN (demonstra ganho do índice ESR)
  Q8  — aggregation: percentual PcD por área geral do conhecimento

Estrutura de _id e join SISU
─────────────────────────────
  _id  = "{ano}_{id_ies}_{id_curso}_{id_municipio}"
         Há um documento por campus/polo — cursos EaD podem ter N docs.

  sisu = bloco agregado por (ano, id_ies, id_curso), sem id_municipio.
         O SISU (br_mec_sisu.microdados) não tem granularidade de campus;
         todos os polos EaD de um mesmo curso compartilham o mesmo bloco
         SISU (comportamento correto — espelha o join do BigQuery gold SQL).
         sisu.siglaUfIes indica a UF sede da IES registrada no SISU.

Uso:
    python src/mongo/consultas.py
    python src/mongo/consultas.py --query 3
"""

import argparse
import datetime as dt
import json
import os
import pprint

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def get_client() -> MongoClient:
    uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    if not uri:
        raise ValueError("MONGO_URI não configurado no .env")
    return MongoClient(uri, tlsCAFile=certifi.where(),
                       serverSelectionTimeoutMS=30000)


def log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] {msg}")


def separator(label: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {label}")
    print("=" * 70)


def show(docs, limit=3) -> None:
    """Imprime até `limit` documentos de resultado."""
    items = list(docs)
    for i, d in enumerate(items[:limit]):
        pprint.pprint(d, sort_dicts=False)
        if i < min(limit, len(items)) - 1:
            print("-" * 40)
    print(f"\n→ {len(items)} documento(s) retornado(s) (exibindo até {limit})")


# ===========================================================================
# Q1 — find + projeção
# Cursos em SP com % matrícula PcD ≥ 5%, apenas campos essenciais.
# Demonstra: filtro simples, dot notation em campo calculado, projeção.
# ===========================================================================
def q1_filtro_projecao(col):
    separator("Q1 — find + projeção: cursos em SP com % PcD ≥ 5 %")

    # Query
    filtro = {
        "ano": 2022,
        "uf": "SP",
        "metricasCalculadas.percentualMatriculasPcd": {"$gte": 5},
    }
    projecao = {
        "_id": 1,
        "uf": 1,
        "curso.nome": 1,
        "ies.nome": 1,
        "indicadoresDeficiencia.matriculas": 1,
        "metricasCalculadas.percentualMatriculasPcd": 1,
    }
    ordenacao = [("metricasCalculadas.percentualMatriculasPcd", -1)]

    cursor = col.find(filtro, projecao).sort(ordenacao).limit(10)
    show(cursor, limit=3)


# ===========================================================================
# Q2 — dot notation + $elemMatch em array de objetos
# Cursos que têm ao menos 1 mulher PcD matriculada no SISU.
# Demonstra: acesso a array de objetos, $elemMatch, campos aninhados.
# ===========================================================================
def q2_array_elemMatch(col):
    separator("Q2 — $elemMatch: cursos com mulheres PcD matriculadas no SISU")

    filtro = {
        "sisu.hasMatch": True,
        "sisu.demografia.porSexo": {
            "$elemMatch": {
                "sexo": "F",
                "matriculados_pcd": {"$gte": 1},
            }
        },
    }
    projecao = {
        "_id": 1,
        "uf": 1,
        "curso.nome": 1,
        "ies.sigla": 1,
        "sisu.demografia.porSexo": 1,
    }

    cursor = col.find(filtro, projecao).limit(10)
    show(cursor, limit=3)


# ===========================================================================
# Q3 — aggregation: ranking de UF por total de matrículas PcD
# $match → $group → $sort → $project
# ===========================================================================
def q3_ranking_uf_pcd(col):
    separator("Q3 — aggregation: ranking de UF por matrículas PcD (Censo)")

    pipeline = [
        {"$match": {"ano": 2022}},
        {"$group": {
            "_id": "$uf",
            "totalMatriculasPcd":   {"$sum": "$indicadoresDeficiencia.matriculas"},
            "totalMatriculas":      {"$sum": "$indicadoresAluno.matriculas"},
            "totalCursos":          {"$sum": 1},
            "cursosComSisu":        {"$sum": {"$cond": ["$sisu.hasMatch", 1, 0]}},
        }},
        {"$addFields": {
            "percentualPcd": {
                "$cond": {
                    "if":   {"$gt": ["$totalMatriculas", 0]},
                    "then": {"$round": [
                        {"$multiply": [
                            {"$divide": ["$totalMatriculasPcd", "$totalMatriculas"]},
                            100
                        ]}, 2
                    ]},
                    "else": 0,
                }
            }
        }},
        {"$sort": {"totalMatriculasPcd": -1}},
        {"$project": {
            "_id": 0,
            "uf":               "$_id",
            "totalMatriculasPcd": 1,
            "totalMatriculas":    1,
            "percentualPcd":      1,
            "totalCursos":        1,
            "cursosComSisu":      1,
        }},
    ]

    cursor = col.aggregate(pipeline)
    show(cursor, limit=5)


# ===========================================================================
# Q4 — aggregation: cursos por modalidade (presencial vs EaD) e categoria IES
# Demonstra: $group em múltiplos campos, $sort, $project
# ===========================================================================
def q4_modalidade_categoria(col):
    separator("Q4 — aggregation: distribuição modalidade × categoria administrativa")

    pipeline = [
        {"$match": {"ano": 2022}},
        {"$group": {
            "_id": {
                "modalidade": "$curso.tipoModalidadeEnsino",
                "categoria":  "$ies.tipoCategoriaAdministrativa",
            },
            "totalCursos":        {"$sum": 1},
            "totalMatriculas":    {"$sum": "$indicadoresAluno.matriculas"},
            "totalMatriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
        }},
        {"$sort": {"totalCursos": -1}},
        {"$project": {
            "_id": 0,
            "modalidade": "$_id.modalidade",
            "categoria":  "$_id.categoria",
            "totalCursos": 1,
            "totalMatriculas": 1,
            "totalMatriculasPcd": 1,
        }},
        {"$limit": 10},
    ]

    cursor = col.aggregate(pipeline)
    show(cursor, limit=5)


# ===========================================================================
# Q5 — $lookup: enriquecer gold com dados completos da coleção ies
# Demonstra: $lookup (relacionamento por referência), pipeline lookup,
#            $arrayElemAt, $unwind.
# ===========================================================================
def q5_lookup_ies(col_gold, col_ies):
    separator("Q5 — $lookup: enriquecer gold com dados completos da coleção 'ies'")

    pipeline = [
        # filtrar apenas cursos com % PcD relevante
        {"$match": {
            "ano": 2022,
            "metricasCalculadas.percentualMatriculasPcd": {"$gte": 10},
        }},
        # $lookup com pipeline para fazer join por (ano, id_ies)
        {"$lookup": {
            "from": "ies",
            "let":  {"ano_curso": "$ano", "id_ies_curso": "$ies.idIes"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$ano",    "$$ano_curso"]},
                    {"$eq": [{"$toString": "$id_ies"}, "$$id_ies_curso"]},
                ]}}},
                # projetar só os campos extras que não estão no embedded
                {"$project": {
                    "_id": 0,
                    "quantidade_docentes_exercicio": 1,
                    "quantidade_docentes_exercicio_doutorado": 1,
                    "indicador_biblioteca_internet": 1,
                }},
            ],
            "as": "_ies_full",
        }},
        # pegar o primeiro (cada IES aparece uma vez por ano)
        {"$addFields": {
            "ies_extra": {"$arrayElemAt": ["$_ies_full", 0]},
        }},
        {"$unset": "_ies_full"},
        {"$project": {
            "_id": 1,
            "uf": 1,
            "curso.nome": 1,
            "ies.nome": 1,
            "ies.sigla": 1,
            "metricasCalculadas.percentualMatriculasPcd": 1,
            "ies_extra": 1,
        }},
        {"$sort": {"metricasCalculadas.percentualMatriculasPcd": -1}},
        {"$limit": 10},
    ]

    cursor = col_gold.aggregate(pipeline)
    show(cursor, limit=3)


# ===========================================================================
# Q6 — aggregation: top-10 cursos por taxa conclusão PcD com match SISU
# Demonstra: $match, $sort, $limit, $project com campos calculados
# ===========================================================================
def q6_top_conclusao_pcd(col):
    separator("Q6 — top-10 cursos: maior taxa de conclusão PcD (com SISU)")

    pipeline = [
        {"$match": {
            "ano": 2022,
            "sisu.hasMatch": True,
            "metricasCalculadas.taxaConclusaoPcd": {"$gt": 0},
            "indicadoresDeficiencia.ingressantes": {"$gte": 5},  # base mínima
        }},
        {"$sort": {"metricasCalculadas.taxaConclusaoPcd": -1}},
        {"$limit": 10},
        {"$project": {
            "_id": 0,
            "uf": 1,
            "curso.nome": 1,
            "ies.sigla": 1,
            "indicadoresDeficiencia.ingressantes": 1,
            "indicadoresDeficiencia.concluintes": 1,
            "metricasCalculadas.taxaConclusaoPcd": 1,
            "metricasCalculadas.taxaConclusaoGeral": 1,
            "sisu.inscricoesPcd": 1,
        }},
    ]

    cursor = col.aggregate(pipeline)
    show(cursor, limit=5)


# ===========================================================================
# Q7 — explain: COLLSCAN → IXSCAN (demonstra ganho do índice ESR)
# Índice: { ano:1, uf:1, indicadoresDeficiencia.matriculas:-1,
#           metricasCalculadas.percentualMatriculasPcd:1 }
# ===========================================================================
def q7_explain_ixscan(col):
    separator("Q7 — explain: COLLSCAN vs IXSCAN (índice ESR)")

    # pymongo 4.x: Cursor.explain() não aceita argumento de verbosidade.
    # Usar db.command("explain", ...) passando o comando find completo.
    db = col.database
    col_name = col.name

    query_filter = {
        "ano": 2022,
        "uf":  "SP",
        "metricasCalculadas.percentualMatriculasPcd": {"$gte": 5, "$lte": 20},
    }
    sort_spec = {"indicadoresDeficiencia.matriculas": -1}

    def run_explain(hint) -> dict:
        return db.command(
            "explain",
            {
                "find":   col_name,
                "filter": query_filter,
                "sort":   sort_spec,
                "hint":   hint,
            },
            verbosity="executionStats",
        )

    def print_stats(plan: dict, label: str) -> int:
        es = plan.get("executionStats", {})
        stages = es.get("executionStages", {})
        # stage pode estar aninhado em inputStage (FETCH → IXSCAN)
        inner = stages.get("inputStage", stages)
        stage_name = inner.get("stage", stages.get("stage", "?"))
        ms = es.get("executionTimeMillis", 0)
        print(f"\n▸ {label}")
        print(f"  stage:               {stage_name}")
        print(f"  totalKeysExamined:   {es.get('totalKeysExamined', '?')}")
        print(f"  totalDocsExamined:   {es.get('totalDocsExamined', '?')}")
        print(f"  nReturned:           {es.get('nReturned', '?')}")
        print(f"  executionTimeMillis: {ms} ms")
        return ms

    # ── COLLSCAN ─────────────────────────────────────────────────────────────
    plan_collscan = run_explain({"$natural": 1})
    ms_collscan = print_stats(plan_collscan, "COLLSCAN (hint: $natural)")

    # ── IXSCAN (índice ESR) ───────────────────────────────────────────────────
    try:
        plan_ixscan = run_explain("idx_esr_pcd_analysis")
        ms_ixscan = print_stats(plan_ixscan, "IXSCAN (índice ESR: ano+uf+matriculas_pcd+percentual)")

        speedup = round(ms_collscan / max(ms_ixscan, 1))
        print(f"\n  → Speedup estimado: ~{speedup}x mais rápido com índice ESR")
    except Exception as e:
        print(f"\n  Índice ESR ainda não existe: {e}")
        print("  Execute build_gold_cursos_sisu.py primeiro para criar os índices.")


# ===========================================================================
# Q8 — aggregation por área geral do conhecimento
# $match → $group → $sort → $project
# ===========================================================================
def q8_area_geral(col):
    separator("Q8 — aggregation: % PcD por área geral do conhecimento")

    pipeline = [
        {"$match": {"ano": 2022}},
        {"$group": {
            "_id": {
                "areaId":   "$curso.areaGeral.id",
                "areaNome": "$curso.areaGeral.nome",
            },
            "totalCursos":        {"$sum": 1},
            "totalMatriculas":    {"$sum": "$indicadoresAluno.matriculas"},
            "totalMatriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
            "cursosComSisu":      {"$sum": {"$cond": ["$sisu.hasMatch", 1, 0]}},
            "totalInscricoesSisu": {"$sum": {"$ifNull": ["$sisu.inscricoesTotal", 0]}},
            "totalPcdSisu":        {"$sum": {"$ifNull": ["$sisu.inscricoesPcd", 0]}},
        }},
        {"$addFields": {
            "percentualPcdCenso": {
                "$cond": {
                    "if": {"$gt": ["$totalMatriculas", 0]},
                    "then": {"$round": [
                        {"$multiply": [
                            {"$divide": ["$totalMatriculasPcd", "$totalMatriculas"]},
                            100
                        ]}, 2
                    ]},
                    "else": None,
                }
            },
            "percentualPcdSisu": {
                "$cond": {
                    "if": {"$gt": ["$totalInscricoesSisu", 0]},
                    "then": {"$round": [
                        {"$multiply": [
                            {"$divide": ["$totalPcdSisu", "$totalInscricoesSisu"]},
                            100
                        ]}, 2
                    ]},
                    "else": None,
                }
            },
        }},
        {"$sort": {"percentualPcdCenso": -1}},
        {"$project": {
            "_id": 0,
            "areaGeral":           "$_id.areaNome",
            "totalCursos":         1,
            "totalMatriculas":     1,
            "totalMatriculasPcd":  1,
            "percentualPcdCenso":  1,
            "cursosComSisu":       1,
            "percentualPcdSisu":   1,
        }},
    ]

    cursor = col.aggregate(pipeline)
    show(cursor, limit=5)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

QUERIES = {
    1: ("Q1 — find + projeção (SP, PcD ≥ 5%)",            lambda c, ci: q1_filtro_projecao(c)),
    2: ("Q2 — $elemMatch em array (mulheres PcD SISU)",     lambda c, ci: q2_array_elemMatch(c)),
    3: ("Q3 — aggregation ranking UF por PcD",              lambda c, ci: q3_ranking_uf_pcd(c)),
    4: ("Q4 — aggregation modalidade × categoria",          lambda c, ci: q4_modalidade_categoria(c)),
    5: ("Q5 — $lookup IES completa",                        lambda c, ci: q5_lookup_ies(c, ci)),
    6: ("Q6 — top-10 taxa conclusão PcD",                   lambda c, ci: q6_top_conclusao_pcd(c)),
    7: ("Q7 — explain COLLSCAN vs IXSCAN",                  lambda c, ci: q7_explain_ixscan(c)),
    8: ("Q8 — % PcD por área geral",                        lambda c, ci: q8_area_geral(c)),
}


def parse_args():
    p = argparse.ArgumentParser(description="Consultas gold_cursos_sisu")
    p.add_argument(
        "--query", type=int, default=0,
        help="Número da query a rodar (0 = todas, 1-8 = individual)"
    )
    p.add_argument(
        "--database",
        default=os.getenv("MONGO_DATABASE") or os.getenv("MONGODB_DB") or "higher_education",
    )
    return p.parse_args()


def main():
    load_dotenv()
    args = parse_args()

    client  = get_client()
    db      = client[args.database]
    col     = db["gold_cursos_sisu"]
    col_ies = db["ies"]

    total = col.count_documents({})
    log(f"Conectado — gold_cursos_sisu tem {total:,} documentos")

    to_run = [args.query] if args.query else list(QUERIES.keys())

    for n in to_run:
        if n not in QUERIES:
            print(f"Query {n} não existe (use 1-8)")
            continue
        label, fn = QUERIES[n]
        try:
            fn(col, col_ies)
        except Exception as e:
            print(f"\n  [ERRO] {label}: {e}")

    client.close()
    log("Consultas finalizadas")


if __name__ == "__main__":
    main()
