# Percurso

Acompanhamento do percurso discente e da produção de um programa de pós-graduação.
Reúne o que funcionava no **SAGA** (percurso do aluno, papéis, painel da coordenação) e no
**Poshboard** (produção docente coletada do OpenAlex, métricas, Qualis).

## O que ele responde

A qualquer momento, no **Painel**:

- quantos discentes estão **em dia**, quem está com **prazo vencido** e há quantos dias;
- quem **ainda não qualificou** e quem já passou do **prazo de qualificar**;
- quem tem **prazo de conclusão nos próximos meses**;
- titulados, desligados, **tempo médio até a titulação** e quantos titularam no prazo;
- tudo isso **por orientador(a)**, e entradas/saídas por ano.

Para cada discente, o **percurso** completo:

| Entrada | Meio | Fim |
|---|---|---|
| Data de ingresso | Disciplinas cursadas × planejadas | Tema da dissertação/tese |
| Orientação e coorientação | Produções (artigos, software, registros, patentes, eventos, startups, prêmios) | Defesa: data, título, banca, resultado |
| Plano de trabalho com disciplinas planejadas | Qualificação: data, título, banca, resultado | Tempo até a titulação e se foi no prazo |
| | Prorrogações | Desligamento, se houver |

E a **produção docente**: coleta do OpenAlex (sem duplicar o que foi cadastrado à mão),
h-index, h5, i10, citações, estratos Qualis e produções com discentes.

## Rodar localmente (5 minutos, sem credenciais)

```bash
# API — vem com dados fictícios em memória
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn percurso.main:app --reload --port 8000     # docs em http://localhost:8000/docs

# Interface (outro terminal)
cd frontend
npm ci
npm run dev                                         # http://localhost:5173
```

No modo de desenvolvimento, use **"Ver como"** no canto superior para alternar entre
coordenação, um docente ou um discente e conferir o que cada papel vê e pode alterar.

### Testar a busca de um(a) professor(a) no OpenAlex

```bash
export OPENALEX_API_KEY=sua-chave      # gratuita em https://openalex.org/settings/api (Windows: set OPENALEX_API_KEY=...)
python scripts/testar_openalex.py "Silvio Ereno Quincozes" --orcid 0000-0001-6793-4033
```

Mostra os candidatos com nome parecido, qual a coleta escolheria e um resumo da produção. Não grava nada.
Desde 13/02/2026 a API do OpenAlex exige chave; sem ela há só uma pequena cota diária de demonstração.
Para a coleta dentro do sistema, defina `OPENALEX_API_KEY` antes de subir a API.

Testes: `cd backend && pytest -q` (regras de situação, API, permissões, coleta OpenAlex e importação).

## Papéis

| Papel | Vê | Altera |
|---|---|---|
| `coordenacao` | Tudo | Tudo, incluindo cadastros, prazos, prorrogações e desligamentos |
| `docente` | Painel, discentes, docentes, produção | Percurso dos **seus orientandos** (plano, disciplinas, qualificação, tema, defesa), o próprio cadastro e produções em que é autor(a) |
| `discente` | O **próprio** percurso e as próprias produções | Produções em que é autor(a) |

Os papéis vêm de *custom claims* do Firebase Auth (`papel`, `docente_id`, `discente_id`).
Use `scripts/definir_papel.py` para atribuí-los.

## Como a situação é calculada

Nada de "atrasado" fica gravado no banco. A situação é derivada dos fatos registrados e dos
prazos configurados em **Cadastros → Programa e prazos** (`backend/percurso/dominio/situacao.py`):

- **prazo de conclusão** = ingresso + prazo do nível (24 meses no mestrado, 48 no doutorado, configurável) + prorrogações;
- **prazo de qualificação** = ingresso + meses até qualificar (12 / 30, configurável);
- **prazo vencido**: hoje passou do prazo de conclusão e não titulou;
- **qualificação atrasada**: não qualificou e hoje passou do prazo de qualificação;
- **em dia**: ativo, sem prazo vencido e sem qualificação atrasada;
- **titulado**: defesa com resultado aprovado (com ou sem ressalvas).

Mudar um prazo muda o painel na hora, sem migração.

## Colocar em produção (Firebase + Cloud Run)

1. Crie um projeto Firebase **novo** com Firestore e Authentication (e-mail/senha).
2. Publique `firestore.rules` (o navegador não acessa o Firestore direto; tudo passa pela API).
3. API no Cloud Run:
   ```bash
   cd backend
   gcloud run deploy percurso-api --source . --region southamerica-east1 \
     --set-env-vars PERCURSO_ARMAZENAMENTO=firestore,PERCURSO_AUTH=firebase,FIREBASE_PROJECT_ID=SEU_PROJETO,OPENALEX_API_KEY=SUA_CHAVE,OPENALEX_MAILTO=voce@instituicao.br,CORS_ORIGENS=https://SEU_PROJETO.web.app
   ```
   No Cloud Run a credencial vem da conta de serviço do próprio serviço — **não** é preciso arquivo JSON.
4. Interface no Firebase Hosting: copie `frontend/.env.example` para `frontend/.env.production`,
   preencha `VITE_API_URL`, `VITE_AUTH=firebase` e as chaves **públicas** do app web, depois
   `npm run build` e `firebase deploy --only hosting` (pasta `frontend/dist`).
5. Dê os papéis: `python scripts/definir_papel.py email@instituicao.br coordenacao`.
6. Coleta periódica da produção docente: agende `scripts/coletar_docentes.py`
   (Cloud Scheduler → Cloud Run Job, ou cron), como era o harvest do Poshboard.

## Trazer os dados do SAGA e do Poshboard

```bash
# Sempre simule antes: mostra o que entra e o que precisa de revisão manual.
python scripts/importar.py saga --projeto-origem PROJETO_DO_SAGA --simular
python scripts/importar.py poshboard --arquivo export-rtdb.json --simular
```

Detalhes do que é convertido e do que fica de fora em [`docs/MIGRACAO.md`](docs/MIGRACAO.md).

## Segurança

- **Nenhuma chave entra no repositório.** O `.gitignore` bloqueia `.env` e JSONs de conta de serviço.
  Em desenvolvimento, aponte `GOOGLE_APPLICATION_CREDENTIALS` para um arquivo **fora** da pasta do projeto.
- `PERCURSO_AUTH=dev` aceita o papel enviado pelo navegador: **nunca** use fora da sua máquina.
  O `Dockerfile` já sobe com `PERCURSO_AUTH=firebase`.

## Estrutura

```
backend/percurso/
  dominio/      modelos, regras de situação (funções puras), métricas bibliométricas
  servicos/     percurso, painel, produções, coleta OpenAlex, repositório tipado
  store/        armazenamento: memória (dev/testes) e Firestore (produção)
  api/          rotas FastAPI
  importacao.py conversão SAGA/Poshboard
frontend/src/   React + TypeScript (painel, percurso, docentes, produção, cadastros)
scripts/        importar, coletar_docentes, definir_papel
docs/           decisões e migração
```
