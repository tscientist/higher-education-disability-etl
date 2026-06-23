from google.cloud import bigquery
from google.oauth2 import service_account
from ..config import GCP_PROJECT_ID, GCP_CREDENTIALS_PATH
from ..utils.logger import logger


class BigQueryClient:
    def __init__(self):
        self.client = bigquery.Client(
            project=GCP_PROJECT_ID,
            credentials=self._load_credentials()
        )
        self.project_id = GCP_PROJECT_ID
    
    def _load_credentials(self):
        """Carrega as credenciais da service account"""
        return service_account.Credentials.from_service_account_file(
            GCP_CREDENTIALS_PATH
        )
    
    def fetch_data(self, query):
        """Executa uma query no BigQuery e retorna os resultados"""
        query_job = self.client.query(query)
        results = query_job.result()
        return [dict(row) for row in results]
    
    def count_records(self, dataset_id, table_id, year_range=None, id_ies=None):
        """
        Conta o número total de registros em uma tabela com filtros opcionais.
        
        Args:
            dataset_id: ID do dataset
            table_id: ID da tabela
            year_range: Tuple (start_year, end_year) para filtrar por ano
            id_ies: ID do IES para filtro opcional
            
        Returns:
            int: Número total de registros
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        query = f"SELECT COUNT(*) as total FROM `{table_ref}`"
        
        if year_range or id_ies:
            filters = []
            if year_range:
                start_year, end_year = year_range
                filters.append(f"ano >= {start_year} AND ano <= {end_year}")
            if id_ies:
                # id_ies é STRING no BigQuery, converter se for int
                ies_str = str(id_ies)
                filters.append(f"id_ies = '{ies_str}'")
            
            query += " WHERE " + " AND ".join(filters)
        
        result = self.fetch_data(query)
        count = result[0]['total'] if result else 0
        
        return count
    
    def read_table(self, dataset_id, table_id, year_range=None, limit=None):
        """
        Lê uma tabela BigQuery com filtros opcionais de ano e limite.
        
        Args:
            dataset_id: ID do dataset
            table_id: ID da tabela
            year_range: Tuple (start_year, end_year) para filtrar por ano
            limit: Limite de registros para testes
            
        Returns:
            List[dict]: Lista de documentos
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        # Contar registros antes de ler
        total_count = self.count_records(dataset_id, table_id, year_range)
        logger.info(f"Tabela {table_id}: {total_count} registros disponíveis")
        
        query = f"SELECT * FROM `{table_ref}`"
        
        if year_range:
            start_year, end_year = year_range
            query += f" WHERE ano >= {start_year} AND ano <= {end_year}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        logger.info(f"Lendo tabela {table_id}")
        results = self.fetch_data(query)
        logger.info(f"Tabela {table_id}: {len(results)} registros lidos")
        
        return results
    
    def read_table_in_batches(self, dataset_id, table_id, year_range=None, limit=None, batch_size=None):
        """
        Lê uma tabela BigQuery em batches.
        
        Args:
            dataset_id: ID do dataset
            table_id: ID da tabela
            year_range: Tuple (start_year, end_year) para filtrar por ano
            limit: Limite total de registros para testes
            batch_size: Tamanho do batch (usa ETL_BATCH_SIZE se não informado)
            
        Yields:
            Tuple[int, List[dict]]: (batch_number, batch_data)
        """
        if batch_size is None:
            from ..config import ETL_BATCH_SIZE
            batch_size = ETL_BATCH_SIZE
        
        # Contar registros antes de ler
        total_count = self.count_records(dataset_id, table_id, year_range)
        logger.info(f"Tabela {table_id}: {total_count} registros disponíveis para processar em {batch_size}-record batches")
        
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        query = f"SELECT * FROM `{table_ref}`"
        
        if year_range:
            start_year, end_year = year_range
            query += f" WHERE ano >= {start_year} AND ano <= {end_year}"
        
        query += f" ORDER BY ano"
        
        logger.info(f"Iniciando leitura de {table_id} em batches")
        
        query_job = self.client.query(query)
        results = query_job.result()
        
        batch = []
        batch_number = 0
        total_records = 0
        
        for row in results:
            batch.append(dict(row))
            total_records += 1
            
            # Verifica se atingiu o limite total (se especificado)
            if limit and total_records > limit:
                batch.pop()  # Remove o último registro que excedeu o limite
                total_records -= 1
                break
            
            # Quando batch está completo, yield e reinicia
            if len(batch) == batch_size:
                batch_number += 1
                logger.info(f"Tabela {table_id} - Batch {batch_number}: {len(batch)} registros")
                yield batch_number, batch
                batch = []
        
        # Yield último batch incompleto
        if batch:
            batch_number += 1
            logger.info(f"Tabela {table_id} - Batch {batch_number}: {len(batch)} registros (final)")
            yield batch_number, batch
        
        logger.info(f"Tabela {table_id}: {total_records} registros lidos em {batch_number} batches")
    
    def read_table_filtered_by_ies(self, dataset_id, table_id, id_ies, year_range=None):
        """Le tabela filtrada por um IES especifico"""
        # Contar registros antes de ler
        total_count = self.count_records(dataset_id, table_id, year_range, id_ies)
        logger.info(f"Tabela {table_id} para IES {id_ies}: {total_count} registros disponíveis")
        
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        # id_ies é STRING no BigQuery
        ies_str = str(id_ies)
        query = f"SELECT * FROM `{table_ref}` WHERE id_ies = '{ies_str}'"
        
        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {start_year} AND ano <= {end_year}"
        
        logger.info(f"Lendo {table_id} para IES {id_ies}")
        results = self.fetch_data(query)
        logger.info(f"  {len(results)} registros lidos")
        
        return results
    
    def aggregate_sisu_by_course_optimized(self, dataset_id, table_id, year_range=None):
        """
        Agrega dados SISU diretamente no BigQuery por (ano, id_ies, id_curso).
        
        MUITO MAIS EFICIENTE: em vez de ler 3.5M registros e agregar na memória,
        a agregação acontece no BigQuery e retorna apenas ~100-200k documentos.
        
        Args:
            dataset_id: ID do dataset
            table_id: ID da tabela SISU
            year_range: Tuple (start_year, end_year) para filtrar por ano
            
        Returns:
            List[dict]: Documentos SISU agregados
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        query = f"""
        SELECT
            ano,
            CAST(id_ies AS STRING) as id_ies,
            CAST(id_curso AS STRING) as id_curso,
            CONCAT(CAST(ano AS STRING), '_', CAST(id_ies AS STRING), '_', CAST(id_curso AS STRING)) as _id,
            nome_curso,
            sigla_ies,
            campus,
            turno,
            sigla_uf as sigla_uf_ies,
            periodicidade,
            COUNT(*) as inscricoes_total,
            COUNTIF(modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%' OR cota_deficiencia = true OR pcd = true) as inscricoes_pcd,
            COUNTIF(status_candidato LIKE '%aprovado%' AND (modalidade_concorrencia NOT LIKE '%deficiencia%' AND tipo_cota NOT LIKE '%deficiencia%')) as aprovados_regular,
            COUNTIF(status_candidato LIKE '%aprovado%' AND (modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%' OR cota_deficiencia = true OR pcd = true)) as aprovados_pcd,
            COUNTIF(status_matricula LIKE '%matriculado%' AND (modalidade_concorrencia NOT LIKE '%deficiencia%' AND tipo_cota NOT LIKE '%deficiencia%')) as matriculados_final,
            COUNTIF(status_matricula LIKE '%matriculado%' AND (modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%' OR cota_deficiencia = true OR pcd = true)) as matriculados_pcd_final,
            ROUND(AVG(SAFE.FLOAT64(nota_candidato)), 2) as nota_candidato_media_geral,
            ROUND(AVG(IF(modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%' OR cota_deficiencia = true OR pcd = true, SAFE.FLOAT64(nota_candidato), NULL)), 2) as nota_candidato_media_pcd,
            ROUND(AVG(SAFE.FLOAT64(nota_corte)), 2) as nota_corte_media_regular,
            ROUND(AVG(IF(modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%' OR cota_deficiencia = true OR pcd = true, SAFE.FLOAT64(nota_corte), NULL)), 2) as nota_corte_media_pcd,
            COUNT(DISTINCT sexo) as sexo_tipos,
            COUNT(DISTINCT id_municipio_candidato) as municipio_tipos
        FROM `{table_ref}`
        WHERE 1=1
        """
        
        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {start_year} AND ano <= {end_year}"
        
        query += """
        GROUP BY ano, id_ies, id_curso, nome_curso, sigla_ies, campus, turno, sigla_uf, periodicidade
        ORDER BY ano DESC, id_ies, id_curso
        """
        
        total_count = self.count_records(dataset_id, table_id, year_range)
        logger.info(f"Tabela {table_id}: {total_count} registros INDIVIDUAIS para agregar")
        
        logger.info("Agregando SISU por curso no BigQuery (operação otimizada)...")
        results = self.fetch_data(query)
        logger.info(f"SISU Agregado: {len(results)} grupos curso/instituição retornados")
        
        return results
    
    def aggregate_sisu_by_ies_optimized(self, dataset_id, table_id, year_range=None):
        """
        Agrega dados SISU por IES (nível superior, menos granular).
        Útil para análises de instituição completa.
        
        Args:
            dataset_id: ID do dataset
            table_id: ID da tabela SISU
            year_range: Tuple (start_year, end_year) para filtrar por ano
            
        Returns:
            List[dict]: Documentos SISU agregados por IES
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        query = f"""
        SELECT
            ano,
            CAST(id_ies AS STRING) as id_ies,
            CONCAT(CAST(ano AS STRING), '_', CAST(id_ies AS STRING)) as _id,
            sigla_ies,
            sigla_uf as sigla_uf_ies,
            COUNT(*) as inscricoes_total,
            COUNTIF(modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%' OR cota_deficiencia = true OR pcd = true) as inscricoes_pcd,
            COUNTIF(status_candidato LIKE '%aprovado%') as aprovados_total,
            COUNTIF(status_matricula LIKE '%matriculado%') as matriculados_total,
            ROUND(AVG(SAFE.FLOAT64(nota_candidato)), 2) as nota_media_geral,
            COUNT(DISTINCT id_curso) as total_cursos,
            COUNT(DISTINCT sexo) as sexo_tipos,
            COUNT(DISTINCT id_municipio_candidato) as municipio_tipos
        FROM `{table_ref}`
        WHERE 1=1
        """
        
        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {start_year} AND ano <= {end_year}"
        
        query += """
        GROUP BY ano, id_ies, sigla_ies, sigla_uf
        ORDER BY ano DESC, id_ies
        """
        
        logger.info("Agregando SISU por IES no BigQuery...")
        results = self.fetch_data(query)
        logger.info(f"SISU por IES: {len(results)} instituições retornadas")
        
        return results
