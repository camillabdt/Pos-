"""Modelo de domínio do Percurso.

O percurso do discente tem três momentos:

- Entrada: data de ingresso, orientador(es) e plano de trabalho
  (incluindo as disciplinas planejadas).
- Meio: disciplinas cursadas, produções, prorrogações e qualificação.
- Fim: tema da dissertação/tese, defesa com banca e tempo de titulação.

Situações (em dia, atrasado, não qualificado...) NÃO são armazenadas:
são calculadas a partir destes fatos em `dominio.situacao`.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Nivel(StrEnum):
    MESTRADO = "mestrado"
    DOUTORADO = "doutorado"


class TipoDocente(StrEnum):
    PERMANENTE = "permanente"
    COLABORADOR = "colaborador"
    VISITANTE = "visitante"


class Resultado(StrEnum):
    AGENDADA = "agendada"
    APROVADO = "aprovado"
    APROVADO_COM_RESSALVAS = "aprovado_com_ressalvas"
    REPROVADO = "reprovado"


RESULTADOS_APROVADOS = {Resultado.APROVADO, Resultado.APROVADO_COM_RESSALVAS}


class PapelBanca(StrEnum):
    PRESIDENTE = "presidente"
    INTERNO = "interno"
    EXTERNO = "externo"
    SUPLENTE = "suplente"


class SituacaoDisciplina(StrEnum):
    CURSANDO = "cursando"
    APROVADO = "aprovado"
    REPROVADO = "reprovado"
    APROVEITADA = "aproveitada"


DISCIPLINA_CONCLUIDA = {SituacaoDisciplina.APROVADO, SituacaoDisciplina.APROVEITADA}


class TipoProducao(StrEnum):
    ARTIGO_PERIODICO = "artigo_periodico"
    ARTIGO_EVENTO = "artigo_evento"
    LIVRO = "livro"
    CAPITULO = "capitulo"
    SOFTWARE = "software"
    REGISTRO_SOFTWARE = "registro_software"
    PATENTE = "patente"
    PARTICIPACAO_EVENTO = "participacao_evento"
    STARTUP = "startup"
    PREMIO = "premio"
    OUTRO = "outro"


TIPOS_BIBLIOGRAFICOS = {
    TipoProducao.ARTIGO_PERIODICO,
    TipoProducao.ARTIGO_EVENTO,
    TipoProducao.LIVRO,
    TipoProducao.CAPITULO,
}


class Papel(StrEnum):
    COORDENACAO = "coordenacao"
    DOCENTE = "docente"
    DISCENTE = "discente"


# --------------------------------------------------------------------------
# Programa (configuração única: este sistema serve a um PPG)
# --------------------------------------------------------------------------


class PrazosNivel(BaseModel):
    conclusao_meses: int = Field(ge=1)
    qualificacao_meses: int = Field(ge=1)
    creditos_minimos: int = Field(default=0, ge=0)


class Programa(BaseModel):
    nome: str = "Programa de Pós-Graduação"
    sigla: str = "PPG"
    mestrado: PrazosNivel = PrazosNivel(conclusao_meses=24, qualificacao_meses=12, creditos_minimos=24)
    doutorado: PrazosNivel = PrazosNivel(conclusao_meses=48, qualificacao_meses=30, creditos_minimos=36)
    # Quantos dias antes do prazo o discente passa a aparecer como "prazo próximo".
    alerta_dias: int = Field(default=90, ge=0)

    def prazos(self, nivel: Nivel) -> PrazosNivel:
        return self.mestrado if nivel == Nivel.MESTRADO else self.doutorado


# --------------------------------------------------------------------------
# Cadastros de apoio
# --------------------------------------------------------------------------


class LinhaCriar(BaseModel):
    nome: str = Field(min_length=1)
    descricao: str | None = None


class Linha(LinhaCriar):
    id: str


class DisciplinaCriar(BaseModel):
    codigo: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    creditos: int = Field(ge=0)
    obrigatoria: bool = False


class Disciplina(DisciplinaCriar):
    id: str


class VeiculoCriar(BaseModel):
    """Periódico/evento com estrato Qualis. ISSN permite casar produções coletadas."""

    nome: str = Field(min_length=1)
    issn: list[str] = []
    qualis: str | None = None  # A1..A4, B1..B4, C, ou None

    @field_validator("issn")
    @classmethod
    def _normaliza_issn(cls, v: list[str]) -> list[str]:
        return [normaliza_issn(x) for x in v if x and x.strip()]


class Veiculo(VeiculoCriar):
    id: str


def normaliza_issn(issn: str) -> str:
    s = issn.strip().upper().replace("-", "")
    return f"{s[:4]}-{s[4:]}" if len(s) == 8 else issn.strip().upper()


# --------------------------------------------------------------------------
# Docentes
# --------------------------------------------------------------------------


class Metricas(BaseModel):
    h_index: int = 0
    h5_index: int = 0
    i10_index: int = 0
    citacoes: int = 0
    total_obras: int = 0
    coletado_em: date | None = None


def cauda_id(v: str | None) -> str | None:
    """Aceita 'A123', 'https://openalex.org/A123' ou 'https://orcid.org/0000-...'."""
    if not v or not v.strip():
        return None
    return v.strip().rstrip("/").split("/")[-1]


class DocenteCriar(BaseModel):
    nome: str = Field(min_length=1)
    email: str | None = None
    tipo: TipoDocente = TipoDocente.PERMANENTE
    linha_id: str | None = None
    lattes: str | None = None
    orcid: str | None = None
    openalex_id: str | None = None
    ativo: bool = True

    @field_validator("orcid", "openalex_id")
    @classmethod
    def _cauda(cls, v: str | None) -> str | None:
        return cauda_id(v)


class DocenteAtualizar(BaseModel):
    nome: str | None = None
    email: str | None = None
    tipo: TipoDocente | None = None
    linha_id: str | None = None
    lattes: str | None = None
    orcid: str | None = None
    openalex_id: str | None = None
    ativo: bool | None = None

    @field_validator("orcid", "openalex_id")
    @classmethod
    def _cauda(cls, v: str | None) -> str | None:
        return cauda_id(v)


class Docente(DocenteCriar):
    id: str
    metricas: Metricas = Metricas()


# --------------------------------------------------------------------------
# Discentes e o percurso
# --------------------------------------------------------------------------


class PlanoTrabalho(BaseModel):
    titulo_projeto: str = Field(min_length=1)
    resumo: str | None = None
    disciplinas_planejadas: list[str] = []  # ids de Disciplina
    aprovado_em: date | None = None


class DisciplinaCursada(BaseModel):
    disciplina_id: str
    semestre: str = Field(pattern=r"^\d{4}/[12]$", description="Ex.: 2026/1")
    situacao: SituacaoDisciplina = SituacaoDisciplina.CURSANDO
    conceito: str | None = None


class MembroBanca(BaseModel):
    nome: str = Field(min_length=1)
    instituicao: str | None = None
    papel: PapelBanca = PapelBanca.INTERNO
    docente_id: str | None = None


class Avaliacao(BaseModel):
    """Qualificação ou defesa: mesma estrutura (data, título, banca, resultado)."""

    data: date
    titulo: str = Field(min_length=1)
    resultado: Resultado = Resultado.AGENDADA
    banca: list[MembroBanca] = []
    observacao: str | None = None

    @property
    def aprovada(self) -> bool:
        return self.resultado in RESULTADOS_APROVADOS


class Prorrogacao(BaseModel):
    meses: int = Field(ge=1, le=24)
    motivo: str = Field(min_length=1)
    concedida_em: date


class Desligamento(BaseModel):
    data: date
    motivo: str = Field(min_length=1)


class DiscenteCriar(BaseModel):
    nome: str = Field(min_length=1)
    email: str | None = None
    matricula: str = Field(min_length=1)
    nivel: Nivel = Nivel.MESTRADO
    linha_id: str | None = None
    data_ingresso: date
    orientador_id: str
    coorientador_ids: list[str] = []
    plano: PlanoTrabalho | None = None
    tema: str | None = None


class DiscenteAtualizar(BaseModel):
    nome: str | None = None
    email: str | None = None
    matricula: str | None = None
    nivel: Nivel | None = None
    linha_id: str | None = None
    data_ingresso: date | None = None
    orientador_id: str | None = None
    coorientador_ids: list[str] | None = None
    tema: str | None = None


class Discente(DiscenteCriar):
    id: str
    disciplinas: list[DisciplinaCursada] = []
    prorrogacoes: list[Prorrogacao] = []
    qualificacao: Avaliacao | None = None
    defesa: Avaliacao | None = None
    desligamento: Desligamento | None = None


# --------------------------------------------------------------------------
# Produções (de discentes E de docentes, com coautoria)
# --------------------------------------------------------------------------


class Autor(BaseModel):
    nome: str = ""  # pode vir vazio quando há discente_id/docente_id: o serviço preenche
    discente_id: str | None = None
    docente_id: str | None = None


class VeiculoRef(BaseModel):
    nome: str | None = None
    issn: list[str] = []
    qualis: str | None = None


class ProducaoCriar(BaseModel):
    tipo: TipoProducao
    titulo: str = Field(min_length=1)
    ano: int = Field(ge=1950, le=2100)
    data: date | None = None
    autores: list[Autor] = Field(min_length=1)
    doi: str | None = None
    url: str | None = None
    veiculo: VeiculoRef | None = None
    # Campos específicos: número INPI, CNPJ da startup, nome do evento, local...
    detalhes: dict[str, str] = {}

    @field_validator("doi")
    @classmethod
    def _normaliza_doi(cls, v: str | None) -> str | None:
        return normaliza_doi(v)


def normaliza_doi(v: str | None) -> str | None:
    if not v or not v.strip():
        return None
    s = v.strip().lower()
    for prefixo in ("https://doi.org/", "http://doi.org/", "doi.org/", "doi:"):
        if s.startswith(prefixo):
            s = s[len(prefixo):]
    return s


class Producao(ProducaoCriar):
    id: str
    origem: str = "manual"  # manual | openalex
    openalex_id: str | None = None
    citacoes: int | None = None
