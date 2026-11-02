# Auditoria de fontes — 01/11/2026

Atualização de 02/11/2026: consulte [a consolidação e suas evidências](VERIFICATION_V04.md) para o estado posterior a esta entrega inicial.

## Finish-him/esports-data (Hugging Face)

URL: https://huggingface.co/datasets/Finish-him/esports-data

Página, API de metadados, árvore e README retornaram HTTP 401 sem autenticação. Não foi possível verificar acesso atual, revisões, cobertura anual, licença ou integridade. A busca pública indexada exibia um esquema semelhante a Oracle's Elixir, mas esse índice não comprova cobertura 2025/2026. Nenhum dado dessa fonte entrou na base. Não foi presumido que a fonte inexista nem solicitado token pessoal.

## twodotone/finalLOL (espelho de Oracle's Elixir)

URL: https://github.com/twodotone/finalLOL

Commit consultado: `192a8783278f7d1fb6e688d5525b702b8bbe6ec1`. API reportou último push em 10/04/2026 às 14:44:22 UTC. Snapshot da árvore, metadados e workflow em `data/audit/`. Há arquivos anuais de 2022–2026 em `data/csv/`. Foram utilizados apenas 2025 e 2026. O CSV 2026 na raiz difere daquele em `data/csv/` (tamanhos 15.251.640 vs 21.720.421 bytes); foi escolhido o arquivo anual da pasta de dados, sem misturar snapshots.

| Arquivo | Bytes esperados no commit | SHA-256 local |
|---|---:|---|
| 2025 | 96.780.579 | c6a82e5e3748f29b5fc64802233541f94a594fc5477aff74e1985dc635f1a907 |
| 2026 | 21.720.421 | 7a35c56d4f08ebcf23d9986cca9cb26f2e897d1659c5f4d5a1c18760c20b40d5 |

Campos: gameid, liga, ano, split, playoffs, data, patch, participante, lado, posição, nome/ID de jogador e equipe, campeão, duração, resultado, K/D/A, dano, visão, ouro e diferenciais aos 10/15/20/25 minutos. Os cabeçalhos diferem entre temporadas; normalização é feita por nome. Linhas de equipe são separadas das de jogador. Alguns campos objetivos são predominantemente de equipe e não foram atribuídos individualmente aos jogadores.

O workflow é disparado por push de CSV ou manualmente e processa modelos; não há garantia de ingestão diária nem atualização até novembro. O prefixo do nome do CSV não garante consistência: 2.470 linhas de jogadores no arquivo 2025 trazem ano 2026 e data 2025 e foram excluídas. Estatísticas parciais da LPL foram preservadas com sinalização. Cobertura efetiva, datas mínima/máxima e nulos estão em `data/report.json`.

**Licenciamento:** API GitHub `license: null`, árvore sem LICENSE e sem declaração verificável de licença dos dados. O nome atribui origem a Oracle's Elixir, mas um espelho público não comprova autorização de redistribuição. Uso nesta entrega é local para análise solicitada; direitos de distribuição/comercialização permanecem pendentes. A procedência é o espelho, não uma validação independente contra cada partida original. Não foram executados scripts do repositório externo.

## gol.gg / Games of Legends

URLs verificadas com HTTP 200:

- https://gol.gg/players/list/season-S15/split-ALL/tournament-ALL/
- https://gol.gg/players/list/season-S16/split-ALL/tournament-ALL/
- https://gol.gg/robots.txt

As páginas S15 e S16 apresentam tabelas de jogadores com jogos, win rate, KDA, CSM/GPM, participação, dano, visão e diferenciais de lane; há filtros por torneio e função. Evidências HTML locais em `data/audit/source-3.txt` e `source-4.txt`. Isso confirma presença de temporadas, não completude de todos os torneios ou uma cadência de atualização. Não foi encontrada declaração verificável de licença aberta ou contrato de API/exportação bulk nas páginas examinadas. Robots não é uma licença de uso dos dados. Sem coleta em massa: não foi usado como segunda amostra estatística nem como preenchimento silencioso de lacunas da LPL.

## Integridade e atualização

A ingestão valida identidade, posição, data, lado e números finitos; preserva os primeiros registros em conflitos e registra suas contagens. Chave de observação = gameid + playerid; também há unicidade gameid + lado + posição. A mesma partida com IDs diferentes entre fornecedores ainda exige conciliação de IDs. O hash comprova reprodução do arquivo baixado, não exatidão dos fatos. SQLite e chaves estrangeiras são verificados pelo relatório. Atualizações novas não são mescladas silenciosamente sobre valores antigos; conflitos precisam de revisão.

## lol.timsevenhuysen.com / Oracle's Elixir

A página do autor foi consultada em 01/11/2026: https://lol.timsevenhuysen.com/. A publicação de 11/08/2026 informa o retorno da cobertura LPL de 2026 com estatísticas ampliadas, após a interrupção mencionada em 27/07/2026. Essa informação demonstra que o snapshot do espelho, encerrado em abril, não deve ser apresentado como a última cobertura disponível do provedor.

A tentativa de obter a página de downloads em `lol.timsevenhuysen.com/tools/downloads/` retornou 404; `oracleselixir.com/tools/downloads` retornou 403 na consulta. Não houve contorno de restrições, nem download ou execução de instaladores. A página do autor não forneceu uma declaração verificável de licença para os CSVs examinados. Foi mantido o snapshot reproduzível, com autoria/origem identificada e licença de redistribuição marcada como não confirmada.

## Revisão de elencos posterior ao corte estatístico

A pesquisa de 01/11/2026 em Mais Esports, Onivia, Games of Legends, LoL Esports, Sheep Esports e outras fontes está em [ROSTERS.md](ROSTERS.md). A curadoria de elencos é independente dos CSVs e não atualiza ratings.
