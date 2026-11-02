# Revisão de elencos — 01/11/2026

O espelho estatístico continua parado em abril: a API GitHub confirmou que `main` ainda aponta para [192a878, de 10/04/2026](https://github.com/twodotone/finalLOL/commit/192a8783278f7d1fb6e688d5525b702b8bbe6ec1). Baixar o mesmo arquivo não resolve transferências posteriores.

## Fontes verificadas

| Fonte | Resultado e uso |
| --- | --- |
| [Mais Esports: elencos](https://maisesports.com.br/cblol-2026-veja-o-que-mudou-nas-escalacoes-dos-times-para-o-2-split) | Publicação de 24/07/2026: oito quintetos anunciados para o Split 2. Importados como snapshot de abertura, sem comprovar contratos atuais. |
| [Mais Esports: Wizer/Kaiwing](https://maisesports.com.br/cblol-2026-vivo-keyd-stars-oficializa-saida-de-kaiwing-e-wizer) | Saídas noticiadas em 28/05/2026. Dois eventos; data de publicação separada da data efetiva do contrato. |
| [Onivia: VKS](https://onivia.com/article/vks-roster-update-for-october-6) | Saídas de ZekaS, Mireu e Jeskla em 06/10/2026; cita Leaguepedia. Três eventos de fonte secundária, confiança explicitada. |
| [GOL: Split 2](https://gol.gg/players/list/season-ALL/split-ALL/tournament-CBLOL%202026%20Split%202/) e [VKS x Fluxo, 07/08](https://gol.gg/game/stats/80947/page-fullstats/) | Corroboram ZekaS e o quinteto da VKS na competição. Não incorporados como estatísticas de partidas ao modelo. |
| [LoL Esports: VKS](https://lolesports.com/en-US/teams/vivo-keyd) | Ainda lista nomes com saídas posteriores noticiadas. Serve como fonte de retratos; não foi aceita como elenco vigente. |
| [Sheep Esports: VKS](https://www.sheepesports.com/us/all/teams/Vivo%20Keyd%20Stars) | A busca e a página aberta divergiram em cobertura; a página aberta exibiu Boal/Morttheus em “Active Roster”. Necessário filtrar competição e conferir data, sem assumir que o rótulo significa vínculo atual. |
| [Liquipedia](https://liquipedia.net/leagueoflegends/Keyd_Stars) | Acesso direto 403; cronologia apareceu na busca. Não importada. |
| Leaguepedia | Catálogo atingiu limite na consulta anterior; sem nova coleta Cargo em massa. |
| [Oracle's Elixir](https://oracleselixir.com/tools/downloads) / [Hugging Face](https://huggingface.co/datasets/Finish-him/esports-data) | Retornaram 403 / 401. Nenhum CSV novo ingerido. |

Anúncios no X incorporados nas matérias retornaram 403 no acesso direto. Não se alega confirmação primária desses anúncios. Não houve contorno de bloqueios. Fontes editoriais não têm licença aberta confirmada; foram registrados fatos concisos e links, sem republicar matérias integrais.

## Caso Wizer / ZekaS

A troca está corroborada. As fontes nomeiam as etapas como **Copa CBLOL, Split 1 e Split 2 de 2026**. Wizer aparece nas partidas de março/abril; sua saída foi noticiada em maio; ZekaS aparece no anúncio do Split 2 e na partida de agosto. Não houve conversão silenciosa para “Split 3”.

O registro secundário de outubro noticia também a saída do próprio ZekaS. Por isso, simplesmente colocá-lo como titular atual de novembro produziria outra afirmação sem suporte suficiente. Saída não estabelece automaticamente status de free agent hoje.

## Entrega e limites

- Oito equipes, 40 vagas anunciadas e cinco eventos datados. Todos os nomes têm uma correspondência única por handle normalizado na base; homônimos ficariam sem associação para revisão.
- Equipes abre em “Elencos anunciados e movimentações”; o histórico das partidas permanece em outra opção. Fichas/comparação incluem fontes e eventos; a lista identifica “Equipe nas estatísticas” e corte individual.
- Snapshot de abertura, não relação de todos os atletas que atuaram no split. Substituições posteriores, incluindo as envolvendo Namiru e Manel, ainda precisam de conciliação com as partidas.
- Vínculos vigentes em novembro, demais movimentações do CBLOL e elencos globais ainda não foram integralmente verificados. Ausência de evento de saída não confirma permanência.
- Ratings continuam com partidas até 10/04/2026. Elencos novos não recebem Overall nem quantidade fictícia de partidas.
- Metadados JSON separados, servidos pelo backend junto com as consultas Supabase. Nenhuma tabela, RLS, estatística ou modelo remoto foi alterado.

## Reproduzir

```powershell
.\.venv\Scripts\python.exe -m backend.rosters config/rosters-reviewed.json
```

A curadoria registra fontes, datas e escopo; o importador gera `data/roster-evidence.json`. Não é um crawler. Ampliações devem acrescentar snapshots/eventos revisados, preservando os anteriores. API: `/api/v3/roster-snapshots`; fichas/lista incluem `roster_context`. `current_team` permanece nulo até existir evidência suficiente.

## Verificação

30 testes backend e 5 frontend aprovados; build React aprovado. Regressões cobrem homônimos, preservação de histórico, fontes desconhecidas, duplicidade de posição e ausência de ratings fictícios. Conferidos no navegador com Supabase: elencos, alternância para histórico e ficha de Wizer com saída em maio. Capturas: `docs/wizer-roster-evidence.png` e `docs/roster-snapshots.png`.
