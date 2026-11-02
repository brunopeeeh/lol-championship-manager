# Retratos dos jogadores — piloto

Foram vinculados 17 retratos oficiais a IDs da base, usando os elencos publicados pelo LoL Esports para paiN Gaming e Vivo Keyd Stars. Destes, 8 correspondem às 79 identidades históricas do CBLOL/LTA Sul. Isso é um piloto, não cobertura completa dos 3.342 jogadores.

Fontes consultadas:

- https://lolesports.com/en-US/teams/pain-gaming
- https://lolesports.com/en-US/teams/vivo-keyd
- https://lol.fandom.com/wiki/Leaguepedia:Copyrights
- API pública https://lol.fandom.com/api.php

A API da Leaguepedia respondeu com retratos para Robo, Wizer e Guigo, porém suas miniaturas padrão incluíam fotos antigas (2017–2019). O esquema público `PlayerImages` foi descoberto, mas a consulta Cargo subsequente retornou `ratelimited`. Essa coleta foi interrompida, sem contorno ou repetição agressiva. As imagens da wiki não foram associadas automaticamente ao aplicativo.

O catálogo `data/player-portraits.json` registra ID, handle, fonte, URL oficial da imagem, data de consulta, método de associação e status de direitos. A associação exige nickname normalizado exato e único na base; homônimos são separados para revisão. Não há reconhecimento facial. A associação por handle ainda requer revisão se o nickname tiver sido reutilizado por outra pessoa em épocas diferentes.

A foto não define a equipe/temporada do jogador. Os elencos oficiais consultados são mais recentes que as estatísticas de abril de 2026. Por isso, a ficha sinaliza retrato de arquivo e pode apresentar uma camisa diferente, preservando a equipe dos dados competitivos.

As imagens permanecem no CDN oficial, sem download ou republicação local. A interface usa carregamento sob demanda, tamanho de miniatura, fonte na ficha e avatar de iniciais quando não há foto confirmada ou o carregamento falha. Nenhuma foto sintética foi criada. Direitos continuam com os titulares; a disponibilidade de uma URL pública não confirma licença de redistribuição/comercialização.

A atualização não criou tabelas, alterou RLS ou modificou ratings no Supabase. O catálogo local acompanha o backend e usa os mesmos UUIDs determinísticos da importação. Para hospedar imagens no Supabase Storage futuramente, primeiro devem ser confirmados os direitos e a política de acesso.

## Atualizar a partir de uma página oficial explícita

```powershell
.\.venv\Scripts\python.exe -m backend.portraits --source https://lolesports.com/en-US/teams/pain-gaming
```

É possível repetir `--source` para outras páginas oficiais previamente verificadas. O importador interrompe acessos restritos ou limitados; não tenta contornar 403/429. Não há descoberta/crawl global automático nesta versão. O catálogo precisa ser expandido com outras equipes e fontes antes de prometer fotos para todos os jogadores.

Validações: 26 testes backend e 4 frontend aprovados; build React aprovado. Há testes específicos para parser, unicidade de identidade, origem e recusa de URLs arbitrárias. Três URLs do piloto retornaram HTTP 200; a exibição também foi conferida no navegador.
