import { tokenAtual, identidadeDev } from "./auth";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export type Nivel = "mestrado" | "doutorado";
export type Resultado = "agendada" | "aprovado" | "aprovado_com_ressalvas" | "reprovado";
export type PapelBanca = "presidente" | "interno" | "externo" | "suplente";
export type SituacaoDisciplina = "cursando" | "aprovado" | "reprovado" | "aproveitada";
export type TipoProducao =
  | "artigo_periodico" | "artigo_evento" | "livro" | "capitulo" | "software" | "registro_software"
  | "patente" | "participacao_evento" | "startup" | "premio" | "outro";

export interface MembroBanca { nome: string; instituicao?: string | null; papel: PapelBanca; docente_id?: string | null }
export interface Avaliacao { data: string; titulo: string; resultado: Resultado; banca: MembroBanca[]; observacao?: string | null }
export interface PlanoTrabalho { titulo_projeto: string; resumo?: string | null; disciplinas_planejadas: string[]; aprovado_em?: string | null }
export interface DisciplinaCursada { disciplina_id: string; semestre: string; situacao: SituacaoDisciplina; conceito?: string | null }
export interface Prorrogacao { meses: number; motivo: string; concedida_em: string }

export interface Situacao {
  vinculo: "ativo" | "titulado" | "desligado";
  fase: "entrada" | "cursando" | "qualificado" | "defesa_agendada" | "titulado" | "desligado";
  prazo_qualificacao: string;
  prazo_conclusao: string;
  meses_prorrogados: number;
  qualificado: boolean;
  atrasado: boolean;
  qualificacao_atrasada: boolean;
  prazo_proximo: boolean;
  em_dia: boolean;
  dias_para_prazo: number | null;
  meses_no_programa: number;
  tempo_titulacao_meses: number | null;
  titulou_no_prazo: boolean | null;
  disciplinas: {
    planejadas: number; cumpridas_do_plano: number; pendentes_do_plano: string[];
    fora_do_plano: string[]; cursando: number; creditos_concluidos: number; creditos_minimos: number;
  };
  pendencias: string[];
}

export interface DiscenteResumo {
  id: string; nome: string; matricula: string; nivel: Nivel; data_ingresso: string;
  orientador_id: string; orientador_nome: string | null; tema: string | null; situacao: Situacao;
}

export interface Discente {
  id: string; nome: string; email?: string | null; matricula: string; nivel: Nivel; linha_id?: string | null;
  data_ingresso: string; orientador_id: string; coorientador_ids: string[]; plano: PlanoTrabalho | null;
  tema: string | null; disciplinas: DisciplinaCursada[]; prorrogacoes: Prorrogacao[];
  qualificacao: Avaliacao | null; defesa: Avaliacao | null; desligamento: { data: string; motivo: string } | null;
  orientador_nome: string | null; coorientadores_nomes: string[]; situacao: Situacao;
}

export interface Metricas { h_index: number; h5_index: number; i10_index: number; citacoes: number; total_obras: number; coletado_em: string | null }
export interface Docente {
  id: string; nome: string; email?: string | null; tipo: "permanente" | "colaborador" | "visitante";
  linha_id?: string | null; lattes?: string | null; orcid?: string | null; openalex_id?: string | null;
  ativo: boolean; metricas: Metricas;
}
export interface ResumoProducao {
  total: number; por_tipo: Record<string, number>; por_ano: Record<string, number>;
  por_qualis: Record<string, number>; com_discentes: number;
}
export interface DocenteDetalhe extends Docente { orientandos: DiscenteResumo[]; producao: ResumoProducao }

export interface Autor { nome: string; discente_id?: string | null; docente_id?: string | null }
export interface Producao {
  id: string; tipo: TipoProducao; titulo: string; ano: number; data?: string | null; autores: Autor[];
  doi?: string | null; url?: string | null; veiculo?: { nome?: string | null; issn: string[]; qualis?: string | null } | null;
  detalhes: Record<string, string>; origem: string; citacoes?: number | null;
}
export type ProducaoCriar = Omit<Producao, "id" | "origem" | "citacoes">;

export interface Disciplina { id: string; codigo: string; nome: string; creditos: number; obrigatoria: boolean }
export interface Linha { id: string; nome: string; descricao?: string | null }
export interface Veiculo { id: string; nome: string; issn: string[]; qualis?: string | null }
export interface PrazosNivel { conclusao_meses: number; qualificacao_meses: number; creditos_minimos: number }
export interface Programa { nome: string; sigla: string; mestrado: PrazosNivel; doutorado: PrazosNivel; alerta_dias: number }

export interface Totais {
  ativos: number; em_dia: number; atrasados: number; nao_qualificados: number;
  qualificacao_atrasada: number; prazo_proximo: number; titulados: number; desligados: number;
}
export interface Painel {
  hoje: string; programa: string; totais: Totais; por_nivel: Record<Nivel, Totais>;
  titulacao: { nivel: Nivel; titulados: number; media_meses: number | null; mediana_meses: number | null; no_prazo: number }[];
  por_orientador: { docente_id: string; nome: string; ativos: number; em_dia: number; atrasados: number; nao_qualificados: number; titulados: number }[];
  por_ano: { ano: number; ingressos: number; titulacoes: number; desligamentos: number }[];
  producao_por_tipo: Record<string, number>;
  producao_discente_ultimos_5_anos: number;
}
export interface ResultadoColeta {
  nome_openalex: string | null; obras_lidas: number; novas: number; atualizadas: number; ignoradas: number; metricas: Metricas;
}
export interface Usuario { uid: string; papel: "coordenacao" | "docente" | "discente"; docente_id?: string | null; discente_id?: string | null }

export class ErroApi extends Error {
  constructor(public status: number, mensagem: string) { super(mensagem); }
}

async function req<T>(metodo: string, caminho: string, corpo?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = await tokenAtual();
  if (token) headers.Authorization = `Bearer ${token}`;
  const dev = identidadeDev();
  if (dev) {
    headers["X-Dev-Papel"] = dev.papel;
    if (dev.id) headers["X-Dev-Id"] = dev.id;
  }
  let r: Response;
  try {
    r = await fetch(`${BASE}${caminho}`, { method: metodo, headers, body: corpo === undefined ? undefined : JSON.stringify(corpo) });
  } catch {
    throw new ErroApi(0, `Não foi possível falar com o servidor em ${BASE}. Ele está rodando?`);
  }
  if (r.status === 204) return undefined as T;
  const dados = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = dados?.detail;
    const msg = typeof det === "string" ? det
      : Array.isArray(det) ? det.map((d: { loc?: string[]; msg: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`).join("; ")
      : `Erro ${r.status}`;
    throw new ErroApi(r.status, msg);
  }
  return dados as T;
}

const qs = (p: Record<string, string | number | boolean | undefined | null>) => {
  const s = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "" && v !== false) s.set(k, String(v)); });
  const t = s.toString();
  return t ? `?${t}` : "";
};

export const api = {
  eu: () => req<Usuario>("GET", "/eu"),
  painel: () => req<Painel>("GET", "/painel"),
  programa: () => req<Programa>("GET", "/programa"),
  salvarPrograma: (p: Programa) => req<Programa>("PUT", "/programa", p),

  discentes: (p: { filtro?: string; orientador_id?: string; busca?: string } = {}) =>
    req<DiscenteResumo[]>("GET", `/discentes${qs(p)}`),
  discente: (id: string) => req<Discente>("GET", `/discentes/${id}`),
  criarDiscente: (d: unknown) => req<Discente>("POST", "/discentes", d),
  atualizarDiscente: (id: string, d: unknown) => req<Discente>("PATCH", `/discentes/${id}`, d),
  apagarDiscente: (id: string) => req<void>("DELETE", `/discentes/${id}`),
  plano: (id: string, p: PlanoTrabalho) => req<Discente>("PUT", `/discentes/${id}/plano`, p),
  disciplina: (id: string, d: DisciplinaCursada) => req<Discente>("PUT", `/discentes/${id}/disciplinas`, d),
  removerDisciplina: (id: string, disc: string, semestre: string) =>
    req<Discente>("DELETE", `/discentes/${id}/disciplinas/${disc}${qs({ semestre })}`),
  qualificacao: (id: string, a: Avaliacao) => req<Discente>("PUT", `/discentes/${id}/qualificacao`, a),
  defesa: (id: string, a: Avaliacao) => req<Discente>("PUT", `/discentes/${id}/defesa`, a),
  prorrogar: (id: string, p: Prorrogacao) => req<Discente>("POST", `/discentes/${id}/prorrogacoes`, p),
  removerProrrogacao: (id: string, i: number) => req<Discente>("DELETE", `/discentes/${id}/prorrogacoes/${i}`),
  desligar: (id: string, d: { data: string; motivo: string }) => req<Discente>("PUT", `/discentes/${id}/desligamento`, d),
  religar: (id: string) => req<Discente>("DELETE", `/discentes/${id}/desligamento`),

  docentes: () => req<Docente[]>("GET", "/docentes"),
  docente: (id: string) => req<DocenteDetalhe>("GET", `/docentes/${id}`),
  criarDocente: (d: unknown) => req<Docente>("POST", "/docentes", d),
  atualizarDocente: (id: string, d: unknown) => req<Docente>("PATCH", `/docentes/${id}`, d),
  coletar: (id: string) => req<ResultadoColeta>("POST", `/docentes/${id}/coletar`),

  producoes: (p: { discente_id?: string; docente_id?: string; tipo?: string; ano_de?: number; ano_ate?: number; so_com_discentes?: boolean; busca?: string } = {}) =>
    req<Producao[]>("GET", `/producoes${qs(p)}`),
  criarProducao: (p: ProducaoCriar) => req<Producao>("POST", "/producoes", p),
  atualizarProducao: (id: string, p: ProducaoCriar) => req<Producao>("PUT", `/producoes/${id}`, p),
  apagarProducao: (id: string) => req<void>("DELETE", `/producoes/${id}`),

  disciplinas: () => req<Disciplina[]>("GET", "/disciplinas"),
  linhas: () => req<Linha[]>("GET", "/linhas"),
  veiculos: () => req<Veiculo[]>("GET", "/veiculos"),
  criar: <T,>(colecao: "disciplinas" | "linhas" | "veiculos", d: unknown) => req<T>("POST", `/${colecao}`, d),
  salvar: <T,>(colecao: "disciplinas" | "linhas" | "veiculos", id: string, d: unknown) => req<T>("PUT", `/${colecao}/${id}`, d),
  apagar: (colecao: "disciplinas" | "linhas" | "veiculos", id: string) => req<void>("DELETE", `/${colecao}/${id}`),
};

/** Só no modo dev: lista pessoas para o seletor "ver como", sempre com olhos da coordenação. */
export async function pessoasParaTroca(): Promise<{ docentes: Docente[]; discentes: DiscenteResumo[] }> {
  const h = { "X-Dev-Papel": "coordenacao" };
  const [docentes, discentes] = await Promise.all([
    fetch(`${BASE}/docentes`, { headers: h }).then((r) => (r.ok ? r.json() : [])),
    fetch(`${BASE}/discentes`, { headers: h }).then((r) => (r.ok ? r.json() : [])),
  ]);
  return { docentes, discentes };
}
