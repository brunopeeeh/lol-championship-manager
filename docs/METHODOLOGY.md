# Modelo de ratings v0.3 — experimental

> As fórmulas iniciais abaixo descrevem a base v0.3.0. A seção “Evolução do motor v0.3.1” ao final documenta os parâmetros ativos, força 12, split recente e adversários. O relatório de implementação contém a validação atual (23 Pytest + 4 Vitest).

As estatísticas de partida são observadas. **Nenhum dos 12 conceitos de habilidade é medido diretamente** por esses CSVs. Atributos disponíveis são marcados `estimated`; ausentes são `unavailable` com valor `null`. As médias estatísticas da ficha são mostradas separadamente com contagens. Não há fallback de atributo ausente para 70 ou zero.

## Proxies

| Código | Proxy e pesos internos | Limite de interpretação |
|---|---|---|
| MEC | DPM 50%, participação no dano 50% | Recursos, campeão e equipe confundem mecânica |
| LAN | gold diff 15: 40%, CS diff 10: 30%, XP diff 15: 30% | Campos realmente ausentes não são imputados |
| AGR | kills/min 60%, participação em kills 40% | Estilo; peso zero no Overall |
| SOB | mortes/min com sinal invertido | Função de engage pode ser penalizada |
| MAC | participação em kills | Proxy fraco de atuação coletiva, não conhecimento de mapa |
| VIS | wards/min 55%, wards removidas/min 45% | Não mede utilidade/localização das wards |
| OBJ | dano a torres/min | Proxy restrito; não é controle de dragões/smite |
| TF | DPM 50%, participação em kills 50% | Sem segmentação de lutas; correlação com MEC/MAC |
| CON | desvio padrão invertido do DPM normalizado | Mínimo 8 observações; estabilidade não garante qualidade |
| VER | entropia de campeões usados | Mínimo 10 picks; diversidade não comprova domínio |
| ADA | indisponível | Exige avaliação de adaptação por patch/contexto |
| DEC | indisponível | Exige dados de decisões/timeline/revisão humana |

Componentes disponíveis de cada proxy são renormalizados; cobertura é informada, e componentes ausentes reduzem confiança. CON e VER exigem ao menos três pares com mesma posição, temporada e região da última equipe. Sua confiança usa o número de observações originais, não apenas o resumo calculado. A entropia ainda tem viés por tamanho de amostra; não é uma nota de champion mastery.

## Normalização e híbrido

1. Cada estatística é normalizada em z-score por posição, liga, temporada e patch. São exigidas 20 observações e desvio não nulo; fallback é a mesma posição/liga/temporada sem patch. Não há fallback cruzando posições ou temporadas. Valores z são limitados a ±3.
2. Cada atributo combina as médias dos componentes disponíveis. O suporte é a menor contagem entre esses componentes: jogos sem métrica não aumentam esse suporte.
3. Histórico usa somente temporadas anteriores do mesmo ID e posição, até 40 jogos de peso por temporada e decaimento `0.5^(diferença de anos)`.
4. Com histórico, o peso atual é `n/(n+20)`; sem histórico, a estimativa é apenas atual. Para evitar atribuição fictícia, um atributo ausente na temporada atual não é ressuscitado do histórico.
5. A estimativa `70 + 10*z_híbrido` é suavizada para 70 usando `suporte/(suporte+20)`, depois recebe o ajuste regional e é limitada a 1–100. **70, 10 e 20 são parâmetros de design**, não parâmetros validados por especialistas.

Benchmarks usam a temporada inteira disponível; são snapshots descritivos ao término do corte observado, não previsões retrospectivas sem vazamento dentro da temporada. Atualizações podem alterar fichas da temporada atual. Fichas históricas não usam temporadas futuras, com teste explícito.

## Calibração entre regiões

A força média de cada liga **não é assumida igual**. A liga de origem da equipe é a mais frequente nas suas observações domésticas da temporada (mesmo teamid). LTA S → CBLOL, LTA N → LCS; original preservado. Torneios internacionais e copas identificadas não definem liga de origem. Não há transferência automática da calibração de uma primeira divisão para sua academia.

Resultados internacionais válidos precisam ter 5 jogadores e resultado consistente por lado, duas equipes e resultados complementares. O ajuste estima efeitos regionais por regressão logística com penalização L2 de força 4: `P(A vence B) = sigmoid(efeito_A - efeito_B)`. Temporadas anteriores recebem peso 0.5 por ano. Otimização determinística: 800 passos de gradiente. Offset = 8 × efeito, sem bônus manuais por liga. Registra-se suporte e grafo de confrontos.

Overall mundial só é publicado para região ligada ao componente da LCK e com pelo menos 5 jogos internacionais observados. Onde isso falta, `overall = null` e `context_overall` pode mostrar apenas comparação contextual. A calibração doméstica/internacional não estima força específica de cada adversário nem separa qualidade de elenco e efeito regional. Ligas com poucos representantes, mudanças de formato e transferências geram grande incerteza. O corte de cinco jogos é apenas operacional, não evidência de precisão.

Mesmo com conexão, o resultado é **global experimental, não ranking mundial validado**. Seleção para torneios, dependência entre jogos da mesma série, campeão, lado e adversários continuam confundidos. A transferência de efeitos de vitórias de equipes para habilidades individuais é uma hipótese forte. Não há intervalo de confiança frequentista ou posterior probabilístico: o indicador exibido é um índice de evidência.

## Overall e confiança

Pesos por posição (cada linha soma 100):

| Posição | MEC | LAN | AGR | SOB | MAC | VIS | OBJ | TF | CON | VER | ADA | DEC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TOP |18|20|0|12|12|2|5|18|7|3|1|2|
| JUNGLE |10|3|0|10|22|8|18|13|8|3|2|3|
| MID |18|18|0|9|16|4|5|18|7|3|1|1|
| ADC |23|20|0|14|7|1|3|21|6|3|1|1|
| SUPPORT |6|7|0|9|22|20|12|13|6|2|1|2|

Overall é média ponderada apenas dos atributos disponíveis, renormalizando pesos; exige no mínimo 60 pontos de peso observado. Portanto compare também as ausências: dois Overall com cobertura diferente não são equivalentes. AGR não aumenta Overall. Os pesos são hipóteses de design.

Índice de confiança = `n_efetivo/(n_efetivo+20) × cobertura_ponderada × (0.5 + 0.5*confiança_regional)`. `n_efetivo` é a média das contagens dos atributos ponderáveis disponíveis. Confiança regional = `min(0.8, jogos_internacionais/(jogos_internacionais+30))`. O índice não mede a validade dos proxies nem a probabilidade de um jogador ser melhor.

## Forma, potencial e identidade

Forma é a diferença entre o z-score médio de DPM/KP dos últimos 10 jogos e o período anterior, em pontos de proxy (×10). Requer ao menos 10 jogos anteriores, 8 observações recentes e 10 anteriores para cada componente utilizado. Não prevê melhora futura. Não é multiplicador oculto do Overall. Potencial fica sempre `null`: estes dados não suportam uma previsão defensável de teto de carreira.

Transferências são reconstruídas por sequência de teamid e datas; períodos observados não equivalem a contratos. Identidades com IDs confiáveis são mantidas entre equipes. Nomes fallback têm confiança de identidade limitada e podem conflitar com homônimos. Renomes com mesmo ID preservam identidade; IDs diferentes precisam de aliases explícitos revisados.

## Verificações desta entrega

14 testes automatizados passaram. Painel verificado no Chrome com base real: lista CBLOL 2026, ficha Robo com histórico LOUD → paiN Gaming, atributos estimados, ADA/DEC/potencial/forma ausentes quando não suportados e comparação Robo × Wizer. A integridade SQLite e as chaves estrangeiras foram verificadas pelo relatório. Os resultados são descritivos, sem validação externa de poder preditivo.

## Evolução do motor v0.3.1

O modelo ativo tem parâmetros versionados em `config/ratings.json`. A força inicial de suavização agora é 12 (configurável); a matriz de pesos foi preservada. O hash da configuração e do snapshot diferencia modelos no Supabase e preserva avaliações anteriores.

O desempenho recente usa observações desde o início do último split doméstico identificado na temporada, incluindo eventos posteriores ao corte. Quando o arquivo não informa split, utiliza a temporada disponível e sinaliza ausência de split. Histórico anterior usa apenas observações válidas dos respectivos proxies, com decaimento e limite configuráveis. CON e VER continuam descrevendo estabilidade e diversidade da temporada, não apenas o split.

A correção por adversários usa Elo cronológico de equipes e dos oponentes da mesma posição. Todos começam no mesmo prior 1500; resultados atualizam as referências somente depois da partida. A correção de cada z-score é limitada a ±0,5, com pesos configuráveis de equipe e jogador. O componente individual continua derivado dos resultados da equipe: é um proxy de contexto, não uma medida isolada de habilidade do adversário. Não há modificador por nacionalidade. Sua contribuição é adicional à calibração regional e pode contar parte da força coletiva duas vezes; ainda precisa de validação/ablação externa.

Champion pool registra picks, jogos e resultados observados. A proficiência exibida por posição é um proxy do DPM normalizado suavizado, apenas com pelo menos 8 observações no campeão. A tabela `champion_proficiency` preserva contagens entre posições e mantém `score` ausente para evitar agregar proxies incompatíveis; o snapshot da avaliação guarda o proxy por posição. Não se infere domínio de campeão de poucas vitórias.

A coluna `form` do esquema remoto aceita apenas 1–100; permanece NULL. A forma com sinal, calculada como diferença de desempenho, fica no JSON de proveniência e é exibida explicitamente como variação de proxy. Atributos em colunas inteiras são arredondados; o JSON preserva as estimativas originais. Todo `calibration_status` remoto é `provisional`; mesmo as 681 avaliações com conexão internacional não são declaradas globalmente validadas.

A confiança inclui cobertura, suporte por atributo, calibração regional e redução de qualidade proporcional a partidas parciais. Permanece um índice de evidência, sem interpretação probabilística ou intervalo calibrado. Benchmarking de uma temporada inteira disponível é descritivo: o uso de Elo pré-partida não transforma o conjunto em um backtest sem vazamento dentro da temporada.
