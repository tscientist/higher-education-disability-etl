"""
Queries Avançadas MongoDB com Aggregation Pipeline

Implementa queries sofisticadas usando:
- Aggregation pipeline com múltiplos estágios ($match, $group, $sort, $project, $limit)
- $lookup para joins entre collections
- $unwind para desconstruir arrays
- $elemMatch para buscar em arrays
- Dot notation para acesso a campos embutidos
- $graphLookup para relacionamentos hierárquicos
"""

from ..clients import MongoDBClient
from ..utils.logger import logger


class MongoDBAdvancedQueries:
    """Queries complexas e otimizadas para análises de deficiência no ensino superior"""
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
    
    # ============================================================
    # 1. QUERIES COM $MATCH e $PROJECT (Filtros e Projeções)
    # ============================================================
    
    def find_courses_with_disability_data(self, collection_name, min_disabled_count=1):
        """
        Encontra cursos com dados de deficiência.
        
        Usa: find() com filtros simples e projeção de campos
        
        Args:
            collection_name: Nome da collection
            min_disabled_count: Mínimo de alunos com deficiência
            
        Returns:
            List[dict]: Cursos encontrados
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        # Query com filtro aninhado (dot notation)
        filter_query = {
            "deficiencia.total": {"$gte": min_disabled_count},
            "status": "ativo"
        }
        
        # Projeção seletiva de campos
        projection = {
            "_id": 1,
            "nome_curso": 1,
            "sigla_ies": 1,
            "deficiencia": 1,
            "ano": 1,
            "inscricoes": 1
        }
        
        logger.info(f"Buscando cursos com deficiência (mínimo: {min_disabled_count})")
        results = list(collection.find(filter_query, projection))
        logger.info(f"Encontrados {len(results)} cursos")
        
        return results
    
    def find_ies_by_region(self, collection_name, regiao):
        """
        Encontra todas as instituições em uma região.
        
        Usa: find() com dot notation para campos aninhados
        
        Args:
            collection_name: Nome da collection
            regiao: Região (nordeste, sudeste, sul, norte, centro-oeste)
            
        Returns:
            List[dict]: IES encontradas
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        filter_query = {
            "localizacao.regiao": regiao,
            "ativo": True
        }
        
        projection = {
            "_id": 1,
            "sigla_ies": 1,
            "nome_ies": 1,
            "localizacao": 1,
            "total_cursos": 1
        }
        
        logger.info(f"Buscando IES na região {regiao}")
        results = list(collection.find(filter_query, projection).sort("sigla_ies", 1))
        
        return results
    
    # ============================================================
    # 2. QUERIES COM $UNWIND E $ELEMATCH (Arrays e Estruturas)
    # ============================================================
    
    def find_courses_by_disability_type(self, collection_name, disability_type):
        """
        Encontra cursos que têm alunos de um tipo específico de deficiência.
        
        Usa: $elemMatch para buscar em arrays
        
        Args:
            collection_name: Nome da collection
            disability_type: Tipo de deficiência (visual, auditiva, motora, etc)
            
        Returns:
            List[dict]: Cursos encontrados
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        filter_query = {
            "deficiencia_tipos": {
                "$elemMatch": {
                    "tipo": disability_type,
                    "quantidade": {"$gt": 0}
                }
            }
        }
        
        projection = {
            "_id": 1,
            "nome_curso": 1,
            "sigla_ies": 1,
            "deficiencia_tipos": {"$elemMatch": {"tipo": disability_type}},
            "ano": 1
        }
        
        logger.info(f"Buscando cursos com alunos {disability_type}")
        results = list(collection.find(filter_query, projection))
        
        return results
    
    # ============================================================
    # 3. AGGREGATION PIPELINE - $GROUP E $SORT
    # ============================================================
    
    def aggregate_disability_stats_by_ies(self, collection_name, year=None):
        """
        Agrega estatísticas de deficiência por instituição.
        
        Usa: $group, $sum, $avg, $sort, $project
        
        Args:
            collection_name: Nome da collection
            year: Ano específico (opcional)
            
        Returns:
            List[dict]: Estatísticas agregadas
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        pipeline = [
            # Estágio 1: Filtrar por ano (opcional)
            {
                "$match": {
                    **({"ano": year} if year else {})
                }
            },
            # Estágio 2: Agrupar por IES
            {
                "$group": {
                    "_id": "$id_ies",
                    "sigla_ies": {"$first": "$sigla_ies"},
                    "total_cursos": {"$sum": 1},
                    "total_alunos_deficiencia": {"$sum": "$deficiencia.total"},
                    "media_alunos_por_curso": {"$avg": "$deficiencia.total"},
                    "inscricoes_total": {"$sum": "$inscricoes"},
                    "percentual_deficiencia": {
                        "$divide": [
                            {"$sum": "$deficiencia.total"},
                            {"$sum": "$inscricoes"}
                        ]
                    }
                }
            },
            # Estágio 3: Ordenar por total de alunos com deficiência (DESC)
            {
                "$sort": {"total_alunos_deficiencia": -1}
            },
            # Estágio 4: Projetar campos finais
            {
                "$project": {
                    "_id": 1,
                    "sigla_ies": 1,
                    "total_cursos": 1,
                    "total_alunos_deficiencia": 1,
                    "media_alunos_por_curso": {"$round": ["$media_alunos_por_curso", 2]},
                    "inscricoes_total": 1,
                    "percentual_deficiencia": {"$round": [{"$multiply": ["$percentual_deficiencia", 100]}, 2]}
                }
            }
        ]
        
        logger.info("Agregando estatísticas de deficiência por IES")
        results = list(collection.aggregate(pipeline))
        logger.info(f"Encontradas {len(results)} instituições")
        
        return results
    
    def aggregate_disability_by_type(self, collection_name, year=None):
        """
        Agrega estatísticas por tipo de deficiência.
        
        Usa: $unwind, $group com operadores de array
        
        Args:
            collection_name: Nome da collection
            year: Ano específico (opcional)
            
        Returns:
            List[dict]: Estatísticas por tipo de deficiência
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        pipeline = [
            # Filtrar por ano
            {
                "$match": {
                    **({"ano": year} if year else {})
                }
            },
            # Desconstruir array de tipos de deficiência
            {
                "$unwind": "$deficiencia_tipos"
            },
            # Agrupar por tipo de deficiência
            {
                "$group": {
                    "_id": "$deficiencia_tipos.tipo",
                    "total_alunos": {"$sum": "$deficiencia_tipos.quantidade"},
                    "media_por_curso": {"$avg": "$deficiencia_tipos.quantidade"},
                    "cursos_com_tipo": {"$sum": 1},
                    "ies_diferentes": {"$addToSet": "$id_ies"}
                }
            },
            # Ordenar por total (DESC)
            {
                "$sort": {"total_alunos": -1}
            },
            # Projetar resultado final
            {
                "$project": {
                    "_id": 1,
                    "tipo_deficiencia": "$_id",
                    "total_alunos": 1,
                    "media_por_curso": {"$round": ["$media_por_curso", 2]},
                    "cursos_com_tipo": 1,
                    "ies_diferentes": {"$size": "$ies_diferentes"}
                }
            }
        ]
        
        logger.info("Agregando estatísticas por tipo de deficiência")
        results = list(collection.aggregate(pipeline))
        
        return results
    
    # ============================================================
    # 4. AGGREGATION COM $LOOKUP (Joins entre Collections)
    # ============================================================
    
    def join_courses_with_sisu_aggregates(self, courses_collection, sisu_collection):
        """
        Junta cursos com dados agregados de SISU.
        
        Usa: $lookup para left join, $project para estruturar resultado
        
        Args:
            courses_collection: Nome da collection de cursos
            sisu_collection: Nome da collection de SISU agregado
            
        Returns:
            List[dict]: Cursos com dados SISU relacionados
        """
        collection = self.mongo_client.get_collection(courses_collection)
        
        pipeline = [
            # Estágio 1: Lookup para trazer dados SISU
            {
                "$lookup": {
                    "from": sisu_collection,
                    "let": {"ano": "$ano", "id_ies": "$id_ies", "id_curso": "$id_curso"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$ano", "$$ano"]},
                                        {"$eq": ["$idIes", "$$id_ies"]},
                                        {"$eq": ["$idCurso", "$$id_curso"]}
                                    ]
                                }
                            }
                        },
                        {
                            "$project": {
                                "inscricoes_total": 1,
                                "inscricoes_pcd": 1,
                                "aprovados_pcd": 1,
                                "matriculados_pcd": 1,
                                "taxa_aprovacao_pcd": {
                                    "$divide": ["$aprovados_pcd", "$inscricoes_pcd"]
                                }
                            }
                        }
                    ],
                    "as": "sisu_data"
                }
            },
            # Estágio 2: Desconstruir o array (se houver match)
            {
                "$unwind": {
                    "path": "$sisu_data",
                    "preserveNullAndEmptyArrays": True
                }
            },
            # Estágio 3: Projetar resultado consolidado
            {
                "$project": {
                    "_id": 1,
                    "nome_curso": 1,
                    "sigla_ies": 1,
                    "ano": 1,
                    "censo_inscricoes": "$inscricoes",
                    "censo_deficiencia": "$deficiencia.total",
                    "sisu_inscricoes": "$sisu_data.inscricoes_total",
                    "sisu_deficiencia": "$sisu_data.inscricoes_pcd",
                    "sisu_taxa_aprovacao": "$sisu_data.taxa_aprovacao_pcd",
                    "match_sisu": {"$cond": [{"$ifNull": ["$sisu_data", False]}, True, False]}
                }
            },
            # Estágio 4: Ordenar
            {
                "$sort": {"sigla_ies": 1, "nome_curso": 1}
            }
        ]
        
        logger.info(f"Juntando {courses_collection} com {sisu_collection}")
        results = list(collection.aggregate(pipeline))
        logger.info(f"Encontrados {len(results)} registros juntados")
        
        return results
    
    # ============================================================
    # 5. AGGREGATION COMPLEXO COM MÚLTIPLOS ESTÁGIOS
    # ============================================================
    
    def advanced_disability_analysis(self, collection_name, year=None, min_courses=5):
        """
        Análise avançada: instituições com mais de X cursos e deficiência.
        
        Usa: $match, $group (múltiplos níveis), $project, $sort, $limit
        
        Args:
            collection_name: Nome da collection
            year: Ano específico
            min_courses: Mínimo de cursos
            
        Returns:
            List[dict]: Análise avançada
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        pipeline = [
            # Estágio 1: Match inicial
            {
                "$match": {
                    **({"ano": year} if year else {}),
                    "deficiencia.total": {"$gt": 0}
                }
            },
            # Estágio 2: Primeiro agrupamento por IES
            {
                "$group": {
                    "_id": "$id_ies",
                    "sigla_ies": {"$first": "$sigla_ies"},
                    "total_cursos": {"$sum": 1},
                    "total_deficiencia": {"$sum": "$deficiencia.total"},
                    "cursos_detalhes": {
                        "$push": {
                            "nome": "$nome_curso",
                            "id_curso": "$id_curso",
                            "deficiencia": "$deficiencia.total",
                            "inscricoes": "$inscricoes"
                        }
                    }
                }
            },
            # Estágio 3: Filtrar por mínimo de cursos
            {
                "$match": {
                    "total_cursos": {"$gte": min_courses}
                }
            },
            # Estágio 4: Calcular métricas adicionais
            {
                "$project": {
                    "_id": 1,
                    "sigla_ies": 1,
                    "total_cursos": 1,
                    "total_deficiencia": 1,
                    "media_deficiencia_por_curso": {
                        "$divide": ["$total_deficiencia", "$total_cursos"]
                    },
                    "cursos_com_mais_deficiencia": {
                        "$slice": [
                            {
                                "$sortArray": {
                                    "input": "$cursos_detalhes",
                                    "sortBy": {"deficiencia": -1}
                                }
                            },
                            3
                        ]
                    }
                }
            },
            # Estágio 5: Ordenar por total deficiência
            {
                "$sort": {"total_deficiencia": -1}
            }
        ]
        
        logger.info(f"Executando análise avançada de deficiência (mínimo: {min_courses} cursos)")
        results = list(collection.aggregate(pipeline))
        logger.info(f"Encontradas {len(results)} instituições que atendem critérios")
        
        return results
    
    # ============================================================
    # 6. QUERIES COM BUSCA DE TEXTO (Text Search)
    # ============================================================
    
    def search_courses_by_name(self, collection_name, search_term):
        """
        Busca cursos por nome usando text search.
        
        Usa: $text operador
        
        Args:
            collection_name: Nome da collection
            search_term: Termo de busca
            
        Returns:
            List[dict]: Cursos encontrados ordenados por score
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        filter_query = {"$text": {"$search": search_term}}
        projection = {
            "score": {"$meta": "textScore"},
            "_id": 1,
            "nome_curso": 1,
            "sigla_ies": 1,
            "deficiencia": 1
        }
        
        logger.info(f"Buscando por: {search_term}")
        results = list(
            collection.find(filter_query, projection)
            .sort([("score", {"$meta": "textScore"})])
            .limit(20)
        )
        
        return results
    
    # ============================================================
    # 7. QUERIES COM FACETED SEARCH (Agregação Multi-dimensional)
    # ============================================================
    
    def faceted_search_disability(self, collection_name, year=None):
        """
        Busca facetada: agregações por múltiplas dimensões.
        
        Usa: $facet para múltiplos pipelines simultâneos
        
        Args:
            collection_name: Nome da collection
            year: Ano específico
            
        Returns:
            dict: Agregações por diferentes dimensões
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        match_stage = {"$match": {**({"ano": year} if year else {})}}
        
        pipeline = [
            match_stage,
            {
                "$facet": {
                    # Dimensão 1: Por região
                    "por_regiao": [
                        {
                            "$group": {
                                "_id": "$localizacao.regiao",
                                "total": {"$sum": "$deficiencia.total"},
                                "cursos": {"$sum": 1}
                            }
                        },
                        {"$sort": {"total": -1}}
                    ],
                    
                    # Dimensão 2: Por tipo de deficiência
                    "por_deficiencia": [
                        {"$unwind": "$deficiencia_tipos"},
                        {
                            "$group": {
                                "_id": "$deficiencia_tipos.tipo",
                                "total": {"$sum": "$deficiencia_tipos.quantidade"}
                            }
                        },
                        {"$sort": {"total": -1}}
                    ],
                    
                    # Dimensão 3: Top 10 cursos
                    "top_cursos": [
                        {
                            "$sort": {"deficiencia.total": -1}
                        },
                        {"$limit": 10},
                        {
                            "$project": {
                                "nome_curso": 1,
                                "sigla_ies": 1,
                                "deficiencia": 1
                            }
                        }
                    ],
                    
                    # Dimensão 4: Estatísticas gerais
                    "resumo_geral": [
                        {
                            "$group": {
                                "_id": None,
                                "total_cursos": {"$sum": 1},
                                "total_alunos_deficiencia": {"$sum": "$deficiencia.total"},
                                "media_deficiencia": {"$avg": "$deficiencia.total"}
                            }
                        }
                    ]
                }
            }
        ]
        
        logger.info("Executando busca facetada de deficiência")
        result = list(collection.aggregate(pipeline))
        
        return result[0] if result else {}
    
    # ============================================================
    # 8. QUERIES COM WINDOW FUNCTIONS (Ranking)
    # ============================================================
    
    def rank_ies_by_disability_percentage(self, collection_name, year=None):
        """
        Ranking de IES por percentual de alunos com deficiência.
        
        Usa: $group com $rank equivalente
        
        Args:
            collection_name: Nome da collection
            year: Ano específico
            
        Returns:
            List[dict]: IES ranqueadas
        """
        collection = self.mongo_client.get_collection(collection_name)
        
        pipeline = [
            # Estágio 1: Match
            {
                "$match": {
                    **({"ano": year} if year else {}),
                    "inscricoes": {"$gt": 0}
                }
            },
            # Estágio 2: Agrupar por IES
            {
                "$group": {
                    "_id": "$id_ies",
                    "sigla_ies": {"$first": "$sigla_ies"},
                    "total_cursos": {"$sum": 1},
                    "total_alunos": {"$sum": "$inscricoes"},
                    "total_deficiencia": {"$sum": "$deficiencia.total"},
                    "percentual": {
                        "$divide": [
                            {"$sum": "$deficiencia.total"},
                            {"$sum": "$inscricoes"}
                        ]
                    }
                }
            },
            # Estágio 3: Ordenar
            {
                "$sort": {"percentual": -1}
            },
            # Estágio 4: Projeto final
            {
                "$project": {
                    "_id": 1,
                    "sigla_ies": 1,
                    "total_cursos": 1,
                    "total_alunos": 1,
                    "total_deficiencia": 1,
                    "percentual_deficiencia": {"$multiply": [{"$round": ["$percentual", 4]}, 100]}
                }
            }
        ]
        
        logger.info("Ranqueando IES por percentual de deficiência")
        results = list(collection.aggregate(pipeline))
        
        # Adicionar ranking
        for i, result in enumerate(results, 1):
            result["rank"] = i
        
        return results
