"""
Phase 11: Validation and Test Output

Valida a transformação e exibe estatísticas.
Busca documentos de teste conhecidos.
"""

from ..clients import MongoDBClient
from ..config import MONGO_COLLECTION_GOLD_COURSE, MONGO_COLLECTION_SISU_AGGREGATED
from ..utils.logger import logger


class PhaseValidation:
    """Valida a transformação e exibe resultados"""
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
    
    def print_validation_summary(self, stats):
        """
        Imprime resumo de validação.
        
        Args:
            stats: Dicionário com estatísticas
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("VALIDATION & TEST OUTPUT")
        logger.info("=" * 80)
        logger.info("")
        
        logger.info("EXTRACTION STATISTICS")
        logger.info("-" * 80)
        logger.info(f"BigQuery Censo IES:      {stats['extraction'].get('censo_ies_count', 0)} registros")
        logger.info(f"BigQuery Censo Curso:    {stats['extraction'].get('censo_curso_count', 0)} registros")
        logger.info(f"BigQuery SISU:           {stats['extraction'].get('sisu_microdados_count', 0)} registros")
        logger.info("")
        
        logger.info("AGGREGATION & TRANSFORMATION STATISTICS")
        logger.info("-" * 80)
        logger.info(f"SISU agregado em:        {stats['sisu'].get('agregated_groups', 0)} grupos")
        logger.info(f"SISU finalizados:        {stats['sisu'].get('final_docs', 0)} documentos")
        logger.info("")
        
        logger.info("FINAL DOCUMENTS STATISTICS")
        logger.info("-" * 80)
        logger.info(f"Documentos finais:       {stats['final'].get('total_docs', 0)} documentos")
        logger.info(f"Com match SISU:          {stats['final'].get('docs_with_sisu', 0)} documentos")
        logger.info("")
        
        logger.info("MONGODB LOAD STATISTICS")
        logger.info("-" * 80)
        logger.info(f"Gold Course Indicators:  "
                   f"{stats['mongodb'].get('gold_matched', 0)} matched, "
                   f"{stats['mongodb'].get('gold_modified', 0)} modified, "
                   f"{stats['mongodb'].get('gold_upserted', 0)} upserted")
        logger.info(f"SISU Aggregated:         "
                   f"{stats['mongodb'].get('sisu_matched', 0)} matched, "
                   f"{stats['mongodb'].get('sisu_modified', 0)} modified, "
                   f"{stats['mongodb'].get('sisu_upserted', 0)} upserted")
        logger.info("")
    
    def find_test_document(self):
        """
        Busca documento de teste com critérios conhecidos.
        
        Returns:
            dict ou None: Documento encontrado
        """
        logger.info("TEST DOCUMENT SEARCH")
        logger.info("-" * 80)
        logger.info("Buscando documento de teste: "
                   "id_ies=634, nome_curso contém 'Computação', ano 2018-2022")
        logger.info("")
        
        collection = self.mongo_client.get_collection(MONGO_COLLECTION_GOLD_COURSE)
        
        # Tentar encontrar um documento com critérios conhecidos
        query = {
            "ies.idIes": "634",
            "ano": {"$gte": 2018, "$lte": 2022},
            "curso.nome": {"$regex": "Computa", "$options": "i"}
        }
        
        doc = collection.find_one(query, projection={"_id": 1, "ano": 1, "ies": 1, "curso": 1})
        
        if doc:
            logger.info("DOCUMENTO DE TESTE ENCONTRADO:")
            logger.info(f"  _id: {doc.get('_id')}")
            logger.info(f"  ano: {doc.get('ano')}")
            logger.info(f"  IES: {doc.get('ies', {}).get('nome', 'N/A')}")
            logger.info(f"  Curso: {doc.get('curso', {}).get('nome', 'N/A')}")
            logger.info("")
            
            # Buscar documento completo para amostra
            full_doc = collection.find_one({"_id": doc.get("_id")})
            return full_doc
        else:
            logger.info("NENHUM DOCUMENTO DE TESTE ENCONTRADO COM CRITÉRIOS PADRÃO")
            logger.info("Buscando qualquer documento para amostra...")
            logger.info("")
            
            # Tentar encontrar qualquer documento
            any_doc = collection.find_one(
                {"ano": {"$gte": 2018, "$lte": 2022}},
                sort=[("_id", 1)]
            )
            
            if any_doc:
                logger.info("AMOSTRA DE DOCUMENTO ENCONTRADA:")
                logger.info(f"  _id: {any_doc.get('_id')}")
                logger.info(f"  ano: {any_doc.get('ano')}")
                logger.info(f"  IES: {any_doc.get('ies', {}).get('nome', 'N/A')}")
                logger.info(f"  Curso: {any_doc.get('curso', {}).get('nome', 'N/A')}")
                logger.info("")
                return any_doc
            else:
                logger.warning("NENHUM DOCUMENTO ENCONTRADO NO MONGODB")
                return None
    
    def print_sample_document(self, doc):
        """
        Imprime exemplo de documento formatado.
        
        Args:
            doc: Documento para imprimir
        """
        if not doc:
            logger.warning("Nenhum documento para exibir")
            return
        
        logger.info("SAMPLE DOCUMENT STRUCTURE:")
        logger.info("-" * 80)
        
        import json
        
        # Preparar versão resumida para log
        sample = {
            "_id": doc.get("_id"),
            "schemaVersion": doc.get("schemaVersion"),
            "ano": doc.get("ano"),
            "uf": doc.get("uf"),
            "idMunicipio": doc.get("idMunicipio"),
            "ies": {
                "idIes": doc.get("ies", {}).get("idIes"),
                "nome": doc.get("ies", {}).get("nome"),
                "sigla": doc.get("ies", {}).get("sigla"),
                "tipoOrganizacaoAcademica": doc.get("ies", {}).get("tipoOrganizacaoAcademica"),
                "tipoCategoriaAdministrativa": doc.get("ies", {}).get("tipoCategoriaAdministrativa"),
            },
            "curso": {
                "idCurso": doc.get("curso", {}).get("idCurso"),
                "nome": doc.get("curso", {}).get("nome"),
                "tipoGrauAcademico": doc.get("curso", {}).get("tipoGrauAcademico"),
                "tipoModalidadeEnsino": doc.get("curso", {}).get("tipoModalidadeEnsino"),
                "indicadorGratuito": doc.get("curso", {}).get("indicadorGratuito"),
            },
            "indicadoresAluno": doc.get("indicadoresAluno"),
            "indicadoresDeficiencia": doc.get("indicadoresDeficiencia"),
            "metricasCalculadas": doc.get("metricasCalculadas"),
            "sisu": {
                "hasMatch": doc.get("sisu", {}).get("hasMatch"),
                "inscricoesTotal": doc.get("sisu", {}).get("inscricoesTotal"),
                "inscricoesPcd": doc.get("sisu", {}).get("inscricoesPcd"),
            },
        }
        
        # Usar logging para imprimir JSON
        logger.info("")
        for line in json.dumps(sample, indent=2, ensure_ascii=False, default=str).split("\n"):
            logger.info(line)
        
        logger.info("-" * 80)
    
    def run(self, phase_results):
        """
        Executa validação e exibe resultados.
        
        Args:
            phase_results: Dicionário com resultados de cada fase
            
        Returns:
            dict: Estatísticas consolidadas
        """
        try:
            # Compilar estatísticas
            stats = {
                "extraction": phase_results.get("phase_1", {}),
                "sisu": {
                    "agregated_groups": len(phase_results.get("sisu_aggregations", {})),
                    "final_docs": len(phase_results.get("sisu_final_docs", [])),
                },
                "final": {
                    "total_docs": len(phase_results.get("final_documents", [])),
                    "docs_with_sisu": sum(
                        1 for d in phase_results.get("final_documents", [])
                        if d.get("sisu", {}).get("hasMatch")
                    ),
                },
                "mongodb": phase_results.get("mongodb_stats", {}),
            }
            
            # Imprimir resumo de validação
            self.print_validation_summary(stats)
            
            # Buscar e exibir documento de teste
            test_doc = self.find_test_document()
            self.print_sample_document(test_doc)
            
            logger.info("=" * 80)
            logger.info("VALIDATION COMPLETE")
            logger.info("=" * 80)
            
            return stats
        except Exception as e:
            logger.error(f"Erro na Phase 11 - Validation: {e}", exc_info=True)
            raise
        finally:
            self.mongo_client.close()
