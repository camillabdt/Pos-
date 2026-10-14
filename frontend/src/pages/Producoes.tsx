import { useState } from "react";
import { api, type Autor, type Producao, type ProducaoCriar, type TipoProducao, type Usuario } from "../api";
import { Campo, Carregando, DETALHES_TIPO, Dialogo, Erro, NOME_TIPO, parametro, useCarregar, useEnvio } from "../ui";

export default function Producoes({ eu }: { eu: Usuario }) {
  const anoAtual = new Date().getFullYear();
  const [tipo, setTipo] = useState(parametro("tipo") ?? "");
  const [anoDe, setAnoDe] = useState(anoAtual - 4);
  const [comDiscentes, setComDiscentes] = useState(false);
  const [busca, setBusca] = useState("");
  const [editando, setEditando] = useState<Producao | null | "nova">(null);
  const lista = useCarregar(
    () => api.producoes({ tipo: tipo || undefined, ano_de: anoDe || undefined, so_com_discentes: comDiscentes, busca: busca || undefined }),
    [tipo, anoDe, comDiscentes, busca],
  );
  const podeEditar = (p: Producao) =>
    eu.papel === "coordenacao" || p.autores.some((a) => (a.docente_id && a.docente_id === eu.docente_id) || (a.discente_id && a.discente_id === eu.discente_id));

  return (
    <div className="pagina">
      <header className="cabecalho">
        <h1>Produção</h1>
        <button className="primario" onClick={() => setEditando("nova")}>Registrar produção</button>
      </header>
      <div className="filtros">
        <Campo rotulo="Buscar no título"><input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} /></Campo>
        <Campo rotulo="Tipo">
          <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="">Todos os tipos</option>
            {Object.entries(NOME_TIPO).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
        </Campo>
        <Campo rotulo="Desde">
          <select value={anoDe} onChange={(e) => setAnoDe(Number(e.target.value))}>
            {[0, 1, 2, 4, 9].map((n) => <option key={n} value={anoAtual - n}>{anoAtual - n}</option>)}
            <option value={0}>Sempre</option>
          </select>
        </Campo>
        <label className="opcao filtro-check">
          <input type="checkbox" checked={comDiscentes} onChange={(e) => setComDiscentes(e.target.checked)} />
          <span>Só com discentes entre os autores</span>
        </label>
      </div>

      {lista.dados === null ? <Carregando erro={lista.erro} recarregar={lista.recarregar} /> : lista.dados.length === 0 ? (
        <p className="vazio">Nenhuma produção com esses filtros.</p>
      ) : (
        <>
          <p className="mudo contagem">{lista.dados.length} {lista.dados.length === 1 ? "produção" : "produções"}</p>
          <ul className="producoes">
            {lista.dados.map((p) => (
              <li key={p.id}>
                <div className="prod-meta">
                  <span>{NOME_TIPO[p.tipo]}</span><span>{p.ano}</span>
                  {p.veiculo?.qualis && <span className="qualis">{p.veiculo.qualis}</span>}
                  {p.citacoes != null && <span>{p.citacoes} citações</span>}
                  {p.origem === "openalex" && <span title="Coletada automaticamente">OpenAlex</span>}
                </div>
                <p className="prod-titulo">
                  {p.doi ? <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer">{p.titulo}</a>
                    : p.url ? <a href={p.url} target="_blank" rel="noreferrer">{p.titulo}</a> : p.titulo}
                </p>
                <p className="prod-autores">
                  {p.autores.map((a, i) => (
                    <span key={i}>
                      {i > 0 && ", "}
                      {a.discente_id ? <a href={`#/discentes/${a.discente_id}`} className="autor-discente">{a.nome}</a>
                        : a.docente_id ? <a href={`#/docentes/${a.docente_id}`} className="autor-docente">{a.nome}</a> : a.nome}
                    </span>
                  ))}
                  {p.veiculo?.nome && <span className="mudo"> · {p.veiculo.nome}</span>}
                </p>
                {Object.keys(p.detalhes).length > 0 && (
                  <p className="mudo">{Object.entries(p.detalhes).map(([k, v]) => `${rotuloDetalhe(p.tipo, k)}: ${v}`).join(" · ")}</p>
                )}
                {podeEditar(p) && <button className="link" onClick={() => setEditando(p)}>Editar</button>}
              </li>
            ))}
          </ul>
          <p className="legenda"><span className="autor-discente">Discentes</span> e <span className="autor-docente">docentes</span> do programa aparecem destacados.</p>
        </>
      )}

      <Dialogo titulo={editando === "nova" ? "Registrar produção" : "Editar produção"} aberto={editando !== null} fechar={() => setEditando(null)} largo>
        <FormProducao
          inicial={editando === "nova" ? null : editando}
          autoresIniciais={eu.papel === "discente" && eu.discente_id ? [{ nome: "", discente_id: eu.discente_id }]
            : eu.docente_id ? [{ nome: "", docente_id: eu.docente_id }] : []}
          salvo={() => { setEditando(null); lista.recarregar(); }}
        />
      </Dialogo>
    </div>
  );
}

function rotuloDetalhe(tipo: TipoProducao, chave: string) {
  return DETALHES_TIPO[tipo]?.find(([k]) => k === chave)?.[1] ?? chave;
}

export function FormProducao({ inicial, autoresIniciais, salvo }: {
  inicial: Producao | null; autoresIniciais: Autor[]; salvo: () => void;
}) {
  const { enviando, erro, enviar } = useEnvio();
  // Discentes não têm acesso às listas completas; nesse caso os autores entram por nome.
  const docentes = useCarregar(() => api.docentes().catch(() => []), []);
  const discentes = useCarregar(() => api.discentes().catch(() => []), []);
  const pessoas: { chave: string; nome: string; docente_id?: string; discente_id?: string }[] = [
    ...(docentes.dados ?? []).map((d) => ({ chave: `doc:${d.id}`, nome: d.nome, docente_id: d.id })),
    ...(discentes.dados ?? []).map((d) => ({ chave: `dis:${d.id}`, nome: d.nome, discente_id: d.id })),
  ];
  const nomeDe = (a: Autor) => a.nome || pessoas.find((p) => p.chave === chaveDe(a))?.nome || "";
  const [p, setP] = useState<ProducaoCriar>(inicial ? { ...inicial } : {
    tipo: "artigo_periodico", titulo: "", ano: new Date().getFullYear(), autores: autoresIniciais,
    doi: "", url: "", veiculo: { nome: "", issn: [], qualis: "" }, detalhes: {}, data: null,
  });
  const autor = (i: number, a: Autor) => setP({ ...p, autores: p.autores.map((x, j) => (j === i ? a : x)) });
  const bibliografica = ["artigo_periodico", "artigo_evento", "livro", "capitulo"].includes(p.tipo);
  const extras = DETALHES_TIPO[p.tipo] ?? [];

  const apagar = () => inicial && enviar(() => api.apagarProducao(inicial.id), salvo);

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      const corpo: ProducaoCriar = {
        ...p,
        autores: p.autores.map((a) => ({ ...a, nome: nomeDe(a) })).filter((a) => a.nome || a.docente_id || a.discente_id),
        doi: p.doi || null, url: p.url || null,
        veiculo: bibliografica && (p.veiculo?.nome || p.veiculo?.issn.length)
          ? { nome: p.veiculo?.nome || null, issn: p.veiculo?.issn ?? [], qualis: p.veiculo?.qualis || null } : null,
        detalhes: Object.fromEntries(Object.entries(p.detalhes).filter(([, v]) => v)),
      };
      enviar(() => (inicial ? api.atualizarProducao(inicial.id, corpo) : api.criarProducao(corpo)), salvo);
    }}>
      <div className="lado">
        <Campo rotulo="Tipo">
          <select value={p.tipo} onChange={(e) => setP({ ...p, tipo: e.target.value as TipoProducao })}>
            {Object.entries(NOME_TIPO).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
        </Campo>
        <Campo rotulo="Ano"><input required type="number" min={1950} max={2100} value={p.ano} onChange={(e) => setP({ ...p, ano: Number(e.target.value) })} /></Campo>
      </div>
      <Campo rotulo={p.tipo === "startup" ? "Nome da empresa" : "Título"}>
        <input required value={p.titulo} onChange={(e) => setP({ ...p, titulo: e.target.value })} />
      </Campo>

      {bibliografica && (
        <div className="lado">
          <Campo rotulo="Veículo (periódico, evento, editora)">
            <input value={p.veiculo?.nome ?? ""} onChange={(e) => setP({ ...p, veiculo: { issn: [], ...p.veiculo, nome: e.target.value } })} />
          </Campo>
          <Campo rotulo="ISSN" dica="Preenche o Qualis pelo cadastro de veículos">
            <input value={p.veiculo?.issn.join(", ") ?? ""} onChange={(e) => setP({ ...p, veiculo: { ...p.veiculo, issn: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) } })} />
          </Campo>
          <Campo rotulo="Qualis"><input value={p.veiculo?.qualis ?? ""} onChange={(e) => setP({ ...p, veiculo: { issn: [], ...p.veiculo, qualis: e.target.value } })} /></Campo>
        </div>
      )}
      <div className="lado">
        {bibliografica && <Campo rotulo="DOI"><input value={p.doi ?? ""} onChange={(e) => setP({ ...p, doi: e.target.value })} /></Campo>}
        <Campo rotulo="Link"><input type="url" value={p.url ?? ""} onChange={(e) => setP({ ...p, url: e.target.value })} /></Campo>
      </div>
      {extras.length > 0 && (
        <div className="lado">
          {extras.map(([k, r]) => (
            <Campo key={k} rotulo={r}>
              <input value={p.detalhes[k] ?? ""} onChange={(e) => setP({ ...p, detalhes: { ...p.detalhes, [k]: e.target.value } })} />
            </Campo>
          ))}
        </div>
      )}

      <fieldset>
        <legend>Autores, na ordem</legend>
        {p.autores.map((a, i) => (
          <div className="membro" key={i}>
            <select aria-label="Pessoa do programa" value={chaveDe(a)} onChange={(e) => {
              const pe = pessoas.find((x) => x.chave === e.target.value);
              autor(i, pe ? { nome: pe.nome, docente_id: pe.docente_id ?? null, discente_id: pe.discente_id ?? null } : { nome: a.nome });
            }}>
              <option value="">Autor(a) externo(a)</option>
              {pessoas.map((x) => <option key={x.chave} value={x.chave}>{x.nome}{x.discente_id ? " (discente)" : ""}</option>)}
              {chaveDe(a) && !pessoas.some((x) => x.chave === chaveDe(a)) && <option value={chaveDe(a)}>Você</option>}
            </select>
            {!chaveDe(a) && <input aria-label="Nome" placeholder="Nome do autor" required value={a.nome} onChange={(e) => autor(i, { nome: e.target.value })} />}
            <button type="button" className="link perigo" onClick={() => setP({ ...p, autores: p.autores.filter((_, j) => j !== i) })}>Remover</button>
          </div>
        ))}
        <button type="button" onClick={() => setP({ ...p, autores: [...p.autores, { nome: "" }] })}>Adicionar autor(a)</button>
      </fieldset>
      <Erro msg={erro} />
      <footer>
        {inicial && <button type="button" className="link perigo" onClick={apagar}>Apagar produção</button>}
        <button className="primario" disabled={enviando}>{inicial ? "Salvar alterações" : "Registrar produção"}</button>
      </footer>
    </form>
  );
}

function chaveDe(a: Autor) {
  return a.docente_id ? `doc:${a.docente_id}` : a.discente_id ? `dis:${a.discente_id}` : "";
}
