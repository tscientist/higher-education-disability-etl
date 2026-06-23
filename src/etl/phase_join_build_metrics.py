"""
Phase 4-6: Join SISU + Censo, Build Final Document, Calculate Metrics

Junta dados de SISU com dados de Censo.
Constrói o documento analítico final.
Calcula métricas derivadas.
"""

from datetime import datetime
from ..utils.logger import logger


class PhaseJoinBuildMetrics:
    """Junta Censo + SISU e constrói documentos finais com métricas calculadas"""
    
    def __init__(self):
        pass
    
    def _safe_divide(self, numerator, denominator):
        """
        Realiza divisão segura (evita ZeroDivisionError).
        
        Args:
            numerator: Numerador
            denominator: Denominador
            
        Returns:
            float ou None: Resultado da divisão ou None
        """
        if denominator is None or denominator == 0:
            return None
        
        try:
            return float(numerator) / float(denominator)
        except (ValueError, TypeError, ZeroDivisionError):
            return None
    
    def _calculate_metrics(self, curso_data):
        """
        Calcula métricas derivadas para um curso.
        
        Args:
            curso_data: Dados do curso com indicadores
            
        Returns:
            dict: Estrutura com métricas calculadas
        """
        # Extrair valores necessários
        indicadores = curso_data.get("indicadores_aluno", {})
        indicadores_pcd = curso_data.get("indicadores_deficiencia", {})
        
        matriculas_total = indicadores.get("matriculas", 0) or 0
        matriculas_pcd = indicadores_pcd.get("matriculas", 0) or 0
        
        ingressantes_total = indicadores.get("ingressantes", 0) or 0
        ingressantes_pcd = indicadores_pcd.get("ingressantes", 0) or 0
        
        concluintes_total = indicadores.get("concluintes", 0) or 0
        concluintes_pcd = indicadores_pcd.get("concluintes", 0) or 0
        
        # Calcular porcentagem de matrículas PcD
        percentual_matriculas_pcd = None
        if matriculas_total and matriculas_total > 0:
            percentual_matriculas_pcd = round(
                self._safe_divide(matriculas_pcd, matriculas_total) * 100,
                2
            )
        
        # Calcular taxa de conclusão geral
        taxa_conclusao_geral = None
        if ingressantes_total and ingressantes_total > 0:
            taxa_conclusao_geral = round(
                self._safe_divide(concluintes_total, ingressantes_total) * 100,
                2
            )
        
        # Calcular taxa de conclusão PcD
        taxa_conclusao_pcd = None
        if ingressantes_pcd and ingressantes_pcd > 0:
            taxa_conclusao_pcd = round(
                self._safe_divide(concluintes_pcd, ingressantes_pcd) * 100,
                2
            )
        
        # Calcular taxa de perda geral
        taxa_perda_geral = None
        if ingressantes_total and ingressantes_total > 0:
            taxa_perda_geral = round(
                self._safe_divide(
                    ingressantes_total - concluintes_total,
                    ingressantes_total
                ) * 100,
                2
            )
        
        # Calcular taxa de perda PcD
        taxa_perda_pcd = None
        if ingressantes_pcd and ingressantes_pcd > 0:
            taxa_perda_pcd = round(
                self._safe_divide(
                    ingressantes_pcd - concluintes_pcd,
                    ingressantes_pcd
                ) * 100,
                2
            )
        
        return {
            "percentualMatriculasPcd": percentual_matriculas_pcd,
            "taxaConclusaoGeral": taxa_conclusao_geral,
            "taxaConclusaoPcd": taxa_conclusao_pcd,
            "taxaPerdaGeral": taxa_perda_geral,
            "taxaPerdaPcd": taxa_perda_pcd,
        }
    
    def build_final_document(self, curso_enriquecido, sisu_doc=None, year_range=None):
        """
        Constrói o documento analítico final para MongoDB.
        
        Args:
            curso_enriquecido: Dados de curso enriquecido da Phase 2
            sisu_doc: Documento SISU agregado (opcional)
            year_range: Tupla (start_year, end_year) para metadados
            
        Returns:
            dict: Documento final pronto para MongoDB
        """
        ano = curso_enriquecido.get("ano")
        id_ies = str(curso_enriquecido.get("id_ies", ""))
        id_curso = str(curso_enriquecido.get("id_curso", ""))
        
        # Preparar dados de IES enrichment
        ies_enrichment = curso_enriquecido.get("_ies_enrichment") or {}
        
        # Extrair dados para transformação
        from .phase_transform_censo import PhaseTransformCenso
        phase2 = PhaseTransformCenso()
        
        # Construir estruturas de referência
        ies_ref = phase2._build_ies_reference(ies_enrichment) if ies_enrichment else {}
        curso_ref = phase2._build_curso_reference(curso_enriquecido)
        indicadores_aluno = phase2._build_indicadores_aluno(curso_enriquecido)
        indicadores_deficiencia = phase2._build_indicadores_deficiencia(curso_enriquecido)
        indicadores_permanencia = phase2._build_indicadores_permanencia(curso_enriquecido)
        
        # Estrutura de SISU
        sisu_structure = {
            "hasMatch": False,
        }
        if sisu_doc:
            sisu_structure = {
                "hasMatch": True,
                "inscricoesTotal": sisu_doc.get("inscricoesTotal", 0),
                "inscricoesPcd": sisu_doc.get("inscricoesPcd", 0),
                "aprovadosRegular": sisu_doc.get("aprovadosRegular", 0),
                "aprovadosPcdRegular": sisu_doc.get("aprovadosPcdRegular", 0),
                "matriculadosFinal": sisu_doc.get("matriculadosFinal", 0),
                "matriculadosPcdFinal": sisu_doc.get("matriculadosPcdFinal", 0),
                "notaCandidatoMediaGeral": sisu_doc.get("notaCandidatoMediaGeral"),
                "notaCandidatoMediaPcd": sisu_doc.get("notaCandidatoMediaPcd"),
                "notaCorteMediaRegular": sisu_doc.get("notaCorteMediaRegular"),
                "notaCorteMediaPcdRegular": sisu_doc.get("notaCorteMediaPcdRegular"),
                "demografia": sisu_doc.get("demografia", {
                    "porSexo": [],
                    "porFaixaEtaria": [],
                    "porMunicipio": [],
                }),
            }
        
        # Preparar dados para cálculo de métricas
        dados_metricas = {
            "indicadores_aluno": indicadores_aluno,
            "indicadores_deficiencia": indicadores_deficiencia,
        }
        
        # Calcular métricas
        metricas_calculadas = self._calculate_metrics(dados_metricas)
        
        # Construir documento final
        doc_final = {
            "_id": f"{ano}_{id_ies}_{id_curso}",
            "schemaVersion": 1,
            "ano": ano,
            "uf": curso_enriquecido.get("sigla_uf"),
            "idMunicipio": str(curso_enriquecido.get("id_municipio", "")),
            "ies": ies_ref,
            "curso": curso_ref,
            "indicadoresAluno": indicadores_aluno,
            "indicadoresDeficiencia": indicadores_deficiencia,
            "indicadoresPermanencia": indicadores_permanencia,
            "sisu": sisu_structure,
            "metricasCalculadas": metricas_calculadas,
            "etlMetadata": {
                "source": ["stg_censo_curso", "stg_censo_ies"],
                "loadedAt": datetime.now().isoformat(),
            }
        }
        
        if sisu_doc:
            doc_final["etlMetadata"]["source"].append("stg_sisu_microdados")
        
        if year_range:
            doc_final["etlMetadata"]["yearRange"] = {
                "start": year_range[0],
                "end": year_range[1],
            }
        
        return doc_final
    
    def join_with_sisu(self, censo_cursos_enriquecidos, sisu_final_docs):
        """
        Realiza left join entre Censo Cursos e SISU.
        
        Args:
            censo_cursos_enriquecidos: Lista de cursos enriquecidos da Phase 2
            sisu_final_docs: Lista de documentos SISU finalizados da Phase 3
            
        Returns:
            List[dict]: Lista de cursos com SISU matcher
        """
        logger.info("Phase 4 - Juntando Censo com SISU...")
        
        # Criar índice SISU por chave (ano, id_ies, id_curso)
        sisu_index = {}
        for sisu_doc in sisu_final_docs:
            ano = sisu_doc.get("ano")
            id_ies = str(sisu_doc.get("idIes", ""))
            id_curso = str(sisu_doc.get("idCurso", ""))
            key = (ano, id_ies, id_curso)
            sisu_index[key] = sisu_doc
        
        # Realizar join left
        joined_result = []
        for curso in censo_cursos_enriquecidos:
            ano = curso.get("ano")
            id_ies = str(curso.get("id_ies", ""))
            id_curso = str(curso.get("id_curso", ""))
            key = (ano, id_ies, id_curso)
            
            sisu_match = sisu_index.get(key)
            
            curso["_sisu_match"] = sisu_match
            joined_result.append(curso)
        
        logger.info(f"Join concluído: {len(joined_result)} cursos processados")
        return joined_result
    
    def run(self, censo_cursos_enriquecidos, sisu_final_docs, year_range=None):
        """
        Executa as fases 4-6: Join, Build e Metrics.
        
        Args:
            censo_cursos_enriquecidos: Cursos enriquecidos da Phase 2
            sisu_final_docs: Documentos SISU finalizados da Phase 3
            year_range: Tupla (start_year, end_year) para metadados
            
        Returns:
            List[dict]: Lista de documentos finais prontos para MongoDB
        """
        try:
            logger.info("=" * 80)
            logger.info("PHASE 4-6: JOIN SISU + CENSO, BUILD & CALCULATE METRICS")
            logger.info("=" * 80)
            
            # Phase 4: Join
            joined_data = self.join_with_sisu(censo_cursos_enriquecidos, sisu_final_docs)
            
            # Phase 5: Build final documents
            logger.info("Phase 5 - Construindo documentos finais...")
            final_docs = []
            for curso in joined_data:
                sisu_match = curso.get("_sisu_match")
                doc = self.build_final_document(curso, sisu_match, year_range)
                final_docs.append(doc)
            
            # Phase 6: Métricas já foram calculadas em build_final_document
            logger.info("Phase 6 - Métricas calculadas")
            
            logger.info("")
            logger.info("PHASE 4-6 - JOIN, BUILD & METRICS SUMMARY")
            logger.info("-" * 80)
            logger.info(f"Documentos finais construídos: {len(final_docs)}")
            docs_with_sisu = sum(1 for d in final_docs if d.get("sisu", {}).get("hasMatch"))
            logger.info(f"Documentos com match SISU:     {docs_with_sisu}")
            logger.info("-" * 80)
            
            return final_docs
        except Exception as e:
            logger.error(f"Erro na Phase 4-6 - Join, Build & Metrics: {e}", exc_info=True)
            raise
