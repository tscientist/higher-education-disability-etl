"""
Phase 10: Explain Plan and Performance

Script para análise de performance de queries antes e depois da criação de índices.
Demonstra a diferença entre COLLSCAN e IXSCAN.
"""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import json
import os


class MongoDBExplainPlan:
    """Análise de performance de queries MongoDB"""
    
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
        self.collection = None
        
        self._connect()
    
    def _connect(self):
        """Conecta ao MongoDB"""
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database_name]
            self.collection = self.db["gold_course_indicators"]
            
            # Testar conexão
            self.client.admin.command("ping")
            print(f"Conectado ao MongoDB: {self.mongo_uri}\n")
        except ServerSelectionTimeoutError:
            print(f"Erro ao conectar ao MongoDB: {self.mongo_uri}")
            raise
    
    def close(self):
        """Fecha a conexão com MongoDB"""
        if self.client:
            self.client.close()
    
    def print_explain_plan(self, title, query, explain_verbose=True):
        """
        Executa e imprime o explain plan de uma query.
        
        Args:
            title: Título da query
            query: Dicionário com a query
            explain_verbose: Se True, usa modo ALLPLANSEXECUTION
        """
        print(f"\n{'='*80}")
        print(f"EXPLAIN PLAN: {title}")
        print(f"{'='*80}")
        
        # Construir comando explain
        filter_query = query.get("filter", {})
        projection = query.get("projection", {})
        
        # Usar PyMongo find().explain()
        cursor = self.collection.find(filter_query, projection)
        explanation = cursor.explain()
        
        # Extrair informações importantes
        execution_stats = explanation.get("executionStats", {})
        execution_stages = execution_stats.get("executionStages", {})
        
        # Imprimir informações
        print("\nQuery:")
        print(json.dumps({"filter": filter_query, "projection": projection}, indent=2))
        
        print("\nExecution Plan Summary:")
        print(f"  Stage: {execution_stages.get('stage', 'N/A')}")
        print(f"  Documents Examined: {execution_stages.get('executionStages', {}).get('nReturned', 0) if isinstance(execution_stages.get('executionStages'), dict) else execution_stats.get('totalDocsExamined', 0)}")
        print(f"  Documents Returned: {execution_stats.get('nReturned', 0)}")
        print(f"  Execution Time (ms): {execution_stats.get('executionTimeMillis', 0)}")
        
        # Detectar se está usando índice ou COLLSCAN
        stage = execution_stages.get("stage", "").upper()
        if "COLLSCAN" in stage:
            print(f"\n  ⚠️  WARNING: COLLSCAN (Collection Scan) - Percorrendo toda a coleção!")
        elif "IXSCAN" in stage:
            print(f"\n  IXSCAN (Index Scan) - Usando índice")
            print(f"     Index Name: {execution_stages.get('indexName', 'N/A')}")
            print(f"     Keys Examined: {execution_stages.get('keysExamined', 0)}")
        
        # Imprimir plano completo para referência
        print("\nDetailed Execution Plan:")
        print(json.dumps(explanation, indent=2, default=str))
    
    def demo_collscan_before_index(self):
        """
        Demonstra COLLSCAN quando não há índice.
        
        Esta é uma query que vai fazer COLLSCAN porque não há índice composto
        nos campos filtrados.
        """
        query = {
            "filter": {
                "ano": 2022,
                "uf": "SP",
                "curso.tipoModalidadeEnsino": "1",
                "ies.tipoCategoriaAdministrativa": "1",
            },
            "projection": {
                "_id": 1,
                "curso.nome": 1,
                "indicadoresAluno.matriculas": 1,
            }
        }
        
        self.print_explain_plan(
            "Filtro composto SEM índice (potencial COLLSCAN)",
            query
        )
    
    def demo_ixscan_after_index(self):
        """
        Demonstra IXSCAN quando há índice.
        
        Esta é a mesma query, mas após a criação do índice composto.
        """
        query = {
            "filter": {
                "ano": 2022,
                "uf": "SP",
            },
            "projection": {
                "_id": 1,
                "ies.nome": 1,
                "curso.nome": 1,
            }
        }
        
        self.print_explain_plan(
            "Filtro simples POR ANO E UF (com índice)",
            query
        )
    
    def demo_query_by_year(self):
        """
        Demonstra query simples por ano.
        Deve usar índice idx_ano.
        """
        query = {
            "filter": {
                "ano": 2022,
            },
            "projection": {
                "_id": 1,
                "ies.nome": 1,
                "curso.nome": 1,
            }
        }
        
        self.print_explain_plan(
            "Filtro simples por ANO (com índice)",
            query
        )
    
    def demo_query_by_ies(self):
        """
        Demonstra query por IES e ano.
        Deve usar índice idx_ies_ano.
        """
        query = {
            "filter": {
                "ies.idIes": "634",
                "ano": 2022,
            },
            "projection": {
                "_id": 1,
                "ies.nome": 1,
                "curso.nome": 1,
            }
        }
        
        self.print_explain_plan(
            "Filtro por IES ID e ANO (com índice)",
            query
        )
    
    def print_index_list(self):
        """
        Lista todos os índices criados na coleção.
        """
        print(f"\n{'='*80}")
        print("ÍNDICES EXISTENTES NA COLEÇÃO")
        print(f"{'='*80}\n")
        
        indexes = self.collection.list_indexes()
        
        for idx in indexes:
            name = idx.get("name", "N/A")
            key = idx.get("key", [])
            
            print(f"Índice: {name}")
            print(f"  Campos: {key}")
            
            # Imprimir tipo
            if name == "_id_":
                print(f"  Tipo: Sistema (sempre presente)")
            else:
                print(f"  Tipo: Customizado")
            
            print("")
    
    def print_performance_recommendations(self):
        """
        Imprime recomendações de performance baseadas na análise.
        """
        print(f"\n{'='*80}")
        print("RECOMENDAÇÕES DE PERFORMANCE")
        print(f"{'='*80}\n")
        
        recommendations = [
            {
                "title": "Índices Simples",
                "description": "Criar índices simples para campos frequentemente filtrados",
                "example": "db.gold_course_indicators.createIndex({ano: 1})",
            },
            {
                "title": "Índices Compostos",
                "description": "Criar índices compostos para queries com múltiplos filtros",
                "example": "db.gold_course_indicators.createIndex({ano: 1, uf: 1, 'curso.tipoModalidadeEnsino': 1})",
            },
            {
                "title": "Índices para Arrays",
                "description": "Criar índices em campos de arrays para queries com $elemMatch",
                "example": "db.gold_course_indicators.createIndex({'sisu.demografia.porSexo': 1})",
            },
            {
                "title": "Evitar COLLSCAN",
                "description": "Sempre filtrar primeiro pelos campos indexados mais seletivos",
                "example": "Filtrar por ano ANTES de filtrar por uf ou curso.modalidade",
            },
            {
                "title": "Usar Projection",
                "description": "Limitar campos retornados para reduzir transferência de dados",
                "example": "find({...}, {'_id': 1, 'ies.nome': 1, 'curso.nome': 1})",
            },
        ]
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec['title']}")
            print(f"   {rec['description']}")
            print(f"   Exemplo: {rec['example']}\n")
    
    def run_performance_analysis(self):
        """
        Executa análise completa de performance.
        """
        try:
            # Listar índices existentes
            self.print_index_list()
            
            # Demonstrar queries
            print("ANALYSIS DE QUERIES:\n")
            
            # Query simples por ano
            self.demo_query_by_year()
            
            # Query por IES
            self.demo_query_by_ies()
            
            # Query composta (demonstra importância de índices)
            self.demo_collscan_before_index()
            
            # Recomendações
            self.print_performance_recommendations()
            
            print(f"\n{'='*80}")
            print("Análise de performance concluída!")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"\nErro durante análise: {e}")
            raise
        finally:
            self.close()


# Comando manual para executar explain em MongoDB CLI:
"""
MANUAL EXPLAIN COMMANDS:

1. Query sem índice (COLLSCAN):
   db.gold_course_indicators.find({
     ano: 2022,
     uf: "SP",
     "curso.tipoModalidadeEnsino": "1",
     "ies.tipoCategoriaAdministrativa": "1"
   }).explain("executionStats")

2. Query com índice (IXSCAN):
   db.gold_course_indicators.find({
     ano: 2022
   }).explain("executionStats")

3. Criar índice:
   db.gold_course_indicators.createIndex({
     ano: 1,
     uf: 1,
     "curso.tipoModalidadeEnsino": 1,
     "ies.tipoCategoriaAdministrativa": 1
   })

4. Listar índices:
   db.gold_course_indicators.getIndexes()

5. Remover índice:
   db.gold_course_indicators.dropIndex("nome_do_indice")
"""


if __name__ == "__main__":
    from dotenv import load_dotenv
    
    load_dotenv()
    
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    database = os.getenv("MONGO_DATABASE", "higher_education")
    
    explain = MongoDBExplainPlan(mongo_uri, database)
    explain.run_performance_analysis()
