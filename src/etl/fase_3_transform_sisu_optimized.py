"""
Fase 3: Transform SISU microdados - OTIMIZADO

Transforma dados de SISU usando agregação no BigQuery:
- Lê dados em batches do BigQuery
- Calcula agregações usando SQL (sem carregar tudo em memória)
- Retorna apenas os agregados finalizados
- BigQuery faz a agregação pesada (COUNT, GROUP BY, etc)
- Python faz apenas transformações leves
- Economiza memória
"""

from ..clients import BigQueryClient
from ..config import ETL_BATCH_SIZE
from ..utils.logger import logger


class Fase3TransformSISUOptimized:
    """Transforma dados SISU usando agregação no BigQuery"""
    
    def __init__(self):
        self.bq_client = BigQueryClient()
        self.dataset = "stg_inep"
        self.table = "stg_sisu_microdados"
    
    def _get_sisu_aggregation_query(self, year_range=None, id_ies=None):
        """
        Gera query de agregação SISU otimizada no BigQuery.
        
        Calcula todas as métricas diretamente no SQL:
        - Contadores (inscrições, aprovados, matriculados)
        - Médias de notas
        - Agregações por demografia (sexo, faixa etária, município)
        
        Args:
            year_range: Tuple (start_year, end_year)
            id_ies: ID do IES para filtrar
            
        Returns:
            str: Query SQL otimizada
        """
        
        # Query agregada que calcula tudo no BigQuery
        query = f"""
        WITH sisu_filtered AS (
            SELECT 
                ano,
                CAST(id_ies AS STRING) as id_ies,
                CAST(id_curso AS STRING) as id_curso,
                nome_curso,
                sigla_ies,
                sigla_uf,
                campus,
                turno,
                periodicidade,
                sexo,
                data_nascimento,
                id_municipio_candidato,
                nome_municipio_candidato,
                uf_candidato,
                nota_candidato,
                nota_corte,
                status_candidato,
                status_matricula,
                modalidade_concorrencia,
                tipo_cota,
                cota_deficiencia,
                deficiencia
            FROM `{self.bq_client.project_id}.{self.dataset}.{self.table}`
            WHERE 1=1
        """
        
        if year_range:
            start_year, end_year = year_range
            query += f" AND ano >= {start_year} AND ano <= {end_year}"
        
        if id_ies:
            query += f" AND CAST(id_ies AS STRING) = '{id_ies}'"
        
        query += """
        ),
        pcd_detection AS (
            SELECT
                *,
                (
                    modalidade_concorrencia LIKE '%deficiencia%'
                    OR modalidade_concorrencia LIKE '%cota%'
                    OR tipo_cota LIKE '%deficiencia%'
                    OR cota_deficiencia != '0'
                    OR deficiencia IS NOT NULL
                ) as is_pcd
            FROM sisu_filtered
        ),
        age_calc AS (
            SELECT
                *,
                EXTRACT(YEAR FROM CURRENT_DATE()) - EXTRACT(YEAR FROM CAST(data_nascimento AS DATE)) as idade,
                CASE
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE()) - EXTRACT(YEAR FROM CAST(data_nascimento AS DATE)) <= 17 THEN '0-17'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE()) - EXTRACT(YEAR FROM CAST(data_nascimento AS DATE)) <= 24 THEN '18-24'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE()) - EXTRACT(YEAR FROM CAST(data_nascimento AS DATE)) <= 29 THEN '25-29'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE()) - EXTRACT(YEAR FROM CAST(data_nascimento AS DATE)) <= 34 THEN '30-34'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE()) - EXTRACT(YEAR FROM CAST(data_nascimento AS DATE)) <= 39 THEN '35-39'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE()) - EXTRACT(YEAR FROM CAST(data_nascimento AS DATE)) <= 49 THEN '40-49'
                    WHEN EXTRACT(YEAR FROM CURRENT_DATE()) - EXTRACT(YEAR FROM CAST(data_nascimento AS DATE)) <= 59 THEN '50-59'
                    ELSE '60+'
                END as faixa_etaria
            FROM pcd_detection
        )
        SELECT
            ano,
            id_ies,
            id_curso,
            MAX(nome_curso) as nome_curso,
            MAX(sigla_ies) as sigla_ies,
            MAX(sigla_uf) as sigla_uf,
            MAX(campus) as campus,
            MAX(turno) as turno,
            MAX(periodicidade) as periodicidade,
            -- Contadores principais
            COUNT(*) as inscricoes_total,
            COUNTIF(is_pcd) as inscricoes_pcd,
            COUNTIF(LOWER(status_candidato) LIKE '%aprovado%' AND NOT is_pcd) as aprovados_regular,
            COUNTIF(LOWER(status_candidato) LIKE '%aprovado%' AND is_pcd) as aprovados_pcd,
            COUNTIF(LOWER(status_matricula) LIKE '%matriculado%' AND NOT is_pcd) as matriculados_final,
            COUNTIF(LOWER(status_matricula) LIKE '%matriculado%' AND is_pcd) as matriculados_pcd_final,
            -- Notas
            AVG(CAST(nota_candidato AS FLOAT64)) as media_nota_candidato,
            AVG(CASE WHEN is_pcd THEN CAST(nota_candidato AS FLOAT64) END) as media_nota_candidato_pcd,
            AVG(CAST(nota_corte AS FLOAT64)) as media_nota_corte,
            AVG(CASE WHEN is_pcd THEN CAST(nota_corte AS FLOAT64) END) as media_nota_corte_pcd,
            -- Agregações por sexo (JSON)
            ARRAY_AGG(STRUCT(
                UPPER(SUBSTR(sexo, 1, 1)) as sexo,
                COUNT(*) as inscricoes,
                COUNTIF(is_pcd) as inscricoes_pcd,
                COUNTIF(LOWER(status_candidato) LIKE '%aprovado%' AND is_pcd) as aprovados_pcd,
                COUNTIF(LOWER(status_matricula) LIKE '%matriculado%' AND is_pcd) as matriculados_pcd
            ) IGNORE NULLS) as por_sexo,
            -- Agregações por faixa etária (JSON)
            ARRAY_AGG(STRUCT(
                faixa_etaria,
                COUNT(*) as inscricoes,
                COUNTIF(is_pcd) as inscricoes_pcd,
                COUNTIF(LOWER(status_candidato) LIKE '%aprovado%' AND is_pcd) as aprovados_pcd,
                COUNTIF(LOWER(status_matricula) LIKE '%matriculado%' AND is_pcd) as matriculados_pcd
            ) IGNORE NULLS) as por_faixa_etaria,
            -- Agregações por município (JSON)
            ARRAY_AGG(STRUCT(
                CAST(id_municipio_candidato AS STRING) as id_municipio,
                nome_municipio_candidato as municipio,
                uf_candidato as uf,
                COUNT(*) as inscricoes,
                COUNTIF(is_pcd) as inscricoes_pcd,
                COUNTIF(LOWER(status_candidato) LIKE '%aprovado%' AND is_pcd) as aprovados_pcd,
                COUNTIF(LOWER(status_matricula) LIKE '%matriculado%' AND is_pcd) as matriculados_pcd
            ) IGNORE NULLS) as por_municipio
        FROM age_calc
        GROUP BY ano, id_ies, id_curso
        ORDER BY ano, id_ies, id_curso
        """
        
        return query
    
    def transform_batch_optimized(self, year_range=None, id_ies=None):
        """
        Transforma batch de SISU usando agregação no BigQuery.
        
        Args:
            year_range: Tuple (start_year, end_year)
            id_ies: ID do IES para filtrar
            
        Returns:
            Tuple[List[dict], List[dict]]: (sisu_agg, sisu_t)
                - sisu_agg: Documentos agregados finalizados prontos para MongoDB
                - sisu_t: Dados brutos transformados (para Fase 4)
        """
        try:
            logger.info("Fase 3 - Transformando SISU (otimizado com BigQuery)...")
            
            # Gerar query de agregação
            query = self._get_sisu_aggregation_query(year_range, id_ies)
            
            logger.info(f"Executando agregação no BigQuery...")
            results = self.bq_client.fetch_data(query)
            
            logger.info(f"BigQuery retornou {len(results)} agregados de cursos")
            
            # Transformar resultados em documentos finalizados
            sisu_docs = []
            for agg in results:
                doc = self._finalize_sisu_document(agg)
                sisu_docs.append(doc)
            
            logger.info(f"Fase 3: {len(sisu_docs)} documentos SISU finalizados")
            
            return sisu_docs, []  # Retorna agregados e lista vazia (não precisa de brutos)
        
        except Exception as e:
            logger.error(f"Erro na Fase 3 (otimizado): {e}", exc_info=True)
            raise
    
    def _finalize_sisu_document(self, agg):
        """
        Finaliza um documento agregado de SISU.
        
        Args:
            agg: Resultado de agregação do BigQuery
            
        Returns:
            dict: Documento pronto para MongoDB
        """
        ano = int(agg.get("ano", 0))
        id_ies = str(agg.get("id_ies", ""))
        id_curso = str(agg.get("id_curso", ""))
        
        doc = {
            "_id": f"{ano}_{id_ies}_{id_curso}",
            "ano": ano,
            "idIes": id_ies,
            "idCurso": id_curso,
            "hasMatch": True,
            "inscricoesTotal": int(agg.get("inscricoes_total", 0)),
            "inscricoesPcd": int(agg.get("inscricoes_pcd", 0)),
            "aprovadosRegular": int(agg.get("aprovados_regular", 0)),
            "aprovadosPcdRegular": int(agg.get("aprovados_pcd", 0)),
            "matriculadosFinal": int(agg.get("matriculados_final", 0)),
            "matriculadosPcdFinal": int(agg.get("matriculados_pcd_final", 0)),
            "notaCandidatoMediaGeral": round(float(agg.get("media_nota_candidato") or 0), 2),
            "notaCandidatoMediaPcd": round(float(agg.get("media_nota_candidato_pcd") or 0), 2),
            "notaCorteMediaRegular": round(float(agg.get("media_nota_corte") or 0), 2),
            "notaCorteMediaPcdRegular": round(float(agg.get("media_nota_corte_pcd") or 0), 2),
            "demografia": {
                "porSexo": self._parse_array_agregado(agg.get("por_sexo", [])),
                "porFaixaEtaria": self._parse_array_agregado(agg.get("por_faixa_etaria", [])),
                "porMunicipio": self._parse_array_agregado(agg.get("por_municipio", [])),
            }
        }
        
        # Adicionar campos opcionais
        if agg.get("nome_curso"):
            doc["nomeCurso"] = agg["nome_curso"]
        if agg.get("sigla_ies"):
            doc["siglaIes"] = agg["sigla_ies"]
        if agg.get("sigla_uf"):
            doc["siglUfIes"] = agg["sigla_uf"]
        if agg.get("campus"):
            doc["campus"] = agg["campus"]
        if agg.get("turno"):
            doc["turno"] = agg["turno"]
        if agg.get("periodicidade"):
            doc["periodicidade"] = agg["periodicidade"]
        
        return doc
    
    def _parse_array_agregado(self, arr):
        """
        Converte arrays agregados do BigQuery para formato de documento.
        
        Args:
            arr: Array de structs do BigQuery
            
        Returns:
            List[dict]: Lista de dicionários
        """
        if not arr:
            return []
        
        result = []
        for item in arr:
            if isinstance(item, dict):
                result.append(item)
            else:
                # Se for tuple ou outro tipo, converter
                result.append(dict(item))
        
        return result
