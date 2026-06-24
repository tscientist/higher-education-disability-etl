from google.cloud import bigquery
from google.oauth2 import service_account
from google.api_core.exceptions import BadRequest

from ..config import GCP_PROJECT_ID, GCP_CREDENTIALS_PATH
from ..utils.logger import logger


class BigQueryClient:
    def __init__(self):
        self.project_id = self._validate_identifier(GCP_PROJECT_ID, "GCP_PROJECT_ID")

        credentials = self._load_credentials()

        self.client = bigquery.Client(
            project=self.project_id,
            credentials=credentials
        )

    def _validate_identifier(self, name: str, label: str):
        """
        Valida identificadores usados em referências BigQuery.

        Isso evita erros como:
        Syntax error: Unclosed identifier literal

        Esse erro pode acontecer quando project_id, dataset_id ou table_id
        vêm com crase, quebra de linha, tabulação ou espaços escondidos.
        """
        if not isinstance(name, str):
            raise ValueError(f"{label} must be a string")

        val = name.strip().strip("'").strip('"')

        if not val:
            raise ValueError(f"{label} is empty after stripping")

        invalid_chars = ["`", "\n", "\r", "\t"]

        if any(char in val for char in invalid_chars):
            raise ValueError(f"{label} contains invalid characters: {repr(val)}")

        return val

    def _table_ref(self, dataset_id: str, table_id: str):
        """
        Monta uma referência segura no formato:
        project.dataset.table
        """
        dataset_id = self._validate_identifier(dataset_id, "BIGQUERY_DATASET")
        table_id = self._validate_identifier(table_id, "BIGQUERY_TABLE")

        return f"{self.project_id}.{dataset_id}.{table_id}"

    def _load_credentials(self):
        """
        Carrega credenciais do BigQuery.

        Se GCP_CREDENTIALS_PATH estiver preenchido, usa o arquivo de service account.
        Se estiver vazio, usa Application Default Credentials configuradas pelo comando:

            gcloud auth application-default login
        """
        credentials_path = str(GCP_CREDENTIALS_PATH or "").strip().strip("'").strip('"')

        if not credentials_path:
            logger.info("GCP_CREDENTIALS_PATH vazio. Usando Application Default Credentials.")
            return None

        logger.info(f"Usando credenciais BigQuery em: {credentials_path}")

        return service_account.Credentials.from_service_account_file(
            credentials_path
        )

    def fetch_data(self, query):
        """
        Executa uma query no BigQuery e retorna os resultados.
        """
        try:
            query_job = self.client.query(query)
            results = query_job.result()
            return [dict(row) for row in results]

        except BadRequest as e:
            logger.error("Erro ao executar query no BigQuery.")
            logger.error("Query enviada ao BigQuery:")
            logger.error(query)
            raise e

    def fetch_pages(self, query: str, page_size: int = 5000):
        """
        Executa uma query e retorna resultados em páginas.
        Não materializa tudo em memória de uma vez.
        """
        try:
            query_job = self.client.query(query)
            rows = query_job.result(page_size=page_size)

            for page in rows.pages:
                yield [dict(row) for row in page]

        except BadRequest as e:
            logger.error("Erro ao executar query paginada no BigQuery.")
            logger.error("Query enviada ao BigQuery:")
            logger.error(query)
            raise e

    def count_records(self, dataset_id, table_id, year_range=None, id_ies=None):
        """
        Conta o número total de registros em uma tabela com filtros opcionais.
        """
        table_ref = self._table_ref(dataset_id, table_id)

        query = f"""
        SELECT COUNT(*) AS total
        FROM `{table_ref}`
        WHERE 1=1
        """

        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {int(start_year)} AND ano <= {int(end_year)}"

        if id_ies:
            ies_str = str(id_ies).replace("'", "\\'")
            query += f" AND id_ies = '{ies_str}'"

        result = self.fetch_data(query)
        return result[0]["total"] if result else 0

    def read_table(self, dataset_id, table_id, year_range=None, limit=None):
        """
        Lê uma tabela BigQuery com filtros opcionais de ano e limite.
        """
        table_ref = self._table_ref(dataset_id, table_id)

        total_count = self.count_records(dataset_id, table_id, year_range)
        logger.info(f"Tabela {table_id}: {total_count} registros disponíveis")

        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE 1=1
        """

        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {int(start_year)} AND ano <= {int(end_year)}"

        if limit:
            query += f" LIMIT {int(limit)}"

        logger.info(f"Lendo tabela {table_id}")
        results = self.fetch_data(query)
        logger.info(f"Tabela {table_id}: {len(results)} registros lidos")

        return results

    def read_table_in_batches(self, dataset_id, table_id, year_range=None, limit=None, batch_size=None):
        """
        Lê uma tabela BigQuery em batches.
        """
        if batch_size is None:
            from ..config import ETL_BATCH_SIZE
            batch_size = ETL_BATCH_SIZE

        table_ref = self._table_ref(dataset_id, table_id)

        total_count = self.count_records(dataset_id, table_id, year_range)
        logger.info(
            f"Tabela {table_id}: {total_count} registros disponíveis "
            f"para processar em batches de {batch_size}"
        )

        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE 1=1
        """

        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {int(start_year)} AND ano <= {int(end_year)}"

        query += " ORDER BY ano"

        logger.info(f"Iniciando leitura de {table_id} em batches")

        try:
            query_job = self.client.query(query)
            results = query_job.result()

        except BadRequest as e:
            logger.error("Erro ao executar query em batches no BigQuery.")
            logger.error("Query enviada ao BigQuery:")
            logger.error(query)
            raise e

        batch = []
        batch_number = 0
        total_records = 0

        for row in results:
            batch.append(dict(row))
            total_records += 1

            if limit and total_records > int(limit):
                batch.pop()
                total_records -= 1
                break

            if len(batch) == int(batch_size):
                batch_number += 1
                logger.info(f"Tabela {table_id} - Batch {batch_number}: {len(batch)} registros")
                yield batch_number, batch
                batch = []

        if batch:
            batch_number += 1
            logger.info(f"Tabela {table_id} - Batch {batch_number}: {len(batch)} registros finais")
            yield batch_number, batch

        logger.info(f"Tabela {table_id}: {total_records} registros lidos em {batch_number} batches")

    def read_table_filtered_by_ies(self, dataset_id, table_id, id_ies, year_range=None):
        """
        Lê tabela filtrada por um IES específico.
        """
        table_ref = self._table_ref(dataset_id, table_id)

        total_count = self.count_records(dataset_id, table_id, year_range, id_ies)
        logger.info(f"Tabela {table_id} para IES {id_ies}: {total_count} registros disponíveis")

        ies_str = str(id_ies).replace("'", "\\'")

        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE id_ies = '{ies_str}'
        """

        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {int(start_year)} AND ano <= {int(end_year)}"

        logger.info(f"Lendo {table_id} para IES {id_ies}")
        results = self.fetch_data(query)
        logger.info(f"{len(results)} registros lidos")

        return results

    def aggregate_sisu_by_course_optimized(self, dataset_id, table_id, year_range=None):
        """
        Agrega dados SISU diretamente no BigQuery por ano, IES e curso.
        """
        table_ref = self._table_ref(dataset_id, table_id)

        query = f"""
        SELECT
            ano,
            CAST(id_ies AS STRING) AS id_ies,
            CAST(id_curso AS STRING) AS id_curso,
            CONCAT(CAST(ano AS STRING), '_', CAST(id_ies AS STRING), '_', CAST(id_curso AS STRING)) AS _id,
            nome_curso,
            sigla_ies,
            campus,
            turno,
            periodicidade,
            COUNT(*) AS inscricoes_total,
            COUNTIF(modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%') AS inscricoes_pcd,
            COUNTIF(status_aprovado = TRUE AND (modalidade_concorrencia NOT LIKE '%deficiencia%' AND tipo_cota NOT LIKE '%deficiencia%')) AS aprovados_regular,
            COUNTIF(status_aprovado = TRUE AND (modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%')) AS aprovados_pcd,
            COUNTIF(status_matricula IS NOT NULL AND (modalidade_concorrencia NOT LIKE '%deficiencia%' AND tipo_cota NOT LIKE '%deficiencia%')) AS matriculados_final,
            COUNTIF(status_matricula IS NOT NULL AND (modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%')) AS matriculados_pcd_final,
            ROUND(AVG(nota_candidato), 2) AS nota_candidato_media_geral,
            ROUND(AVG(IF(modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%', nota_candidato, NULL)), 2) AS nota_candidato_media_pcd,
            ROUND(AVG(nota_corte), 2) AS nota_corte_media_regular,
            ROUND(AVG(IF(modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%', nota_corte, NULL)), 2) AS nota_corte_media_pcd,
            COUNT(DISTINCT sexo) AS sexo_tipos,
            COUNT(DISTINCT id_municipio_candidato) AS municipio_tipos
        FROM `{table_ref}`
        WHERE 1=1
        """

        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {int(start_year)} AND ano <= {int(end_year)}"

        query += """
        GROUP BY ano, id_ies, id_curso, nome_curso, sigla_ies, campus, turno, periodicidade
        ORDER BY ano DESC, id_ies, id_curso
        """

        total_count = self.count_records(dataset_id, table_id, year_range)
        logger.info(f"Tabela {table_id}: {total_count} registros individuais para agregar")

        logger.info("Agregando SISU por curso no BigQuery...")
        results = self.fetch_data(query)
        logger.info(f"SISU agregado: {len(results)} grupos curso/instituição retornados")

        return results

    def aggregate_sisu_by_ies_optimized(self, dataset_id, table_id, year_range=None):
        """
        Agrega dados SISU por IES.
        """
        table_ref = self._table_ref(dataset_id, table_id)

        query = f"""
        SELECT
            ano,
            CAST(id_ies AS STRING) AS id_ies,
            CONCAT(CAST(ano AS STRING), '_', CAST(id_ies AS STRING)) AS _id,
            sigla_ies,
            COUNT(*) AS inscricoes_total,
            COUNTIF(modalidade_concorrencia LIKE '%deficiencia%' OR tipo_cota LIKE '%deficiencia%') AS inscricoes_pcd,
            COUNTIF(status_aprovado = TRUE) AS aprovados_total,
            COUNTIF(status_matricula IS NOT NULL) AS matriculados_total,
            ROUND(AVG(nota_candidato), 2) AS nota_media_geral,
            COUNT(DISTINCT id_curso) AS total_cursos,
            COUNT(DISTINCT sexo) AS sexo_tipos,
            COUNT(DISTINCT id_municipio_candidato) AS municipio_tipos
        FROM `{table_ref}`
        WHERE 1=1
        """

        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {int(start_year)} AND ano <= {int(end_year)}"

        query += """
        GROUP BY ano, id_ies, sigla_ies
        ORDER BY ano DESC, id_ies
        """

        logger.info("Agregando SISU por IES no BigQuery...")
        results = self.fetch_data(query)
        logger.info(f"SISU por IES: {len(results)} instituições retornadas")

        return results
