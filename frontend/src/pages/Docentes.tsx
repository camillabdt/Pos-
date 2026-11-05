import { useState } from "react";
import { api, type CandidatoOpenAlex, type Docente as TDocente, type ResultadoColeta, type Usuario } from "../api";
import { Campo, Carregando, Dialogo, Erro, Etiqueta, NOME_TIPO, Trilho, dataBR, ir, useCarregar, useEnvio } from "../ui";

const NOME_VINCULO = { permanente: "Permanente", colaborador: "Colaborador(a)", visitante: "Visitante" };

export function Docentes({ eu }: { eu: Usuario }) {
  const lista = useCarregar(api.docentes, []);
  const [novo, setNovo] = useState(false);
  if (!lista.dados) return <Carregando erro={lista.erro} recarregar={lista.recarregar} />;
  return (
    <div className="pagina">
      <header className="cabecalho">
        <h1>Docentes</h1>
        {eu.papel === "coordenacao" && <button className="primario" onClick={() => setNovo(true)}>Cadastrar docente</button>}
      </header>
      <div className="rolagem">
        <table>
          <thead>
            <tr><th>Docente</th><th>Vínculo</th><th className="num">h-index</th><th className="num">h5</th><th className="num">Citações</th><th>Última coleta</th></tr>
          </thead>
          <tbody>
            {lista.dados.map((d) => (
              <tr key={d.id} className={`clicavel ${d.ativo ? "" : "inativo"}`} onClick={() => ir(`/docentes/${d.id}`)}>
                <td><a href={`#/docentes/${d.id}`}><b>{d.nome}</b></a>{!d.ativo && <small className="bloco-small">Inativo(a)</small>}</td>
                <td>{NOME_VINCULO[d.tipo]}</td>
                <td className="num">{d.metricas.h_index}</td>
                <td className="num">{d.metricas.h5_index}</td>
                <td className="num">{d.metricas.citacoes}</td>
                <td>{d.metricas.coletado_em ? dataBR(d.metricas.coletado_em) : <span className="mudo">Nunca</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Dialogo titulo="Cadastrar docente" aberto={novo} fechar={() => setNovo(false)}>
        <FormDocente inicial={null} coord salvo={(d) => { setNovo(false); ir(`/docentes/${d.id}`); }} />
      </Dialogo>
    </div>
  );
}

export function Docente({ id, eu }: { id: string; eu: Usuario }) {
  const d = useCarregar(() => api.docente(id), [id]);
  const prods = useCarregar(() => api.producoes({ docente_id: id }), [id]);
  const [editar, setEditar] = useState(false);
  const [buscar, setBuscar] = useState(false);
  const [coleta, setColeta] = useState<ResultadoColeta | null>(null);
  const { enviando, erro, enviar } = useEnvio();

  if (!d.dados) return <Carregando erro={d.erro} recarregar={d.recarregar} />;
  const x = d.dados;
  const pode = eu.papel === "coordenacao" || eu.docente_id === id;
  const ativos = x.orientandos.filter((o) => o.situacao.vinculo === "ativo");
  const egressos = x.orientandos.filter((o) => o.situacao.vinculo !== "ativo");

  return (
    <div className="pagina">
      <a className="voltar" href="#/docentes">Docentes</a>
      <header className="cabecalho">
        <div>
          <h1>{x.nome}</h1>
          <p className="mudo">
            {NOME_VINCULO[x.tipo]}{x.ativo ? "" : " · inativo(a)"}
            {x.lattes && <> · <a href={x.lattes} target="_blank" rel="noreferrer">Lattes</a></>}
            {x.orcid && <> · <a href={`https://orcid.org/${x.orcid}`} target="_blank" rel="noreferrer">ORCID</a></>}
            {x.openalex_id && <> · <a href={`https://openalex.org/${x.openalex_id}`} target="_blank" rel="noreferrer">OpenAlex</a></>}
          </p>
        </div>
        {pode && <button onClick={() => setEditar(true)}>Editar cadastro</button>}
      </header>

      <section className="bloco metricas">
        <dl className="numeros linha">
          <div><dt>h-index</dt><dd><b>{x.metricas.h_index}</b></dd></div>
          <div><dt>h5-index</dt><dd><b>{x.metricas.h5_index}</b></dd></div>
          <div><dt>i10-index</dt><dd><b>{x.metricas.i10_index}</b></dd></div>
          <div><dt>Citações</dt><dd><b>{x.metricas.citacoes}</b></dd></div>
          <div><dt>Produções no Percurso</dt><dd><b>{x.producao.total}</b><small>{x.producao.com_discentes} com discentes</small></dd></div>
        </dl>
        <div className="coleta">
          <p>
            {x.openalex_id ? <>Perfil no OpenAlex: <a href={`https://openalex.org/${x.openalex_id}`} target="_blank" rel="noreferrer">{x.openalex_id}</a></>
              : <span className="mudo">Nenhum perfil do OpenAlex vinculado.</span>}
            {x.metricas.coletado_em && <span className="mudo"> · produção coletada em {dataBR(x.metricas.coletado_em)}</span>}
          </p>
          {!x.openalex_id && !x.orcid && (
            <p className="mudo">Sem perfil nem ORCID, a coleta escolhe pelo nome o perfil mais citado. Confira antes em “Encontrar no OpenAlex”.</p>
          )}
          {pode && (
            <div className="acoes">
              <button onClick={() => setBuscar(true)}>{x.openalex_id ? "Trocar perfil do OpenAlex" : "Encontrar no OpenAlex"}</button>
              <button disabled={enviando} onClick={() => enviar(async () => {
                setColeta(await api.coletar(id));
                d.recarregar(); prods.recarregar();
              })}>{enviando ? "Coletando…" : "Coletar produção"}</button>
            </div>
          )}
          <Erro msg={erro} />
          {coleta && <ResumoColeta r={coleta} />}
        </div>
      </section>

      <div className="grade-2">
        <section className="bloco">
          <h2>Orientandos ativos ({ativos.length})</h2>
          {ativos.length === 0 ? <p className="mudo">Nenhum.</p> : (
            <ul className="linhas-discentes compacta">
              {ativos.map((o) => (
                <li key={o.id}>
                  <a className="linha-discente" href={`#/discentes/${o.id}`}>
                    <span className="ld-nome"><b>{o.nome}</b><small>{o.nivel === "doutorado" ? "Doutorado" : "Mestrado"}</small></span>
                    <Trilho ingresso={o.data_ingresso} s={o.situacao} />
                    <span className="ld-situacao"><Etiqueta s={o.situacao} /></span>
                  </a>
                </li>
              ))}
            </ul>
          )}
          {egressos.length > 0 && (
            <>
              <h3>Egressos e desligados ({egressos.length})</h3>
              <ul className="simples">
                {egressos.map((o) => (
                  <li key={o.id}><a href={`#/discentes/${o.id}`}>{o.nome}</a> <Etiqueta s={o.situacao} /></li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="bloco">
          <h2>Produção por tipo</h2>
          <ul className="barras">
            {Object.entries(x.producao.por_tipo).map(([t, n]) => (
              <li key={t}>
                <span>{NOME_TIPO[t as keyof typeof NOME_TIPO] ?? t}</span>
                <span className="barra"><span style={{ width: `${(n / Math.max(...Object.values(x.producao.por_tipo))) * 100}%` }} /></span>
                <b>{n}</b>
              </li>
            ))}
          </ul>
          {Object.keys(x.producao.por_qualis).length > 0 && (
            <>
              <h3>Estratos Qualis (bibliográfica)</h3>
              <p>{Object.entries(x.producao.por_qualis).map(([q, n]) => `${q}: ${n}`).join(" · ")}</p>
            </>
          )}
          <h3>Mais recentes</h3>
          <ul className="producoes-compactas">
            {(prods.dados ?? []).slice(0, 8).map((p) => (
              <li key={p.id}><span className="tipo">{NOME_TIPO[p.tipo]} · {p.ano}{p.citacoes != null ? ` · ${p.citacoes} cit.` : ""}</span>{p.titulo}</li>
            ))}
          </ul>
        </section>
      </div>

      <Dialogo titulo="Encontrar no OpenAlex" aberto={buscar} fechar={() => setBuscar(false)} largo>
        <BuscaOpenAlex docente={x} vinculado={() => { d.recarregar(); }}
          coletado={(r) => { setColeta(r); setBuscar(false); d.recarregar(); prods.recarregar(); }} />
      </Dialogo>
      <Dialogo titulo="Editar cadastro" aberto={editar} fechar={() => setEditar(false)}>
        <FormDocente inicial={x} coord={eu.papel === "coordenacao"} salvo={() => { setEditar(false); d.recarregar(); }} />
      </Dialogo>
    </div>
  );
}

function FormDocente({ inicial, coord, salvo }: { inicial: TDocente | null; coord: boolean; salvo: (d: TDocente) => void }) {
  const linhas = useCarregar(api.linhas, []);
  const { enviando, erro, enviar } = useEnvio();
  const [f, setF] = useState({
    nome: inicial?.nome ?? "", email: inicial?.email ?? "", tipo: inicial?.tipo ?? "permanente",
    linha_id: inicial?.linha_id ?? "", lattes: inicial?.lattes ?? "", orcid: inicial?.orcid ?? "",
    openalex_id: inicial?.openalex_id ?? "", ativo: inicial?.ativo ?? true,
  });
  const muda = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      const limpo = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === "" ? null : v]));
      if (!coord) { delete limpo.tipo; delete limpo.ativo; }
      enviar(async () => salvo(inicial ? await api.atualizarDocente(inicial.id, limpo) : await api.criarDocente(limpo)));
    }}>
      <Campo rotulo="Nome"><input required value={f.nome} onChange={muda("nome")} /></Campo>
      <div className="lado">
        <Campo rotulo="E-mail"><input type="email" value={f.email} onChange={muda("email")} /></Campo>
        <Campo rotulo="Vínculo">
          <select disabled={!coord} value={f.tipo} onChange={muda("tipo")}>
            {Object.entries(NOME_VINCULO).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
        </Campo>
      </div>
      <Campo rotulo="Linha de pesquisa">
        <select value={f.linha_id} onChange={muda("linha_id")}>
          <option value="">—</option>
          {(linhas.dados ?? []).map((l) => <option key={l.id} value={l.id}>{l.nome}</option>)}
        </select>
      </Campo>
      <Campo rotulo="Currículo Lattes (link)"><input type="url" value={f.lattes} onChange={muda("lattes")} /></Campo>
      <div className="lado">
        <Campo rotulo="ORCID" dica="Ex.: 0000-0002-1825-0097"><input value={f.orcid} onChange={muda("orcid")} /></Campo>
        <Campo rotulo="Id no OpenAlex" dica="Preenchido na primeira coleta"><input value={f.openalex_id} onChange={muda("openalex_id")} /></Campo>
      </div>
      {coord && (
        <label className="opcao"><input type="checkbox" checked={f.ativo} onChange={(e) => setF({ ...f, ativo: e.target.checked })} /><span>Ativo(a) no programa</span></label>
      )}
      <Erro msg={erro} />
      <footer><button className="primario" disabled={enviando}>{inicial ? "Salvar alterações" : "Cadastrar docente"}</button></footer>
    </form>
  );
}

function ResumoColeta({ r }: { r: ResultadoColeta }) {
  return (
    <p className="sucesso" role="status">
      Coleta concluída ({r.nome_openalex}): {r.obras_lidas} obras lidas, {r.novas} novas,{" "}
      {r.atualizadas} já existentes atualizadas, {r.ignoradas} ignoradas. h-index {r.metricas.h_index}.
    </p>
  );
}

/** Procura o perfil no OpenAlex sem gravar nada; a pessoa escolhe qual vincular. */
function BuscaOpenAlex({ docente, vinculado, coletado }: {
  docente: TDocente; vinculado: () => void; coletado: (r: ResultadoColeta) => void;
}) {
  const saude = useCarregar(api.saude, []);
  const [nome, setNome] = useState(docente.nome);
  const [orcid, setOrcid] = useState(docente.orcid ?? "");
  const [res, setRes] = useState<CandidatoOpenAlex[] | null>(null);
  const [escolhido, setEscolhido] = useState<string | null>(docente.openalex_id ?? null);
  const busca = useEnvio();
  const acao = useEnvio();

  const procurar = () => busca.enviar(async () => setRes(await api.candidatosOpenAlex(nome, orcid || undefined)));
  const usar = (c: CandidatoOpenAlex) => acao.enviar(async () => {
    await api.atualizarDocente(docente.id, { openalex_id: c.openalex_id, ...(c.orcid && !docente.orcid ? { orcid: c.orcid } : {}) });
    setEscolhido(c.openalex_id);
    vinculado();
  });

  return (
    <div className="busca-openalex">
      {saude.dados && !saude.dados.openalex_chave && (
        <p className="aviso">
          O servidor está sem chave do OpenAlex, então só há uma pequena cota diária de teste.
          Para uso real, crie a chave gratuita em openalex.org/settings/api e coloque <code>OPENALEX_API_KEY=…</code> no arquivo <code>backend/.env</code>.
        </p>
      )}
      <form onSubmit={(e) => { e.preventDefault(); procurar(); }}>
        <div className="lado">
          <Campo rotulo="Nome como aparece nos artigos"><input value={nome} onChange={(e) => setNome(e.target.value)} /></Campo>
          <Campo rotulo="ORCID (opcional)" dica="Com ORCID o perfil certo vem primeiro"><input value={orcid} onChange={(e) => setOrcid(e.target.value)} placeholder="0000-0000-0000-0000" /></Campo>
        </div>
        <footer><button className="primario" disabled={busca.enviando}>{busca.enviando ? "Procurando…" : "Procurar"}</button></footer>
      </form>
      <Erro msg={busca.erro} />

      {res && (
        res.length === 0 ? <p className="vazio">Nenhum perfil encontrado. Tente o nome completo, com o sobrenome do meio, ou o ORCID.</p> : (
          <>
            {res.length > 1 && !res[0].achado_por_orcid && (
              <p className="mudo">Há {res.length} perfis parecidos. Confira a instituição e as obras antes de escolher.</p>
            )}
            <ul className="candidatos">
              {res.map((c) => (
                <li key={c.openalex_id} className={escolhido === c.openalex_id ? "escolhido" : ""}>
                  <div>
                    <p><b>{c.nome}</b>{c.achado_por_orcid && <span className="selo">pelo ORCID</span>}{c.nome_identico && <span className="selo">nome idêntico</span>}</p>
                    <p className="mudo">
                      {c.instituicao ?? "Instituição não informada"} · {c.obras} obras · {c.citacoes} citações · ORCID {c.orcid ?? "não vinculado"}
                    </p>
                    <p className="mudo">
                      <a href={`https://openalex.org/${c.openalex_id}`} target="_blank" rel="noreferrer">Ver perfil no OpenAlex</a>
                      {c.ja_vinculado_a && c.ja_vinculado_a !== docente.nome && <> · já vinculado a {c.ja_vinculado_a}</>}
                    </p>
                  </div>
                  {escolhido === c.openalex_id ? <span className="sucesso">Vinculado</span>
                    : <button disabled={acao.enviando} onClick={() => usar(c)}>Usar este perfil</button>}
                </li>
              ))}
            </ul>
          </>
        )
      )}
      <Erro msg={acao.erro} />
      {escolhido && (
        <footer className="rodape-busca">
          <span className="mudo">Perfil {escolhido} vinculado. A coleta grava as produções e recalcula as métricas.</span>
          <button className="primario" disabled={acao.enviando}
            onClick={() => acao.enviar(async () => coletado(await api.coletar(docente.id)))}>
            {acao.enviando ? "Coletando…" : "Coletar produção agora"}
          </button>
        </footer>
      )}
    </div>
  );
}
