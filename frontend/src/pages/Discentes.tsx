import { useState } from "react";
import { api, type Docente, type Linha, type Usuario } from "../api";
import { Campo, Carregando, Dialogo, Erro, Etiqueta, NOME_FASE, Trilho, ir, parametro, useCarregar, useEnvio } from "../ui";

const FILTROS: [string, string][] = [
  ["", "Todos"],
  ["ativos", "Ativos"],
  ["em_dia", "Em dia"],
  ["atrasados", "Prazo vencido"],
  ["qualificacao_atrasada", "Qualificação atrasada"],
  ["nao_qualificados", "Ainda não qualificaram"],
  ["prazo_proximo", "Prazo nos próximos meses"],
  ["titulados", "Titulados"],
  ["desligados", "Desligados"],
];

export default function Discentes({ eu }: { eu: Usuario }) {
  const [filtro, setFiltro] = useState(parametro("filtro") ?? "ativos");
  const [orientador, setOrientador] = useState(parametro("orientador") ?? "");
  const [busca, setBusca] = useState("");
  const [novo, setNovo] = useState(false);
  const docentes = useCarregar(api.docentes, []);
  const lista = useCarregar(
    () => api.discentes({ filtro: filtro || undefined, orientador_id: orientador || undefined, busca: busca || undefined }),
    [filtro, orientador, busca],
  );

  return (
    <div className="pagina">
      <header className="cabecalho">
        <h1>Discentes</h1>
        {eu.papel === "coordenacao" && <button className="primario" onClick={() => setNovo(true)}>Cadastrar discente</button>}
      </header>

      <div className="filtros">
        <Campo rotulo="Buscar">
          <input type="search" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Nome ou matrícula" />
        </Campo>
        <Campo rotulo="Situação">
          <select value={filtro} onChange={(e) => setFiltro(e.target.value)}>
            {FILTROS.map(([v, r]) => <option key={v} value={v}>{r}</option>)}
          </select>
        </Campo>
        <Campo rotulo="Orientação">
          <select value={orientador} onChange={(e) => setOrientador(e.target.value)}>
            <option value="">Todos os docentes</option>
            {docentes.dados?.map((d) => <option key={d.id} value={d.id}>{d.nome}</option>)}
          </select>
        </Campo>
      </div>

      {lista.dados === null ? <Carregando erro={lista.erro} recarregar={lista.recarregar} /> : lista.dados.length === 0 ? (
        <p className="vazio">Nenhum discente com esses filtros.</p>
      ) : (
        <>
          <p className="mudo contagem">{lista.dados.length} {lista.dados.length === 1 ? "discente" : "discentes"}</p>
          <div className="rolagem">
            <table className="tabela-discentes">
              <thead>
                <tr><th>Discente</th><th>Orientação</th><th>Fase</th><th className="col-trilho">Percurso</th><th>Situação</th></tr>
              </thead>
              <tbody>
                {lista.dados.map((d) => (
                  <tr key={d.id} className="clicavel" onClick={() => ir(`/discentes/${d.id}`)}>
                    <td>
                      <a href={`#/discentes/${d.id}`}><b>{d.nome}</b></a>
                      <small className="bloco-small">{d.nivel === "doutorado" ? "Doutorado" : "Mestrado"} · {d.matricula}</small>
                    </td>
                    <td>{d.orientador_nome ?? "—"}</td>
                    <td>{NOME_FASE[d.situacao.fase]}</td>
                    <td className="col-trilho"><Trilho ingresso={d.data_ingresso} s={d.situacao} /></td>
                    <td><Etiqueta s={d.situacao} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <Dialogo titulo="Cadastrar discente" aberto={novo} fechar={() => setNovo(false)}>
        <NovoDiscente docentes={docentes.dados ?? []} criado={(id) => { setNovo(false); ir(`/discentes/${id}`); }} />
      </Dialogo>
    </div>
  );
}

function NovoDiscente({ docentes, criado }: { docentes: Docente[]; criado: (id: string) => void }) {
  const linhas = useCarregar(api.linhas, []);
  const { enviando, erro, enviar } = useEnvio();
  const [f, setF] = useState({ nome: "", email: "", matricula: "", nivel: "mestrado", data_ingresso: "", orientador_id: "", linha_id: "" });
  const muda = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        enviar(async () => {
          const d = await api.criarDiscente({ ...f, email: f.email || null, linha_id: f.linha_id || null });
          criado(d.id);
        });
      }}
    >
      <Campo rotulo="Nome completo"><input required value={f.nome} onChange={muda("nome")} /></Campo>
      <div className="lado">
        <Campo rotulo="Matrícula"><input required value={f.matricula} onChange={muda("matricula")} /></Campo>
        <Campo rotulo="E-mail"><input type="email" value={f.email} onChange={muda("email")} /></Campo>
      </div>
      <div className="lado">
        <Campo rotulo="Nível">
          <select value={f.nivel} onChange={muda("nivel")}><option value="mestrado">Mestrado</option><option value="doutorado">Doutorado</option></select>
        </Campo>
        <Campo rotulo="Data de ingresso"><input required type="date" value={f.data_ingresso} onChange={muda("data_ingresso")} /></Campo>
      </div>
      <Campo rotulo="Orientador(a)">
        <select required value={f.orientador_id} onChange={muda("orientador_id")}>
          <option value="">Escolha…</option>
          {docentes.filter((d) => d.ativo).map((d) => <option key={d.id} value={d.id}>{d.nome}</option>)}
        </select>
      </Campo>
      <Campo rotulo="Linha de pesquisa">
        <select value={f.linha_id} onChange={muda("linha_id")}>
          <option value="">—</option>
          {(linhas.dados ?? []).map((l: Linha) => <option key={l.id} value={l.id}>{l.nome}</option>)}
        </select>
      </Campo>
      <p className="mudo">O plano de trabalho, as disciplinas e a qualificação são registrados na página do discente.</p>
      <Erro msg={erro} />
      <footer><button className="primario" disabled={enviando}>Cadastrar discente</button></footer>
    </form>
  );
}
