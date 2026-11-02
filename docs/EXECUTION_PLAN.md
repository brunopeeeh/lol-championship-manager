# Plano de execução — consolidação da v0.4

## Objetivo

Entregar uma versão reproduzível do projeto publicado, com elencos do CBLOL contextualizados por data e ratings atualizados apenas quando houver partidas novas verificáveis. Não iniciar o simulador.

## 1. Validar as PRs em uma cópia limpa

1. Consultar o estado atual das PRs #1 a #4 e seus commits no GitHub.
2. Criar um checkout isolado dentro do workspace, sem copiar `.env`, banco, CSVs, dependências ou build da pasta original.
3. Conferir cada etapa encadeada: base v0.3, pipeline, APIs e interface. Verificar as dependências entre branches.
4. Instalar dependências pelos locks, executar os testes adequados em cada etapa e construir o frontend final.
5. Validar inicialização sem dados estatísticos, erros de configuração e reconstrução do staging pelo pipeline documentado. Usar configuração local explicitamente fornecida para verificar a leitura do Supabase, sem publicar credenciais.
6. Corrigir falhas nas branches correspondentes e atualizar descrições e evidências das PRs.

**Concluído quando:** checkout independente executa os testes/build; instalação e comportamento sem dados estão documentados; nenhum arquivo local não versionado é necessário sem instrução explícita. Registrar resultados em `docs/VERIFICATION_V04.md`.

## 2. Consolidar as alterações no GitHub

1. Confirmar ausência de conflitos, diffs esperados e verificações aprovadas nos commits finais.
2. Preparar integração na ordem #1 → #2 → #3 → #4; adaptar as bases das PRs conforme o estado real após cada integração.
3. Executar merges somente após autorização explícita do usuário. A autorização existente cobre implementação e abertura de PRs, não merge.
4. Após integração autorizada, conferir a árvore final da `main` e repetir apenas as verificações necessárias para validar o resultado integrado.

**Concluído quando:** `main` contém a árvore revisada e validada, com referências dos commits. Se faltar autorização, manter esta etapa pendente e continuar as pesquisas e revisões independentes.

## 3. Obter uma atualização estatística verificável

1. Reavaliar Oracle's Elixir, espelhos identificáveis e outras fontes que ofereçam observações por partida. Priorizar procedência e cobertura, não apenas a data de publicação do arquivo.
2. Registrar URL, fornecedor, data de coleta, licença conhecida, formato, temporadas, ligas e datas mínima/máxima dos registros.
3. Comparar a cobertura com o corte atual de 10/04/2026. Não tratar agregados por jogador como partidas, nem notícias de transferência como evidência estatística.
4. Armazenar cada candidato separadamente, com hash; executar a inspeção antes da ingestão.
5. Avaliar restrições de acesso sem contorná-las. Se nenhuma fonte posterior estiver disponível, registrar o impedimento e manter o corte anterior explícito.

**Concluído quando:** existe candidato com partidas posteriores ao corte e relatório verificável, ou relatório demonstrando por que a atualização ainda não pode ocorrer. Nunca declarar dados atualizados sem ingestão real.

## 4. Conciliar e atualizar o staging

1. Preservar uma cópia identificada do banco e dos relatórios anteriores; usar um banco candidato isolado para a atualização.
2. Revisar IDs, renomes, equipes, posições, datas, torneios e splits; documentar aliases necessários.
3. Identificar partidas sobrepostas entre fornecedores. Não confiar somente na diferença de IDs para concluir que são jogos distintos.
4. Revisar conflitos de observação e lacunas; preservar nulos e distinguir correção de dado antigo de nova evidência.
5. Importar com hash revisado; verificar integridade, chaves estrangeiras, contagens e cobertura. Reimportar uma amostra para verificar idempotência.
6. Recalcular ratings sob um novo identificador de modelo, preservando os anteriores.
7. Comparar distribuição, confiança, amostras e variações de jogadores do CBLOL e das principais regiões. Investigar mudanças anormais antes de aceitar o novo modelo.

**Concluído quando:** relatório antes/depois explica novos jogos, jogadores, conflitos, nulos, cobertura e alterações de ratings; não há inconsistências não resolvidas que comprometam a publicação.

**Dependência:** ingestão de partidas novas exige candidato aprovado na etapa 3. Revisões do pipeline e da qualidade podem continuar mesmo sem ele.

## 5. Completar a cronologia do CBLOL

1. Revisar as oito equipes por competição de 2026: Copa, Split 1 e Split 2, preservando a nomenclatura da fonte.
2. Levantar titulares, substituições, reservas, entradas, saídas e empréstimos quando houver evidência; incluir os casos Wizer/ZekaS, Keine/Namiru e frosty/Manel.
3. Diferenciar anúncio de elenco, participação efetiva em partida e registro contratual. Uma foto ou ausência de notícia de saída não confirma permanência.
4. Registrar publicação, data efetiva quando disponível, origem e grau de confirmação. Conflitos e homônimos entram em revisão, sem resolução por suposição.
5. Ampliar snapshots/eventos e testes para consultas anteriores e posteriores às mudanças. Só apresentar vínculo atual quando houver suporte suficiente.

**Concluído quando:** cada equipe possui cronologia com cobertura declarada, fontes e pendências visíveis; substituições verificadas aparecem corretamente nas consultas por data. Esta etapa pode ocorrer independentemente da obtenção de CSV novo.

## 6. Publicar os dados aprovados e verificar o painel

1. Conferir novamente o esquema real e a sincronização existente do Supabase antes de preparar os lotes.
2. Usar a carga existente e IDs estáveis para os dados aprovados. Não alterar políticas RLS, permissões ou esquema como efeito colateral.
3. Manter o modelo anterior selecionado até a nova carga estar completa e verificada; só então tornar o novo modelo elegível para leitura.
4. Comparar contagens, amostras, fontes e corte entre staging, Supabase e API. Verificar reimportação amostral e comportamento de falhas.
5. Conferir no navegador lista, filtros, fichas, comparação, elencos, transferências e qualidade. Verificar que a auditoria local não é apresentada como auditoria do banco remoto.
6. Atualizar README, relatório de cobertura e limitações. Registrar mudanças em PRs pequenas, com testes e evidências reais.

**Concluído quando:** o painel reflete a versão aprovada dos dados, com fontes e datas coerentes; rollback para a seleção do modelo anterior está documentado. Se a etapa 3 não produzir dados novos, publicar apenas melhorias de código/curadoria e manter os ratings antigos identificados.

## Ordem operacional

Começar pela etapa 1. A etapa 2 depende de autorização de merge. Pesquisa estatística (3) e cronologia do CBLOL (5) podem avançar sem essa autorização. Atualização de dados (4) depende de evidência nova aprovada. Sincronização (6) depende dos resultados aprovados, sem presumir que todos os fornecedores estarão acessíveis.

## Limites

- Não inventar partidas, contratos, potencial ou forma.
- Não iniciar mecânicas de gerenciamento ou simulação nesta execução.
- Não trocar a arquitetura nem recriar tabelas por conveniência.
- Não sobrescrever o banco original para experimentar uma importação.
- Não fazer merge automaticamente nem publicar segredos ou arquivos de dados sem conferir o escopo da entrega.
