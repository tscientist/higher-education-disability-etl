"""
Fase 3: Transform SISU microdados

Transforma dados de SISU:
- Remove identificadores pessoais
- Calcula idade e faixa etária
- Normaliza sexo e município
- Agregação por curso/instituição
"""

import re
from datetime import datetime
from ..utils.logger import logger


class FaseTransformSISU:
    """Transforma dados de SISU microdados"""
    
    # Faixas etárias padrão
    FAIXAS_ETARIAS = [
        (0, 17, "0-17"),
        (18, 24, "18-24"),
        (25, 29, "25-29"),
        (30, 34, "30-34"),
        (35, 39, "35-39"),
        (40, 49, "40-49"),
        (50, 59, "50-59"),
        (60, 200, "60+"),
    ]
    
    def __init__(self):
        self.schema_warnings = set()
        self.missing_columns = set()
    
    def _normalize_accents_case(self, text):
        """Remove acentos e converte para lowercase"""
        if not isinstance(text, str):
            return text
        
        accent_map = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
            'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c', 'ñ': 'n',
        }
        
        result = []
        for char in text.lower():
            result.append(accent_map.get(char, char))
        
        return ''.join(result)
    
    def _is_pcd_record(self, record):
        """
        Detecta se um registro é de PcD baseado em campos disponíveis.
        
        Args:
            record: Dicionário com dados do candidato
            
        Returns:
            bool: True se for identificado como PcD
        """
        pcd_indicators = [
            "modalidade_concorrencia",
            "tipo_cota",
            "cota_deficiencia",
            "deficiencia",
            "pcd",
        ]
        
        for field in pcd_indicators:
            if field in record:
                value = record[field]
                if value is None or value == "" or value == 0:
                    continue
                
                # Normalizar para comparação
                value_str = self._normalize_accents_case(str(value))
                
                # Verificar se contém indicadores de deficiência
                pcd_keywords = [
                    "deficiencia",
                    "deficiência",
                    "pcd",
                    "cota deficiencia",
                    "reserva deficiencia",
                ]
                
                for keyword in pcd_keywords:
                    if keyword in value_str:
                        return True
        
        return False
    
    def _calculate_idade(self, data_nascimento):
        """
        Calcula idade a partir da data de nascimento.
        
        Args:
            data_nascimento: Data de nascimento (str ou datetime)
            
        Returns:
            int ou None: Idade em anos
        """
        if not data_nascimento:
            return None
        
        try:
            # Se for string, tentar diferentes formatos
            if isinstance(data_nascimento, str):
                # Tentar formato YYYY-MM-DD
                if "T" in data_nascimento:
                    data_nascimento = data_nascimento.split("T")[0]
                
                try:
                    dt = datetime.strptime(data_nascimento, "%Y-%m-%d")
                except ValueError:
                    # Tentar DD/MM/YYYY
                    try:
                        dt = datetime.strptime(data_nascimento, "%d/%m/%Y")
                    except ValueError:
                        return None
            else:
                dt = data_nascimento
            
            today = datetime.now()
            idade = today.year - dt.year - (
                (today.month, today.day) < (dt.month, dt.day)
            )
            return max(0, idade)
        except Exception:
            return None
    
    def _get_faixa_etaria(self, idade):
        """
        Classifica idade em faixa etária.
        
        Args:
            idade: Idade em anos
            
        Returns:
            str: Faixa etária
        """
        if idade is None:
            return "nao_informado"
        
        for min_age, max_age, label in self.FAIXAS_ETARIAS:
            if min_age <= idade <= max_age:
                return label
        
        return "nao_informado"
    
    def _normalize_sexo(self, sexo):
        """
        Normaliza sexo para F, M ou NAO_INFORMADO.
        
        Args:
            sexo: Valor bruto de sexo
            
        Returns:
            str: F, M ou NAO_INFORMADO
        """
        if not sexo or sexo == "":
            return "NAO_INFORMADO"
        
        sexo_str = str(sexo).upper().strip()
        
        if sexo_str in ["F", "FEMININO", "FEM", "FEMALE"]:
            return "F"
        elif sexo_str in ["M", "MASCULINO", "MASC", "MALE"]:
            return "M"
        else:
            return "NAO_INFORMADO"
    
    def _inspect_schema(self, records):
        """
        Inspeciona o schema dos registros SISU.
        
        Args:
            records: Lista de registros
            
        Returns:
            set: Conjunto de nomes de colunas
        """
        if not records:
            return set()
        
        columns = set()
        for record in records:
            if isinstance(record, dict):
                columns.update(record.keys())
        
        logger.info(f"Colunas encontradas em SISU: {sorted(columns)}")
        return columns
    
    def aggregate_sisu_by_course(self, sisu_records):
        """
        Agrega registros SISU por curso/instituição.
        
        Args:
            sisu_records: Lista de registros de SISU
            
        Returns:
            dict: Dicionário com chave (ano, id_ies, id_curso) e dados agregados
        """
        logger.info("Agregando dados de SISU por curso/instituição...")
        
        if not sisu_records:
            logger.warning("Nenhum registro de SISU para agregar")
            return {}
        
        # Inspecionar schema
        schema = self._inspect_schema(sisu_records)
        
        # Agregar por chave
        aggregations = {}
        
        for record in sisu_records:
            # Extrair chave de agregação
            ano = record.get("ano")
            id_ies = record.get("id_ies")
            id_curso = record.get("id_curso")
            
            if not (ano and id_ies and id_curso):
                logger.warning(f"Registro de SISU faltando chave: {record}")
                continue
            
            key = (int(ano), str(id_ies), str(id_curso))
            
            if key not in aggregations:
                aggregations[key] = {
                    "ano": int(ano),
                    "id_ies": str(id_ies),
                    "id_curso": str(id_curso),
                    "sigla_uf_ies": record.get("sigla_uf"),
                    "nome_curso": record.get("nome_curso"),
                    "sigla_ies": record.get("sigla_ies"),
                    "campus": record.get("campus"),
                    "turno": record.get("turno"),
                    "periodicidade": record.get("periodicidade"),
                    # Contadores
                    "inscricoes_total": 0,
                    "inscricoes_pcd": 0,
                    "aprovados_regular": 0,
                    "aprovados_pcd": 0,
                    "matriculados_final": 0,
                    "matriculados_pcd_final": 0,
                    # Notas
                    "notas_candidato": [],
                    "notas_candidato_pcd": [],
                    "notas_corte": [],
                    "notas_corte_pcd": [],
                    # Demográficos
                    "demograficos_sexo": {},
                    "demograficos_faixa_etaria": {},
                    "demograficos_municipio": {},
                }
            
            # Contar inscrição
            aggregations[key]["inscricoes_total"] += 1
            
            # Verificar se é PcD
            is_pcd = self._is_pcd_record(record)
            if is_pcd:
                aggregations[key]["inscricoes_pcd"] += 1
            
            # Contar aprovados (se aplicável)
            status_aprovacao = record.get("status_candidato", "")
            if status_aprovacao and "aprovado" in str(status_aprovacao).lower():
                if is_pcd:
                    aggregations[key]["aprovados_pcd"] += 1
                else:
                    aggregations[key]["aprovados_regular"] += 1
            
            # Contar matriculados (se aplicável)
            status_matricula = record.get("status_matricula", "")
            if status_matricula and "matriculado" in str(status_matricula).lower():
                if is_pcd:
                    aggregations[key]["matriculados_pcd_final"] += 1
                else:
                    aggregations[key]["matriculados_final"] += 1
            
            # Coletar notas se disponível
            if "nota_candidato" in schema:
                nota = record.get("nota_candidato")
                if nota is not None:
                    try:
                        if is_pcd:
                            aggregations[key]["notas_candidato_pcd"].append(float(nota))
                        else:
                            aggregations[key]["notas_candidato"].append(float(nota))
                    except (ValueError, TypeError):
                        pass
            
            if "nota_corte" in schema:
                nota = record.get("nota_corte")
                if nota is not None:
                    try:
                        if is_pcd:
                            aggregations[key]["notas_corte_pcd"].append(float(nota))
                        else:
                            aggregations[key]["notas_corte"].append(float(nota))
                    except (ValueError, TypeError):
                        pass
            
            # Coletar dados demográficos
            sexo = self._normalize_sexo(record.get("sexo"))
            if sexo not in aggregations[key]["demograficos_sexo"]:
                aggregations[key]["demograficos_sexo"][sexo] = {
                    "sexo": sexo,
                    "inscricoes": 0,
                    "inscricoes_pcd": 0,
                    "aprovados_pcd": 0,
                    "matriculados_pcd": 0,
                }
            
            aggregations[key]["demograficos_sexo"][sexo]["inscricoes"] += 1
            if is_pcd:
                aggregations[key]["demograficos_sexo"][sexo]["inscricoes_pcd"] += 1
            
            # Faixa etária
            if "data_nascimento" in schema:
                idade = self._calculate_idade(record.get("data_nascimento"))
                faixa = self._get_faixa_etaria(idade)
                
                if faixa not in aggregations[key]["demograficos_faixa_etaria"]:
                    aggregations[key]["demograficos_faixa_etaria"][faixa] = {
                        "faixaEtaria": faixa,
                        "inscricoes": 0,
                        "inscricoes_pcd": 0,
                        "aprovados_pcd": 0,
                        "matriculados_pcd": 0,
                    }
                
                aggregations[key]["demograficos_faixa_etaria"][faixa]["inscricoes"] += 1
                if is_pcd:
                    aggregations[key]["demograficos_faixa_etaria"][faixa]["inscricoes_pcd"] += 1
            
            # Município de residência
            id_municipio_candidato = record.get("id_municipio_candidato")
            if id_municipio_candidato:
                id_municipio_candidato = str(id_municipio_candidato)
                nome_municipio = record.get("nome_municipio_candidato", "")
                uf_candidato = record.get("uf_candidato", "")
                
                if id_municipio_candidato not in aggregations[key]["demograficos_municipio"]:
                    aggregations[key]["demograficos_municipio"][id_municipio_candidato] = {
                        "idMunicipio": id_municipio_candidato,
                        "municipio": nome_municipio,
                        "uf": uf_candidato,
                        "inscricoes": 0,
                        "inscricoes_pcd": 0,
                        "aprovados_pcd": 0,
                        "matriculados_pcd": 0,
                    }
                
                aggregations[key]["demograficos_municipio"][id_municipio_candidato]["inscricoes"] += 1
                if is_pcd:
                    aggregations[key]["demograficos_municipio"][id_municipio_candidato][
                        "inscricoes_pcd"
                    ] += 1
        
        logger.info(f"SISU agregado em {len(aggregations)} grupos curso/instituição")
        return aggregations
    
    def _calculate_media_segura(self, values):
        """
        Calcula média com divisão segura.
        
        Args:
            values: Lista de valores numéricos
            
        Returns:
            float ou None: Média ou None se lista vazia
        """
        if not values or len(values) == 0:
            return None
        
        try:
            return round(sum(values) / len(values), 2)
        except (ValueError, TypeError, ZeroDivisionError):
            return None
    
    def finalize_sisu_aggregations(self, aggregations):
        """
        Finaliza agregações SISU calculando médias e estruturando dados.
        
        Args:
            aggregations: Dicionário de agregações brutas
            
        Returns:
            List[dict]: Lista de documentos SISU agregados finalizados
        """
        logger.info("Finalizando agregações de SISU...")
        
        final_docs = []
        
        for (ano, id_ies, id_curso), agg_data in aggregations.items():
            # Calcular médias de notas
            media_nota_candidato = self._calculate_media_segura(agg_data["notas_candidato"])
            media_nota_candidato_pcd = self._calculate_media_segura(agg_data["notas_candidato_pcd"])
            media_nota_corte = self._calculate_media_segura(agg_data["notas_corte"])
            media_nota_corte_pcd = self._calculate_media_segura(agg_data["notas_corte_pcd"])
            
            # Estruturar documento final
            doc = {
                "_id": f"{ano}_{id_ies}_{id_curso}",
                "ano": ano,
                "idIes": id_ies,
                "idCurso": id_curso,
                "hasMatch": True,
                "inscricoesTotal": agg_data["inscricoes_total"],
                "inscricoesPcd": agg_data["inscricoes_pcd"],
                "aprovadosRegular": agg_data["aprovados_regular"],
                "aprovadosPcdRegular": agg_data["aprovados_pcd"],
                "matriculadosFinal": agg_data["matriculados_final"],
                "matriculadosPcdFinal": agg_data["matriculados_pcd_final"],
                "notaCandidatoMediaGeral": media_nota_candidato,
                "notaCandidatoMediaPcd": media_nota_candidato_pcd,
                "notaCorteMediaRegular": media_nota_corte,
                "notaCorteMediaPcdRegular": media_nota_corte_pcd,
                "demografia": {
                    "porSexo": list(agg_data["demograficos_sexo"].values()),
                    "porFaixaEtaria": list(agg_data["demograficos_faixa_etaria"].values()),
                    "porMunicipio": list(agg_data["demograficos_municipio"].values()),
                }
            }
            
            # Adicionar campos opcionais se disponíveis
            if agg_data.get("sigla_uf_ies"):
                doc["siglUfIes"] = agg_data["sigla_uf_ies"]
            if agg_data.get("nome_curso"):
                doc["nomeCurso"] = agg_data["nome_curso"]
            if agg_data.get("sigla_ies"):
                doc["siglaIes"] = agg_data["sigla_ies"]
            if agg_data.get("campus"):
                doc["campus"] = agg_data["campus"]
            if agg_data.get("turno"):
                doc["turno"] = agg_data["turno"]
            if agg_data.get("periodicidade"):
                doc["periodicidade"] = agg_data["periodicidade"]
            
            final_docs.append(doc)
        
        logger.info(f"SISU: {len(final_docs)} documentos finalizados")
        return final_docs
    
    def run(self, sisu_records):
        """
        Executa a transformação completa de SISU.
        
        Args:
            sisu_records: Lista de registros de SISU
            
        Returns:
            tuple: (agregações brutas, documentos finalizados)
        """
        try:
            logger.info("=" * 80)
            logger.info("PHASE 3: TRANSFORM SISU MICRODADOS")
            logger.info("=" * 80)
            
            aggregations = self.aggregate_sisu_by_course(sisu_records)
            final_docs = self.finalize_sisu_aggregations(aggregations)
            
            logger.info("")
            logger.info("PHASE 3 - SISU TRANSFORMATION SUMMARY")
            logger.info("-" * 80)
            logger.info(f"Registros SISU originais:     {len(sisu_records)}")
            logger.info(f"Grupos agregados:            {len(aggregations)}")
            logger.info(f"Documentos finalizados:      {len(final_docs)}")
            logger.info("-" * 80)
            
            return aggregations, final_docs
        except Exception as e:
            logger.error(f"Erro na Phase 3 - Transform SISU: {e}", exc_info=True)
            raise
