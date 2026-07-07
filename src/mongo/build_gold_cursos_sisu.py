"""
build_gold_cursos_sisu.py
=========================
Constrói a collection 'gold_cursos_sisu' a partir das collections
'cursos', 'ies' e 'sisu' já carregadas no MongoDB.

O join é feito inteiramente via aggregation pipeline do MongoDB
(escrito explicitamente com $lookup + $group), sem uso de métodos
de alto nível do pymongo.

Uso:
    python src/mongo/build_gold_cursos_sisu.py
    python src/mongo/build_gold_cursos_sisu.py --batch-size 5000 --drop-existing
"""

import argparse
import datetime as dt
import math
import os

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

# ---------------------------------------------------------------------------
# $jsonSchema — validator aplicado à collection gold_cursos_sisu
# Cobre: campos obrigatórios, tipos, subdocumentos, arrays de objetos
# e campos opcionais (notas SISU podem ser null quando sem PcD suficiente).
# ---------------------------------------------------------------------------
GOLD_SCHEMA_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "title": "gold_cursos_sisu v1",
        "required": [
            "_id", "schemaVersion", "ano", "uf",
            "ies", "curso",
            "indicadoresAluno", "indicadoresDeficiencia",
            "sisu", "metricasCalculadas", "etlMetadata",
        ],
        "properties": {
            "_id":           {"bsonType": "string",  "description": "PK: ano_idIes_idCurso_idMunicipio"},
            "schemaVersion": {"bsonType": "int",     "minimum": 1},
            "ano":           {"bsonType": "int",     "minimum": 2000, "maximum": 2100},
            "uf":            {"bsonType": "string",  "minLength": 2, "maxLength": 2},
            "idMunicipio":   {"bsonType": "string"},
            # ── Embedded reference: IES ──────────────────────────────────
            "ies": {
                "bsonType": "object",
                "required": ["idIes"],
                "description": "Embedded reference — campos frequentes da IES",
                "properties": {
                    "idIes":  {"bsonType": "string"},
                    "nome":   {"bsonType": "string"},
                    "sigla":  {"bsonType": "string"},
                    "tipoOrganizacaoAcademica":    {"bsonType": "string"},
                    "tipoCategoriaAdministrativa": {"bsonType": "string"},
                    "endereco": {"bsonType": "object"},
                },
            },
            # ── Embedded reference: Curso ────────────────────────────────
            "curso": {
                "bsonType": "object",
                "required": ["idCurso", "nome"],
                "description": "Embedded reference — campos frequentes do curso",
                "properties": {
                    "idCurso":              {"bsonType": "string"},
                    "nome":                 {"bsonType": "string"},
                    "nomeCine":             {"bsonType": "string"},
                    "idCursoCine":          {"bsonType": ["string", "null"]},
                    "areaGeral":            {"bsonType": "object"},
                    "areaEspecifica":       {"bsonType": "object"},
                    "areaDetalhada":        {"bsonType": "object"},
                    "tipoGrauAcademico":    {"bsonType": "string"},
                    "tipoModalidadeEnsino": {"bsonType": "string"},
                    "tipoNivelAcademico":   {"bsonType": "string"},
                    "indicadorGratuito":    {"bsonType": "bool"},
                },
            },
            # ── Subdocumento: indicadores Censo ──────────────────────────
            "indicadoresAluno": {
                "bsonType": "object",
                "properties": {
                    "vagas":        {"bsonType": ["int", "long", "double"], "minimum": 0},
                    "inscritos":    {"bsonType": ["int", "long", "double"], "minimum": 0},
                    "ingressantes": {"bsonType": ["int", "long", "double"], "minimum": 0},
                    "matriculas":   {"bsonType": ["int", "long", "double"], "minimum": 0},
                    "concluintes":  {"bsonType": ["int", "long", "double"], "minimum": 0},
                },
            },
            "indicadoresDeficiencia": {
                "bsonType": "object",
                "properties": {
                    "alunos":       {"bsonType": ["int", "long", "double"], "minimum": 0},
                    "ingressantes": {"bsonType": ["int", "long", "double"], "minimum": 0},
                    "matriculas":   {"bsonType": ["int", "long", "double"], "minimum": 0},
                    "concluintes":  {"bsonType": ["int", "long", "double"], "minimum": 0},
                    "reservaVaga":  {"bsonType": "object"},
                },
            },
            "indicadoresPermanencia": {"bsonType": "object"},
            # ── Subdocumento SISU (opcional quando hasMatch=false) ────────
            "sisu": {
                "bsonType": "object",
                "required": ["hasMatch"],
                "description": "Dados SISU agregados; campos de nota são opcionais (null ok)",
                "properties": {
                    "hasMatch":             {"bsonType": "bool"},
                    "siglaUfIes":           {"bsonType": ["string", "null"]},
                    "inscricoesTotal":      {"bsonType": ["int", "long", "double", "null"]},
                    "inscricoesPcd":        {"bsonType": ["int", "long", "double", "null"]},
                    "aprovadosRegular":     {"bsonType": ["int", "long", "double", "null"]},
                    "aprovadosPcd":         {"bsonType": ["int", "long", "double", "null"]},
                    "matriculadosFinal":    {"bsonType": ["int", "long", "double", "null"]},
                    "matriculadosPcdFinal": {"bsonType": ["int", "long", "double", "null"]},
                    # campos opcionais: podem ser null quando nenhum PcD no grupo
                    "notaCandidatoMediaGeral": {"bsonType": ["double", "int", "null"]},
                    "notaCandidatoMediaPcd":   {"bsonType": ["double", "int", "null"]},
                    "notaCorteMediaGeral":     {"bsonType": ["double", "int", "null"]},
                    "notaCorteMediaPcd":       {"bsonType": ["double", "int", "null"]},
                    "demografia": {
                        "bsonType": "object",
                        "properties": {
                            # array de objetos com campos bem definidos
                            "porSexo": {
                                "bsonType": "array",
                                "items": {
                                    "bsonType": "object",
                                    "required": ["sexo"],
                                    "properties": {
                                        "sexo":             {"bsonType": "string"},
                                        "inscricoes":       {"bsonType": ["int", "long", "double"]},
                                        "inscricoes_pcd":   {"bsonType": ["int", "long", "double"]},
                                        "aprovados_pcd":    {"bsonType": ["int", "long", "double"]},
                                        "matriculados_pcd": {"bsonType": ["int", "long", "double"]},
                                    },
                                },
                            },
                            # array de objetos (faixa etária calculada)
                            "porFaixaEtaria": {
                                "bsonType": "array",
                                "items": {"bsonType": "object"},
                            },
                            # array de objetos (municípios de origem)
                            "porMunicipio": {
                                "bsonType": "array",
                                "items": {"bsonType": "object"},
                            },
                        },
                    },
                },
            },
            # ── Subdocumento: métricas calculadas ────────────────────────
            "metricasCalculadas": {
                "bsonType": "object",
                "properties": {
                    "percentualMatriculasPcd": {"bsonType": ["double", "int", "null"]},
                    "taxaConclusaoGeral":      {"bsonType": ["double", "int", "null"]},
                    "taxaConclusaoPcd":        {"bsonType": ["double", "int", "null"]},
                    "taxaPerdaGeral":          {"bsonType": ["double", "int", "null"]},
                    "taxaPerdaPcd":            {"bsonType": ["double", "int", "null"]},
                },
            },
            # ── Subdocumento: metadados ETL ──────────────────────────────
            "etlMetadata": {
                "bsonType": "object",
                "properties": {
                    # array simples de strings
                    "source":    {"bsonType": "array", "items": {"bsonType": "string"}},
                    "loadedAt":  {"bsonType": "string"},
                    "yearRange": {"bsonType": "object"},
                },
            },
        },
    }
}


def apply_schema_validator(db) -> None:
    """Aplica $jsonSchema como validator na collection gold_cursos_sisu."""
    col_name = "gold_cursos_sisu"
    existing = db.list_collection_names()

    if col_name not in existing:
        db.create_collection(col_name, validator=GOLD_SCHEMA_VALIDATOR,
                             validationLevel="moderate",   # não rejeita docs antigos
                             validationAction="warn")      # warn em vez de error
        log(f"Collection '{col_name}' criada com $jsonSchema validator")
    else:
        db.command("collMod", col_name,
                   validator=GOLD_SCHEMA_VALIDATOR,
                   validationLevel="moderate",
                   validationAction="warn")
        log(f"$jsonSchema validator aplicado em '{col_name}' (collMod)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def get_mongodb_client() -> MongoClient:
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI ou MONGODB_URI nao configurado no .env")
    return MongoClient(
        mongo_uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=60000,
        connectTimeoutMS=60000,
        socketTimeoutMS=600000,
        maxPoolSize=10,
        retryWrites=True,
    )


def safe_div(num, den, decimals=2):
    """Divisão segura com arredondamento."""
    try:
        if den and den != 0:
            return round(float(num) / float(den) * 100, decimals)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


# ---------------------------------------------------------------------------
# Pipeline de aggregation para o SISU
# ---------------------------------------------------------------------------
# Agrupa os microdados do SISU por (ano, id_ies, id_curso) gerando
# os mesmos campos que o documento gold espera em "sisu".
#
# ── Decisão de design: chave de agrupamento (ano, id_ies, id_curso) ──────────
#
# O SISU (br_mec_sisu.microdados) NÃO possui campo de município da OFERTA
# (campus). Os únicos campos de localização são:
#   • id_municipio_candidato / sigla_uf_candidato → município do candidato
#   • sigla_uf_ies → UF da sede da IES (não do polo EaD)
#
# Por isso o agrupamento usa APENAS (ano, id_ies, id_curso), exatamente como
# o BigQuery faz em silver_sisu_aggregated_2022.sql e o join final em
# gold_course_indicators_source_2022.sql (c.ano=s.ano AND c.id_ies=s.id_ies
# AND c.id_curso=s.id_curso — sem id_municipio).
#
# Consequência intencional para cursos EaD:
#   • A coleção 'cursos' (Censo) pode ter N linhas para o mesmo
#     (ano, id_ies, id_curso) — uma por município de polo.
#   • O gold_id usa f"{ano}_{id_ies}_{id_curso}_{id_municipio}" para
#     distinguir cada campus como documento separado.
#   • Todos esses documentos gold de mesmo curso compartilham o MESMO
#     bloco SISU agregado — comportamento correto, pois o SISU opera
#     na granularidade de curso/IES, não de campus/polo.
#
# NOTA: esta aggregation é escrita manualmente como lista de dicts,
# equivalente a executar no mongosh:
#
# db.sisu.aggregate([
#   { $match: { ano: 2022 } },
#   { $group: {
#       _id: { ano: "$ano", id_ies: "$id_ies", id_curso: "$id_curso" },
#       inscricoesTotal:        { $sum: 1 },
#       ...
#   }},
#   ...
# ])
# ---------------------------------------------------------------------------

SISU_AGGREGATION_PIPELINE = [
    # ── 1. filtrar só ano 2022 ───────────────────────────────────────────────
    {"$match": {"ano": 2022}},

    # ── 2. campos computados por candidato ──────────────────────────────────
    # Campos reais do schema SISU:
    #   status_aprovado   → boolean (True/False)
    #   status_matricula  → string  ("Matriculado", "Pendente", ...)
    #   tipo_cota         → string ou null
    #   modalidade_concorrencia → string longa (pode conter "defici")
    #   sexo              → "M" / "F"
    #   sigla_uf_candidato → "SP", "MT", ...
    #   data_nascimento   → "YYYY-MM-DD" string
    {"$addFields": {
        "_is_pcd": {"$or": [
            {"$regexMatch": {
                "input": {"$toLower": {"$ifNull": ["$modalidade_concorrencia", ""]}},
                "regex": "defici"
            }},
            {"$regexMatch": {
                "input": {"$toLower": {"$ifNull": ["$tipo_cota", ""]}},
                "regex": "defici|pcd"
            }},
        ]},
        # status_aprovado é boolean direto
        "_approved": {"$eq": ["$status_aprovado", True]},
        # status_matricula é string: "Matriculado", "Pendente", etc.
        "_enrolled": {"$regexMatch": {
            "input": {"$toLower": {"$ifNull": ["$status_matricula", ""]}},
            "regex": "matriculado"
        }},
        "_sexo_norm": {"$toUpper": {"$substrCP": [
            {"$ifNull": ["$sexo", "N"]}, 0, 1
        ]}},
    }},

    # ── 3a. calcular ano de nascimento a partir de data_nascimento ───────────
    {"$addFields": {
        "_birth_year": {
            "$cond": {
                "if":   {"$gt": ["$data_nascimento", None]},
                "then": {"$year": {"$toDate": "$data_nascimento"}},
                "else": None,
            }
        }
    }},

    # ── 3b. calcular faixa etária (referência: ano 2022) ─────────────────────
    {"$addFields": {
        "_faixa_etaria": {
            "$cond": {
                "if": {"$gt": ["$_birth_year", None]},
                "then": {"$switch": {
                    "branches": [
                        {"case": {"$lte": [{"$subtract": [2022, "$_birth_year"]}, 17]}, "then": "0-17"},
                        {"case": {"$lte": [{"$subtract": [2022, "$_birth_year"]}, 24]}, "then": "18-24"},
                        {"case": {"$lte": [{"$subtract": [2022, "$_birth_year"]}, 29]}, "then": "25-29"},
                        {"case": {"$lte": [{"$subtract": [2022, "$_birth_year"]}, 34]}, "then": "30-34"},
                        {"case": {"$lte": [{"$subtract": [2022, "$_birth_year"]}, 39]}, "then": "35-39"},
                        {"case": {"$lte": [{"$subtract": [2022, "$_birth_year"]}, 49]}, "then": "40-49"},
                        {"case": {"$lte": [{"$subtract": [2022, "$_birth_year"]}, 59]}, "then": "50-59"},
                    ],
                    "default": "60+",
                }},
                "else": "nao_informado",
            }
        }
    }},

    # ── 4. agrupar por (ano, id_ies, id_curso) ───────────────────────────────
    # sigla_uf_ies é capturada com $first (fora do _id) para evitar que
    # variações de NULL vs string fragmentem grupos do mesmo curso/IES.
    # É constante dentro do grupo (atributo da IES), então $first é seguro.
    {"$group": {
        "_id": {
            "ano":      "$ano",
            "id_ies":   {"$toString": "$id_ies"},
            "id_curso": {"$toString": "$id_curso"},
        },
        "siglaUfIes":        {"$first": {"$ifNull": ["$sigla_uf_ies", ""]}},
        "inscricoesTotal":   {"$sum": 1},
        "inscricoesPcd":     {"$sum": {"$cond": ["$_is_pcd", 1, 0]}},
        "aprovadosRegular":  {"$sum": {"$cond": ["$_approved", 1, 0]}},
        "aprovadosPcd":      {"$sum": {"$cond": [{"$and": ["$_is_pcd", "$_approved"]}, 1, 0]}},
        "matriculadosFinal": {"$sum": {"$cond": ["$_enrolled", 1, 0]}},
        "matriculadosPcdFinal": {"$sum": {"$cond": [{"$and": ["$_is_pcd", "$_enrolled"]}, 1, 0]}},

        # Notas médias (candidato e corte)
        "notaCandidatoMediaGeral": {"$avg": "$nota_candidato"},
        "notaCandidatoMediaPcd":   {"$avg": {"$cond": [
            "$_is_pcd", "$nota_candidato", "$$REMOVE"
        ]}},
        "notaCorteMediaGeral": {"$avg": "$nota_corte"},
        "notaCorteMediaPcd":   {"$avg": {"$cond": [
            "$_is_pcd", "$nota_corte", "$$REMOVE"
        ]}},

        # arrays para demografias (sexo)
        "_sexo_items": {"$push": {
            "sexo":             "$_sexo_norm",
            "is_pcd":           "$_is_pcd",
            "is_approved":      "$_approved",
            "is_enrolled":      "$_enrolled",
        }},

        # faixa etaria calculada + municipio/uf do candidato
        "_faixa_items": {"$push": {
            "faixa_etaria": "$_faixa_etaria",
            "id_municipio": {"$toString": {"$ifNull": ["$id_municipio_candidato", ""]}},
            "uf_candidato": {"$ifNull": ["$sigla_uf_candidato", ""]},
            "is_pcd":       "$_is_pcd",
            "is_approved":  "$_approved",
            "is_enrolled":  "$_enrolled",
        }},
    }},

    # ── 5. calcular demografia por sexo ─────────────────────────────────────
    {"$addFields": {
        "_sexo_M": {"$filter": {"input": "$_sexo_items", "cond": {"$eq": ["$$this.sexo", "M"]}}},
        "_sexo_F": {"$filter": {"input": "$_sexo_items", "cond": {"$eq": ["$$this.sexo", "F"]}}},
    }},
    {"$addFields": {
        "demografiaPorSexo": [
            {
                "sexo": "M",
                "inscricoes":        {"$size": "$_sexo_M"},
                "inscricoes_pcd":    {"$size": {"$filter": {"input": "$_sexo_M", "cond": "$$this.is_pcd"}}},
                "aprovados_pcd":     {"$size": {"$filter": {"input": "$_sexo_M", "cond": {"$and": ["$$this.is_pcd", "$$this.is_approved"]}}}},
                "matriculados_pcd":  {"$size": {"$filter": {"input": "$_sexo_M", "cond": {"$and": ["$$this.is_pcd", "$$this.is_enrolled"]}}}},
            },
            {
                "sexo": "F",
                "inscricoes":        {"$size": "$_sexo_F"},
                "inscricoes_pcd":    {"$size": {"$filter": {"input": "$_sexo_F", "cond": "$$this.is_pcd"}}},
                "aprovados_pcd":     {"$size": {"$filter": {"input": "$_sexo_F", "cond": {"$and": ["$$this.is_pcd", "$$this.is_approved"]}}}},
                "matriculados_pcd":  {"$size": {"$filter": {"input": "$_sexo_F", "cond": {"$and": ["$$this.is_pcd", "$$this.is_enrolled"]}}}},
            },
        ],
    }},

    # ── 6. limpar campos temporários ─────────────────────────────────────────
    {"$unset": ["_sexo_M", "_sexo_F", "_sexo_items", "_birth_year", "_faixa_etaria"]},

    # ── 7. projetar campos finais do SISU ─────────────────────────────────────
    {"$project": {
        "_id": 0,
        "ano":          "$_id.ano",
        "id_ies":       "$_id.id_ies",
        "id_curso":     "$_id.id_curso",
        "sigla_uf_ies": "$siglaUfIes",
        "inscricoesTotal": 1,
        "inscricoesPcd": 1,
        "aprovadosRegular": 1,
        "aprovadosPcd": 1,
        "matriculadosFinal": 1,
        "matriculadosPcdFinal": 1,
        "notaCandidatoMediaGeral": {"$round": ["$notaCandidatoMediaGeral", 2]},
        "notaCandidatoMediaPcd":   {"$round": ["$notaCandidatoMediaPcd",   2]},
        "notaCorteMediaGeral":     {"$round": ["$notaCorteMediaGeral",     2]},
        "notaCorteMediaPcd":       {"$round": ["$notaCorteMediaPcd",       2]},
        "demografiaPorSexo": 1,
        "_faixa_items": 1,   # mantemos para o passo Python
    }},
]


# ---------------------------------------------------------------------------
# Helpers de transformação Python (mapeia doc de cursos → gold)
# ---------------------------------------------------------------------------

def _build_ies(ies_doc: dict) -> dict:
    return {
        "idIes": str(ies_doc.get("id_ies", "")),
        "nome": ies_doc.get("nome", ""),
        "sigla": ies_doc.get("sigla", ""),
        "tipoOrganizacaoAcademica": str(ies_doc.get("tipo_organizacao_academica") or ""),
        "tipoCategoriaAdministrativa": str(ies_doc.get("tipo_categoria_administrativa") or ""),
        "endereco": {
            "logradouro": ies_doc.get("endereco", ""),
            "numero":     str(ies_doc.get("numero") or ""),
            "complemento": ies_doc.get("complemento", ""),
            "bairro":     ies_doc.get("bairro", ""),
            "cep":        str(ies_doc.get("cep") or ""),
        },
    }


def _build_curso(c: dict) -> dict:
    return {
        "idCurso": str(c.get("id_curso", "")),
        "nome": c.get("nome_curso", ""),
        "nomeCine": c.get("nome_curso_cine", ""),
        "idCursoCine": c.get("id_curso_cine", ""),
        "areaGeral": {
            "id":   str(c.get("id_area_geral") or ""),
            "nome": c.get("nome_area_geral", ""),
        },
        "areaEspecifica": {
            "id":   str(c.get("id_area_especifica") or ""),
            "nome": c.get("nome_area_especifica", ""),
        },
        "areaDetalhada": {
            "id":   str(c.get("id_area_detalhada") or ""),
            "nome": c.get("nome_area_detalhada", ""),
        },
        "tipoGrauAcademico":    str(c.get("tipo_grau_academico") or ""),
        "tipoModalidadeEnsino": str(c.get("tipo_modalidade_ensino") or ""),
        "tipoNivelAcademico":   str(c.get("tipo_nivel_academico") or ""),
        "indicadorGratuito":    bool(c.get("indicador_gratuito")),
    }


def _build_indicadores_aluno(c: dict) -> dict:
    return {
        "vagas":        c.get("quantidade_vagas", 0) or 0,
        "inscritos":    c.get("quantidade_inscritos", 0) or 0,
        "ingressantes": c.get("quantidade_ingressantes", 0) or 0,
        "matriculas":   c.get("quantidade_matriculas", 0) or 0,
        "concluintes":  c.get("quantidade_concluintes", 0) or 0,
    }


def _build_indicadores_deficiencia(c: dict) -> dict:
    return {
        "alunos":       c.get("quantidade_alunos_deficiencia", 0) or 0,
        "ingressantes": c.get("quantidade_ingressantes_deficiencia", 0) or 0,
        "matriculas":   c.get("quantidade_matriculas_deficiencia", 0) or 0,
        "concluintes":  c.get("quantidade_concluintes_deficiencia", 0) or 0,
        "reservaVaga": {
            "ingressantes": c.get("quantidade_ingressantes_reserva_vaga_deficiencia", 0) or 0,
            "matriculas":   c.get("quantidade_matriculas_reserva_vaga_deficiencia", 0) or 0,
            "concluintes":  c.get("quantidade_concluintes_reserva_vaga_deficiencia", 0) or 0,
        },
    }


def _build_indicadores_permanencia(c: dict) -> dict:
    return {
        "situacao": {
            "trancada":    c.get("quantidade_alunos_situacao_trancada", 0) or 0,
            "desvinculada": c.get("quantidade_alunos_situacao_desvinculada", 0) or 0,
            "transferida": c.get("quantidade_alunos_situacao_transferida", 0) or 0,
            "falecidos":   c.get("quantidade_alunos_situacao_falecidos", 0) or 0,
        },
        "apoioSocial": {
            "alunos":       c.get("quantidade_alunos_apoio_social", 0) or 0,
            "ingressantes": c.get("quantidade_ingressantes_apoio_social", 0) or 0,
            "matriculas":   c.get("quantidade_matriculas_apoio_social", 0) or 0,
            "concluintes":  c.get("quantidade_concluintes_apoio_social", 0) or 0,
        },
        "atividadeExtracurricular": {
            "alunos":       c.get("quantidade_alunos_atividade_extracurricular", 0) or 0,
            "ingressantes": c.get("quantidade_ingressantes_atividade_extracurricular", 0) or 0,
            "matriculas":   c.get("quantidade_matriculas_atividade_extracurricular", 0) or 0,
            "concluintes":  c.get("quantidade_concluintes_atividade_extracurricular", 0) or 0,
        },
        "mobilidadeAcademica": {
            "alunos":       c.get("quantidade_alunos_mobilidade_academica", 0) or 0,
            "ingressantes": c.get("quantidade_ingressantes_mobilidade_academica", 0) or 0,
            "matriculas":   c.get("quantidade_matriculas_mobilidade_academica", 0) or 0,
            "concluintes":  c.get("quantidade_concluintes_mobilidade_academica", 0) or 0,
        },
        "parfor": {
            "alunos":       c.get("quantidade_alunos_parfor", 0) or 0,
            "ingressantes": c.get("quantidade_ingressantes_parfor", 0) or 0,
            "matriculas":   c.get("quantidade_matriculas_parfor", 0) or 0,
            "concluintes":  c.get("quantidade_concluintes_parfor", 0) or 0,
        },
    }


def _build_sisu_block(sisu: dict | None) -> dict:
    if not sisu:
        return {"hasMatch": False}

    # Demografias por faixa etária agrupadas via Python a partir de _faixa_items
    faixa_map: dict = {}
    municipio_map: dict = {}
    for item in sisu.get("_faixa_items", []):
        fe = item.get("faixa_etaria", "nao_informado")
        if fe not in faixa_map:
            faixa_map[fe] = {"inscricoes": 0, "inscricoes_pcd": 0, "aprovados_pcd": 0, "matriculados_pcd": 0}
        faixa_map[fe]["inscricoes"] += 1
        if item.get("is_pcd"):
            faixa_map[fe]["inscricoes_pcd"] += 1
        if item.get("is_pcd") and item.get("is_approved"):
            faixa_map[fe]["aprovados_pcd"] += 1
        if item.get("is_pcd") and item.get("is_enrolled"):
            faixa_map[fe]["matriculados_pcd"] += 1

        mun = item.get("id_municipio", "")
        uf  = item.get("uf_candidato", "")
        if mun:
            key = (mun, uf)
            if key not in municipio_map:
                municipio_map[key] = {"inscricoes": 0, "inscricoes_pcd": 0, "aprovados_pcd": 0, "matriculados_pcd": 0}
            municipio_map[key]["inscricoes"] += 1
            if item.get("is_pcd"):
                municipio_map[key]["inscricoes_pcd"] += 1
            if item.get("is_pcd") and item.get("is_approved"):
                municipio_map[key]["aprovados_pcd"] += 1
            if item.get("is_pcd") and item.get("is_enrolled"):
                municipio_map[key]["matriculados_pcd"] += 1

    por_faixa = [
        {"faixa_etaria": k, **v} for k, v in faixa_map.items()
    ]
    por_municipio = [
        {"id_municipio_candidato": k[0], "uf": k[1], **v}
        for k, v in municipio_map.items()
    ]

    return {
        "hasMatch": True,
        "siglaUfIes":              sisu.get("sigla_uf_ies") or sisu.get("siglaUfIes"),
        "inscricoesTotal":         sisu.get("inscricoesTotal", 0),
        "inscricoesPcd":           sisu.get("inscricoesPcd", 0),
        "aprovadosRegular":        sisu.get("aprovadosRegular", 0),
        "aprovadosPcd":            sisu.get("aprovadosPcd", 0),
        "matriculadosFinal":       sisu.get("matriculadosFinal", 0),
        "matriculadosPcdFinal":    sisu.get("matriculadosPcdFinal", 0),
        "notaCandidatoMediaGeral": sisu.get("notaCandidatoMediaGeral"),
        "notaCandidatoMediaPcd":   sisu.get("notaCandidatoMediaPcd"),
        "notaCorteMediaGeral":     sisu.get("notaCorteMediaGeral"),
        "notaCorteMediaPcd":       sisu.get("notaCorteMediaPcd"),
        "demografia": {
            "porSexo":       sisu.get("demografiaPorSexo", []),
            "porFaixaEtaria": por_faixa,
            "porMunicipio":  por_municipio,
        },
    }


def _build_metricas(ind_aluno: dict, ind_def: dict) -> dict:
    mat_total = ind_aluno.get("matriculas", 0) or 0
    mat_pcd   = ind_def.get("matriculas", 0) or 0
    ing_total = ind_aluno.get("ingressantes", 0) or 0
    ing_pcd   = ind_def.get("ingressantes", 0) or 0
    con_total = ind_aluno.get("concluintes", 0) or 0
    con_pcd   = ind_def.get("concluintes", 0) or 0

    return {
        "percentualMatriculasPcd": safe_div(mat_pcd, mat_total),
        "taxaConclusaoGeral":      safe_div(con_total, ing_total),
        "taxaConclusaoPcd":        safe_div(con_pcd, ing_pcd),
        "taxaPerdaGeral":          safe_div(ing_total - con_total, ing_total),
        "taxaPerdaPcd":            safe_div(ing_pcd - con_pcd, ing_pcd),
    }


def build_gold_document(curso: dict, ies: dict | None, sisu: dict | None) -> dict:
    """Monta o documento gold_cursos_sisu completo."""
    ano       = curso.get("ano", 2022)
    id_ies    = str(curso.get("id_ies", ""))
    id_curso  = str(curso.get("id_curso", ""))
    id_mun    = str(curso.get("id_municipio", ""))

    ind_aluno = _build_indicadores_aluno(curso)
    ind_def   = _build_indicadores_deficiencia(curso)

    return {
        "_id":           f"{ano}_{id_ies}_{id_curso}_{id_mun}",
        "schemaVersion": 1,
        "ano":           ano,
        "uf":            curso.get("sigla_uf", ""),
        "idMunicipio":   id_mun,
        "ies":                    _build_ies(ies) if ies else {"idIes": id_ies},
        "curso":                  _build_curso(curso),
        "indicadoresAluno":       ind_aluno,
        "indicadoresDeficiencia": ind_def,
        "indicadoresPermanencia": _build_indicadores_permanencia(curso),
        "sisu":                   _build_sisu_block(sisu),
        "metricasCalculadas":     _build_metricas(ind_aluno, ind_def),
        "etlMetadata": {
            "source":    ["cursos", "ies", "sisu"],
            "loadedAt":  dt.datetime.utcnow().isoformat(),
            "yearRange": {"start": ano, "end": ano},
        },
    }


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run(database_name: str, batch_size: int, drop_existing: bool, limit: int | None) -> None:
    client = get_mongodb_client()
    db     = client[database_name]

    col_cursos = db["cursos"]
    col_ies    = db["ies"]
    col_sisu   = db["sisu"]
    col_gold   = db["gold_cursos_sisu"]

    try:
        if drop_existing:
            log("Removendo collection gold_cursos_sisu existente...")
            col_gold.drop()

        # ── 0. Aplicar $jsonSchema validator ──────────────────────────────────
        apply_schema_validator(db)
        log("Carregando lookup de IES em memória...")
        ies_index: dict[tuple, dict] = {}
        for doc in col_ies.find({"ano": 2022}, {"_id": 0}):
            key = (doc.get("ano"), str(doc.get("id_ies", "")))
            ies_index[key] = doc
        log(f"  {len(ies_index):,} IES carregadas")

        # ── 2. Agregar SISU via pipeline explícito ────────────────────────────
        log("Executando aggregation pipeline no SISU...")
        # allowDiskUse=True necessário pois os dados podem ultrapassar 100MB RAM
        sisu_cursor = col_sisu.aggregate(
            SISU_AGGREGATION_PIPELINE,
            allowDiskUse=True
        )

        # Chave de lookup: (ano, id_ies, id_curso) — sem id_municipio.
        # O SISU não tem granularidade de campus/polo, apenas de curso/IES.
        # Cursos EaD com múltiplos municípios no Censo receberão o MESMO
        # bloco SISU (correto — espelha o join do BigQuery gold SQL).
        sisu_index: dict[tuple, dict] = {}
        for doc in sisu_cursor:
            key = (doc.get("ano"), str(doc.get("id_ies", "")), str(doc.get("id_curso", "")))
            sisu_index[key] = doc
        log(f"  {len(sisu_index):,} combinações SISU agregadas (chave: ano+id_ies+id_curso)")

        # ── 3. Iterar cursos e construir documentos gold ──────────────────────
        total_cursos = col_cursos.count_documents({"ano": 2022})
        log(f"Total de cursos a processar: {total_cursos:,}")

        query   = {"ano": 2022}
        cursor  = col_cursos.find(query, {"_id": 0})
        if limit:
            cursor = cursor.limit(limit)
            total_cursos = min(total_cursos, limit)

        batch       = []
        total_upsert = 0
        n_sisu_match = 0
        batch_num   = 0
        inicio      = dt.datetime.now()

        for curso in cursor:
            ano      = curso.get("ano", 2022)
            id_ies   = str(curso.get("id_ies", ""))
            id_curso = str(curso.get("id_curso", ""))

            ies  = ies_index.get((ano, id_ies))
            sisu = sisu_index.get((ano, id_ies, id_curso))

            if sisu:
                n_sisu_match += 1

            gold_doc = build_gold_document(curso, ies, sisu)
            batch.append(UpdateOne(
                {"_id": gold_doc["_id"]},
                {"$set": gold_doc},
                upsert=True,
            ))

            if len(batch) >= batch_size:
                batch_num += 1
                result = col_gold.bulk_write(batch, ordered=False)
                total_upsert += result.upserted_count + result.modified_count
                elapsed = (dt.datetime.now() - inicio).seconds
                log(
                    f"Batch {batch_num}: {len(batch):,} docs"
                    f" | acumulado: {total_upsert:,}"
                    f" | SISU match: {n_sisu_match:,}"
                    f" | {elapsed}s"
                )
                batch = []

        # flush último batch
        if batch:
            batch_num += 1
            result = col_gold.bulk_write(batch, ordered=False)
            total_upsert += result.upserted_count + result.modified_count
            elapsed = (dt.datetime.now() - inicio).seconds
            log(
                f"Batch {batch_num} (final): {len(batch):,} docs"
                f" | acumulado: {total_upsert:,}"
                f" | SISU match: {n_sisu_match:,}"
                f" | {elapsed}s"
            )

        # ── 4. Criar índices na collection gold ───────────────────────────────
        log("Criando índices em gold_cursos_sisu...")
        indexes = [
            ([("ano", 1)],                              {}),
            ([("uf", 1), ("ano", 1)],                   {}),
            ([("ies.idIes", 1), ("ano", 1)],            {}),
            ([("curso.idCurso", 1), ("ano", 1)],        {}),
            ([("curso.tipoModalidadeEnsino", 1), ("ano", 1)], {}),
            ([("ies.tipoCategoriaAdministrativa", 1), ("ano", 1)], {}),
            ([("sisu.hasMatch", 1)],                    {}),
            (
                [("ano", 1), ("uf", 1),
                 ("indicadoresDeficiencia.matriculas", -1),
                 ("metricasCalculadas.percentualMatriculasPcd", 1)],
                {"name": "idx_esr_pcd_analysis"},
            ),
        ]
        for keys, opts in indexes:
            try:
                name = col_gold.create_index(keys, **opts)
                log(f"  ok: {name}")
            except Exception as e:
                log(f"  aviso: {e}")

        # ── 5. Resumo ─────────────────────────────────────────────────────────
        total_elapsed = (dt.datetime.now() - inicio).seconds
        final_count   = col_gold.count_documents({})
        log("=" * 60)
        log(f"gold_cursos_sisu construído com sucesso!")
        log(f"  Documentos na collection: {final_count:,}")
        log(f"  Com match SISU:           {n_sisu_match:,} / {total_cursos:,}")
        log(f"  Tempo total:              {total_elapsed}s")
        log("=" * 60)

    finally:
        client.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Constrói gold_cursos_sisu a partir de cursos + ies + sisu no MongoDB"
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MONGO_DATABASE") or os.getenv("MONGODB_DB") or "higher_education",
    )
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument(
        "--drop-existing", action="store_true",
        help="Remove a collection antes de construir"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Processar apenas N cursos (para testes)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    load_dotenv()
    args = parse_args()
    log("=" * 60)
    log("Iniciando build: gold_cursos_sisu")
    log("=" * 60)
    run(
        database_name=args.database,
        batch_size=args.batch_size,
        drop_existing=args.drop_existing,
        limit=args.limit,
    )
