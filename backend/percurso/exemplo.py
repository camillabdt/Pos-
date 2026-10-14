"""Dados de exemplo (fictícios) para desenvolvimento e demonstração.

As datas são relativas a hoje, para que sempre existam discentes em dia,
atrasados, sem qualificação, com prazo próximo, titulados e desligados.
"""

from __future__ import annotations

from datetime import date, timedelta

from percurso.dominio.modelos import (
    Autor,
    Avaliacao,
    Desligamento,
    Discente,
    Disciplina,
    DisciplinaCursada,
    Docente,
    Linha,
    MembroBanca,
    Metricas,
    PapelBanca,
    PlanoTrabalho,
    Producao,
    Programa,
    Prorrogacao,
    Resultado,
    TipoDocente,
    TipoProducao,
    Veiculo,
    VeiculoRef,
)
from percurso.dominio.situacao import soma_meses
from percurso.servicos.repo import Repo


def _semestre(d: date) -> str:
    return f"{d.year}/{1 if d.month <= 6 else 2}"


def carregar(repo: Repo, hoje: date | None = None) -> None:
    hoje = hoje or date.today()

    def ha(meses: int, dias: int = 0) -> date:
        return soma_meses(hoje, -meses) - timedelta(days=dias)

    repo.salvar_programa(Programa(nome="Programa de Pós-Graduação em Computação", sigla="PPGC"))

    linhas = [
        Linha(id="es", nome="Engenharia de Software"),
        Linha(id="si", nome="Sistemas Inteligentes"),
        Linha(id="rs", nome="Redes e Segurança"),
    ]
    for x in linhas:
        repo.linhas.salvar(x)

    docentes = [
        Docente(id="ana", nome="Ana Ribeiro", tipo=TipoDocente.PERMANENTE, linha_id="es", email="ana.ribeiro@exemplo.edu.br"),
        Docente(id="bruno", nome="Bruno Teixeira", tipo=TipoDocente.PERMANENTE, linha_id="si"),
        Docente(id="carla", nome="Carla Menezes", tipo=TipoDocente.PERMANENTE, linha_id="rs"),
        Docente(id="diego", nome="Diego Farias", tipo=TipoDocente.PERMANENTE, linha_id="si"),
        Docente(id="elisa", nome="Elisa Prado", tipo=TipoDocente.COLABORADOR, linha_id="es"),
        Docente(id="fabio", nome="Fábio Lemos", tipo=TipoDocente.VISITANTE, linha_id="rs"),
    ]
    for x in docentes:
        repo.docentes.salvar(x)

    disciplinas = [
        Disciplina(id="metod", codigo="PPGC001", nome="Metodologia da Pesquisa", creditos=4, obrigatoria=True),
        Disciplina(id="semin", codigo="PPGC002", nome="Seminários de Pesquisa", creditos=2, obrigatoria=True),
        Disciplina(id="eswe", codigo="PPGC101", nome="Engenharia de Software Empírica", creditos=4),
        Disciplina(id="aprend", codigo="PPGC102", nome="Aprendizado de Máquina", creditos=4),
        Disciplina(id="segur", codigo="PPGC103", nome="Segurança de Redes", creditos=4),
        Disciplina(id="distr", codigo="PPGC104", nome="Sistemas Distribuídos", creditos=4),
        Disciplina(id="visao", codigo="PPGC105", nome="Visão Computacional", creditos=4),
        Disciplina(id="estag", codigo="PPGC106", nome="Estágio de Docência", creditos=2),
    ]
    for x in disciplinas:
        repo.disciplinas.salvar(x)

    repo.veiculos.salvar(Veiculo(id="jss", nome="Journal of Systems and Software", issn=["0164-1212"], qualis="A1"))
    repo.veiculos.salvar(Veiculo(id="sbes", nome="Simpósio Brasileiro de Engenharia de Software", qualis="A3"))
    repo.veiculos.salvar(Veiculo(id="sbseg", nome="Simpósio Brasileiro de Segurança da Informação", qualis="A4"))
    repo.veiculos.salvar(Veiculo(id="rita", nome="Revista de Informática Teórica e Aplicada", issn=["0103-4308"], qualis="B1"))

    def cursadas(inicio: date, ids: list[str], ate_semestres: int, cursando: list[str] | None = None):
        """Distribui as disciplinas aprovadas nos primeiros semestres a partir do ingresso."""
        out = []
        for i, d in enumerate(ids):
            sem = soma_meses(inicio, 6 * min(i // 2, max(ate_semestres - 1, 0)))
            out.append(DisciplinaCursada(disciplina_id=d, semestre=_semestre(sem), situacao="aprovado", conceito="A" if i % 3 else "B"))
        for d in cursando or []:
            out.append(DisciplinaCursada(disciplina_id=d, semestre=_semestre(hoje), situacao="cursando"))
        return out

    def banca(orientador: str, *internos: str, externo: str = "Rita Camargo") -> list[MembroBanca]:
        nomes = {d.id: d.nome for d in docentes}
        return (
            [MembroBanca(nome=nomes[orientador], instituicao="PPGC", papel=PapelBanca.PRESIDENTE, docente_id=orientador)]
            + [MembroBanca(nome=nomes[i], instituicao="PPGC", papel=PapelBanca.INTERNO, docente_id=i) for i in internos]
            + [MembroBanca(nome=externo, instituicao="UFRGS", papel=PapelBanca.EXTERNO)]
        )

    plano_padrao = ["metod", "semin", "eswe", "distr", "estag"]

    def novo(id, nome, nivel, ingresso, orientador, **kw) -> Discente:
        mat = f"{ingresso.year}{ingresso.month:02d}{len(id):02d}{id[:3].upper()}"
        return Discente(id=id, nome=nome, matricula=mat, nivel=nivel, data_ingresso=ingresso,
                        orientador_id=orientador, linha_id=next(d.linha_id for d in docentes if d.id == orientador), **kw)

    alunos: list[Discente] = []

    i = ha(1)
    alunos.append(novo("lucas", "Lucas Andrade", "mestrado", i, "ana"))  # recém-chegado, sem plano

    i = ha(4)
    alunos.append(novo("marina", "Marina Costa", "mestrado", i, "bruno",
        plano=PlanoTrabalho(titulo_projeto="Detecção de deriva em modelos de linguagem", disciplinas_planejadas=["metod", "semin", "aprend", "visao"], aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, [], 1, cursando=["metod", "aprend", "visao"])))

    i = ha(10)
    alunos.append(novo("pedro", "Pedro Henrique Silva", "mestrado", i, "carla",
        plano=PlanoTrabalho(titulo_projeto="Detecção de intrusão em redes IoT industriais", disciplinas_planejadas=["metod", "semin", "segur", "distr"], aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, ["metod", "segur", "distr"], 2, cursando=["semin"])))

    i = ha(15)
    alunos.append(novo("julia", "Júlia Fernandes", "mestrado", i, "diego", coorientador_ids=["bruno"],
        plano=PlanoTrabalho(titulo_projeto="Aprendizado federado para dados clínicos", disciplinas_planejadas=["metod", "semin", "aprend", "distr"], aprovado_em=soma_meses(i, 2)),
        disciplinas=cursadas(i, ["metod", "semin", "aprend"], 2)))

    i = ha(20)
    alunos.append(novo("rafael", "Rafael Moura", "mestrado", i, "ana",
        tema="Testes de mutação guiados por LLMs",
        plano=PlanoTrabalho(titulo_projeto="Geração automática de testes", disciplinas_planejadas=plano_padrao, aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, plano_padrao, 3),
        qualificacao=Avaliacao(data=soma_meses(i, 11), titulo="Testes de mutação guiados por LLMs", resultado=Resultado.APROVADO, banca=banca("ana", "elisa"))))

    i = ha(22, 15)
    alunos.append(novo("beatriz", "Beatriz Lima", "mestrado", i, "bruno",
        tema="Explicabilidade em classificadores de imagens médicas",
        plano=PlanoTrabalho(titulo_projeto="Explicabilidade em visão computacional", disciplinas_planejadas=["metod", "semin", "aprend", "visao"], aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, ["metod", "semin", "aprend", "visao", "estag"], 3),
        qualificacao=Avaliacao(data=soma_meses(i, 12), titulo="Explicabilidade em classificadores de imagens médicas", resultado=Resultado.APROVADO_COM_RESSALVAS, banca=banca("bruno", "diego"))))

    i = ha(23)
    alunos.append(novo("thiago", "Thiago Rocha", "mestrado", i, "carla",
        tema="Honeypots adaptativos para redes 5G",
        plano=PlanoTrabalho(titulo_projeto="Honeypots adaptativos", disciplinas_planejadas=["metod", "semin", "segur", "distr"], aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, ["metod", "semin", "segur", "distr"], 2),
        qualificacao=Avaliacao(data=soma_meses(i, 12), titulo="Honeypots adaptativos para redes 5G", resultado=Resultado.APROVADO, banca=banca("carla", "fabio")),
        defesa=Avaliacao(data=hoje + timedelta(days=24), titulo="Honeypots adaptativos para redes 5G", resultado=Resultado.AGENDADA, banca=banca("carla", "fabio", externo="Marcos Vieira"))))

    i = ha(27)
    alunos.append(novo("camila", "Camila Duarte", "mestrado", i, "ana",
        tema="Dívida técnica em projetos científicos",
        plano=PlanoTrabalho(titulo_projeto="Dívida técnica em software científico", disciplinas_planejadas=plano_padrao, aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, ["metod", "semin", "eswe", "distr"], 3),
        qualificacao=Avaliacao(data=soma_meses(i, 14), titulo="Dívida técnica em projetos científicos", resultado=Resultado.APROVADO, banca=banca("ana", "elisa"))))

    i = ha(28)
    alunos.append(novo("gustavo", "Gustavo Pires", "mestrado", i, "diego",
        tema="Otimização de hiperparâmetros com orçamento limitado",
        plano=PlanoTrabalho(titulo_projeto="AutoML com orçamento", disciplinas_planejadas=["metod", "semin", "aprend", "distr"], aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, ["metod", "semin", "aprend", "distr"], 2),
        prorrogacoes=[Prorrogacao(meses=6, motivo="Licença saúde no 3º semestre", concedida_em=soma_meses(i, 22))],
        qualificacao=Avaliacao(data=soma_meses(i, 13), titulo="Otimização de hiperparâmetros com orçamento limitado", resultado=Resultado.APROVADO, banca=banca("diego", "bruno"))))

    i = ha(26)
    alunos.append(novo("larissa", "Larissa Nunes", "mestrado", i, "elisa",
        plano=PlanoTrabalho(titulo_projeto="Acessibilidade em aplicativos móveis", disciplinas_planejadas=plano_padrao),
        disciplinas=cursadas(i, ["metod", "eswe"], 2)))

    i = ha(30)
    alunos.append(novo("vinicius", "Vinícius Alves", "mestrado", i, "bruno",
        tema="Sumarização de prontuários com modelos de linguagem",
        plano=PlanoTrabalho(titulo_projeto="PLN clínico", disciplinas_planejadas=["metod", "semin", "aprend"], aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, ["metod", "semin", "aprend", "visao"], 2),
        qualificacao=Avaliacao(data=soma_meses(i, 11), titulo="Sumarização de prontuários", resultado=Resultado.APROVADO, banca=banca("bruno", "diego")),
        defesa=Avaliacao(data=soma_meses(i, 23), titulo="Sumarização de prontuários com modelos de linguagem", resultado=Resultado.APROVADO, banca=banca("bruno", "diego", externo="Helena Souza"))))

    i = ha(40)
    alunos.append(novo("aline", "Aline Batista", "mestrado", i, "carla",
        tema="Criptografia leve para sensores agrícolas",
        plano=PlanoTrabalho(titulo_projeto="Criptografia leve", disciplinas_planejadas=["metod", "semin", "segur"], aprovado_em=soma_meses(i, 1)),
        disciplinas=cursadas(i, ["metod", "semin", "segur", "distr"], 2),
        qualificacao=Avaliacao(data=soma_meses(i, 15), titulo="Criptografia leve para sensores agrícolas", resultado=Resultado.APROVADO, banca=banca("carla", "fabio")),
        defesa=Avaliacao(data=soma_meses(i, 27), titulo="Criptografia leve para sensores agrícolas", resultado=Resultado.APROVADO, banca=banca("carla", "fabio", externo="Paulo Gomes"))))

    i = ha(18)
    alunos.append(novo("eduardo", "Eduardo Matos", "mestrado", i, "elisa",
        plano=PlanoTrabalho(titulo_projeto="Ensino de programação com feedback automático", disciplinas_planejadas=plano_padrao),
        disciplinas=cursadas(i, ["metod"], 1),
        desligamento=Desligamento(data=soma_meses(i, 9), motivo="Desistência (aprovado em concurso)")))

    i = ha(20)
    alunos.append(novo("sofia", "Sofia Martins", "doutorado", i, "ana",
        plano=PlanoTrabalho(titulo_projeto="Evolução de arquiteturas de microsserviços", disciplinas_planejadas=["metod", "semin", "eswe", "distr", "estag"], aprovado_em=soma_meses(i, 2)),
        disciplinas=cursadas(i, ["metod", "semin", "eswe"], 2, cursando=["distr"])))

    i = ha(36)
    alunos.append(novo("henrique", "Henrique Castro", "doutorado", i, "diego",
        plano=PlanoTrabalho(titulo_projeto="Aprendizado por reforço em robótica", disciplinas_planejadas=["metod", "semin", "aprend", "visao", "estag"], aprovado_em=soma_meses(i, 2)),
        disciplinas=cursadas(i, ["metod", "semin", "aprend", "visao", "estag"], 3)))

    i = ha(54)
    alunos.append(novo("patricia", "Patrícia Gonçalves", "doutorado", i, "carla",
        tema="Detecção de anomalias em tráfego cifrado",
        plano=PlanoTrabalho(titulo_projeto="Tráfego cifrado", disciplinas_planejadas=["metod", "semin", "segur", "distr", "estag"], aprovado_em=soma_meses(i, 2)),
        disciplinas=cursadas(i, ["metod", "semin", "segur", "distr", "estag"], 3),
        qualificacao=Avaliacao(data=soma_meses(i, 26), titulo="Anomalias em tráfego cifrado", resultado=Resultado.APROVADO, banca=banca("carla", "fabio", "ana")),
        defesa=Avaliacao(data=soma_meses(i, 47), titulo="Detecção de anomalias em tráfego cifrado", resultado=Resultado.APROVADO, banca=banca("carla", "fabio", "ana", externo="Sérgio Tavares"))))

    for a in alunos:
        repo.discentes.salvar(a)

    nomes = {d.id: d.nome for d in [*docentes, *alunos]}

    def doc(*ids):
        return [Autor(nome=nomes[x], docente_id=x) for x in ids]

    def dis(*ids):
        return [Autor(nome=nomes[x], discente_id=x) for x in ids]

    ano = hoje.year
    prods = [
        Producao(id="p1", tipo=TipoProducao.ARTIGO_PERIODICO, titulo="Mutation testing with large language models: an empirical study",
                 ano=ano, autores=dis("rafael") + doc("ana", "elisa"), doi="10.1016/j.jss.2026.000001",
                 veiculo=VeiculoRef(nome="Journal of Systems and Software", issn=["0164-1212"], qualis="A1"), citacoes=3),
        Producao(id="p2", tipo=TipoProducao.ARTIGO_EVENTO, titulo="Honeypots adaptativos em redes 5G: resultados preliminares",
                 ano=ano - 1, autores=dis("thiago") + doc("carla"), veiculo=VeiculoRef(nome="Simpósio Brasileiro de Segurança da Informação", qualis="A4"), citacoes=1),
        Producao(id="p3", tipo=TipoProducao.SOFTWARE, titulo="MutaLLM — ferramenta de testes de mutação",
                 ano=ano, autores=dis("rafael") + doc("ana"), url="https://github.com/exemplo/mutallm",
                 detalhes={"licenca": "MIT"}),
        Producao(id="p4", tipo=TipoProducao.REGISTRO_SOFTWARE, titulo="Sistema de sumarização de prontuários",
                 ano=ano - 1, autores=dis("vinicius") + doc("bruno"), detalhes={"numero_inpi": "BR512025000123-4"}),
        Producao(id="p5", tipo=TipoProducao.STARTUP, titulo="AgroCripto Tecnologia Ltda.",
                 ano=ano - 1, autores=dis("aline") + doc("carla"), detalhes={"cnpj": "00.000.000/0001-00", "incubadora": "Incubadora do campus"}),
        Producao(id="p6", tipo=TipoProducao.PARTICIPACAO_EVENTO, titulo="Apresentação de pôster no SBES",
                 ano=ano, autores=dis("camila"), detalhes={"evento": "SBES", "local": "Porto Alegre"}),
        Producao(id="p7", tipo=TipoProducao.ARTIGO_PERIODICO, titulo="Federated learning for clinical data: a systematic mapping",
                 ano=ano, autores=dis("julia") + doc("diego", "bruno"), veiculo=VeiculoRef(nome="Revista de Informática Teórica e Aplicada", issn=["0103-4308"], qualis="B1")),
        Producao(id="p8", tipo=TipoProducao.ARTIGO_PERIODICO, titulo="Anomaly detection in encrypted traffic using graph embeddings",
                 ano=ano - 2, autores=dis("patricia") + doc("carla", "fabio"), veiculo=VeiculoRef(nome="Computers & Security", qualis="A1"), citacoes=27),
        Producao(id="p9", tipo=TipoProducao.PREMIO, titulo="Melhor dissertação do ano — prêmio regional",
                 ano=ano - 1, autores=dis("vinicius"), detalhes={"concedido_por": "Sociedade regional de computação"}),
    ]
    # Produção só de docentes (como viria da coleta do OpenAlex), com citações.
    for k, (quem, cits) in enumerate([("ana", [40, 22, 15, 9, 4]), ("bruno", [61, 30, 12, 11, 7, 2]),
                                      ("carla", [18, 10, 6, 3]), ("diego", [25, 14, 8])]):
        for j, c in enumerate(cits):
            prods.append(Producao(
                id=f"d{k}{j}", tipo=TipoProducao.ARTIGO_PERIODICO if j % 2 == 0 else TipoProducao.ARTIGO_EVENTO,
                titulo=f"Estudo {j + 1} de {nomes[quem].split()[0]} sobre {['qualidade de software', 'aprendizado de máquina', 'segurança', 'otimização'][k]}",
                ano=ano - j, autores=doc(quem), citacoes=c, origem="openalex", openalex_id=f"W{k}{j}000",
            ))
    for p in prods:
        repo.producoes.salvar(p)

    from percurso.servicos.producoes import ProducoesServico

    ps = ProducoesServico(repo)
    for d in docentes:
        m = ps.metricas_docente(d.id, ano)
        d.metricas = Metricas(**m, total_obras=len(ps.listar(docente_id=d.id)), coletado_em=hoje if m["citacoes"] else None)
        repo.docentes.salvar(d)
