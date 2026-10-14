import { useEffect, useState } from "react";
import { api, pessoasParaTroca } from "./api";
import { MODO_AUTH, definirIdentidadeDev, entrar, identidadeDev, observarLogin, sair, type IdentidadeDev } from "./auth";
import { Campo, Carregando, Erro, ir, useCarregar, useEnvio, useRota } from "./ui";
import Painel from "./pages/Painel";
import Discentes from "./pages/Discentes";
import Discente from "./pages/Discente";
import { Docente, Docentes } from "./pages/Docentes";
import Producoes from "./pages/Producoes";
import Cadastros from "./pages/Cadastros";

export default function App() {
  const [logado, setLogado] = useState<boolean | null>(MODO_AUTH === "dev" ? true : null);
  const [versao, setVersao] = useState(0); // muda ao trocar de identidade, para recarregar tudo

  useEffect(() => {
    if (MODO_AUTH !== "firebase") return;
    let desfazer: (() => void) | undefined;
    observarLogin((u) => setLogado(!!u)).then((f) => { desfazer = f; });
    return () => desfazer?.();
  }, []);

  if (logado === null) return <p className="carregando">Carregando…</p>;
  if (!logado) return <Login />;
  return <Shell key={versao} trocou={() => setVersao((v) => v + 1)} />;
}

function Shell({ trocou }: { trocou: () => void }) {
  const eu = useCarregar(api.eu, []);
  const rota = useRota();
  if (!eu.dados) return <Carregando erro={eu.erro} recarregar={eu.recarregar} />;
  const u = eu.dados;
  const equipe = u.papel !== "discente";
  const [secao, id] = rota;

  let pagina: JSX.Element;
  if (!equipe) {
    // Discente vê o próprio percurso e as próprias produções.
    pagina = secao === "producoes" ? <Producoes eu={u} /> : <Discente id={u.discente_id ?? ""} eu={u} />;
  } else if (secao === "discentes" && id) pagina = <Discente id={id} eu={u} />;
  else if (secao === "discentes") pagina = <Discentes eu={u} />;
  else if (secao === "docentes" && id) pagina = <Docente id={id} eu={u} />;
  else if (secao === "docentes") pagina = <Docentes eu={u} />;
  else if (secao === "producoes") pagina = <Producoes eu={u} />;
  else if (secao === "cadastros") pagina = <Cadastros eu={u} />;
  else pagina = <Painel />;

  const itens: [string, string][] = equipe
    ? [["", "Painel"], ["discentes", "Discentes"], ["docentes", "Docentes"], ["producoes", "Produção"], ["cadastros", "Cadastros"]]
    : [["", "Meu percurso"], ["producoes", "Minha produção"]];

  return (
    <>
      <a className="pular" href="#conteudo">Ir para o conteúdo</a>
      <header className="topo">
        <a className="marca" href="#/">Percurso</a>
        <nav aria-label="Seções">
          {itens.map(([k, r]) => (
            <a key={k} href={`#/${k}`} aria-current={(secao ?? "") === k ? "page" : undefined}>{r}</a>
          ))}
        </nav>
        <div className="quem">
          {MODO_AUTH === "dev" ? <TrocaDev trocou={trocou} /> : <button className="link" onClick={() => sair()}>Sair</button>}
        </div>
      </header>
      <main id="conteudo">{pagina}</main>
    </>
  );
}

function TrocaDev({ trocou }: { trocou: () => void }) {
  const pessoas = useCarregar(pessoasParaTroca, []);
  const atual = identidadeDev();
  const opcoes: IdentidadeDev[] = [
    { papel: "coordenacao", rotulo: "Coordenação" },
    ...(pessoas.dados?.docentes ?? []).map((d) => ({ papel: "docente" as const, id: d.id, rotulo: `Docente: ${d.nome}` })),
    ...(pessoas.dados?.discentes ?? []).map((d) => ({ papel: "discente" as const, id: d.id, rotulo: `Discente: ${d.nome}` })),
  ];
  const chave = (i: IdentidadeDev | null) => (i ? `${i.papel}:${i.id ?? ""}` : "");
  return (
    <label className="troca">
      <span>Ver como</span>
      <select value={chave(atual)} onChange={(e) => {
        const i = opcoes.find((o) => chave(o) === e.target.value);
        if (i) { definirIdentidadeDev(i); ir("/"); trocou(); }
      }}>
        {opcoes.map((o) => <option key={chave(o)} value={chave(o)}>{o.rotulo}</option>)}
      </select>
    </label>
  );
}

function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const { enviando, erro, enviar } = useEnvio();
  return (
    <main className="login">
      <h1>Percurso</h1>
      <p className="mudo">Acompanhamento do percurso discente e da produção do programa.</p>
      <form onSubmit={(e) => { e.preventDefault(); enviar(() => entrar(email, senha)); }}>
        <Campo rotulo="E-mail institucional"><input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} /></Campo>
        <Campo rotulo="Senha"><input type="password" required autoComplete="current-password" value={senha} onChange={(e) => setSenha(e.target.value)} /></Campo>
        <Erro msg={erro && "E-mail ou senha não conferem."} />
        <button className="primario" disabled={enviando}>Entrar</button>
      </form>
    </main>
  );
}
