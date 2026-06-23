"""
Fase 2: Transform Censo Curso + Censo IES

Join das tabelas de Censo Curso e Censo IES.
Seleciona campos relevantes e normaliza tipos de dados.
"""

from ..utils.logger import logger


class Fase2TransformCenso:
    """Transforma e une dados de Censo Curso e Censo IES"""
    
    # Campos selecionados de Censo IES para enrichment
    CENSO_IES_FIELDS = [
        "ano",
        "id_ies",
        "nome",
        "sigla",
        "sigla_uf",
        "id_municipio",
        "tipo_organizacao_academica",
        "tipo_categoria_administrativa",
        "endereco",
        "numero",
        "complemento",
        "bairro",
        "cep",
    ]
    
    # Campos de Censo Curso
    CENSO_CURSO_FIELDS = [
        # Identificação e chave de join
        "ano",
        "id_ies",
        "id_curso",
        "sigla_uf",
        "id_municipio",
        # Nome e classificação
        "nome_curso",
        "nome_curso_cine",
        "id_curso_cine",
        "id_area_geral",
        "nome_area_geral",
        "id_area_especifica",
        "nome_area_especifica",
        "id_area_detalhada",
        "nome_area_detalhada",
        # Tipo/Classificação do curso
        "tipo_dimensao",
        "tipo_organizacao_academica",
        "tipo_organizacao_administrativa",
        "rede",
        "tipo_grau_academico",
        "indicador_gratuito",
        "tipo_modalidade_ensino",
        "tipo_nivel_academico",
        # Indicadores gerais de alunos
        "quantidade_vagas",
        "quantidade_inscritos",
        "quantidade_ingressantes",
        "quantidade_matriculas",
        "quantidade_concluintes",
        # Indicadores de deficiência
        "quantidade_alunos_deficiencia",
        "quantidade_ingressantes_deficiencia",
        "quantidade_matriculas_deficiencia",
        "quantidade_concluintes_deficiencia",
        # Indicadores de reserva de vaga
        "quantidade_ingressantes_reserva_vaga",
        "quantidade_ingressantes_reserva_vaga_rede_publica",
        "quantidade_ingressantes_reserva_vaga_etnico",
        "quantidade_ingressantes_reserva_vaga_deficiencia",
        "quantidade_ingressantes_reserva_vaga_social_renda_familiar",
        "quantidade_ingressantes_reserva_vaga_outros",
        "quantidade_matriculas_reserva_vaga",
        "quantidade_matriculas_reserva_vaga_rede_publica",
        "quantidade_matriculas_reserva_vaga_etnico",
        "quantidade_matriculas_reserva_vaga_deficiencia",
        "quantidade_matriculas_reserva_vaga_social_renda_familiar",
        "quantidade_matriculas_reserva_vaga_outros",
        "quantidade_concluintes_reserva_vaga",
        "quantidade_concluintes_reserva_vaga_rede_publica",
        "quantidade_concluintes_reserva_vaga_etnico",
        "quantidade_concluintes_reserva_vaga_deficiencia",
        "quantidade_concluintes_reserva_vaga_social_renda_familiar",
        "quantidade_concluintes_reserva_vaga_outros",
        # Indicadores de permanência/status
        "quantidade_alunos_situacao_trancada",
        "quantidade_alunos_situacao_desvinculada",
        "quantidade_alunos_situacao_transferida",
        "quantidade_alunos_situacao_falecidos",
        "quantidade_alunos_parfor",
        "quantidade_ingressantes_parfor",
        "quantidade_matriculas_parfor",
        "quantidade_concluintes_parfor",
        "quantidade_alunos_apoio_social",
        "quantidade_ingressantes_apoio_social",
        "quantidade_matriculas_apoio_social",
        "quantidade_concluintes_apoio_social",
        "quantidade_alunos_atividade_extracurricular",
        "quantidade_ingressantes_atividade_extracurricular",
        "quantidade_matriculas_atividade_extracurricular",
        "quantidade_concluintes_atividade_extracurricular",
        "quantidade_alunos_mobilidade_academica",
        "quantidade_ingressantes_mobilidade_academica",
        "quantidade_matriculas_mobilidade_academica",
        "quantidade_concluintes_mobilidade_academica",
    ]
    
    def __init__(self):
        self.missing_fields = set()
    
    def _select_fields(self, record, allowed_fields):
        """
        Seleciona apenas os campos permitidos de um registro.
        
        Args:
            record: Dicionário com os dados
            allowed_fields: Lista de campos permitidos
            
        Returns:
            dict: Novo dicionário com campos selecionados
        """
        selected = {}
        for field in allowed_fields:
            if field in record:
                selected[field] = record[field]
            else:
                self.missing_fields.add(field)
        return selected
    
    def _normalize_numeric(self, value):
        """
        Normaliza valores numéricos.
        
        Args:
            value: Valor a normalizar
            
        Returns:
            int ou float ou None
        """
        if value is None or value == "":
            return None
        
        # Se for string, tenta converter
        if isinstance(value, str):
            try:
                # Tenta int primeiro
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return None
        
        return value
    
    def _normalize_boolean(self, value):
        """
        Normaliza valores booleanos.
        
        Args:
            value: Valor a normalizar (string, bool ou int)
            
        Returns:
            bool ou None
        """
        if value is None or value == "":
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ["true", "1", "sim", "yes", "s"]:
                return True
            elif value_lower in ["false", "0", "nao", "no", "n"]:
                return False
        
        if isinstance(value, int):
            return value != 0
        
        return None
    
    def _normalize_census_record(self, record):
        """
        Normaliza um registro de Censo Curso.
        
        Args:
            record: Dicionário com dados brutos
            
        Returns:
            dict: Registro normalizado
        """
        normalized = record.copy()
        
        # Converter campos numéricos de contagem para int, faltando vira 0
        count_fields = [
            field for field in self.CENSO_CURSO_FIELDS
            if field.startswith("quantidade_")
        ]
        
        for field in count_fields:
            if field in normalized:
                value = normalized[field]
                normalized[field] = self._normalize_numeric(value)
                if normalized[field] is None:
                    normalized[field] = 0
        
        # Normalizar campos booleanos
        if "indicador_gratuito" in normalized:
            normalized["indicador_gratuito"] = self._normalize_boolean(
                normalized["indicador_gratuito"]
            )
        
        # Normalizar ano
        if "ano" in normalized:
            normalized["ano"] = int(normalized["ano"])
        
        return normalized
    
    def _normalize_ies_record(self, record):
        """
        Normaliza um registro de Censo IES.
        
        Args:
            record: Dicionário com dados brutos
            
        Returns:
            dict: Registro normalizado
        """
        normalized = record.copy()
        
        # Normalizar ano
        if "ano" in normalized:
            normalized["ano"] = int(normalized["ano"])
        
        # id_ies deve ser string
        if "id_ies" in normalized:
            normalized["id_ies"] = str(normalized["id_ies"])
        
        return normalized
    
    def _build_ies_reference(self, ies_record):
        """
        Constrói um Extended Reference para IES.
        
        Args:
            ies_record: Registro de Censo IES normalizado
            
        Returns:
            dict: Estrutura de IES para o documento final
        """
        return {
            "idIes": str(ies_record.get("id_ies", "")),
            "nome": ies_record.get("nome", ""),
            "sigla": ies_record.get("sigla", ""),
            "tipoOrganizacaoAcademica": ies_record.get("tipo_organizacao_academica"),
            "tipoCategoriaAdministrativa": ies_record.get("tipo_categoria_administrativa"),
            "endereco": {
                "logradouro": ies_record.get("endereco", ""),
                "numero": ies_record.get("numero", ""),
                "complemento": ies_record.get("complemento", ""),
                "bairro": ies_record.get("bairro", ""),
                "cep": ies_record.get("cep", ""),
            }
        }
    
    def _build_curso_reference(self, curso_record):
        """
        Constrói um Extended Reference para curso.
        
        Args:
            curso_record: Registro de Censo Curso normalizado
            
        Returns:
            dict: Estrutura de curso para o documento final
        """
        return {
            "idCurso": str(curso_record.get("id_curso", "")),
            "nome": curso_record.get("nome_curso", ""),
            "nomeCine": curso_record.get("nome_curso_cine", ""),
            "idCursoCine": curso_record.get("id_curso_cine", ""),
            "areaGeral": {
                "id": str(curso_record.get("id_area_geral", "")),
                "nome": curso_record.get("nome_area_geral", ""),
            },
            "areaEspecifica": {
                "id": str(curso_record.get("id_area_especifica", "")),
                "nome": curso_record.get("nome_area_especifica", ""),
            },
            "areaDetalhada": {
                "id": str(curso_record.get("id_area_detalhada", "")),
                "nome": curso_record.get("nome_area_detalhada", ""),
            },
            "tipoGrauAcademico": curso_record.get("tipo_grau_academico"),
            "tipoModalidadeEnsino": curso_record.get("tipo_modalidade_ensino"),
            "tipoNivelAcademico": curso_record.get("tipo_nivel_academico"),
            "indicadorGratuito": curso_record.get("indicador_gratuito"),
        }
    
    def _build_indicadores_aluno(self, curso_record):
        """Constrói estrutura de indicadores gerais de alunos"""
        return {
            "vagas": curso_record.get("quantidade_vagas", 0),
            "inscritos": curso_record.get("quantidade_inscritos", 0),
            "ingressantes": curso_record.get("quantidade_ingressantes", 0),
            "matriculas": curso_record.get("quantidade_matriculas", 0),
            "concluintes": curso_record.get("quantidade_concluintes", 0),
        }
    
    def _build_indicadores_deficiencia(self, curso_record):
        """Constrói estrutura de indicadores de deficiência"""
        return {
            "alunos": curso_record.get("quantidade_alunos_deficiencia", 0),
            "ingressantes": curso_record.get("quantidade_ingressantes_deficiencia", 0),
            "matriculas": curso_record.get("quantidade_matriculas_deficiencia", 0),
            "concluintes": curso_record.get("quantidade_concluintes_deficiencia", 0),
            "reservaVaga": {
                "ingressantes": curso_record.get("quantidade_ingressantes_reserva_vaga_deficiencia", 0),
                "matriculas": curso_record.get("quantidade_matriculas_reserva_vaga_deficiencia", 0),
                "concluintes": curso_record.get("quantidade_concluintes_reserva_vaga_deficiencia", 0),
            }
        }
    
    def _build_indicadores_permanencia(self, curso_record):
        """Constrói estrutura de indicadores de permanência"""
        return {
            "situacao": {
                "trancada": curso_record.get("quantidade_alunos_situacao_trancada", 0),
                "desvinculada": curso_record.get("quantidade_alunos_situacao_desvinculada", 0),
                "transferida": curso_record.get("quantidade_alunos_situacao_transferida", 0),
                "falecidos": curso_record.get("quantidade_alunos_situacao_falecidos", 0),
            },
            "apoioSocial": {
                "alunos": curso_record.get("quantidade_alunos_apoio_social", 0),
                "ingressantes": curso_record.get("quantidade_ingressantes_apoio_social", 0),
                "matriculas": curso_record.get("quantidade_matriculas_apoio_social", 0),
                "concluintes": curso_record.get("quantidade_concluintes_apoio_social", 0),
            },
            "atividadeExtracurricular": {
                "alunos": curso_record.get("quantidade_alunos_atividade_extracurricular", 0),
                "ingressantes": curso_record.get("quantidade_ingressantes_atividade_extracurricular", 0),
                "matriculas": curso_record.get("quantidade_matriculas_atividade_extracurricular", 0),
                "concluintes": curso_record.get("quantidade_concluintes_atividade_extracurricular", 0),
            },
            "mobilidadeAcademica": {
                "alunos": curso_record.get("quantidade_alunos_mobilidade_academica", 0),
                "ingressantes": curso_record.get("quantidade_ingressantes_mobilidade_academica", 0),
                "matriculas": curso_record.get("quantidade_matriculas_mobilidade_academica", 0),
                "concluintes": curso_record.get("quantidade_concluintes_mobilidade_academica", 0),
            },
            "parfor": {
                "alunos": curso_record.get("quantidade_alunos_parfor", 0),
                "ingressantes": curso_record.get("quantidade_ingressantes_parfor", 0),
                "matriculas": curso_record.get("quantidade_matriculas_parfor", 0),
                "concluintes": curso_record.get("quantidade_concluintes_parfor", 0),
            }
        }
    
    def join_censo_curso_with_ies(self, censo_curso_list, censo_ies_list):
        """
        Realiza left join de Censo Curso com Censo IES.
        
        Args:
            censo_curso_list: Lista de registros de Censo Curso
            censo_ies_list: Lista de registros de Censo IES
            
        Returns:
            List[dict]: Lista de cursos enriquecidos com dados de IES
        """
        logger.info("Iniciando join de Censo Curso + Censo IES...")
        
        # Normalizar dados
        curso_normalized = [self._normalize_census_record(r) for r in censo_curso_list]
        ies_normalized = [self._normalize_ies_record(r) for r in censo_ies_list]
        
        # Criar índice de IES por chave (ano, id_ies)
        ies_index = {}
        for ies_record in ies_normalized:
            key = (ies_record.get("ano"), str(ies_record.get("id_ies", "")))
            ies_index[key] = ies_record
        
        # Realizar join
        joined_data = []
        for curso in curso_normalized:
            ano = curso.get("ano")
            id_ies = str(curso.get("id_ies", ""))
            key = (ano, id_ies)
            
            # Buscar IES correspondente
            ies_data = ies_index.get(key)
            
            if ies_data:
                # Left join: adicionar dados de IES
                curso["_ies_enrichment"] = ies_data
            else:
                logger.warning(f"IES não encontrado para ano={ano}, id_ies={id_ies}")
                curso["_ies_enrichment"] = None
            
            joined_data.append(curso)
        
        logger.info(f"Join concluído: {len(joined_data)} registros de curso enriquecidos")
        return joined_data
    
    def run(self, censo_curso_list, censo_ies_list):
        """
        Executa a transformação de Censo.
        
        Args:
            censo_curso_list: Lista de registros de Censo Curso
            censo_ies_list: Lista de registros de Censo IES
            
        Returns:
            List[dict]: Lista de cursos transformados e enriquecidos
        """
        try:
            logger.info("=" * 80)
            logger.info("PHASE 2: TRANSFORM CENSO CURSO + CENSO IES")
            logger.info("=" * 80)
            
            joined_data = self.join_censo_curso_with_ies(censo_curso_list, censo_ies_list)
            
            logger.info("")
            logger.info("PHASE 2 - TRANSFORMATION SUMMARY")
            logger.info("-" * 80)
            logger.info(f"Registros de curso processados: {len(joined_data)}")
            if self.missing_fields:
                logger.warning(f"Campos faltantes encontrados: {sorted(self.missing_fields)}")
            logger.info("-" * 80)
            
            return joined_data
        except Exception as e:
            logger.error(f"Erro na Phase 2 - Transform Censo: {e}", exc_info=True)
            raise
    
    def transform_batch(self, censo_curso_batch, censo_ies_batch):
        """
        Transforma um batch de dados CENSO (Join IES + Curso).
        
        Args:
            censo_curso_batch: List de registros CENSO CURSO do batch
            censo_ies_batch: List de registros CENSO IES do batch
            
        Returns:
            List[dict]: Dados transformados e enriquecidos
        """
        try:
            logger.info(f"Transformando batch: {len(censo_curso_batch)} cursos + {len(censo_ies_batch)} IES")
            joined_data = self.join_censo_curso_with_ies(censo_curso_batch, censo_ies_batch)
            logger.info(f"Batch transformado: {len(joined_data)} registros")
            return joined_data
        except Exception as e:
            logger.error(f"Erro ao transformar batch CENSO: {e}", exc_info=True)
            raise
