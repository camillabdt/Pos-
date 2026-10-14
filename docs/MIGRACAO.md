# Migração do SAGA e do Poshboard

O script `scripts/importar.py` lê a origem, converte e mostra um resumo com **avisos**.
Rode sempre com `--simular` primeiro e leia os avisos.

## SAGA (Firestore)

```bash
GOOGLE_APPLICATION_CREDENTIALS=/fora/do/repo/saga.json \
  python scripts/importar.py saga --projeto-origem PROJETO_DO_SAGA --simular
```

| SAGA | Percurso |
|---|---|
| `advisors` | docentes (vínculo "permanente"; ajuste depois) |
| `students` | discentes (ingresso, nível, orientação, coorientação) |
| `students/*/work_plan` | título do plano de trabalho |
| `prazo_final` além do prazo regular | prorrogação com a diferença em meses |
| `qualificacao_aprovada` + data | qualificação aprovada (**sem título** — completar) |
| situação `concluido` | defesa aprovada na `data_conclusao` (**sem título e banca** — completar) |
| situação `desligado` | desligamento |
| atividades "Disciplina" aprovadas | disciplinas do catálogo criadas a partir do texto (revisar nomes, códigos, créditos) |
| `productions` + `vehicles` | produções com autores discentes e Qualis do veículo |

Não importados: checklist, créditos por grupo, pesos Qualis versionados, auditoria e notificações.

## Poshboard (Realtime Database)

Exporte o JSON pelo console (Realtime Database → ⋮ → Exportar JSON) e rode:

```bash
python scripts/importar.py poshboard --arquivo export.json --simular
```

| Poshboard | Percurso |
|---|---|
| `linhas` | linhas de pesquisa |
| `docentes` | docentes (tipo, ORCID, Lattes) |
| `discentes` + `pesquisas` | discentes; orientação, linha, tema e datas vêm da pesquisa |
| pesquisa `DEFENDIDA` com `data_fim` | defesa aprovada |
| pesquisa `ARQUIVADA` | desligamento |
| `veiculos` | veículos (ISSN, Qualis) |

Os **produtos** do Poshboard não são copiados: depois de importar os docentes (com ORCID),
use "Coletar do OpenAlex" em cada um, ou `scripts/coletar_docentes.py`. A coleta deduplica por
DOI e vincula coautores discentes, o que a cópia direta não faria.

## Antes de tudo: as chaves do Poshboard

O repositório do Poshboard tem `service-account.json` e `poshbard-firebase.json` com chaves
privadas. Revogue as duas no Google Cloud Console (IAM → Contas de serviço → Chaves), remova os
arquivos do histórico do git (`git filter-repo`) e gere uma chave nova, guardada fora do
repositório, só para rodar a migração.
