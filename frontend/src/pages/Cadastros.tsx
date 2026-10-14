import { useEffect, useState } from "react";
import { api, type Disciplina, type Linha, type Programa, type Usuario, type Veiculo } from "../api";
import { Campo, Carregando, Erro, useCarregar, useEnvio } from "../ui";

export default function Cadastros({ eu }: { eu: Usuario }) {
  const coord = eu.papel === "coordenacao";
  return (
    <div className="pagina">
      <header className="cabecalho"><h1>Cadastros</h1></header>
      <PrazosPrograma coord={coord} />
      <TabelaDisciplinas coord={coord} />
      <div className="grade-2">
        <TabelaLinhas coord={coord} />
        <TabelaVeiculos coord={coord} />
      </div>
    </div>
  );
}

function PrazosPrograma({ coord }: { coord: boolean }) {
  const prog = useCarregar(api.programa, []);
  const [p, setP] = useState<Programa | null>(null);
  const { enviando, erro, enviar } = useEnvio();
  const [salvo, setSalvo] = useState(false);
  useEffect(() => { if (prog.dados) setP(prog.dados); }, [prog.dados]);
  if (!p) return <Carregando erro={prog.erro} />;
  const nivel = (n: "mestrado" | "doutorado", k: keyof Programa["mestrado"]) => (
    <input type="number" min={0} disabled={!coord} value={p[n][k]}
      onChange={(e) => { setSalvo(false); setP({ ...p, [n]: { ...p[n], [k]: Number(e.target.value) } }); }} />
  );
  return (
    <section className="bloco">
      <h2>Programa e prazos</h2>
      <p className="mudo">Os prazos valem para todos os discentes e mudam o painel na hora — nada fica gravado como "atrasado".</p>
      <form onSubmit={(e) => { e.preventDefault(); enviar(async () => { setP(await api.salvarPrograma(p)); setSalvo(true); }); }}>
        <div className="lado">
          <Campo rotulo="Nome do programa"><input disabled={!coord} value={p.nome} onChange={(e) => setP({ ...p, nome: e.target.value })} /></Campo>
          <Campo rotulo="Sigla"><input disabled={!coord} value={p.sigla} onChange={(e) => setP({ ...p, sigla: e.target.value })} /></Campo>
          <Campo rotulo="Avisar prazo com antecedência de (dias)">
            <input type="number" min={0} disabled={!coord} value={p.alerta_dias} onChange={(e) => setP({ ...p, alerta_dias: Number(e.target.value) })} />
          </Campo>
        </div>
        <table className="prazos">
          <thead><tr><th></th><th>Concluir em (meses)</th><th>Qualificar em (meses)</th><th>Créditos mínimos</th></tr></thead>
          <tbody>
            <tr><th>Mestrado</th><td>{nivel("mestrado", "conclusao_meses")}</td><td>{nivel("mestrado", "qualificacao_meses")}</td><td>{nivel("mestrado", "creditos_minimos")}</td></tr>
            <tr><th>Doutorado</th><td>{nivel("doutorado", "conclusao_meses")}</td><td>{nivel("doutorado", "qualificacao_meses")}</td><td>{nivel("doutorado", "creditos_minimos")}</td></tr>
          </tbody>
        </table>
        <Erro msg={erro} />
        {coord && <footer>{salvo && <span className="sucesso">Prazos salvos.</span>}<button className="primario" disabled={enviando}>Salvar prazos</button></footer>}
      </form>
    </section>
  );
}

/** Tabela editável genérica: lista + linha de inclusão. */
function TabelaSimples<T extends { id: string }, F extends Record<string, unknown>>({
  titulo, colecao, carregar, vazio, colunas, coord, novoVazio, paraCorpo, explicacao,
}: {
  titulo: string; colecao: "disciplinas" | "linhas" | "veiculos"; carregar: () => Promise<T[]>;
  vazio: string; coord: boolean; novoVazio: F; explicacao?: string;
  colunas: { rotulo: string; ver: (x: T) => React.ReactNode; campo: (f: F, set: (f: F) => void) => React.ReactNode; num?: boolean }[];
  paraCorpo: (f: F) => unknown;
}) {
  const lista = useCarregar(carregar, []);
  const [f, setF] = useState<F>(novoVazio);
  const { enviando, erro, enviar } = useEnvio();
  return (
    <section className="bloco">
      <h2>{titulo}</h2>
      {explicacao && <p className="mudo">{explicacao}</p>}
      {!lista.dados ? <Carregando erro={lista.erro} /> : (
        <form onSubmit={(e) => { e.preventDefault(); enviar(() => api.criar(colecao, paraCorpo(f)), () => { setF(novoVazio); lista.recarregar(); }); }}>
          <div className="rolagem">
            <table>
              <thead><tr>{colunas.map((c) => <th key={c.rotulo} className={c.num ? "num" : ""}>{c.rotulo}</th>)}{coord && <th></th>}</tr></thead>
              <tbody>
                {lista.dados.length === 0 && <tr><td colSpan={colunas.length + 1} className="mudo">{vazio}</td></tr>}
                {lista.dados.map((x) => (
                  <tr key={x.id}>
                    {colunas.map((c) => <td key={c.rotulo} className={c.num ? "num" : ""}>{c.ver(x)}</td>)}
                    {coord && (
                      <td><button type="button" className="link perigo"
                        onClick={() => enviar(() => api.apagar(colecao, x.id), lista.recarregar)}>Remover</button></td>
                    )}
                  </tr>
                ))}
                {coord && (
                  <tr className="nova-linha">
                    {colunas.map((c) => <td key={c.rotulo}>{c.campo(f, setF)}</td>)}
                    <td><button className="primario" disabled={enviando}>Incluir</button></td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <Erro msg={erro} />
        </form>
      )}
    </section>
  );
}

function TabelaDisciplinas({ coord }: { coord: boolean }) {
  return (
    <TabelaSimples<Disciplina, { codigo: string; nome: string; creditos: string; obrigatoria: boolean }>
      titulo="Disciplinas" colecao="disciplinas" carregar={api.disciplinas} coord={coord}
      vazio="Nenhuma disciplina cadastrada. Cadastre-as para montar os planos de trabalho."
      explicacao="Disciplinas usadas no plano de trabalho e no registro das cursadas. Disciplinas em uso não podem ser removidas."
      novoVazio={{ codigo: "", nome: "", creditos: "4", obrigatoria: false }}
      paraCorpo={(f) => ({ ...f, creditos: Number(f.creditos) })}
      colunas={[
        { rotulo: "Código", ver: (x) => x.codigo, campo: (f, s) => <input aria-label="Código" required value={f.codigo} onChange={(e) => s({ ...f, codigo: e.target.value })} /> },
        { rotulo: "Nome", ver: (x) => x.nome, campo: (f, s) => <input aria-label="Nome" required value={f.nome} onChange={(e) => s({ ...f, nome: e.target.value })} /> },
        { rotulo: "Créditos", num: true, ver: (x) => x.creditos, campo: (f, s) => <input aria-label="Créditos" type="number" min={0} required value={f.creditos} onChange={(e) => s({ ...f, creditos: e.target.value })} /> },
        { rotulo: "Obrigatória", ver: (x) => (x.obrigatoria ? "Sim" : "Não"), campo: (f, s) => <input aria-label="Obrigatória" type="checkbox" checked={f.obrigatoria} onChange={(e) => s({ ...f, obrigatoria: e.target.checked })} /> },
      ]}
    />
  );
}

function TabelaLinhas({ coord }: { coord: boolean }) {
  return (
    <TabelaSimples<Linha, { nome: string }>
      titulo="Linhas de pesquisa" colecao="linhas" carregar={api.linhas} coord={coord}
      vazio="Nenhuma linha cadastrada." novoVazio={{ nome: "" }} paraCorpo={(f) => f}
      colunas={[{ rotulo: "Nome", ver: (x) => x.nome, campo: (f, s) => <input aria-label="Nome da linha" required value={f.nome} onChange={(e) => s({ ...f, nome: e.target.value })} /> }]}
    />
  );
}

function TabelaVeiculos({ coord }: { coord: boolean }) {
  return (
    <TabelaSimples<Veiculo, { nome: string; issn: string; qualis: string }>
      titulo="Veículos e Qualis" colecao="veiculos" carregar={api.veiculos} coord={coord}
      vazio="Nenhum veículo cadastrado."
      explicacao="Produções com o mesmo ISSN herdam o estrato, inclusive as coletadas do OpenAlex."
      novoVazio={{ nome: "", issn: "", qualis: "" }}
      paraCorpo={(f) => ({ nome: f.nome, issn: f.issn.split(",").map((x) => x.trim()).filter(Boolean), qualis: f.qualis || null })}
      colunas={[
        { rotulo: "Nome", ver: (x) => x.nome, campo: (f, s) => <input aria-label="Nome do veículo" required value={f.nome} onChange={(e) => s({ ...f, nome: e.target.value })} /> },
        { rotulo: "ISSN", ver: (x) => x.issn.join(", ") || "—", campo: (f, s) => <input aria-label="ISSN" value={f.issn} onChange={(e) => s({ ...f, issn: e.target.value })} /> },
        { rotulo: "Qualis", ver: (x) => x.qualis ?? "—", campo: (f, s) => <input aria-label="Qualis" size={4} value={f.qualis} onChange={(e) => s({ ...f, qualis: e.target.value })} /> },
      ]}
    />
  );
}
