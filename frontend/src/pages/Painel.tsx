import { useState } from "react";
import { api, type Painel as TPainel, type Totais } from "../api";
import { Carregando, Etiqueta, NOME_TIPO, Trilho, ir, plural, useCarregar } from "../ui";

const RECORTES: { chave: keyof Totais; rotulo: string; tom: string }[] = [
  { chave: "atrasados", rotulo: "Prazo vencido", tom: "atraso" },
  { chave: "qualificacao_atrasada", rotulo: "Qualificação atrasada", tom: "alerta" },
  { chave: "prazo_proximo", rotulo: "Prazo nos próximos meses", tom: "alerta" },
  { chave: "nao_qualificados", rotulo: "Ainda não qualificaram", tom: "neutro" },
  { chave: "em_dia", rotulo: "Em dia", tom: "ok" },
  { chave: "titulados", rotulo: "Titulados", tom: "fim" },
  { chave: "desligados", rotulo: "Desligados", tom: "neutro" },
];

export default function Painel() {
  const { dados: p, erro, recarregar } = useCarregar(api.painel, []);
  const [recorte, setRecorte] = useState<keyof Totais>("atrasados");
  const lista = useCarregar(() => api.discentes({ filtro: recorte }), [recorte]);

  if (!p) return <Carregando erro={erro} recarregar={recarregar} />;
  const t = p.totais;

  return (
    <div className="pagina">
      <section className="manchete">
        <p className="manchete-texto">
          <strong>{plural(t.ativos, "discente ativo", "discentes ativos")}</strong> no {p.programa}.{" "}
          <span className="tom-ok-texto">{t.em_dia} em dia</span>,{" "}
          <span className="tom-atraso-texto">{t.atrasados} com prazo vencido</span> e{" "}
          <span className="tom-alerta-texto">{t.qualificacao_atrasada} sem qualificar no prazo</span>.
        </p>
        <Niveis p={p} />
      </section>

      <section className="bloco">
        <div className="recortes" role="tablist" aria-label="Recortes de discentes">
          {RECORTES.map((r) => (
            <button
              key={r.chave}
              role="tab"
              aria-selected={recorte === r.chave}
              className={`recorte tom-${r.tom} ${recorte === r.chave ? "ativo" : ""}`}
              onClick={() => setRecorte(r.chave)}
            >
              <span className="recorte-n">{t[r.chave]}</span>
              <span className="recorte-rotulo">{r.rotulo}</span>
            </button>
          ))}
        </div>

        <div className="lista-recorte" role="tabpanel">
          {lista.dados === null ? <Carregando erro={lista.erro} /> : lista.dados.length === 0 ? (
            <p className="vazio">Ninguém neste recorte.</p>
          ) : (
            <ul className="linhas-discentes">
              {lista.dados.map((d) => (
                <li key={d.id}>
                  <a href={`#/discentes/${d.id}`} className="linha-discente">
                    <span className="ld-nome">
                      <b>{d.nome}</b>
                      <small>{d.nivel === "doutorado" ? "Doutorado" : "Mestrado"} · {d.orientador_nome ?? "sem orientação"}</small>
                    </span>
                    <Trilho ingresso={d.data_ingresso} s={d.situacao} />
                    <span className="ld-situacao">
                      <Etiqueta s={d.situacao} />
                      {d.situacao.pendencias[0] && d.situacao.pendencias[0] !== "" && !d.situacao.atrasado && !d.situacao.prazo_proximo && (
                        <small>{d.situacao.pendencias[0]}</small>
                      )}
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <div className="grade-2">
        <section className="bloco">
          <h2>Por orientador(a)</h2>
          <div className="rolagem">
            <table>
              <thead>
                <tr><th>Docente</th><th className="num">Ativos</th><th className="num">Em dia</th><th className="num">Prazo vencido</th><th className="num">Sem qualificar</th><th className="num">Titulados</th></tr>
              </thead>
              <tbody>
                {p.por_orientador.map((o) => (
                  <tr key={o.docente_id} className="clicavel" onClick={() => ir(`/docentes/${o.docente_id}`)}>
                    <td><a href={`#/docentes/${o.docente_id}`}>{o.nome}</a></td>
                    <td className="num">{o.ativos}</td>
                    <td className="num">{o.em_dia}</td>
                    <td className={`num ${o.atrasados ? "tom-atraso-texto" : ""}`}>{o.atrasados}</td>
                    <td className="num">{o.nao_qualificados}</td>
                    <td className="num">{o.titulados}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="bloco">
          <h2>Tempo até a titulação</h2>
          <dl className="numeros">
            {p.titulacao.map((x) => (
              <div key={x.nivel}>
                <dt>{x.nivel === "mestrado" ? "Mestrado" : "Doutorado"}</dt>
                <dd>
                  {x.media_meses === null ? <span className="mudo">Ninguém titulado ainda</span> : (
                    <>
                      <b>{x.media_meses.toLocaleString("pt-BR")}</b> meses em média
                      <small>{x.no_prazo} de {plural(x.titulados, "titulado", "titulados")} dentro do prazo · mediana {x.mediana_meses?.toLocaleString("pt-BR")} meses</small>
                    </>
                  )}
                </dd>
              </div>
            ))}
          </dl>

          <h2>Produção nos últimos 5 anos</h2>
          <p className="mudo">{plural(p.producao_discente_ultimos_5_anos, "produção tem", "produções têm")} discentes entre os autores.</p>
          <ul className="barras">
            {Object.entries(p.producao_por_tipo).map(([tipo, n]) => {
              const max = Math.max(...Object.values(p.producao_por_tipo));
              return (
                <li key={tipo}>
                  <a href={`#/producoes?tipo=${tipo}`}>{NOME_TIPO[tipo as keyof typeof NOME_TIPO] ?? tipo}</a>
                  <span className="barra"><span style={{ width: `${(n / max) * 100}%` }} /></span>
                  <b>{n}</b>
                </li>
              );
            })}
          </ul>
        </section>
      </div>

      <section className="bloco">
        <h2>Entradas e saídas por ano</h2>
        <div className="rolagem">
          <table className="anos">
            <thead><tr><th>Ano</th>{p.por_ano.map((a) => <th key={a.ano} className="num">{a.ano}</th>)}</tr></thead>
            <tbody>
              <tr><th>Ingressos</th>{p.por_ano.map((a) => <td key={a.ano} className="num">{a.ingressos || "—"}</td>)}</tr>
              <tr><th>Titulações</th>{p.por_ano.map((a) => <td key={a.ano} className="num">{a.titulacoes || "—"}</td>)}</tr>
              <tr><th>Desligamentos</th>{p.por_ano.map((a) => <td key={a.ano} className="num">{a.desligamentos || "—"}</td>)}</tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Niveis({ p }: { p: TPainel }) {
  return (
    <p className="manchete-sub">
      Mestrado: {p.por_nivel.mestrado.ativos} ativos, {p.por_nivel.mestrado.atrasados} com prazo vencido.{" "}
      Doutorado: {p.por_nivel.doutorado.ativos} ativos, {p.por_nivel.doutorado.atrasados} com prazo vencido.
    </p>
  );
}
