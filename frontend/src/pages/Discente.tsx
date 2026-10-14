import { useState } from "react";
import {
  api, type Avaliacao, type Discente as TDiscente, type Disciplina, type DisciplinaCursada,
  type Docente, type MembroBanca, type PapelBanca, type Resultado, type Usuario,
} from "../api";
import {
  Campo, Carregando, Dialogo, Erro, Etiqueta, NOME_FASE, NOME_PAPEL_BANCA, NOME_RESULTADO, NOME_TIPO,
  Trilho, dataBR, hojeISO, mesAno, plural, useCarregar, useEnvio,
} from "../ui";
import { FormProducao } from "./Producoes";

type Modal = null | "plano" | "disciplina" | "qualificacao" | "defesa" | "prorrogacao" | "desligamento" | "tema" | "producao";

export default function Discente({ id, eu }: { id: string; eu: Usuario }) {
  const d = useCarregar(() => api.discente(id), [id]);
  const catalogo = useCarregar(api.disciplinas, []);
  const docentes = useCarregar(api.docentes, []);
  const producoes = useCarregar(() => api.producoes({ discente_id: id }), [id]);
  const [modal, setModal] = useState<Modal>(null);
  const fechar = () => setModal(null);
  const atualizado = (novo: TDiscente) => { d.setDados(novo); fechar(); };

  if (!d.dados) return <Carregando erro={d.erro} recarregar={d.recarregar} />;
  const x = d.dados;
  const s = x.situacao;
  const coord = eu.papel === "coordenacao";
  const orienta = !!eu.docente_id && (x.orientador_id === eu.docente_id || x.coorientador_ids.includes(eu.docente_id));
  const edita = coord || orienta;
  const cat = Object.fromEntries((catalogo.dados ?? []).map((c) => [c.id, c]));
  const trabalho = x.nivel === "doutorado" ? "tese" : "dissertação";

  return (
    <div className="pagina">
      {eu.papel !== "discente" && <a className="voltar" href="#/discentes">Discentes</a>}
      <header className="cabecalho-discente">
        <div>
          <h1>{x.nome}</h1>
          <p className="mudo">
            {x.nivel === "doutorado" ? "Doutorado" : "Mestrado"} · matrícula {x.matricula} · {NOME_FASE[s.fase]}
            {x.email && <> · <a href={`mailto:${x.email}`}>{x.email}</a></>}
          </p>
        </div>
        <Etiqueta s={s} />
      </header>

      <section className="bloco trilho-bloco">
        <Trilho grande ingresso={x.data_ingresso} s={s} qualificacao={x.qualificacao?.data}
          defesa={x.defesa?.data} defesaAgendada={x.defesa?.resultado === "agendada"} />
        {s.pendencias.length > 0 && (
          <ul className="pendencias">{s.pendencias.map((p) => <li key={p}>{p}</li>)}</ul>
        )}
      </section>

      <div className="percurso">
        {/* ------------------------------------------------------- ENTRADA */}
        <section className="etapa">
          <h2>Entrada</h2>
          <dl className="fatos">
            <div><dt>Ingresso</dt><dd>{dataBR(x.data_ingresso)}</dd></div>
            <div><dt>Orientação</dt><dd>{x.orientador_nome ?? "—"}</dd></div>
            {x.coorientadores_nomes.length > 0 && <div><dt>Coorientação</dt><dd>{x.coorientadores_nomes.join(", ")}</dd></div>}
          </dl>

          <h3>Plano de trabalho</h3>
          {x.plano ? (
            <>
              <p><b>{x.plano.titulo_projeto}</b></p>
              {x.plano.resumo && <p className="resumo">{x.plano.resumo}</p>}
              <p className="mudo">{x.plano.aprovado_em ? `Aprovado em ${dataBR(x.plano.aprovado_em)}` : "Aprovação não registrada"}</p>
            </>
          ) : <p className="mudo">Nenhum plano registrado.</p>}
          {edita && <button onClick={() => setModal("plano")}>{x.plano ? "Editar plano" : "Registrar plano"}</button>}
        </section>

        {/* ------------------------------------------------------- MEIO */}
        <section className="etapa">
          <h2>Meio</h2>

          <h3>Disciplinas</h3>
          <p className="mudo">
            {s.disciplinas.cumpridas_do_plano} de {plural(s.disciplinas.planejadas, "planejada", "planejadas")} cumpridas ·{" "}
            {s.disciplinas.creditos_concluidos} de {s.disciplinas.creditos_minimos} créditos
          </p>
          <TabelaDisciplinas d={x} cat={cat} edita={edita} mudou={(n) => d.setDados(n)} />
          {edita && <button onClick={() => setModal("disciplina")}>Registrar disciplina cursada</button>}

          <h3>Qualificação</h3>
          <CartaoAvaliacao a={x.qualificacao} vazio={`Ainda não qualificou. Prazo: ${dataBR(s.prazo_qualificacao)}.`} />
          {edita && <button onClick={() => setModal("qualificacao")}>{x.qualificacao ? "Editar qualificação" : "Registrar qualificação"}</button>}

          <h3>Prorrogações</h3>
          {x.prorrogacoes.length === 0 ? <p className="mudo">Nenhuma.</p> : (
            <ul className="simples">
              {x.prorrogacoes.map((p, i) => (
                <li key={i}>
                  <b>{plural(p.meses, "mês", "meses")}</b>, concedida em {dataBR(p.concedida_em)} — {p.motivo}
                  {coord && <button className="link perigo" onClick={async () => d.setDados(await api.removerProrrogacao(x.id, i))}>Remover</button>}
                </li>
              ))}
            </ul>
          )}
          {coord && s.vinculo === "ativo" && <button onClick={() => setModal("prorrogacao")}>Conceder prorrogação</button>}

          <h3>Produções</h3>
          {producoes.dados === null ? <Carregando erro={producoes.erro} /> : producoes.dados.length === 0 ? (
            <p className="mudo">Nenhuma produção registrada.</p>
          ) : (
            <ul className="producoes-compactas">
              {producoes.dados.map((p) => (
                <li key={p.id}>
                  <span className="tipo">{NOME_TIPO[p.tipo]} · {p.ano}{p.veiculo?.qualis ? ` · ${p.veiculo.qualis}` : ""}</span>
                  {p.titulo}
                </li>
              ))}
            </ul>
          )}
          <button onClick={() => setModal("producao")}>Registrar produção</button>
        </section>

        {/* ------------------------------------------------------- FIM */}
        <section className="etapa">
          <h2>Fim</h2>
          <h3>Tema da {trabalho}</h3>
          <p>{x.tema ? <b>{x.tema}</b> : <span className="mudo">Não registrado.</span>}</p>
          {edita && <button onClick={() => setModal("tema")}>{x.tema ? "Alterar tema" : "Registrar tema"}</button>}

          <h3>Defesa</h3>
          <CartaoAvaliacao a={x.defesa} vazio={`Sem defesa registrada. Prazo de conclusão: ${dataBR(s.prazo_conclusao)}.`} />
          {edita && s.vinculo !== "desligado" && (
            <button onClick={() => setModal("defesa")}>{x.defesa ? "Editar defesa" : "Agendar ou registrar defesa"}</button>
          )}

          <h3>Tempo no programa</h3>
          {s.tempo_titulacao_meses !== null ? (
            <p><b className="grande">{s.tempo_titulacao_meses.toLocaleString("pt-BR")}</b> meses até a titulação
              <br /><span className="mudo">{s.titulou_no_prazo ? "Dentro do prazo" : "Após o prazo"} de {dataBR(s.prazo_conclusao)}{s.meses_prorrogados ? `, já com ${plural(s.meses_prorrogados, "mês", "meses")} de prorrogação` : ""}.</span></p>
          ) : (
            <p><b className="grande">{s.meses_no_programa.toLocaleString("pt-BR")}</b> meses {s.vinculo === "desligado" ? "até o desligamento" : "até hoje"}</p>
          )}

          {x.desligamento && (
            <div className="aviso">
              Desligado(a) em {dataBR(x.desligamento.data)}: {x.desligamento.motivo}
              {coord && <button className="link" onClick={async () => d.setDados(await api.religar(x.id))}>Desfazer desligamento</button>}
            </div>
          )}
          {coord && s.vinculo === "ativo" && <button className="link perigo" onClick={() => setModal("desligamento")}>Registrar desligamento</button>}
        </section>
      </div>

      <Dialogo titulo="Plano de trabalho" aberto={modal === "plano"} fechar={fechar} largo>
        <FormPlano d={x} catalogo={catalogo.dados ?? []} salvo={atualizado} />
      </Dialogo>
      <Dialogo titulo="Registrar disciplina cursada" aberto={modal === "disciplina"} fechar={fechar}>
        <FormDisciplina d={x} catalogo={catalogo.dados ?? []} salvo={atualizado} />
      </Dialogo>
      <Dialogo titulo="Qualificação" aberto={modal === "qualificacao"} fechar={fechar} largo>
        <FormAvaliacao inicial={x.qualificacao} docentes={docentes.dados ?? []} orientador={x.orientador_id}
          tituloPadrao={x.tema ?? x.plano?.titulo_projeto ?? ""} salvar={(a) => api.qualificacao(x.id, a)} salvo={atualizado} acao="Salvar qualificação" />
      </Dialogo>
      <Dialogo titulo="Defesa" aberto={modal === "defesa"} fechar={fechar} largo>
        <FormAvaliacao inicial={x.defesa ?? (x.qualificacao ? { ...x.qualificacao, data: "", resultado: "agendada" } : null)}
          docentes={docentes.dados ?? []} orientador={x.orientador_id} tituloPadrao={x.tema ?? ""}
          salvar={(a) => api.defesa(x.id, a)} salvo={atualizado} acao="Salvar defesa" />
      </Dialogo>
      <Dialogo titulo="Conceder prorrogação" aberto={modal === "prorrogacao"} fechar={fechar}>
        <FormProrrogacao d={x} salvo={atualizado} />
      </Dialogo>
      <Dialogo titulo="Registrar desligamento" aberto={modal === "desligamento"} fechar={fechar}>
        <FormDesligamento d={x} salvo={atualizado} />
      </Dialogo>
      <Dialogo titulo={`Tema da ${trabalho}`} aberto={modal === "tema"} fechar={fechar}>
        <FormTema d={x} salvo={atualizado} />
      </Dialogo>
      <Dialogo titulo="Registrar produção" aberto={modal === "producao"} fechar={fechar} largo>
        <FormProducao
          inicial={null}
          autoresIniciais={[{ nome: x.nome, discente_id: x.id }, ...(x.orientador_nome ? [{ nome: x.orientador_nome, docente_id: x.orientador_id }] : [])]}
          salvo={() => { fechar(); producoes.recarregar(); }}
        />
      </Dialogo>
    </div>
  );
}

// ------------------------------------------------------------------ partes

function TabelaDisciplinas({ d, cat, edita, mudou }: {
  d: TDiscente; cat: Record<string, Disciplina>; edita: boolean; mudou: (d: TDiscente) => void;
}) {
  const planejadas = d.plano?.disciplinas_planejadas ?? [];
  const cursadas = d.disciplinas;
  const extras = cursadas.filter((c) => !planejadas.includes(c.disciplina_id));
  const linhas: { id: string; registro?: DisciplinaCursada; noPlano: boolean }[] = [
    ...planejadas.map((id) => ({
      id,
      registro: [...cursadas].reverse().find((c) => c.disciplina_id === id),
      noPlano: true,
    })),
    ...extras.map((c) => ({ id: c.disciplina_id, registro: c, noPlano: false })),
  ];
  if (linhas.length === 0) return <p className="mudo">Nenhuma disciplina planejada ou cursada.</p>;
  const rotulo = (r?: DisciplinaCursada) =>
    !r ? "Por cursar" : r.situacao === "aprovado" ? `Aprovado${r.conceito ? ` (${r.conceito})` : ""}`
      : r.situacao === "aproveitada" ? "Aproveitada" : r.situacao === "cursando" ? "Cursando" : "Reprovado";
  return (
    <table className="disciplinas">
      <tbody>
        {linhas.map(({ id, registro, noPlano }) => (
          <tr key={`${id}-${registro?.semestre ?? "p"}`} className={!registro ? "pendente" : ""}>
            <td>
              {cat[id]?.nome ?? id}
              {!noPlano && <small className="bloco-small">Fora do plano</small>}
            </td>
            <td className="mudo">{registro?.semestre ?? ""}</td>
            <td className={`sit sit-${registro?.situacao ?? "pendente"}`}>{rotulo(registro)}</td>
            {edita && (
              <td>{registro && (
                <button className="x" aria-label={`Remover registro de ${cat[id]?.nome ?? id} em ${registro.semestre}`}
                  title="Remover registro"
                  onClick={async () => mudou(await api.removerDisciplina(d.id, id, registro.semestre))}>×</button>
              )}</td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CartaoAvaliacao({ a, vazio }: { a: Avaliacao | null; vazio: string }) {
  if (!a) return <p className="mudo">{vazio}</p>;
  return (
    <div className={`cartao-aval res-${a.resultado}`}>
      <p><b>{a.titulo}</b></p>
      <p>{dataBR(a.data)} · {NOME_RESULTADO[a.resultado]}</p>
      {a.banca.length > 0 && (
        <ul className="banca">
          {a.banca.map((m, i) => (
            <li key={i}>{m.nome}<span className="mudo"> — {NOME_PAPEL_BANCA[m.papel]}{m.instituicao ? `, ${m.instituicao}` : ""}</span></li>
          ))}
        </ul>
      )}
      {a.observacao && <p className="mudo">{a.observacao}</p>}
    </div>
  );
}

// ------------------------------------------------------------------ formulários

function FormPlano({ d, catalogo, salvo }: { d: TDiscente; catalogo: Disciplina[]; salvo: (d: TDiscente) => void }) {
  const { enviando, erro, enviar } = useEnvio();
  const [titulo, setTitulo] = useState(d.plano?.titulo_projeto ?? "");
  const [resumo, setResumo] = useState(d.plano?.resumo ?? "");
  const [aprovado, setAprovado] = useState(d.plano?.aprovado_em ?? "");
  const [sel, setSel] = useState<string[]>(d.plano?.disciplinas_planejadas ?? catalogo.filter((c) => c.obrigatoria).map((c) => c.id));
  const alterna = (id: string) => setSel(sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id]);
  const creditos = catalogo.filter((c) => sel.includes(c.id)).reduce((a, c) => a + c.creditos, 0);
  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      enviar(async () => salvo(await api.plano(d.id, {
        titulo_projeto: titulo, resumo: resumo || null, disciplinas_planejadas: sel, aprovado_em: aprovado || null,
      })));
    }}>
      <Campo rotulo="Título do projeto"><input required value={titulo} onChange={(e) => setTitulo(e.target.value)} /></Campo>
      <Campo rotulo="Resumo"><textarea rows={3} value={resumo} onChange={(e) => setResumo(e.target.value)} /></Campo>
      <Campo rotulo="Aprovado em"><input type="date" value={aprovado} onChange={(e) => setAprovado(e.target.value)} /></Campo>
      <fieldset>
        <legend>Disciplinas planejadas ({creditos} créditos)</legend>
        {catalogo.length === 0 && <p className="mudo">Cadastre disciplinas em Cadastros antes.</p>}
        <div className="opcoes">
          {catalogo.map((c) => (
            <label key={c.id} className="opcao">
              <input type="checkbox" checked={sel.includes(c.id)} onChange={() => alterna(c.id)} />
              <span>{c.codigo} {c.nome} <small>{c.creditos} cr{c.obrigatoria ? " · obrigatória" : ""}</small></span>
            </label>
          ))}
        </div>
      </fieldset>
      <Erro msg={erro} />
      <footer><button className="primario" disabled={enviando}>Salvar plano</button></footer>
    </form>
  );
}

function semestreAtual() {
  const d = new Date();
  return `${d.getFullYear()}/${d.getMonth() < 6 ? 1 : 2}`;
}

function FormDisciplina({ d, catalogo, salvo }: { d: TDiscente; catalogo: Disciplina[]; salvo: (d: TDiscente) => void }) {
  const { enviando, erro, enviar } = useEnvio();
  const pendentes = d.situacao.disciplinas.pendentes_do_plano;
  const [f, setF] = useState<DisciplinaCursada>({
    disciplina_id: pendentes[0] ?? "", semestre: semestreAtual(), situacao: "aprovado", conceito: "A",
  });
  const ordenado = [...catalogo].sort((a, b) => Number(!pendentes.includes(a.id)) - Number(!pendentes.includes(b.id)));
  return (
    <form onSubmit={(e) => { e.preventDefault(); enviar(async () => salvo(await api.disciplina(d.id, { ...f, conceito: f.conceito || null }))); }}>
      <Campo rotulo="Disciplina">
        <select required value={f.disciplina_id} onChange={(e) => setF({ ...f, disciplina_id: e.target.value })}>
          <option value="">Escolha…</option>
          {ordenado.map((c) => <option key={c.id} value={c.id}>{pendentes.includes(c.id) ? "● " : ""}{c.codigo} {c.nome}</option>)}
        </select>
      </Campo>
      <div className="lado">
        <Campo rotulo="Semestre" dica="Ex.: 2026/1">
          <input required pattern="\d{4}/[12]" value={f.semestre} onChange={(e) => setF({ ...f, semestre: e.target.value })} />
        </Campo>
        <Campo rotulo="Situação">
          <select value={f.situacao} onChange={(e) => setF({ ...f, situacao: e.target.value as DisciplinaCursada["situacao"] })}>
            <option value="cursando">Cursando</option><option value="aprovado">Aprovado</option>
            <option value="reprovado">Reprovado</option><option value="aproveitada">Aproveitada</option>
          </select>
        </Campo>
        <Campo rotulo="Conceito"><input value={f.conceito ?? ""} onChange={(e) => setF({ ...f, conceito: e.target.value })} /></Campo>
      </div>
      <p className="mudo">● disciplinas do plano ainda não cumpridas. Registrar de novo no mesmo semestre atualiza o registro.</p>
      <Erro msg={erro} />
      <footer><button className="primario" disabled={enviando}>Registrar disciplina</button></footer>
    </form>
  );
}

function FormAvaliacao({ inicial, docentes, orientador, tituloPadrao, salvar, salvo, acao }: {
  inicial: Avaliacao | null; docentes: Docente[]; orientador: string; tituloPadrao: string; acao: string;
  salvar: (a: Avaliacao) => Promise<TDiscente>; salvo: (d: TDiscente) => void;
}) {
  const { enviando, erro, enviar } = useEnvio();
  const orient = docentes.find((x) => x.id === orientador);
  const [a, setA] = useState<Avaliacao>(inicial ?? {
    data: "", titulo: tituloPadrao, resultado: "agendada", observacao: "",
    banca: orient ? [{ nome: orient.nome, papel: "presidente", docente_id: orient.id, instituicao: null }] : [],
  });
  const membro = (i: number, m: Partial<MembroBanca>) => setA({ ...a, banca: a.banca.map((x, j) => (j === i ? { ...x, ...m } : x)) });
  return (
    <form onSubmit={(e) => { e.preventDefault(); enviar(async () => salvo(await salvar({ ...a, observacao: a.observacao || null }))); }}>
      <Campo rotulo="Título do trabalho"><input required value={a.titulo} onChange={(e) => setA({ ...a, titulo: e.target.value })} /></Campo>
      <div className="lado">
        <Campo rotulo="Data"><input required type="date" value={a.data} onChange={(e) => setA({ ...a, data: e.target.value })} /></Campo>
        <Campo rotulo="Resultado">
          <select value={a.resultado} onChange={(e) => setA({ ...a, resultado: e.target.value as Resultado })}>
            {Object.entries(NOME_RESULTADO).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
        </Campo>
      </div>
      <fieldset>
        <legend>Banca</legend>
        {a.banca.map((m, i) => (
          <div className="membro" key={i}>
            <select aria-label="Docente do programa" value={m.docente_id ?? ""} onChange={(e) => {
              const doc = docentes.find((x) => x.id === e.target.value);
              membro(i, doc ? { docente_id: doc.id, nome: doc.nome, instituicao: null } : { docente_id: null });
            }}>
              <option value="">Membro externo ao programa</option>
              {docentes.map((x) => <option key={x.id} value={x.id}>{x.nome}</option>)}
            </select>
            {!m.docente_id && <>
              <input aria-label="Nome" placeholder="Nome" required value={m.nome} onChange={(e) => membro(i, { nome: e.target.value })} />
              <input aria-label="Instituição" placeholder="Instituição" value={m.instituicao ?? ""} onChange={(e) => membro(i, { instituicao: e.target.value })} />
            </>}
            <select aria-label="Papel na banca" value={m.papel} onChange={(e) => membro(i, { papel: e.target.value as PapelBanca })}>
              {Object.entries(NOME_PAPEL_BANCA).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
            </select>
            <button type="button" className="link perigo" onClick={() => setA({ ...a, banca: a.banca.filter((_, j) => j !== i) })}>Remover</button>
          </div>
        ))}
        <button type="button" onClick={() => setA({ ...a, banca: [...a.banca, { nome: "", papel: a.banca.length ? "interno" : "presidente", docente_id: null, instituicao: "" }] })}>
          Adicionar membro
        </button>
      </fieldset>
      <Campo rotulo="Observação"><textarea rows={2} value={a.observacao ?? ""} onChange={(e) => setA({ ...a, observacao: e.target.value })} /></Campo>
      <Erro msg={erro} />
      <footer><button className="primario" disabled={enviando}>{acao}</button></footer>
    </form>
  );
}

function FormProrrogacao({ d, salvo }: { d: TDiscente; salvo: (d: TDiscente) => void }) {
  const { enviando, erro, enviar } = useEnvio();
  const [meses, setMeses] = useState(6);
  const [motivo, setMotivo] = useState("");
  const [data, setData] = useState(hojeISO());
  return (
    <form onSubmit={(e) => { e.preventDefault(); enviar(async () => salvo(await api.prorrogar(d.id, { meses, motivo, concedida_em: data }))); }}>
      <div className="lado">
        <Campo rotulo="Meses"><input required type="number" min={1} max={24} value={meses} onChange={(e) => setMeses(Number(e.target.value))} /></Campo>
        <Campo rotulo="Concedida em"><input required type="date" value={data} onChange={(e) => setData(e.target.value)} /></Campo>
      </div>
      <Campo rotulo="Motivo"><input required value={motivo} onChange={(e) => setMotivo(e.target.value)} /></Campo>
      <p className="mudo">O prazo de conclusão passa de {dataBR(d.situacao.prazo_conclusao)} para {meses} {meses === 1 ? "mês" : "meses"} depois ({mesAno(addMeses(d.situacao.prazo_conclusao, meses))}).</p>
      <Erro msg={erro} />
      <footer><button className="primario" disabled={enviando}>Conceder prorrogação</button></footer>
    </form>
  );
}

function addMeses(iso: string, m: number) {
  const [a, mm] = iso.split("-").map(Number);
  const t = a * 12 + (mm - 1) + m;
  return `${Math.floor(t / 12)}-${String((t % 12) + 1).padStart(2, "0")}`;
}

function FormDesligamento({ d, salvo }: { d: TDiscente; salvo: (d: TDiscente) => void }) {
  const { enviando, erro, enviar } = useEnvio();
  const [data, setData] = useState(hojeISO());
  const [motivo, setMotivo] = useState("");
  return (
    <form onSubmit={(e) => { e.preventDefault(); enviar(async () => salvo(await api.desligar(d.id, { data, motivo }))); }}>
      <Campo rotulo="Data"><input required type="date" value={data} onChange={(e) => setData(e.target.value)} /></Campo>
      <Campo rotulo="Motivo"><input required value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Desistência, jubilamento, transferência…" /></Campo>
      <p className="mudo">{d.nome} sai das contagens de ativos e atrasados. Dá para desfazer depois.</p>
      <Erro msg={erro} />
      <footer><button className="primario perigo" disabled={enviando}>Registrar desligamento</button></footer>
    </form>
  );
}

function FormTema({ d, salvo }: { d: TDiscente; salvo: (d: TDiscente) => void }) {
  const { enviando, erro, enviar } = useEnvio();
  const [tema, setTema] = useState(d.tema ?? d.qualificacao?.titulo ?? "");
  return (
    <form onSubmit={(e) => { e.preventDefault(); enviar(async () => salvo(await api.atualizarDiscente(d.id, { tema: tema || null }))); }}>
      <Campo rotulo="Tema"><textarea rows={2} value={tema} onChange={(e) => setTema(e.target.value)} /></Campo>
      <Erro msg={erro} />
      <footer><button className="primario" disabled={enviando}>Salvar tema</button></footer>
    </form>
  );
}
