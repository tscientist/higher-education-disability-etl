from bson import ObjectId

from db import GOLD_COLLECTION, SISU_COLLECTION, get_db, get_gold_collection, get_sisu_collection


UF_REGIAO = {
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}


def _serialize(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _as_list(cursor):
    return [_serialize(doc) for doc in cursor]


def _year_match(ano=None, ano_inicio=None, ano_fim=None):
    match = {}
    if ano is not None:
        match["ano"] = int(ano)
    elif ano_inicio is not None or ano_fim is not None:
        interval = {}
        if ano_inicio is not None:
            interval["$gte"] = int(ano_inicio)
        if ano_fim is not None:
            interval["$lte"] = int(ano_fim)
        match["ano"] = interval
    return match


def _optional_match(ano=None, uf=None, modalidade=None, categoria=None):
    match = _year_match(ano=ano)
    if uf and uf != "Todos":
        match["uf"] = uf
    if modalidade and modalidade != "Todas":
        match["curso.tipoModalidadeEnsino"] = modalidade
    if categoria and categoria != "Todas":
        match["ies.tipoCategoriaAdministrativa"] = categoria
    return match


def _safe_percent(numerator, denominator):
    return {
        "$cond": [
            {"$eq": [denominator, 0]},
            0,
            {"$round": [{"$multiply": [{"$divide": [numerator, denominator]}, 100]}, 2]},
        ]
    }


def listar_anos():
    return sorted(get_gold_collection().distinct("ano"))


def listar_ufs():
    return sorted(uf for uf in get_gold_collection().distinct("uf") if uf)


def listar_modalidades():
    return sorted(
        item for item in get_gold_collection().distinct("curso.tipoModalidadeEnsino") if item
    )


def listar_categorias():
    return sorted(
        item for item in get_gold_collection().distinct("ies.tipoCategoriaAdministrativa") if item
    )


def get_resumo_geral(ano=None, uf=None, modalidade=None, categoria=None):
    match = _optional_match(ano, uf, modalidade, categoria)
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "cursos": {"$sum": 1},
                "instituicoesSet": {"$addToSet": "$ies.idIes"},
                "matriculas": {"$sum": "$indicadoresAluno.matriculas"},
                "matriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                "sisuInscricoesPcd": {"$sum": "$sisu.inscricoesPcd"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "cursos": 1,
                "instituicoes": {"$size": "$instituicoesSet"},
                "matriculas": 1,
                "matriculasPcd": 1,
                "sisuInscricoesPcd": 1,
                "percentualPcd": _safe_percent("$matriculasPcd", "$matriculas"),
            }
        },
    ]
    result = _as_list(get_gold_collection().aggregate(pipeline))
    return result[0] if result else {}


# Requisito find com filtros, projecoes e dot notation.
def get_cursos_por_uf(ano=None, uf=None, limit=100):
    filtro = _optional_match(ano=ano, uf=uf)
    projection = {
        "uf": 1,
        "ies.sigla": 1,
        "ies.nome": 1,
        "curso.nome": 1,
        "curso.tipoModalidadeEnsino": 1,
        "indicadoresAluno.matriculas": 1,
        "indicadoresDeficiencia.matriculas": 1,
        "metricasCalculadas.percentualMatriculasPcd": 1,
    }
    cursor = (
        get_gold_collection()
        .find(filtro, projection)
        .sort("indicadoresDeficiencia.matriculas", -1)
        .limit(int(limit))
    )
    return _as_list(cursor)


# Requisito 1: evolucao anual de matriculas PcD.
def get_evolucao_matriculas_pcd(ano_inicio=None, ano_fim=None):
    pipeline = [
        {"$match": _year_match(ano_inicio=ano_inicio, ano_fim=ano_fim)},
        {
            "$group": {
                "_id": "$ano",
                "matriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                "matriculasTotal": {"$sum": "$indicadoresAluno.matriculas"},
                "cursos": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "ano": "$_id",
                "matriculasPcd": 1,
                "matriculasTotal": 1,
                "cursos": 1,
                "percentualPcd": _safe_percent("$matriculasPcd", "$matriculasTotal"),
            }
        },
        {"$sort": {"ano": 1}},
    ]
    return _as_list(get_gold_collection().aggregate(pipeline))


# Requisito 2: concentracao por UF.
def get_matriculas_pcd_por_uf(ano=None):
    pipeline = [
        {"$match": _year_match(ano=ano)},
        {
            "$group": {
                "_id": "$uf",
                "matriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                "matriculasTotal": {"$sum": "$indicadoresAluno.matriculas"},
                "cursos": {"$sum": 1},
                "instituicoesSet": {"$addToSet": "$ies.idIes"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "uf": "$_id",
                "regiao": {"$literal": None},
                "matriculasPcd": 1,
                "matriculasTotal": 1,
                "cursos": 1,
                "instituicoes": {"$size": "$instituicoesSet"},
                "percentualPcd": _safe_percent("$matriculasPcd", "$matriculasTotal"),
            }
        },
        {"$sort": {"matriculasPcd": -1}},
    ]
    docs = _as_list(get_gold_collection().aggregate(pipeline))
    for doc in docs:
        doc["regiao"] = UF_REGIAO.get(doc.get("uf"), "Nao informado")
    return docs


def get_matriculas_pcd_por_regiao(ano=None):
    por_uf = get_matriculas_pcd_por_uf(ano)
    regioes = {}
    for row in por_uf:
        regiao = row["regiao"]
        current = regioes.setdefault(
            regiao,
            {
                "regiao": regiao,
                "matriculasPcd": 0,
                "matriculasTotal": 0,
                "cursos": 0,
                "instituicoes": 0,
            },
        )
        current["matriculasPcd"] += row.get("matriculasPcd", 0) or 0
        current["matriculasTotal"] += row.get("matriculasTotal", 0) or 0
        current["cursos"] += row.get("cursos", 0) or 0
        current["instituicoes"] += row.get("instituicoes", 0) or 0
    results = list(regioes.values())
    for row in results:
        total = row["matriculasTotal"]
        row["percentualPcd"] = round(row["matriculasPcd"] / total * 100, 2) if total else 0
    return sorted(results, key=lambda item: item["matriculasPcd"], reverse=True)


# Requisito 3: modalidade x categoria administrativa.
def get_distribuicao_pcd_modalidade_categoria(ano=None):
    pipeline = [
        {"$match": _year_match(ano=ano)},
        {
            "$group": {
                "_id": {
                    "modalidade": "$curso.tipoModalidadeEnsino",
                    "categoria": "$ies.tipoCategoriaAdministrativa",
                },
                "matriculasTotal": {"$sum": "$indicadoresAluno.matriculas"},
                "matriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                "cursos": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "modalidade": "$_id.modalidade",
                "categoria": "$_id.categoria",
                "matriculasTotal": 1,
                "matriculasPcd": 1,
                "cursos": 1,
                "percentualPcd": _safe_percent("$matriculasPcd", "$matriculasTotal"),
            }
        },
        {"$sort": {"modalidade": 1, "matriculasPcd": -1}},
    ]
    return _as_list(get_gold_collection().aggregate(pipeline))


# Requisito 4: ranking por categoria administrativa.
def get_ranking_categoria_administrativa(ano=None):
    pipeline = [
        {"$match": _year_match(ano=ano)},
        {
            "$group": {
                "_id": "$ies.tipoCategoriaAdministrativa",
                "matriculasTotal": {"$sum": "$indicadoresAluno.matriculas"},
                "matriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                "cursos": {"$sum": 1},
                "instituicoesSet": {"$addToSet": "$ies.idIes"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "categoria": "$_id",
                "matriculasTotal": 1,
                "matriculasPcd": 1,
                "cursos": 1,
                "instituicoes": {"$size": "$instituicoesSet"},
                "percentualPcd": _safe_percent("$matriculasPcd", "$matriculasTotal"),
            }
        },
        {"$sort": {"percentualPcd": -1, "matriculasPcd": -1}},
    ]
    return _as_list(get_gold_collection().aggregate(pipeline))


# Requisito 5: taxas por regiao usando totais agregados por UF.
def get_taxa_conclusao_por_regiao(ano=None):
    pipeline = [
        {"$match": _year_match(ano=ano)},
        {
            "$group": {
                "_id": "$uf",
                "ingressantes": {"$sum": "$indicadoresAluno.ingressantes"},
                "concluintes": {"$sum": "$indicadoresAluno.concluintes"},
                "ingressantesPcd": {"$sum": "$indicadoresDeficiencia.ingressantes"},
                "concluintesPcd": {"$sum": "$indicadoresDeficiencia.concluintes"},
            }
        },
        {"$project": {"_id": 0, "uf": "$_id", "ingressantes": 1, "concluintes": 1, "ingressantesPcd": 1, "concluintesPcd": 1}},
    ]
    por_uf = _as_list(get_gold_collection().aggregate(pipeline))
    regioes = {}
    for row in por_uf:
        regiao = UF_REGIAO.get(row.get("uf"), "Nao informado")
        current = regioes.setdefault(
            regiao,
            {
                "regiao": regiao,
                "ingressantes": 0,
                "concluintes": 0,
                "ingressantesPcd": 0,
                "concluintesPcd": 0,
            },
        )
        for key in ["ingressantes", "concluintes", "ingressantesPcd", "concluintesPcd"]:
            current[key] += row.get(key, 0) or 0
    results = list(regioes.values())
    for row in results:
        row["taxaConclusaoGeral"] = (
            round(row["concluintes"] / row["ingressantes"] * 100, 2)
            if row["ingressantes"]
            else None
        )
        row["taxaConclusaoPcd"] = (
            round(row["concluintesPcd"] / row["ingressantesPcd"] * 100, 2)
            if row["ingressantesPcd"]
            else None
        )
        if row["taxaConclusaoGeral"] is not None and row["taxaConclusaoPcd"] is not None:
            row["diferenca"] = round(row["taxaConclusaoGeral"] - row["taxaConclusaoPcd"], 2)
        else:
            row["diferenca"] = None
    return sorted(results, key=lambda item: item["regiao"])


# Requisito 6: taxa de perda por UF.
def get_taxa_perda_por_uf(ano=None):
    pipeline = [
        {"$match": _year_match(ano=ano)},
        {
            "$group": {
                "_id": "$uf",
                "ingressantes": {"$sum": "$indicadoresAluno.ingressantes"},
                "concluintes": {"$sum": "$indicadoresAluno.concluintes"},
                "ingressantesPcd": {"$sum": "$indicadoresDeficiencia.ingressantes"},
                "concluintesPcd": {"$sum": "$indicadoresDeficiencia.concluintes"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "uf": "$_id",
                "ingressantes": 1,
                "concluintes": 1,
                "ingressantesPcd": 1,
                "concluintesPcd": 1,
                "taxaPerdaGeral": {
                    "$cond": [
                        {"$eq": ["$ingressantes", 0]},
                        None,
                        {"$round": [{"$multiply": [{"$divide": [{"$subtract": ["$ingressantes", "$concluintes"]}, "$ingressantes"]}, 100]}, 2]},
                    ]
                },
                "taxaPerdaPcd": {
                    "$cond": [
                        {"$eq": ["$ingressantesPcd", 0]},
                        None,
                        {"$round": [{"$multiply": [{"$divide": [{"$subtract": ["$ingressantesPcd", "$concluintesPcd"]}, "$ingressantesPcd"]}, 100]}, 2]},
                    ]
                },
            }
        },
        {
            "$addFields": {
                "diferencaPerdas": {
                    "$cond": [
                        {"$or": [{"$eq": ["$taxaPerdaGeral", None]}, {"$eq": ["$taxaPerdaPcd", None]}]},
                        None,
                        {"$round": [{"$subtract": ["$taxaPerdaPcd", "$taxaPerdaGeral"]}, 2]},
                    ]
                }
            }
        },
        {"$match": {"diferencaPerdas": {"$ne": None}}},
        {"$sort": {"diferencaPerdas": -1}},
    ]
    return _as_list(get_gold_collection().aggregate(pipeline))


# Requisito 7: funil SISU PcD.
def get_funil_sisu_pcd(ano=None):
    aprovados_expr = {"$ifNull": ["$sisu.aprovadosPcd", "$sisu.aprovadosPcdRegular"]}
    pipeline = [
        {"$match": {**_year_match(ano=ano), "sisu.hasMatch": True}},
        {
            "$group": {
                "_id": "$ano",
                "inscricoesPcd": {"$sum": "$sisu.inscricoesPcd"},
                "aprovadosPcd": {"$sum": aprovados_expr},
                "matriculadosPcd": {"$sum": "$sisu.matriculadosPcdFinal"},
                "cursos": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "ano": "$_id",
                "inscricoesPcd": 1,
                "aprovadosPcd": 1,
                "matriculadosPcd": 1,
                "cursos": 1,
                "taxaAprovacao": _safe_percent("$aprovadosPcd", "$inscricoesPcd"),
                "taxaMatricula": _safe_percent("$matriculadosPcd", "$aprovadosPcd"),
                "taxaConversao": _safe_percent("$matriculadosPcd", "$inscricoesPcd"),
            }
        },
        {"$sort": {"ano": 1}},
    ]
    return _as_list(get_gold_collection().aggregate(pipeline))


# Requisito 8: demanda SISU embutida x matriculas Censo.
def get_demanda_sisu_vs_matriculas_censo(ano=None, uf=None):
    pipeline = [
        {"$match": {**_year_match(ano=ano), **({"uf": uf} if uf and uf != "Todos" else {}), "sisu.hasMatch": True}},
        {
            "$project": {
                "_id": 1,
                "ano": 1,
                "uf": 1,
                "ies": "$ies.nome",
                "siglaIes": "$ies.sigla",
                "curso": "$curso.nome",
                "demandaPcd": "$sisu.inscricoesPcd",
                "aprovadosPcd": {"$ifNull": ["$sisu.aprovadosPcd", "$sisu.aprovadosPcdRegular"]},
                "matriculadosSisuPcd": "$sisu.matriculadosPcdFinal",
                "matriculasPcdCenso": "$indicadoresDeficiencia.matriculas",
                "razaoDemandaMatricula": {
                    "$cond": [
                        {"$eq": ["$indicadoresDeficiencia.matriculas", 0]},
                        None,
                        {"$round": [{"$divide": ["$sisu.inscricoesPcd", "$indicadoresDeficiencia.matriculas"]}, 2]},
                    ]
                },
            }
        },
        {"$match": {"razaoDemandaMatricula": {"$ne": None}}},
        {"$sort": {"demandaPcd": -1}},
        {"$limit": 500},
    ]
    return _as_list(get_gold_collection().aggregate(pipeline))


# Requisito $lookup: relacionamento por referencia com coleção sisu (novo pipeline).
# A coleção 'sisu' contém microdados brutos — o lookup agrega em pipeline.
def get_demanda_sisu_vs_censo_lookup(ano=None, uf=None):
    match = _year_match(ano=ano)
    if uf and uf != "Todos":
        match["uf"] = uf
    pipeline = [
        {"$match": match},
        {
            "$lookup": {
                "from": SISU_COLLECTION,
                "let": {
                    "v_ano": "$ano",
                    "v_id_ies": "$ies.idIes",
                    "v_id_curso": "$curso.idCurso",
                },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$ano", "$$v_ano"]},
                                    {"$eq": [{"$toString": "$id_ies"}, "$$v_id_ies"]},
                                    {"$eq": [{"$toString": "$id_curso"}, "$$v_id_curso"]},
                                ]
                            }
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                            "inscricoesPcd": {"$sum": {
                                "$cond": [{"$or": [
                                    {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$modalidade_concorrencia", ""]}}, "regex": "defici"}},
                                    {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$tipo_cota", ""]}}, "regex": "defici|pcd"}},
                                ]}, 1, 0]
                            }},
                            "aprovadosPcd": {"$sum": {"$cond": [
                                {"$and": [
                                    {"$eq": ["$status_aprovado", True]},
                                    {"$or": [
                                        {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$modalidade_concorrencia", ""]}}, "regex": "defici"}},
                                        {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$tipo_cota", ""]}}, "regex": "defici|pcd"}},
                                    ]},
                                ]},
                                1, 0
                            ]}},
                            "matriculadosPcd": {"$sum": {"$cond": [
                                {"$and": [
                                    {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$status_matricula", ""]}}, "regex": "matriculado"}},
                                    {"$or": [
                                        {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$modalidade_concorrencia", ""]}}, "regex": "defici"}},
                                        {"$regexMatch": {"input": {"$toLower": {"$ifNull": ["$tipo_cota", ""]}}, "regex": "defici|pcd"}},
                                    ]},
                                ]},
                                1, 0
                            ]}},
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                            "inscricoesPcd": 1,
                            "aprovadosPcd": 1,
                            "matriculadosPcd": 1,
                        }
                    },
                ],
                "as": "sisuRef",
            }
        },
        {"$unwind": {"path": "$sisuRef", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 1,
                "ano": 1,
                "uf": 1,
                "ies": "$ies.nome",
                "siglaIes": "$ies.sigla",
                "curso": "$curso.nome",
                "matriculasPcdCenso": "$indicadoresDeficiencia.matriculas",
                "sisuInscricoesPcd": "$sisuRef.inscricoesPcd",
                "sisuAprovadosPcd": "$sisuRef.aprovadosPcd",
                "sisuMatriculadosPcd": "$sisuRef.matriculadosPcd",
                "sisuTemMatch": {"$cond": [{"$ifNull": ["$sisuRef", False]}, True, False]},
            }
        },
        {"$sort": {"sisuInscricoesPcd": -1}},
        {"$limit": 500},
    ]
    return _as_list(get_gold_collection().aggregate(pipeline, allowDiskUse=True))


# Requisito $elemMatch.
def get_sisu_por_demografia_sexo(ano=None, sexo=None):
    filtro = {"sisu.hasMatch": True}
    filtro.update(_year_match(ano=ano))
    if sexo and sexo != "Todos":
        filtro["sisu.demografia.porSexo"] = {"$elemMatch": {"sexo": sexo}}
    projection = {
        "ano": 1,
        "uf": 1,
        "ies.sigla": 1,
        "curso.nome": 1,
        "sisu.demografia.porSexo": 1,
        "sisu.inscricoesPcd": 1,
        "sisu.matriculadosPcdFinal": 1,
    }
    return _as_list(get_gold_collection().find(filtro, projection).limit(100))


def create_indexes():
    gold = get_gold_collection()
    sisu = get_sisu_collection()
    created = []
    created.append(gold.create_index([("ano", 1), ("uf", 1)], name="idx_ano_uf"))
    created.append(
        gold.create_index(
            [("ano", 1), ("indicadoresDeficiencia.matriculas", -1)],
            name="idx_ano_matriculas_pcd",
        )
    )
    created.append(
        gold.create_index(
            [("ano", 1), ("uf", 1), ("indicadoresDeficiencia.matriculas", -1)],
            name="idx_ano_uf_matriculas_pcd",
        )
    )
    created.append(
        gold.create_index(
            [
                ("ano", 1),
                ("curso.tipoModalidadeEnsino", 1),
                ("ies.tipoCategoriaAdministrativa", 1),
            ],
            name="idx_ano_modalidade_categoria",
        )
    )
    created.append(
        gold.create_index(
            [("ano", 1), ("ies.idIes", 1), ("curso.idCurso", 1)],
            name="idx_ano_ies_curso",
        )
    )
    # coleção sisu (microdados brutos) — chave de join usada pelo $lookup
    created.append(
        sisu.create_index(
            [("ano", 1), ("id_ies", 1), ("id_curso", 1)],
            name="idx_sisu_ano_ies_curso",
        )
    )
    return created


def get_explain_consulta_indexada(ano, uf):
    filtro = {"ano": int(ano), "uf": uf}
    projection = {
        "ies.sigla": 1,
        "curso.nome": 1,
        "indicadoresDeficiencia.matriculas": 1,
    }
    cursor = (
        get_gold_collection()
        .find(filtro, projection)
        .sort("indicadoresDeficiencia.matriculas", -1)
        .limit(50)
    )
    return _serialize(cursor.explain())


def detectar_estagios_explain(explain):
    text = str(explain)
    return {
        "usa_ixscan": "IXSCAN" in text,
        "usa_collscan": "COLLSCAN" in text,
    }


def sample_pipeline_lookup():
    return [
        {"$match": {"ano": 2022, "uf": "SP"}},
        {
            "$lookup": {
                "from": SISU_COLLECTION,
                "let": {"v_ano": "$ano", "v_id_ies": "$ies.idIes", "v_id_curso": "$curso.idCurso"},
                "pipeline": [{"$match": {"$expr": {"$and": ["..."]}}}],
                "as": "sisuRef",
            }
        },
    ]
