import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import type { Situacao, TipoProducao, Resultado, PapelBanca } from "./api";

// ------------------------------------------------------------------ roteamento

export function useRota(): string[] {
  const ler = () => (window.location.hash.replace(/^#\/?/, "").split("?")[0] || "").split("/").filter(Boolean);
  const [partes, setPartes] = useState(ler);
  useEffect(() => {
    const f = () => { setPartes(ler()); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  return partes;
}

export const ir = (caminho: string) => { window.location.hash = caminho; };

/** Lê ?chave=valor de dentro do hash (ex.: #/producoes?tipo=software). */
export const parametro = (nome: string) =>
  new URLSearchParams(window.location.hash.split("?")[1] ?? "").get(nome) ?? undefined;

// ------------------------------------------------------------------ dados

export function useCarregar<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [dados, setDados] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const seq = useRef(0);
  const recarregar = useCallback(() => {
    const n = ++seq.current;
    setCarregando(true);
    fn().then(
      (d) => { if (n === seq.current) { setDados(d); setErro(null); } },
      (e: Error) => { if (n === seq.current) setErro(e.message); },
    ).finally(() => { if (n === seq.current) setCarregando(false); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(recarregar, [recarregar]);
  return { dados, erro, carregando, recarregar, setDados };
}

// ------------------------------------------------------------------ formatos

export const dataBR = (iso?: string | null) => {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
};
export const mesAno = (iso: string) => {
  const meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const [a, m] = iso.split("-");
  return `${meses[Number(m) - 1]} ${a}`;
};
export const hojeISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;

export const NOME_TIPO: Record<TipoProducao, string> = {
  artigo_periodico: "Artigo em periódico",
  artigo_evento: "Artigo em evento",
  livro: "Livro",
  capitulo: "Capítulo de livro",
  software: "Software",
  registro_software: "Registro de software",
  patente: "Patente",
  participacao_evento: "Participação em evento",
  startup: "Startup",
  premio: "Prêmio",
  outro: "Outra produção",
};

/** Campos extras sugeridos por tipo (ficam em `detalhes`). */
export const DETALHES_TIPO: Partial<Record<TipoProducao, [string, string][]>> = {
  software: [["repositorio", "Repositório"], ["licenca", "Licença"]],
  registro_software: [["numero_inpi", "Número no INPI"], ["data_registro", "Data do registro"]],
  patente: [["numero_inpi", "Número no INPI"], ["situacao", "Situação (depositada, concedida)"]],
  participacao_evento: [["evento", "Evento"], ["local", "Local"], ["modalidade", "Modalidade (ouvinte, apresentação)"]],
  startup: [["cnpj", "CNPJ"], ["incubadora", "Incubadora/aceleradora"]],
  premio: [["concedido_por", "Concedido por"]],
};

export const NOME_RESULTADO: Record<Resultado, string> = {
  agendada: "Agendada",
  aprovado: "Aprovado",
  aprovado_com_ressalvas: "Aprovado com ressalvas",
  reprovado: "Reprovado",
};
export const NOME_PAPEL_BANCA: Record<PapelBanca, string> = {
  presidente: "Presidente", interno: "Interno", externo: "Externo", suplente: "Suplente",
};
export const NOME_FASE: Record<Situacao["fase"], string> = {
  entrada: "Ingressante, sem plano",
  cursando: "Cursando",
  qualificado: "Qualificado",
  defesa_agendada: "Defesa agendada",
  titulado: "Titulado",
  desligado: "Desligado",
};

// ------------------------------------------------------------------ situação

export type Tom = "ok" | "alerta" | "atraso" | "fim" | "neutro";

export function tomDe(s: Situacao): Tom {
  if (s.vinculo === "titulado") return "fim";
  if (s.vinculo === "desligado") return "neutro";
  if (s.atrasado) return "atraso";
  if (s.qualificacao_atrasada || s.prazo_proximo) return "alerta";
  return "ok";
}

export function rotuloSituacao(s: Situacao): string {
  if (s.vinculo === "titulado") return s.titulou_no_prazo ? "Titulado no prazo" : "Titulado após o prazo";
  if (s.vinculo === "desligado") return "Desligado";
  if (s.atrasado) return `Prazo vencido há ${plural(-(s.dias_para_prazo ?? 0), "dia", "dias")}`;
  if (s.qualificacao_atrasada) return "Qualificação atrasada";
  if (s.prazo_proximo) return `Prazo em ${plural(s.dias_para_prazo ?? 0, "dia", "dias")}`;
  return "Em dia";
}

export function Etiqueta({ s }: { s: Situacao }) {
  return <span className={`etiqueta tom-${tomDe(s)}`}>{rotuloSituacao(s)}</span>;
}

// ------------------------------------------------------------------ trilho

const dias = (a: string, b: string) => (Date.parse(b) - Date.parse(a)) / 86_400_000;

interface TrilhoProps {
  ingresso: string;
  s: Situacao;
  qualificacao?: string | null;
  defesa?: string | null;
  defesaAgendada?: boolean;
  grande?: boolean;
}

/**
 * A régua do percurso: do ingresso ao prazo de conclusão.
 * Marca o prazo de qualificação, a qualificação feita, hoje e a defesa.
 * O que passa do prazo aparece como trecho de atraso.
 */
export function Trilho({ ingresso, s, qualificacao, defesa, defesaAgendada, grande }: TrilhoProps) {
  const hoje = hojeISO();
  const fimReal = s.vinculo === "titulado" && defesa ? defesa : hoje;
  const limite = [s.prazo_conclusao, fimReal, defesa ?? s.prazo_conclusao].reduce((a, b) => (a > b ? a : b));
  const total = Math.max(dias(ingresso, limite), 1);
  const pos = (d: string) => `${Math.min(100, Math.max(0, (dias(ingresso, d) / total) * 100))}%`;
  const tom = tomDe(s);
  const andado = s.vinculo === "desligado" ? 0 : dias(ingresso, fimReal);
  const noPrazo = Math.min(andado, dias(ingresso, s.prazo_conclusao));
  const pct = (n: number) => `${(Math.max(0, n) / total) * 100}%`;
  const rotulo = `Ingresso ${dataBR(ingresso)}, prazo ${dataBR(s.prazo_conclusao)}. ${rotuloSituacao(s)}.`;

  return (
    <div className={`trilho ${grande ? "trilho-grande" : ""} tom-${tom}`} role="img" aria-label={rotulo}>
      <div className="trilho-base" />
      <div className="trilho-feito" style={{ width: pct(noPrazo) }} />
      {andado > dias(ingresso, s.prazo_conclusao) && (
        <div className="trilho-excesso" style={{ left: pos(s.prazo_conclusao), width: pct(andado - dias(ingresso, s.prazo_conclusao)) }} />
      )}
      <span className="marco marco-prazo-q" style={{ left: pos(s.prazo_qualificacao) }} title={`Prazo para qualificar: ${dataBR(s.prazo_qualificacao)}`} />
      <span className="marco marco-prazo" style={{ left: pos(s.prazo_conclusao) }} title={`Prazo de conclusão: ${dataBR(s.prazo_conclusao)}`} />
      {qualificacao && <span className="ponto ponto-q" style={{ left: pos(qualificacao) }} title={`Qualificação: ${dataBR(qualificacao)}`} />}
      {defesa && <span className={`ponto ponto-d ${defesaAgendada ? "agendada" : ""}`} style={{ left: pos(defesa) }} title={`Defesa: ${dataBR(defesa)}`} />}
      {s.vinculo === "ativo" && <span className="agulha" style={{ left: pos(hoje) }} title="Hoje" />}
      {grande && (
        <div className="trilho-legendas" aria-hidden>
          <span style={{ left: 0 }}>Ingresso<br /><b>{dataBR(ingresso)}</b></span>
          <span style={{ left: pos(s.prazo_qualificacao) }}>Qualificar até<br /><b>{dataBR(s.prazo_qualificacao)}</b></span>
          <span style={{ left: pos(s.prazo_conclusao) }}>Concluir até<br /><b>{dataBR(s.prazo_conclusao)}</b></span>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ formulários

export function Dialogo({ titulo, aberto, fechar, children, largo }: {
  titulo: string; aberto: boolean; fechar: () => void; children: ReactNode; largo?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (aberto && !d.open) d.showModal();
    if (!aberto && d.open) d.close();
  }, [aberto]);
  return (
    <dialog ref={ref} className={largo ? "largo" : ""} onClose={fechar} onCancel={fechar}>
      <header><h2>{titulo}</h2><button className="fechar" onClick={fechar} aria-label="Fechar">×</button></header>
      {aberto && children}
    </dialog>
  );
}

export function Campo({ rotulo, children, dica }: { rotulo: string; children: ReactNode; dica?: string }) {
  return (
    <label className="campo">
      <span>{rotulo}</span>
      {children}
      {dica && <small>{dica}</small>}
    </label>
  );
}

/** Envolve um envio: desabilita o botão, mostra o erro do servidor. */
export function useEnvio() {
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const enviar = async (fn: () => Promise<unknown>, depois?: () => void) => {
    setEnviando(true);
    setErro(null);
    try {
      await fn();
      depois?.();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  };
  return { enviando, erro, enviar, setErro };
}

export function Erro({ msg }: { msg: string | null }) {
  return msg ? <p className="erro" role="alert">{msg}</p> : null;
}

export function Carregando({ erro, recarregar }: { erro: string | null; recarregar?: () => void }) {
  if (erro) {
    return (
      <div className="vazio">
        <p className="erro">{erro}</p>
        {recarregar && <button onClick={recarregar}>Tentar de novo</button>}
      </div>
    );
  }
  return <p className="carregando">Carregando…</p>;
}
