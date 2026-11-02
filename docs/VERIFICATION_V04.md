# Consolidação e verificação — 02/11/2026

## Instalação independente

Checkout público em `data/verification-v04`, sem copiar ambiente, dependências, banco, CSVs ou build da pasta original. Dependências instaladas pelos locks em ambiente virtual novo (Python 3.15.1 / Node 26.12.1). O bootstrap Python precisou executar `ensurepip` com as permissões normais da máquina, pois a restrição da sessão interrompeu a primeira tentativa. `npm ci` instalou 126 pacotes e não apontou vulnerabilidades.

| Etapa publicada | Evidência no checkout limpo |
| --- | --- |
| PR #1, `1f40e2d` | 30 testes Python, 5 testes frontend, build aprovado |
| PR #2, `2fc75ce` | 2 testes adicionais do pipeline aprovados |
| PR #3, `757c552` | 3 testes adicionais das APIs aprovados |
| PR #4, `8cfdad7` | Suíte completa: 35 testes Python, 7 frontend e build aprovados |
| Correções de consolidação | 40 testes Python, 8 frontend e build aprovados também no checkout limpo |

Os snapshots originais foram baixados novamente pelos hashes documentados e reconstruíram 12.563 jogos e 4.673 ratings. Não foi copiado o banco original. Inicialização sem dados respondeu 200 para health, lista vazia, dashboard e qualidade. A configuração Supabase ausente retornava 500; foi corrigida e agora responde 503 com mensagem explícita. Credenciais não foram copiadas para o checkout nem publicadas.

## Atualização estatística conciliada

Fonte candidata: [CSV no espelho Heimerdinger](https://github.com/sunrisesineast/heimerdinger/blob/a6fd39443d39467e295f98c67a78280141d77a51/data/raw/2026_LoL_esports_match_data_from_OraclesElixir.csv). Commit `a6fd39443d39467e295f98c67a78280141d77a51`, 50.694.201 bytes, SHA-256 `7fbb37c6cf6c2bac6bd0efb7252e7f9f85d9d298c7411484192a311b07d10bbb`. O repositório atribui a origem a Oracle's Elixir; não é uma confirmação independente de cada partida nem uma licença de redistribuição.

O CSV contém 77.004 linhas e 165 colunas, com último registro em 22/07/2026. Após normalizar os nomes de competições (`AC`/`Americas Cup` e `KESPA CUP`/`KESPA`), a conciliação encontrou 26.819 observações idênticas à base, 439 observações antigas com diferenças e 482 chaves novas anteriores ao corte. Estas duas últimas categorias não foram sobrescritas ou acrescentadas por suposição. Foram selecionados somente jogos posteriores ao corte de 10/04/2026: **3.643 jogos / 36.430 observações**. Duas colisões de fingerprint em jogos antigos (`LOLTMNT02_355631` e `LOLTMNT02_355637`) ficaram registradas para revisão, sem serem usadas como jogos novos.

| Medida | Antes | Candidato aprovado |
| --- | ---: | ---: |
| Identidades | 3.342 | 3.819 conciliadas (3.821 IDs brutos) |
| Partidas | 12.563 | 16.206 |
| Observações | 125.630 | 162.060 |
| Fichas | 4.673 | 5.477 |
| Overalls globais experimentais | 681 | 795 |
| Corte global | 10/04/2026 | 22/07/2026 |
| Corte CBLOL | 05/04/2026 | 06/06/2026 |
| Identidades no histórico CBLOL/LTA Sul | 79 | 82 |

O corte CBLOL refere-se a partidas classificadas como essa liga no CSV. Jogadores dessa região podem ter partidas internacionais posteriores, que aparecem nas fichas com a data real. As 39 regiões do relatório são contextos competitivos normalizados, não países; a cobertura detalhada por liga e temporada está na tela Qualidade e em `data/report.json`.

Integridade SQLite: `ok`; nenhum erro de chave estrangeira. Reimportação de uma amostra de 12 linhas produziu dez duplicatas e nenhuma nova observação. O banco candidato permaneceu com 162.060 observações. A maior variação entre Overalls comparáveis foi de quatro pontos; o relatório detalhado permanece em `data/consolidation/comparison.json`.

Há 2.150 novas observações parciais da LPL e 669 observações novas que usam identificação alternativa por nome por ausência de ID no fornecedor. Não se assume identidade civil verificada nesses casos. A normalização não une homônimos; rótulos como `NL` não foram equiparados automaticamente a outra liga. As fontes continuam com licença de redistribuição não confirmada. Não houve envio de CSV bruto ao GitHub.

O pacote revisado identifica o modelo `v0.3.1-58b14bbaa706` (`7f0352f2-5b87-508c-9aea-02822b4b61bf`). O primeiro candidato `874e062c-5a74-5acf-bea4-10535b9a12d4` foi rejeitado antes da ativação: IDs diferentes dividiam ZekaS e Zoen. A revisão identificou César Berteli França e Enzo Ganino por nome completo e continuidade entre equipes, sem unir os homônimos Envy. Os aliases estão em `config/player-identities.json`; a resolução ocorre na leitura, preservando o staging bruto. A sincronização mantém também `provider_player_id` na evidência. ZekaS reúne 35 jogos em 2026 e 52 em 2025. Os dois registros de alias permanecem no cadastro remoto para preservar referências dos modelos anteriores; não geram fichas no modelo aprovado.

O modelo anterior, `v0.3.1-99004b1371ed`, permanece disponível. O número do motor continua 0.3.1; o hash diferencia o conjunto de dados, não significa que as notas receberam validação externa. Referências da revisão: [ZekaS](https://liquipedia.net/leagueoflegends/Zekas), [Zoen](https://lol.fandom.com/wiki/Zoen_(Enzo_Ganino)), [paiN Academy](https://ensigame.com/teams/lol/pain-gaming-academy).

## Cronologia do CBLOL

Três registros por competição, cada um com oito times e cinco posições: 120 vagas históricas, não 120 pessoas distintas. A Copa usa a primeira escalação observada em partidas, com data e ID do jogo. Split 1 e Split 2 usam anúncios de abertura publicados em 27/03 e 24/07. Nove movimentações revisadas incluem a promoção de Namiru, afastamento de Keine, saída de frosty e atuação de Manel no principal. Promoção não é tratada como contratação ou rescisão.

Envy possui homônimo: o registro da LOUD foi associado por ID de fornecedor observado nas partidas, sem mesclar identidades. Não restaram nomes sem associação na curadoria atual. Isso não comprova todos os contratos de novembro nem cobre toda troca de reserva ou empréstimo. A ausência de notícia de saída continua sem significar permanência.

Fontes novas: [anúncio do Split 1](https://maisesports.com.br/cblol-2026-red-confirma-zynts-como-titular-veja-todas-as-line-ups), [Namiru/Keine](https://www.pichauarena.com.br/lol/pain-gaming-mudanca-cblol/), [entrevista de Manel](https://www.sheepesports.com/pt/articles/it-s-my-time-manel-talks-about-his-cblol-debut-and-fast-growth-at-red/pt), [publicação sobre frosty](https://hubinsider.substack.com/p/cblol-2026-entenda-a-saida-do-frosty). Datas de publicação são preservadas separadamente da data efetiva, quando esta não é verificável. O guia pré-temporada de 05/01 não foi transformado em escalação confirmada, pois continha nomes ainda não confirmados e depois substituídos.

## Reproduzir a seleção

```powershell
python -m backend.download --candidate heimerdinger-2026-a6fd394
python -m backend.reconcile data/candidates/heimerdinger-2026-a6fd394.csv --baseline CAMINHO_DO_SNAPSHOT.db --output data/candidates/jogos-novos.csv
```

Para carregar no banco candidato, defina `LCM_DB` para uma cópia consistente e use o CSV completo, preservando seu hash:

```powershell
python -m backend.importer data/candidates/heimerdinger-2026-a6fd394.csv --season 2026 --after "2026-04-10 11:46:50" --source-url https://raw.githubusercontent.com/sunrisesineast/heimerdinger/a6fd39443d39467e295f98c67a78280141d77a51/data/raw/2026_LoL_esports_match_data_from_OraclesElixir.csv --no-ratings
python -m backend.ratings
```

Não executar esses comandos sobre o banco original para experimentar. Snapshots desta execução estão em `data/consolidation/original-snapshot.db` e `candidate.db`, fora do Git. Novos jogos não autorizam sobrescrever conflitos antigos automaticamente.

## Estado operacional

A sincronização manteve `import_complete=false` até a verificação de contagens e amostras, e o modelo revisado foi então ativado. Permanecem 3.821 cadastros físicos e cinco stints de aliases antigos para preservar a auditoria dos modelos anteriores; o modelo ativo usa 3.819 identidades e 6.454 stints canônicos. Os registros anteriores não foram removidos. Após autorização explícita do usuário em 02/11/2026, as PRs #1–#5 foram integradas na `main`. O arquivo `docs/CONSOLIDATION_STATUS.md` registra os commits e a comparação da árvore final com a versão validada.

O navegador confirmou lista e busca, comparação ZekaS/Wizer (35/22 jogos; Overall 66/65), registros da Copa identificados como observações e nove movimentações com fontes. A conferência HTTP real está em `data/consolidation/api-verification.json`; a captura local em `data/consolidation/painel-v04.png`. As cinco PRs foram fechadas como integradas, sem conflitos. Não havia status checks publicados nos commits aprovados; os resultados desta entrega são de execução local independente. O CodeRabbit informou revisão ignorada nas branches encadeadas, portanto não se declara revisão automática aprovada.
