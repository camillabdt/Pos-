# Decisões

Registro curto do porquê de cada escolha, para quem pegar o projeto depois.

## 1. Um sistema novo, aproveitando os dois anteriores

O SAGA tinha o percurso do aluno, mas nasceu como trabalho de disciplina, com exigências que
não são do programa (motor de inferência próprio, orientação a aspectos). O Poshboard tinha a
produção docente, mas no Realtime Database e com chaves versionadas. O Percurso reaproveita
as ideias e o código útil de cada um num desenho mais simples:

| Veio do SAGA | Veio do Poshboard |
|---|---|
| Ciclo do discente, papéis (coordenação/docente/discente) | Coleta OpenAlex (autor por ORCID/nome, paginação por cursor) |
| Plano de trabalho, qualificação, prorrogação, desligamento | Tipos de docente (permanente/colaborador/visitante), linhas de pesquisa |
| Painel da coordenação, tempo de integralização, alunos em risco | h-index / h5 / i10 calculados localmente |
| Coautoria com crédito cheio para cada autor | Veículos identificados por ISSN, DOI como chave de deduplicação |

## 2. Situação calculada, não gravada

"Em dia", "prazo vencido", "qualificação atrasada" etc. são funções puras dos fatos
(`dominio/situacao.py`). No SAGA havia situação registrada e inferida que podiam divergir; aqui
não há o que divergir. Mudar um prazo do programa reflete na hora.

## 3. Uma coleção de produções para discentes e docentes

Cada produção tem uma lista de autores; quem é do programa leva `discente_id` ou `docente_id`.
Assim, um artigo de aluno com orientador aparece nos dois perfis sem cópia, e o painel conta
"produções com discentes" — dado que a avaliação da CAPES pede.

Tipos incluídos a pedido da coordenação: artigo em periódico, artigo em evento, livro, capítulo,
software, registro de software, patente, participação em evento, startup, prêmio e outro.
Campos específicos (nº INPI, CNPJ, evento) ficam em `detalhes`.

## 4. Disciplinas como catálogo

No SAGA, "disciplina cursada" era uma atividade com descrição em texto livre — impossível
comparar com o planejado. Aqui há um catálogo; o plano lista disciplinas do catálogo e os
registros de cursadas apontam para elas.

## 5. Armazenamento atrás de uma interface mínima

`store/base.py` tem cinco operações. Em memória para desenvolvimento e testes (roda sem
credenciais, com dados fictícios); Firestore em produção. As listagens leem a coleção inteira —
adequado para um PPG (centenas de discentes). Se crescer muito, troca-se a implementação.

## 6. Um programa por instalação

O SAGA era multi-programa. Para o uso pretendido (um PPG), isso só adicionava complexidade.
Os prazos e créditos ficam em `config/programa`.

## O que ficou de fora (pode entrar depois)

- Fluxo de validação de atividades em duas instâncias e pontuação RL05 do SAGA.
- Proficiência em língua estrangeira e trancamento de matrícula (que pausaria o prazo).
- Leitura do Lattes (o Poshboard tinha só o esboço).
- Histórico de alterações/auditoria.
