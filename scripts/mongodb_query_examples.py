"""
fase 9: MongoDB Query Examples

Exemplos de queries MongoDB para responder questões analíticas.
"""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import os
import json
from datetime import datetime


class MongoDBQueryExamples:
    """Exemplos de queries analíticas para o projeto"""
    
    def __init__(self, mongo_uri="mongodb://localhost:27017", database="higher_education"):
        """
        Inicializa a conexão com MongoDB.
        
        Args:
            mongo_uri: URI de conexão do MongoDB
            database: Nome do banco de dados
        """
        self.mongo_uri = mongo_uri
        self.database_name = database
        self.client = None
        self.db = None
        self.collection_gold = None
        self.collection_sisu = None
        
        self._connect()
    
    def _connect(self):
        """Conecta ao MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database_name]
            self.collection_gold = self.db["gold_course_indicators"]
            self.collection_sisu = self.db["sisu_aggregated"]
            
            # Testar conexão
            self.client.admin.command("ping")
            print(f"Conectado ao MongoDB: {self.mongo_uri}")
        except ServerSelectionTimeoutError:
            print(f"Erro ao conectar ao MongoDB: {self.mongo_uri}")
            raise
    
    def close(self):
        """Fecha a conexão com MongoDB"""
        if self.client:
            self.client.close()
    
    def print_query(self, title, query, collection_name="gold_course_indicators"):
        """
        Executa e imprime resultado de uma query.
        
        Args:
            title: Título da query
            query: Dicionário com a query
            collection_name: Nome da coleção
        """
        print(f"\n{'='*80}")
        print(f"QUERY: {title}")
        print(f"{'='*80}")
        
        collection = self.collection_gold if collection_name == "gold_course_indicators" else self.collection_sisu
        
        # Imprimir query em formato legível
        print("\nQuery:")
        print(json.dumps(query, indent=2, default=str))
        
        # Executar
        results = list(collection.find(**query))
        print(f"\nResultados: {len(results)} documentos")
        
        # Exibir primeiros resultados
        if results:
            print("\nPrimeiros documentos:")
            for doc in results[:3]:
                print(json.dumps(doc, indent=2, ensure_ascii=False, default=str))
    
    def print_aggregation(self, title, pipeline, collection_name="gold_course_indicators"):
        """
        Executa e imprime resultado de uma aggregation pipeline.
        
        Args:
            title: Título da aggregation
            pipeline: Lista de estágios da pipeline
            collection_name: Nome da coleção
        """
        print(f"\n{'='*80}")
        print(f"AGGREGATION: {title}")
        print(f"{'='*80}")
        
        collection = self.collection_gold if collection_name == "gold_course_indicators" else self.collection_sisu
        
        # Imprimir pipeline em formato legível
        print("\nPipeline:")
        for i, stage in enumerate(pipeline):
            print(f"  Stage {i+1}: {list(stage.keys())[0]}")
            print(json.dumps(stage, indent=4, default=str))
        
        # Executar
        results = list(collection.aggregate(pipeline))
        print(f"\nResultados: {len(results)} documentos")
        
        # Exibir resultados
        if results:
            print("\nResultados da aggregation:")
            for doc in results[:10]:
                print(json.dumps(doc, indent=2, ensure_ascii=False, default=str))
    
    # ========== FIND QUERIES (Básicas) ==========
    
    def query_1_filter_by_year_uf_modality(self):
        """
        Query 1: Filtro por ano, UF, modalidade e categoria administrativa.
        
        Demonstrates:
        - Simple $match filter
        - Dot notation for nested documents
        - Projection to limit returned fields
        """
        query = {
            "filter": {
                "ano": 2022,
                "uf": "SP",
                "curso.tipoModalidadeEnsino": "1",  # Presencial
                "ies.tipoCategoriaAdministrativa": "1",  # Federal
            },
            "projection": {
                "_id": 1,
                "curso.nome": 1,
                "ies.nome": 1,
                "indicadoresAluno.matriculas": 1,
            }
        }
        
        self.print_query(
            "Filtrar cursos por ano, UF, modalidade e categoria administrativa",
            query
        )
    
    def query_2_dot_notation_nested(self):
        """
        Query 2: Acesso via dot notation a documentos aninhados.
        
        Demonstrates:
        - Dot notation for nested fields
        - Multiple field access
        """
        query = {
            "filter": {
                "ies.sigla": "USP",
                "curso.nome": {"$regex": "Engenharia", "$options": "i"},
                "metricasCalculadas.percentualMatriculasPcd": {"$gt": 5},
            },
            "projection": {
                "_id": 1,
                "ies.sigla": 1,
                "ies.nome": 1,
                "curso.nome": 1,
                "metricasCalculadas": 1,
            }
        }
        
        self.print_query(
            "Acessar campos aninhados: IES, Curso, Métricas",
            query
        )
    
    def query_3_array_access_sisu_demografic(self):
        """
        Query 3: Acesso a arrays em SISU - Demográficos.
        
        Demonstrates:
        - Array access with $elemMatch
        - Querying nested array elements
        """
        query = {
            "filter": {
                "sisu.hasMatch": True,
                "sisu.demografia.porSexo": {
                    "$elemMatch": {"sexo": "F", "inscricoesPcd": {"$gt": 5}}
                }
            },
            "projection": {
                "_id": 1,
                "curso.nome": 1,
                "sisu.demografia.porSexo": 1,
            }
        }
        
        self.print_query(
            "Acessar array de demográficos por sexo em SISU",
            query
        )
    
    # ========== AGGREGATION PIPELINES (Complexas) ==========
    
    def aggregation_q1_evolution_pcd_enrollments(self):
        """
        Pergunta 1: Como evoluiu o número de matrículas de alunos com deficiência ao longo dos anos?
        
        Aggregation:
        - Group by ano
        - Sum de PcD enrollments
        - Sort by year
        """
        pipeline = [
            {
                "$match": {
                    "ano": {"$gte": 2018, "$lte": 2022}
                }
            },
            {
                "$group": {
                    "_id": "$ano",
                    "totalMatriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                    "totalMatriculas": {"$sum": "$indicadoresAluno.matriculas"},
                    "cursos": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "ano": "$_id",
                    "totalMatriculasPcd": 1,
                    "totalMatriculas": 1,
                    "percentualPcd": {
                        "$cond": [
                            {"$eq": ["$totalMatriculas", 0]},
                            None,
                            {
                                "$multiply": [
                                    {"$divide": ["$totalMatriculasPcd", "$totalMatriculas"]},
                                    100
                                ]
                            }
                        ]
                    },
                    "cursos": 1,
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        self.print_aggregation(
            "Evolução de Matrículas PcD por Ano",
            pipeline
        )
    
    def aggregation_q2_pcd_by_region(self):
        """
        Pergunta 2: Quais regiões e UFs concentram o maior número de matrículas PcD?
        
        Aggregation:
        - Group by UF
        - Sum PcD and total enrollments
        - Calculate percentage
        - Sort by PcD enrollment
        """
        pipeline = [
            {
                "$match": {"ano": 2022}
            },
            {
                "$group": {
                    "_id": "$uf",
                    "totalMatriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                    "totalMatriculas": {"$sum": "$indicadoresAluno.matriculas"},
                    "cursos": {"$sum": 1},
                    "instituicoes": {"$addToSet": "$ies.idIes"},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "uf": "$_id",
                    "totalMatriculasPcd": 1,
                    "totalMatriculas": 1,
                    "percentualPcd": {
                        "$multiply": [
                            {"$divide": ["$totalMatriculasPcd", "$totalMatriculas"]},
                            100
                        ]
                    },
                    "cursos": 1,
                    "instituicoes": {"$size": "$instituicoes"},
                }
            },
            {
                "$sort": {"totalMatriculasPcd": -1}
            }
        ]
        
        self.print_aggregation(
            "Concentração de Matrículas PcD por UF",
            pipeline
        )
    
    def aggregation_q3_pcd_by_modality(self):
        """
        Pergunta 3: A distribuição de alunos PcD difere entre educação presencial e a distância?
        
        Aggregation:
        - Group by modalidade e categoria administrativa
        - Compare percentuais PcD
        """
        pipeline = [
            {
                "$match": {"ano": 2022}
            },
            {
                "$group": {
                    "_id": {
                        "modalidade": "$curso.tipoModalidadeEnsino",
                        "categoria": "$ies.tipoCategoriaAdministrativa",
                    },
                    "totalMatriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                    "totalMatriculas": {"$sum": "$indicadoresAluno.matriculas"},
                    "cursos": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "modalidade": "$_id.modalidade",
                    "categoria": "$_id.categoria",
                    "totalMatriculasPcd": 1,
                    "totalMatriculas": 1,
                    "percentualPcd": {
                        "$multiply": [
                            {"$divide": ["$totalMatriculasPcd", "$totalMatriculas"]},
                            100
                        ]
                    },
                    "cursos": 1,
                }
            },
            {
                "$sort": {"percentualPcd": -1}
            }
        ]
        
        self.print_aggregation(
            "Comparação de PcD por Modalidade e Categoria",
            pipeline
        )
    
    def aggregation_q4_pcd_by_administrative_category(self):
        """
        Pergunta 4: Quais categorias administrativas têm maior participação de alunos PcD?
        
        Aggregation:
        - Group by categoria administrativa
        - Calculate total and PcD enrollment rates
        - Sort by PcD percentage
        """
        pipeline = [
            {
                "$match": {"ano": 2022}
            },
            {
                "$group": {
                    "_id": "$ies.tipoCategoriaAdministrativa",
                    "totalMatriculasPcd": {"$sum": "$indicadoresDeficiencia.matriculas"},
                    "totalMatriculas": {"$sum": "$indicadoresAluno.matriculas"},
                    "cursos": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "categoria": "$_id",
                    "totalMatriculasPcd": 1,
                    "totalMatriculas": 1,
                    "percentualPcd": {
                        "$multiply": [
                            {"$divide": ["$totalMatriculasPcd", "$totalMatriculas"]},
                            100
                        ]
                    },
                    "cursos": 1,
                }
            },
            {
                "$sort": {"percentualPcd": -1}
            }
        ]
        
        self.print_aggregation(
            "Participação de PcD por Categoria Administrativa",
            pipeline
        )
    
    def aggregation_q5_completion_rate_by_region(self):
        """
        Pergunta 5: Como a taxa geral de conclusão se compara com a taxa PcD por região?
        
        Aggregation:
        - Group by UF
        - Calculate both general and PcD completion rates
        - Sort by UF
        """
        pipeline = [
            {
                "$match": {"ano": 2022}
            },
            {
                "$group": {
                    "_id": "$uf",
                    "ingressantesGeral": {"$sum": "$indicadoresAluno.ingressantes"},
                    "concluintesGeral": {"$sum": "$indicadoresAluno.concluintes"},
                    "ingressantesPcd": {"$sum": "$indicadoresDeficiencia.ingressantes"},
                    "concluintesPcd": {"$sum": "$indicadoresDeficiencia.concluintes"},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "uf": "$_id",
                    "taxaConclusaoGeral": {
                        "$cond": [
                            {"$eq": ["$ingressantesGeral", 0]},
                            None,
                            {
                                "$multiply": [
                                    {"$divide": ["$concluintesGeral", "$ingressantesGeral"]},
                                    100
                                ]
                            }
                        ]
                    },
                    "taxaConclusaoPcd": {
                        "$cond": [
                            {"$eq": ["$ingressantesPcd", 0]},
                            None,
                            {
                                "$multiply": [
                                    {"$divide": ["$concluintesPcd", "$ingressantesPcd"]},
                                    100
                                ]
                            }
                        ]
                    },
                }
            },
            {
                "$sort": {"uf": 1}
            }
        ]
        
        self.print_aggregation(
            "Taxa de Conclusão Geral vs PcD por UF",
            pipeline
        )
    
    def aggregation_q6_pcd_loss_rate_by_uf(self):
        """
        Pergunta 6: Em quais UFs a taxa de perda de PcD é maior comparada à perda geral?
        
        Aggregation:
        - Group by UF
        - Calculate loss rates
        - Sort by PcD loss rate descending
        """
        pipeline = [
            {
                "$match": {"ano": 2022}
            },
            {
                "$group": {
                    "_id": "$uf",
                    "ingressantesGeral": {"$sum": "$indicadoresAluno.ingressantes"},
                    "concluintesGeral": {"$sum": "$indicadoresAluno.concluintes"},
                    "ingressantesPcd": {"$sum": "$indicadoresDeficiencia.ingressantes"},
                    "concluintesPcd": {"$sum": "$indicadoresDeficiencia.concluintes"},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "uf": "$_id",
                    "taxaPerdaGeral": {
                        "$cond": [
                            {"$eq": ["$ingressantesGeral", 0]},
                            None,
                            {
                                "$multiply": [
                                    {
                                        "$divide": [
                                            {
                                                "$subtract": ["$ingressantesGeral", "$concluintesGeral"]
                                            },
                                            "$ingressantesGeral"
                                        ]
                                    },
                                    100
                                ]
                            }
                        ]
                    },
                    "taxaPerdaPcd": {
                        "$cond": [
                            {"$eq": ["$ingressantesPcd", 0]},
                            None,
                            {
                                "$multiply": [
                                    {
                                        "$divide": [
                                            {
                                                "$subtract": ["$ingressantesPcd", "$concluintesPcd"]
                                            },
                                            "$ingressantesPcd"
                                        ]
                                    },
                                    100
                                ]
                            }
                        ]
                    },
                }
            },
            {
                "$sort": {"taxaPerdaPcd": -1}
            }
        ]
        
        self.print_aggregation(
            "Taxa de Perda PcD vs Geral por UF",
            pipeline
        )
    
    def aggregation_q7_sisu_access_funnel_pcd(self):
        """
        Pergunta 7: Como funciona o funil de acesso SISU para candidatos PcD?
        
        Aggregation:
        - Group by year
        - Sum SISU PcD inscriptions, approved, and enrolled
        - Sort by year
        """
        pipeline = [
            {
                "$match": {"hasMatch": True}
            },
            {
                "$group": {
                    "_id": "$ano",
                    "inscricoesPcd": {"$sum": "$inscricoesPcd"},
                    "aprovadosPcd": {"$sum": "$aprovadosPcdRegular"},
                    "matriculadosPcd": {"$sum": "$matriculadosPcdFinal"},
                    "inscricoesTotal": {"$sum": "$inscricoesTotal"},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "ano": "$_id",
                    "inscricoesPcd": 1,
                    "aprovadosPcd": 1,
                    "matriculadosPcd": 1,
                    "taxaAprovacaoPcd": {
                        "$cond": [
                            {"$eq": ["$inscricoesPcd", 0]},
                            None,
                            {
                                "$multiply": [
                                    {"$divide": ["$aprovadosPcd", "$inscricoesPcd"]},
                                    100
                                ]
                            }
                        ]
                    },
                    "taxaMatriculaPcd": {
                        "$cond": [
                            {"$eq": ["$aprovadosPcd", 0]},
                            None,
                            {
                                "$multiply": [
                                    {"$divide": ["$matriculadosPcd", "$aprovadosPcd"]},
                                    100
                                ]
                            }
                        ]
                    },
                    "percentualPcdTotal": {
                        "$multiply": [
                            {"$divide": ["$inscricoesPcd", "$inscricoesTotal"]},
                            100
                        ]
                    },
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        self.print_aggregation(
            "Funil de Acesso SISU para PcD por Ano",
            pipeline,
            collection_name="sisu_aggregated"
        )
    
    # ========== LOOKUP QUERY (Joins) ==========
    
    def query_8_lookup_sisu_match(self):
        """
        Pergunta 8: Qual é a relação entre demanda PcD em SISU e matrículas PcD no Censo?
        
        Demonstrates:
        - $lookup between gold_course_indicators and sisu_aggregated
        - Using multiple fields in lookup
        """
        pipeline = [
            {
                "$match": {
                    "ano": 2022,
                    "sisu.hasMatch": True
                }
            },
            {
                "$lookup": {
                    "from": "sisu_aggregated",
                    "let": {
                        "ano": "$ano",
                        "idIes": "$ies.idIes",
                        "idCurso": "$curso.idCurso",
                    },
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$ano", "$$ano"]},
                                        {"$eq": ["$idIes", "$$idIes"]},
                                        {"$eq": ["$idCurso", "$$idCurso"]},
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "sisuMatch"
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "curso.nome": 1,
                    "ies.nome": 1,
                    "censoMatriculasPcd": "$indicadoresDeficiencia.matriculas",
                    "sisuInscricoesPcd": {"$arrayElemAt": ["$sisuMatch.inscricoesPcd", 0]},
                    "sisuMatriculadosPcd": {"$arrayElemAt": ["$sisuMatch.matriculadosPcdFinal", 0]},
                }
            },
            {
                "$sort": {"censoMatriculasPcd": -1}
            },
            {
                "$limit": 10
            }
        ]
        
        self.print_aggregation(
            "Relação entre Demanda SISU PcD e Matrículas Censo PcD",
            pipeline
        )
    
    # ========== DEMOGRAfIC QUERIES (Demográficas) ==========
    
    def aggregation_demografic_sisu_pcd_by_sex(self):
        """
        Query Demográfica 1: Funil de acesso SISU PcD por sexo
        
        Demonstrates:
        - Unwinding arrays
        - Aggregating on unwound data
        """
        pipeline = [
            {
                "$match": {"hasMatch": True, "ano": 2022}
            },
            {
                "$unwind": "$demografia.porSexo"
            },
            {
                "$group": {
                    "_id": "$demografia.porSexo.sexo",
                    "inscricoesPcd": {"$sum": "$demografia.porSexo.inscricoesPcd"},
                    "aprovadosPcd": {"$sum": "$demografia.porSexo.aprovados_pcd"},
                    "matriculadosPcd": {"$sum": "$demografia.porSexo.matriculados_pcd"},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "sexo": "$_id",
                    "inscricoesPcd": 1,
                    "aprovadosPcd": 1,
                    "matriculadosPcd": 1,
                }
            }
        ]
        
        self.print_aggregation(
            "Funil SISU PcD por Sexo",
            pipeline,
            collection_name="sisu_aggregated"
        )
    
    def aggregation_demografic_sisu_pcd_by_age_group(self):
        """
        Query Demográfica 2: Funil de acesso SISU PcD por faixa etária
        """
        pipeline = [
            {
                "$match": {"hasMatch": True, "ano": 2022}
            },
            {
                "$unwind": "$demografia.porFaixaEtaria"
            },
            {
                "$group": {
                    "_id": "$demografia.porFaixaEtaria.faixaEtaria",
                    "inscricoesPcd": {"$sum": "$demografia.porFaixaEtaria.inscricoesPcd"},
                    "aprovadosPcd": {"$sum": "$demografia.porFaixaEtaria.aprovados_pcd"},
                    "matriculadosPcd": {"$sum": "$demografia.porFaixaEtaria.matriculados_pcd"},
                }
            },
            {
                "$project": {
                    "faixaEtaria": "$_id",
                    "inscricoesPcd": 1,
                    "aprovadosPcd": 1,
                    "matriculadosPcd": 1,
                }
            }
        ]
        
        self.print_aggregation(
            "Funil SISU PcD por Faixa Etária",
            pipeline,
            collection_name="sisu_aggregated"
        )
    
    # ========== EXECUTION ==========
    
    def run_all_examples(self):
        """Executa todos os exemplos de queries"""
        try:
            # Find queries (simples)
            self.query_1_filter_by_year_uf_modality()
            self.query_2_dot_notation_nested()
            self.query_3_array_access_sisu_demografic()
            
            # Aggregation pipelines (complexas)
            self.aggregation_q1_evolution_pcd_enrollments()
            self.aggregation_q2_pcd_by_region()
            self.aggregation_q3_pcd_by_modality()
            self.aggregation_q4_pcd_by_administrative_category()
            self.aggregation_q5_completion_rate_by_region()
            self.aggregation_q6_pcd_loss_rate_by_uf()
            self.aggregation_q7_sisu_access_funnel_pcd()
            
            # Lookup query
            self.query_8_lookup_sisu_match()
            
            # Demografic queries
            self.aggregation_demografic_sisu_pcd_by_sex()
            self.aggregation_demografic_sisu_pcd_by_age_group()
            
            print(f"\n{'='*80}")
            print("Todas as queries foram executadas com sucesso!")
            print(f"{'='*80}\n")
        except Exception as e:
            print(f"\nErro ao executar queries: {e}")
            raise
        finally:
            self.close()


if __name__ == "__main__":
    # Para executar como script
    from dotenv import load_dotenv
    
    load_dotenv()
    
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    database = os.getenv("MONGO_DATABASE", "higher_education")
    
    examples = MongoDBQueryExamples(mongo_uri, database)
    examples.run_all_examples()
