"""
Phase 8: Create Indexes

Cria índices necessários para queries eficientes em MongoDB.
"""

from ..clients import MongoDBClient
from ..config import MONGO_COLLECTION_GOLD_COURSE, MONGO_COLLECTION_SISU_AGGREGATED
from ..utils.logger import logger


class PhaseCreateIndexes:
    """Cria índices para otimizar queries em MongoDB"""
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
    
    def create_indexes_gold_course(self):
        """
        Cria índices para a coleção gold_course_indicators.
        """
        logger.info(f"Criando índices em {MONGO_COLLECTION_GOLD_COURSE}...")
        
        indexes_to_create = [
            # Índice simples por ano
            (
                [("ano", 1)],
                {"name": "idx_ano"}
            ),
            # Índice por UF e ano
            (
                [("uf", 1), ("ano", 1)],
                {"name": "idx_uf_ano"}
            ),
            # Índice por ID IES e ano
            (
                [("ies.idIes", 1), ("ano", 1)],
                {"name": "idx_ies_ano"}
            ),
            # Índice por ID Curso e ano
            (
                [("curso.idCurso", 1), ("ano", 1)],
                {"name": "idx_curso_ano"}
            ),
            # Índice por tipo de modalidade e ano
            (
                [("curso.tipoModalidadeEnsino", 1), ("ano", 1)],
                {"name": "idx_modalidade_ano"}
            ),
            # Índice por categoria administrativa e ano
            (
                [("ies.tipoCategoriaAdministrativa", 1), ("ano", 1)],
                {"name": "idx_categoria_administrativa_ano"}
            ),
            # Índice por área geral e ano
            (
                [("curso.areaGeral.id", 1), ("ano", 1)],
                {"name": "idx_area_geral_ano"}
            ),
            # Índice para query de sexo em SISU
            (
                [("sisu.demografia.porSexo.sexo", 1), ("ano", 1)],
                {"name": "idx_sisu_sexo_ano"}
            ),
            # Índice para query de faixa etária em SISU
            (
                [("sisu.demografia.porFaixaEtaria.faixaEtaria", 1), ("ano", 1)],
                {"name": "idx_sisu_faixa_etaria_ano"}
            ),
            # Índice composto para filtros comuns
            (
                [
                    ("ano", 1),
                    ("uf", 1),
                    ("curso.tipoModalidadeEnsino", 1),
                    ("ies.tipoCategoriaAdministrativa", 1)
                ],
                {"name": "idx_compound_main_filters"}
            ),
        ]
        
        created_indexes = []
        for index_spec, index_opts in indexes_to_create:
            try:
                index_name = self.mongo_client.create_index(
                    MONGO_COLLECTION_GOLD_COURSE,
                    index_spec,
                    **index_opts
                )
                created_indexes.append(index_name)
            except Exception as e:
                logger.error(f"Erro ao criar índice {index_opts.get('name')}: {e}")
        
        return created_indexes
    
    def create_indexes_sisu_aggregated(self):
        """
        Cria índices para a coleção sisu_aggregated.
        """
        logger.info(f"Criando índices em {MONGO_COLLECTION_SISU_AGGREGATED}...")
        
        indexes_to_create = [
            # Índice por ano
            (
                [("ano", 1)],
                {"name": "idx_ano"}
            ),
            # Índice por ID IES e ano
            (
                [("idIes", 1), ("ano", 1)],
                {"name": "idx_ies_ano"}
            ),
            # Índice por ID Curso e ano
            (
                [("idCurso", 1), ("ano", 1)],
                {"name": "idx_curso_ano"}
            ),
        ]
        
        created_indexes = []
        for index_spec, index_opts in indexes_to_create:
            try:
                index_name = self.mongo_client.create_index(
                    MONGO_COLLECTION_SISU_AGGREGATED,
                    index_spec,
                    **index_opts
                )
                created_indexes.append(index_name)
            except Exception as e:
                logger.error(f"Erro ao criar índice {index_opts.get('name')}: {e}")
        
        return created_indexes
    
    def run(self):
        """
        Executa criação de todos os índices.
        """
        try:
            logger.info("=" * 80)
            logger.info("PHASE 8: CREATE INDEXES")
            logger.info("=" * 80)
            
            gold_indexes = self.create_indexes_gold_course()
            sisu_indexes = self.create_indexes_sisu_aggregated()
            
            logger.info("")
            logger.info("PHASE 8 - CREATE INDEXES SUMMARY")
            logger.info("-" * 80)
            logger.info(f"Índices criados em {MONGO_COLLECTION_GOLD_COURSE}: {len(gold_indexes)}")
            logger.info(f"Índices criados em {MONGO_COLLECTION_SISU_AGGREGATED}: {len(sisu_indexes)}")
            logger.info("-" * 80)
            
            return {
                "gold_course_indicators": gold_indexes,
                "sisu_aggregated": sisu_indexes,
            }
        except Exception as e:
            logger.error(f"Erro na Phase 8 - Create Indexes: {e}", exc_info=True)
            raise
        finally:
            self.mongo_client.close()
