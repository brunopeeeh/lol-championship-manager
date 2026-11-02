# Estado da consolidação — 02/11/2026

Etapas 1, 3, 4 e 6 do plano executadas; a etapa 5 foi ampliada com cobertura parcial explicitamente declarada. A integração das PRs na `main` aguarda autorização explícita, conforme o item 2.3 do [plano](EXECUTION_PLAN.md). Não foi iniciado simulador.

## Dados ativos

Modelo Supabase `7f0352f2-5b87-508c-9aea-02822b4b61bf`, versão `v0.3.1-58b14bbaa706`, com carga completa verificada antes da ativação. Fonte nova fixa por commit e SHA-256, descrita no [relatório](VERIFICATION_V04.md).

| Verificação remota | Resultado |
| --- | ---: |
| Identidades canônicas com observações | 3.819 |
| Equipes | 607 |
| Partidas | 16.206 |
| Observações por jogador/partida | 162.060 |
| Novas observações da fonte auditada | 36.430 |
| Fichas do modelo ativo | 5.477 |
| Overall global experimental disponível | 795 |
| Champion pools canônicos do modelo ativo | 52.007 |
| Stints canônicos | 6.454 |
| Fichas anteriores preservadas | 4.673 |

São 2025 e 2026 parcial, corte global 22/07/2026; liga CBLOL 06/06/2026. Há 82 identidades no histórico CBLOL/LTA Sul. Os atributos continuam proxies experimentais, com 50.970 valores estimados e 14.754 indisponíveis; potencial, ADA e DEC não foram inventados. Regiões sem conexão estatística suficiente não recebem Overall global.

61 observações foram ligadas aos IDs canônicos revisados de ZekaS e Zoen, preservando o ID recebido do fornecedor em `raw_metrics`. Envy e seu homônimo europeu continuam separados. Cinco stints e dois cadastros de alias permanecem para auditoria; não pertencem às fichas ativas. O candidato `874e062c-5a74-5acf-bea4-10535b9a12d4` foi rejeitado antes da ativação e permanece incompleto. O histórico público das fichas consulta apenas modelos completos.

## Verificação e execução

Instalação independente pelos locks; reconstrução dos dados originais por download, sem copiar `.env`, SQLite, CSVs ou dependências. Consolidação validada com 40 testes Python, 8 frontend e build. Testes HTTP reais conferiram dashboard, filtros, ficha de ZekaS, comparação com Wizer, cronologia e transferências. A tela Qualidade declara o escopo do staging e não certifica o Supabase por inferência. A conferência remota acima foi feita por consultas diretas.

O painel local usa o staging aprovado em `data/manager.db`. O banco anterior está preservado em `data/manager-before-consolidation-20261102.db` e `data/consolidation/original-snapshot.db`. O candidato, exportações e evidências de execução ficam em `data/consolidation/`, ignorado pelo Git. `data/report.json` e `data/ratings.csv` foram gerados pelo pipeline; não são dados de exemplo. Nenhum CSV, SQLite, credencial ou retrato bruto foi enviado ao repositório.

## Reversão

O modelo anterior `4d57fdbf-aee0-5790-abf1-8f3d91955009` continua completo e com 4.673 ratings. Para reverter a seleção, um administrador pode definir somente `config.import_complete=false` no modelo novo; a API volta a selecionar o modelo completo anterior por data. Não excluir fatos para reverter avaliações. Champion pools no PostgreSQL são uma projeção atual sem versionamento completo; as fichas históricas preservam seus pools na proveniência.

Para reverter o staging, pare o backend e restaure a cópia identificada do SQLite, preservando também a versão aprovada. Código de curadoria e ratings são independentes: notícias novas não geram estatísticas ou contratos automaticamente.

## Pendências declaradas

- Merge das PRs #1–#5, após autorização; conferir bases na ordem e a árvore final da `main` após integrar.
- Curadoria cobre oito equipes em três referências e nove movimentações, não toda substituição, reserva, empréstimo ou contrato de novembro.
- 439 observações antigas divergentes, 482 chaves anteriores ao corte e duas colisões antigas seguem em revisão; não foram sobrescritas.
- 2.150 novas observações parciais da LPL; 669 observações novas sem ID do fornecedor usam fallback por nome. Outros possíveis aliases globais continuam sujeitos à revisão, sem fusão por semelhança.
- Licenças de redistribuição dos CSVs e de retratos continuam sem confirmação. Oracle's Elixir retornou 403 e o dataset Hugging Face 401 nesta sessão; restrições não foram contornadas.
- Retratos permanecem um piloto; não houve expansão fictícia de cobertura ou criação de contas de teste remotas.
