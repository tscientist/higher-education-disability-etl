"""
Phases 4-8: Memory-safe ETL orchestrator for 2022
Reads from gold_course_indicators_source_2022 in pages
Transforms to MongoDB documents
Bulk upserts to MongoDB with idempotent upserts
Implements checkpoints and validation
"""

from datetime import datetime
from typing import Dict, List, Optional
from pymongo import ReplaceOne

from ..clients import BigQueryClient, MongoDBClient
from ..config import (
    BIGQUERY_DATASET,
    BQ_TABLE_GOLD_COURSE_INDICATORS_2022,
    BQ_TABLE_SILVER_SISU_AGGREGATED_2022,
    MONGO_COLLECTION_GOLD_COURSE,
    MONGO_COLLECTION_SISU_AGGREGATED,
    MONGO_COLLECTION_CHECKPOINTS,
    ETL_PAGE_SIZE,
)
from ..utils.logger import logger


class DocumentBuilder:
    """Builds MongoDB documents from BigQuery source rows"""
    
    AGE_GROUPS = [
        (0, 17, "0-17"),
        (18, 24, "18-24"),
        (25, 29, "25-29"),
        (30, 34, "30-34"),
        (35, 39, "35-39"),
        (40, 49, "40-49"),
        (50, 59, "50-59"),
        (60, 200, "60+"),
    ]
    
    @staticmethod
    def _safe_divide(numerator, denominator, multiply_by=1):
        """Safe division that returns None if denominator is 0 or None"""
        if not denominator or denominator == 0:
            return None
        if numerator is None:
            return None
        result = (numerator / denominator) * multiply_by
        return round(result, 2) if isinstance(result, float) else result
    
    @staticmethod
    def _normalize_boolean(value):
        """Normalize boolean values from BigQuery"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)
    
    @staticmethod
    def _normalize_int(value, default=0):
        """Normalize integer values"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def _build_sisu_section(row: Dict) -> Dict:
        """Build SISU section of the document"""
        sisu_section = {
            "hasMatch": DocumentBuilder._normalize_boolean(row.get("sisu_has_match")),
            "inscricoesTotal": DocumentBuilder._normalize_int(row.get("sisu_inscricoes_total")),
            "inscricoesPcd": DocumentBuilder._normalize_int(row.get("sisu_inscricoes_pcd")),
            "aprovadosRegular": DocumentBuilder._normalize_int(row.get("sisu_aprovados_regular")),
            "aprovadosPcd": DocumentBuilder._normalize_int(row.get("sisu_aprovados_pcd")),
            "matriculadosFinal": DocumentBuilder._normalize_int(row.get("sisu_matriculados_final")),
            "matriculadosPcdFinal": DocumentBuilder._normalize_int(row.get("sisu_matriculados_pcd_final")),
            "notaCandidatoMediaGeral": row.get("sisu_nota_candidato_media_geral"),
            "notaCandidatoMediaPcd": row.get("sisu_nota_candidato_media_pcd"),
            "notaCorteMediaGeral": row.get("sisu_nota_corte_media_geral"),
            "notaCorteMediaPcd": row.get("sisu_nota_corte_media_pcd"),
            "demografia": {
                "porSexo": row.get("sisu_demografia_por_sexo") or [],
                "porFaixaEtaria": row.get("sisu_demografia_por_faixa_etaria") or [],
                "porMunicipio": row.get("sisu_demografia_por_municipio_candidato") or [],
            }
        }
        return sisu_section
    
    @staticmethod
    def build_document(row: Dict) -> Dict:
        """
        Build a complete MongoDB document from a BigQuery source row
        
        Args:
            row: Dictionary from BigQuery result
            
        Returns:
            Dictionary suitable for MongoDB insertion
        """
        ano = DocumentBuilder._normalize_int(row.get("ano"))
        id_ies = str(row.get("id_ies", ""))
        id_curso = str(row.get("id_curso", ""))
        uf = row.get("sigla_uf", "XX")
        
        # Build deterministic ID
        _id = f"{ano}_{id_ies}_{id_curso}"
        
        # Build document
        doc = {
            "_id": _id,
            "schemaVersion": 1,
            "ano": ano,
            "uf": uf,
            "idMunicipio": row.get("id_municipio_curso"),
            
            "ies": {
                "idIes": id_ies,
                "nome": row.get("ies_nome", ""),
                "sigla": row.get("ies_sigla", ""),
                "tipoOrganizacaoAcademica": row.get("ies_tipo_organizacao_academica"),
                "tipoCategoriaAdministrativa": row.get("ies_tipo_categoria_administrativa"),
                "endereco": {
                    "logradouro": row.get("ies_endereco", ""),
                    "numero": row.get("ies_numero", ""),
                    "complemento": row.get("ies_complemento", ""),
                    "bairro": row.get("ies_bairro", ""),
                    "cep": row.get("ies_cep", ""),
                }
            },
            
            "curso": {
                "idCurso": id_curso,
                "nome": row.get("nome_curso", ""),
                "nomeCine": row.get("nome_curso_cine", ""),
                "idCursoCine": row.get("id_curso_cine", ""),
                "areaGeral": {
                    "id": row.get("id_area_geral", ""),
                    "nome": row.get("nome_area_geral", ""),
                },
                "areaEspecifica": {
                    "id": row.get("id_area_especifica", ""),
                    "nome": row.get("nome_area_especifica", ""),
                },
                "areaDetalhada": {
                    "id": row.get("id_area_detalhada", ""),
                    "nome": row.get("nome_area_detalhada", ""),
                },
                "tipoGrauAcademico": row.get("tipo_grau_academico"),
                "tipoModalidadeEnsino": row.get("tipo_modalidade_ensino"),
                "tipoNivelAcademico": row.get("tipo_nivel_academico"),
                "indicadorGratuito": DocumentBuilder._normalize_boolean(row.get("indicador_gratuito")),
            },
            
            "indicadoresAluno": {
                "vagas": DocumentBuilder._normalize_int(row.get("quantidade_vagas")),
                "inscritos": DocumentBuilder._normalize_int(row.get("quantidade_inscritos")),
                "ingressantes": DocumentBuilder._normalize_int(row.get("quantidade_ingressantes")),
                "matriculas": DocumentBuilder._normalize_int(row.get("quantidade_matriculas")),
                "concluintes": DocumentBuilder._normalize_int(row.get("quantidade_concluintes")),
            },
            
            "indicadoresDeficiencia": {
                "alunos": DocumentBuilder._normalize_int(row.get("quantidade_alunos_deficiencia")),
                "ingressantes": DocumentBuilder._normalize_int(row.get("quantidade_ingressantes_deficiencia")),
                "matriculas": DocumentBuilder._normalize_int(row.get("quantidade_matriculas_deficiencia")),
                "concluintes": DocumentBuilder._normalize_int(row.get("quantidade_concluintes_deficiencia")),
                "reservaVaga": {
                    "ingressantes": DocumentBuilder._normalize_int(row.get("quantidade_ingressantes_reserva_vaga_deficiencia")),
                    "matriculas": DocumentBuilder._normalize_int(row.get("quantidade_matriculas_reserva_vaga_deficiencia")),
                    "concluintes": DocumentBuilder._normalize_int(row.get("quantidade_concluintes_reserva_vaga_deficiencia")),
                }
            },
            
            "indicadoresPermanencia": {
                "situacao": {
                    "trancada": DocumentBuilder._normalize_int(row.get("quantidade_alunos_situacao_trancada")),
                    "desvinculada": DocumentBuilder._normalize_int(row.get("quantidade_alunos_situacao_desvinculada")),
                    "transferida": DocumentBuilder._normalize_int(row.get("quantidade_alunos_situacao_transferida")),
                    "falecidos": DocumentBuilder._normalize_int(row.get("quantidade_alunos_situacao_falecidos")),
                },
                "apoioSocial": {
                    "alunos": DocumentBuilder._normalize_int(row.get("quantidade_alunos_apoio_social")),
                    "ingressantes": DocumentBuilder._normalize_int(row.get("quantidade_ingressantes_apoio_social")),
                    "matriculas": DocumentBuilder._normalize_int(row.get("quantidade_matriculas_apoio_social")),
                    "concluintes": DocumentBuilder._normalize_int(row.get("quantidade_concluintes_apoio_social")),
                },
                "atividadeExtracurricular": {
                    "alunos": DocumentBuilder._normalize_int(row.get("quantidade_alunos_atividade_extracurricular")),
                    "ingressantes": DocumentBuilder._normalize_int(row.get("quantidade_ingressantes_atividade_extracurricular")),
                    "matriculas": DocumentBuilder._normalize_int(row.get("quantidade_matriculas_atividade_extracurricular")),
                    "concluintes": DocumentBuilder._normalize_int(row.get("quantidade_concluintes_atividade_extracurricular")),
                },
                "mobilidadeAcademica": {
                    "alunos": DocumentBuilder._normalize_int(row.get("quantidade_alunos_mobilidade_academica")),
                    "ingressantes": DocumentBuilder._normalize_int(row.get("quantidade_ingressantes_mobilidade_academica")),
                    "matriculas": DocumentBuilder._normalize_int(row.get("quantidade_matriculas_mobilidade_academica")),
                    "concluintes": DocumentBuilder._normalize_int(row.get("quantidade_concluintes_mobilidade_academica")),
                },
                "parfor": {
                    "alunos": DocumentBuilder._normalize_int(row.get("quantidade_alunos_parfor")),
                    "ingressantes": DocumentBuilder._normalize_int(row.get("quantidade_ingressantes_parfor")),
                    "matriculas": DocumentBuilder._normalize_int(row.get("quantidade_matriculas_parfor")),
                    "concluintes": DocumentBuilder._normalize_int(row.get("quantidade_concluintes_parfor")),
                }
            },
            
            "sisu": DocumentBuilder._build_sisu_section(row),
            
            "metricasCalculadas": {
                "percentualMatriculasPcd": DocumentBuilder._safe_divide(
                    row.get("quantidade_matriculas_deficiencia"),
                    row.get("quantidade_matriculas"),
                    100
                ),
                "taxaConclusaoGeral": DocumentBuilder._safe_divide(
                    row.get("quantidade_concluintes"),
                    row.get("quantidade_ingressantes"),
                    100
                ),
                "taxaConclusaoPcd": DocumentBuilder._safe_divide(
                    row.get("quantidade_concluintes_deficiencia"),
                    row.get("quantidade_ingressantes_deficiencia"),
                    100
                ),
                "taxaPerdaGeral": DocumentBuilder._safe_divide(
                    DocumentBuilder._normalize_int(row.get("quantidade_ingressantes"), 0) - 
                    DocumentBuilder._normalize_int(row.get("quantidade_concluintes"), 0),
                    row.get("quantidade_ingressantes"),
                    100
                ),
                "taxaPerdaPcd": DocumentBuilder._safe_divide(
                    DocumentBuilder._normalize_int(row.get("quantidade_ingressantes_deficiencia"), 0) - 
                    DocumentBuilder._normalize_int(row.get("quantidade_concluintes_deficiencia"), 0),
                    row.get("quantidade_ingressantes_deficiencia"),
                    100
                ),
            },
            
            "etlMetadata": {
                "source": [
                    "stg_censo_curso",
                    "stg_censo_ies",
                    "silver_sisu_aggregated_2022",
                    "stg_sisu_microdados"
                ],
                "loadedAt": datetime.utcnow().isoformat(),
                "yearRange": {
                    "start": ano,
                    "end": ano,
                }
            }
        }
        
        return doc


class CheckpointManager:
    """Manages ETL checkpoint for resumability"""
    
    def __init__(self, mongo_client: MongoDBClient):
        self.mongo_client = mongo_client
        self.collection = mongo_client.db[MONGO_COLLECTION_CHECKPOINTS]
    
    def start_job(self, year: int):
        """Mark job as started"""
        checkpoint = {
            "_id": f"gold_course_indicators_{year}",
            "jobName": "gold_course_indicators",
            "year": year,
            "status": "running",
            "processedCount": 0,
            "lastProcessedKey": None,
            "startedAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat(),
            "completedAt": None,
        }
        self.collection.replace_one({"_id": checkpoint["_id"]}, checkpoint, upsert=True)
        return checkpoint
    
    def check_if_completed(self, year: int) -> bool:
        """Check if job is already completed"""
        checkpoint = self.collection.find_one({"_id": f"gold_course_indicators_{year}"})
        if checkpoint and checkpoint.get("status") == "completed":
            return True
        return False
    
    def update_progress(self, year: int, processed_count: int, last_key: Optional[str] = None):
        """Update progress"""
        self.collection.update_one(
            {"_id": f"gold_course_indicators_{year}"},
            {
                "$set": {
                    "processedCount": processed_count,
                    "lastProcessedKey": last_key,
                    "updatedAt": datetime.utcnow().isoformat(),
                }
            }
        )
    
    def mark_completed(self, year: int):
        """Mark job as completed"""
        self.collection.update_one(
            {"_id": f"gold_course_indicators_{year}"},
            {
                "$set": {
                    "status": "completed",
                    "completedAt": datetime.utcnow().isoformat(),
                    "updatedAt": datetime.utcnow().isoformat(),
                }
            }
        )
    
    def mark_failed(self, year: int, error: str):
        """Mark job as failed"""
        self.collection.update_one(
            {"_id": f"gold_course_indicators_{year}"},
            {
                "$set": {
                    "status": "failed",
                    "error": error,
                    "updatedAt": datetime.utcnow().isoformat(),
                }
            }
        )


class ETLOrchestrator2022:
    """
    Phases 4-8: Main ETL orchestrator for 2022
    Reads from gold_course_indicators_source_2022 in pages
    Transforms to MongoDB documents
    Bulk upserts with checkpoints
    Validates counts
    """
    
    def __init__(self):
        self.bq_client = BigQueryClient()
        self.mongo_client = MongoDBClient()
        self.checkpoint_manager = CheckpointManager(self.mongo_client)
        self.total_processed = 0
    
    def run(self, force=False):
        """
        Run the complete ETL for 2022
        
        Args:
            force: If True, skip checkpoint and reprocess
        """
        year = 2022
        
        logger.info(f"\nPHASES 4-8: ETL ORCHESTRATOR FOR {year}")
        
        try:
            # Check if already completed
            if not force and self.checkpoint_manager.check_if_completed(year):
                logger.info(f"  Job for {year} already completed. Use --force to reprocess.")
                return self._validate(year)
            
            # Start checkpoint
            self.checkpoint_manager.start_job(year)
            logger.info(f"Started job for year {year}")
            
            # Phase 4: Read from gold table in pages
            logger.info(f"\n[PHASE 4] Reading gold_course_indicators_source_{year} in pages...")
            
            query = f"""
            SELECT *
            FROM `{self.bq_client.project_id}.{BIGQUERY_DATASET}.{BQ_TABLE_GOLD_COURSE_INDICATORS_2022}`
            WHERE ano = {year}
            ORDER BY id_ies, id_curso
            """
            
            page_num = 0
            for page in self.bq_client.fetch_pages(query, page_size=ETL_PAGE_SIZE):
                page_num += 1
                logger.info(f"\n[PAGE #{page_num}] Processing {len(page)} rows...")
                
                try:
                    # Phase 5-6: Transform documents and compute metrics
                    docs = []
                    for row in page:
                        doc = DocumentBuilder.build_document(row)
                        docs.append(doc)
                    
                    logger.info(f"Prepared {len(docs)} documents")
                    
                    # Phase 7: Bulk upsert to MongoDB
                    self._bulk_upsert_page(docs, page_num, year)
                    
                    self.total_processed += len(docs)
                    
                    # Update checkpoint
                    last_key = docs[-1]["_id"] if docs else None
                    self.checkpoint_manager.update_progress(year, self.total_processed, last_key)
                    
                except Exception as e:
                    logger.error(f"Error processing page {page_num}: {e}", exc_info=True)
                    self.checkpoint_manager.mark_failed(year, str(e))
                    raise
            
            # Mark completed
            self.checkpoint_manager.mark_completed(year)
            logger.info(f"\n  ETL completed: {self.total_processed} documents processed")
            
            # Phase 8: Validate gold_course_indicators
            gold_ok = self._validate(year)

            # Phase 9-B: Load sisu_aggregated (referenced collection for $lookup)
            logger.info("\n" + "=" * 80)
            logger.info("PHASE 9-B: POPULATING sisu_aggregated")
            logger.info("=" * 80)
            sisu_loader = SisuAggregatedLoader()
            sisu_ok = sisu_loader.run(force=force)

            return gold_ok and sisu_ok
            
        except Exception as e:
            logger.error(f" ETL failed: {e}", exc_info=True)
            self.checkpoint_manager.mark_failed(year, str(e))
            return False
    
    def _bulk_upsert_page(self, docs: List[Dict], page_num: int, year: int):
        """Bulk upsert a page of documents"""
        logger.info(f"Upserting {len(docs)} documents to MongoDB...")
        
        operations = [
            ReplaceOne(
                {"_id": doc["_id"]},
                doc,
                upsert=True
            )
            for doc in docs
        ]
        
        collection = self.mongo_client.db[MONGO_COLLECTION_GOLD_COURSE]
        result = collection.bulk_write(operations, ordered=False)
        
        logger.info(f"Upserted: {result.upserted_count} new, "
                   f"Matched: {result.matched_count}, "
                   f"Modified: {result.modified_count}")
    
    def _validate(self, year: int) -> bool:
        """Validate BigQuery vs MongoDB counts"""
        logger.info("\nPHASE 8: VALIDATION")
        
        try:
            # BigQuery count
            bq_count_query = f"""
            SELECT COUNT(*) as total, COUNT(DISTINCT sigla_uf) as uf_count
            FROM `{self.bq_client.project_id}.{BIGQUERY_DATASET}.{BQ_TABLE_GOLD_COURSE_INDICATORS_2022}`
            WHERE ano = {year}
            """
            bq_result = self.bq_client.fetch_data(bq_count_query)
            bq_total = bq_result[0]['total'] if bq_result else 0
            bq_uf_count = bq_result[0]['uf_count'] if bq_result else 0
            
            # MongoDB count
            collection = self.mongo_client.db[MONGO_COLLECTION_GOLD_COURSE]
            mongo_total = collection.count_documents({"ano": year})
            
            logger.info(f"\n Count Validation:")
            logger.info(f"  BigQuery total: {bq_total:,} (UFs: {bq_uf_count})")
            logger.info(f"  MongoDB total:  {mongo_total:,}")
            logger.info(f"  Match: {'  YES' if bq_total == mongo_total else '✗ NO'}")
            
            # Sample document
            sample = collection.find_one({"ano": year})
            if sample:
                logger.info(f"\n Sample Document:")
                logger.info(f"  _id: {sample['_id']}")
                logger.info(f"  IES: {sample['ies']['sigla']} - {sample['ies']['nome']}")
                logger.info(f"  Curso: {sample['curso']['nome']}")
                logger.info(f"  Matriculas: {sample['indicadoresAluno']['matriculas']}")
                logger.info(f"  Matriculas PcD: {sample['indicadoresDeficiencia']['matriculas']}")
            
            return bq_total == mongo_total
            
        except Exception as e:
            logger.error(f" Validation failed: {e}", exc_info=True)
            return False


class SisuAggregatedLoader:
    """
    Phase 9-B: Loads silver_sisu_aggregated_2022 from BigQuery into the
    MongoDB sisu_aggregated collection.

    This collection exists to satisfy the academic requirement for $lookup
    (referenced relationship). SISU data is still embedded inside
    gold_course_indicators for read performance — this is a deliberate
    duplication for demonstration purposes.

    Document shape:
    {
      "_id": "2022_634_15002",
      "ano": 2022,
      "id_ies": "634",
      "id_curso": "15002",
      "sigla_uf_ies": "RS",
      "inscricoes_total": 123,
      ...
      "demografia": { "porSexo": [], "porFaixaEtaria": [], "porMunicipio": [] },
      "etlMetadata": { "source": "silver_sisu_aggregated_2022", ... }
    }
    """

    def __init__(self):
        self.bq_client = BigQueryClient()
        self.mongo_client = MongoDBClient()

    @staticmethod
    def _build_sisu_doc(row: Dict) -> Dict:
        """Transform a BigQuery silver_sisu_aggregated row to a MongoDB document."""
        ano     = int(row.get("ano", 0))
        id_ies  = str(row.get("id_ies", ""))
        id_curso = str(row.get("id_curso", ""))

        def _int(v, default=0):
            try:
                return int(v) if v is not None else default
            except (ValueError, TypeError):
                return default

        def _float(v):
            try:
                return float(v) if v is not None else None
            except (ValueError, TypeError):
                return None

        def _list(v):
            """Ensure BigQuery repeated/array field is always a list of plain dicts."""
            if v is None:
                return []
            # BigQuery client returns repeated fields as lists of Row objects
            result = []
            for item in v:
                result.append(dict(item) if hasattr(item, 'items') else item)
            return result

        return {
            "_id": f"{ano}_{id_ies}_{id_curso}",
            "ano": ano,
            "id_ies": id_ies,
            "id_curso": id_curso,
            "sigla_uf_ies": row.get("sigla_uf_ies"),
            "inscricoes_total":          _int(row.get("inscricoes_total")),
            "inscricoes_pcd":            _int(row.get("inscricoes_pcd")),
            "aprovados_regular":         _int(row.get("aprovados_regular")),
            "aprovados_pcd":             _int(row.get("aprovados_pcd")),
            "matriculados_final":        _int(row.get("matriculados_final")),
            "matriculados_pcd_final":    _int(row.get("matriculados_pcd_final")),
            "nota_candidato_media_geral": _float(row.get("nota_candidato_media_geral")),
            "nota_candidato_media_pcd":   _float(row.get("nota_candidato_media_pcd")),
            "nota_corte_media_geral":     _float(row.get("nota_corte_media_geral")),
            "nota_corte_media_pcd":       _float(row.get("nota_corte_media_pcd")),
            "demografia": {
                "porSexo":        _list(row.get("demografia_por_sexo")),
                "porFaixaEtaria": _list(row.get("demografia_por_faixa_etaria")),
                "porMunicipio":   _list(row.get("demografia_por_municipio_candidato")),
            },
            "etlMetadata": {
                "source":   BQ_TABLE_SILVER_SISU_AGGREGATED_2022,
                "loadedAt": datetime.utcnow().isoformat(),
                "year":     ano,
            },
        }

    def run(self, force: bool = False) -> bool:
        """
        Read silver_sisu_aggregated_2022 from BigQuery in pages and
        bulk-upsert into MongoDB sisu_aggregated.
        """
        year = 2022
        collection = self.mongo_client.db[MONGO_COLLECTION_SISU_AGGREGATED]

        logger.info("\n" + "=" * 80)
        logger.info("PHASE 9-B: LOADING sisu_aggregated FROM silver_sisu_aggregated_2022")
        logger.info("=" * 80)

        # Skip if already populated and force not requested
        if not force:
            existing = collection.count_documents({"ano": year})
            if existing > 0:
                logger.info(f"  sisu_aggregated already has {existing:,} documents for {year}.")
                logger.info("  Use --force to reload. Skipping.")
                return self._validate(year)

        query = f"""
        SELECT *
        FROM `{self.bq_client.project_id}.{BIGQUERY_DATASET}.{BQ_TABLE_SILVER_SISU_AGGREGATED_2022}`
        WHERE ano = {year}
        ORDER BY id_ies, id_curso
        """

        page_num = 0
        total_processed = 0

        try:
            for page in self.bq_client.fetch_pages(query, page_size=ETL_PAGE_SIZE):
                page_num += 1
                logger.info(f"\n[SISU PAGE #{page_num}] Processing {len(page)} rows...")

                docs = [self._build_sisu_doc(row) for row in page]
                logger.info(f"  Prepared {len(docs)} documents")

                operations = [
                    ReplaceOne({"_id": doc["_id"]}, doc, upsert=True)
                    for doc in docs
                ]
                result = collection.bulk_write(operations, ordered=False)

                logger.info(
                    f"  Upserted: {result.upserted_count} new, "
                    f"Matched: {result.matched_count}, "
                    f"Modified: {result.modified_count}"
                )
                total_processed += len(docs)

            logger.info(f"\n  sisu_aggregated load complete: {total_processed:,} documents")
            return self._validate(year)

        except Exception as e:
            logger.error(f"  sisu_aggregated load failed: {e}", exc_info=True)
            return False

    def _validate(self, year: int) -> bool:
        """Compare BigQuery silver row count against MongoDB sisu_aggregated count."""
        logger.info("\n[SISU VALIDATION]")
        try:
            bq_result = self.bq_client.fetch_data(f"""
                SELECT COUNT(*) AS total
                FROM `{self.bq_client.project_id}.{BIGQUERY_DATASET}.{BQ_TABLE_SILVER_SISU_AGGREGATED_2022}`
                WHERE ano = {year}
            """)
            bq_total = bq_result[0]["total"] if bq_result else 0

            mongo_total = self.mongo_client.db[MONGO_COLLECTION_SISU_AGGREGATED].count_documents({"ano": year})

            logger.info(f"  BigQuery silver rows : {bq_total:,}")
            logger.info(f"  MongoDB sisu_aggregated: {mongo_total:,}")
            match = bq_total == mongo_total
            logger.info(f"  Match: {'✓ YES' if match else '✗ NO (delta=' + str(abs(bq_total - mongo_total)) + ')'}")
            return match

        except Exception as e:
            logger.error(f"  sisu_aggregated validation failed: {e}", exc_info=True)
            return False
