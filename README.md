# LoL Championship Manager — v0.4

Aplicação de scouting com React 19 + TypeScript + Vite + Tailwind, FastAPI e Supabase/PostgreSQL. Os dados competitivos reais ficam separados das futuras carreiras privadas. O importador e o motor Python anteriores foram reaproveitados; SQLite permanece como staging reproduzível. Não há simulador de partidas nesta versão.

## Executar localmente

Requisitos: Python 3.12+ e Node.js compatível com Vite 8 (22.12+; entrega validada em Node 26.12 e Python 3.15). As dependências diretas estão fixadas e os locks foram incluídos.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm.cmd --prefix frontend ci
```

Copie `.env.example` para `.env` e `frontend/.env.example` para `frontend/.env.local`. Preencha URL e **chave publicável** do projeto Supabase em ambos. As configurações locais desta entrega já estão preenchidas; os arquivos de ambiente são ignorados pelo Git. Nunca coloque uma chave secreta ou `service_role` em variável `VITE_*`.

```powershell
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000. O backend serve o build React e consulta o Supabase com a chave publicável, respeitando as políticas RLS existentes. Para desenvolver o frontend, execute `npm.cmd --prefix frontend run dev` em outro terminal: Vite encaminha `/api` para a porta 8000. No macOS/Linux use `.venv/bin/python` e `npm`.

Caso o alias `python` da Microsoft Store esteja indisponível no Windows, use a instalação real de Python para criar o ambiente virtual. Nesta máquina ela fica em `AppData/Local/Python/bin/python.exe`.

## Funcionalidades

- Dashboard com jogadores, equipes, partidas, cobertura, distribuição de Overall e qualidade dos atributos.
- Jogadores com paginação no banco, busca por nickname, filtros por temporada/região/equipe/posição e ordenação.
- Ficha com 12 atributos, estatísticas observadas, champion pool, proficiência por proxy quando há amostra, histórico de avaliações, equipes e fontes.
- Comparação de dois jogadores com atributos, estatísticas, temporadas e champion pools.
- Equipes do CBLOL com jogadores observados e data de corte; não é uma confirmação de contratos/escalação atual.
- Login por e-mail/senha com Supabase Auth. O endpoint privado valida o token no Auth e delega o mesmo token ao banco para aplicar RLS. Contas precisam existir no projeto; não foi criada uma conta de teste remota. Gestão e criação de carreiras ficam para a próxima fase.

**Cobertura consolidada:** 2025 e 2026, com 2026 parcial até 22/07/2026 no conjunto global e 06/06/2026 no CBLOL. Para reproduzir a atualização posterior ao snapshot inicial, siga [a conciliação documentada](docs/VERIFICATION_V04.md). Não representa elencos atuais de novembro. OVR é experimental e só aparece com suporte regional mínimo. Potencial, ADA e DEC permanecem ausentes. Forma é uma variação de proxy recente, não uma previsão.

## Pipeline reproduzível

```powershell
.\.venv\Scripts\python.exe -m backend.download
.\.venv\Scripts\python.exe -m backend.importer data/raw/2025.csv --source-url https://raw.githubusercontent.com/twodotone/finalLOL/192a8783278f7d1fb6e688d5525b702b8bbe6ec1/data/csv/2025_LoL_esports_match_data_from_OraclesElixir.csv --no-ratings
.\.venv\Scripts\python.exe -m backend.importer data/raw/2026.csv --source-url https://raw.githubusercontent.com/twodotone/finalLOL/192a8783278f7d1fb6e688d5525b702b8bbe6ec1/data/csv/2026_LoL_esports_match_data_from_OraclesElixir.csv --no-ratings
.\.venv\Scripts\python.exe -m backend.identity_review
.\.venv\Scripts\python.exe -m backend.ratings
.\.venv\Scripts\python.exe -m backend.sync --prepare
```

Pandas processa CSVs em blocos, preservando vazios e IDs como strings. `--league`, `--season`, `--source-url`, `--retrieved-at`, `--license` e `--aliases arquivo.json` permitem selecionar dados e registrar procedência. Campos ausentes não viram zero. Similaridade de nomes cria uma fila para revisão, sem mesclas automáticas. `config/ratings.json` contém pesos e hiperparâmetros; configure-os antes do recálculo.

O pacote em `data/supabase-import/` mapeia o esquema real existente, com UUIDs determinísticos e constraints de duplicidade. Para aplicar por CLI, configure **somente no ambiente administrativo** `SUPABASE_SERVICE_KEY`, então execute:

```powershell
.\.venv\Scripts\python.exe -m backend.sync --apply
```

O backend público não precisa dessa chave. Também é possível aplicar os lotes pelo conector Supabase autorizado, usando `python -m backend.sync --sql INDICE`, como nesta entrega. O MCP de auditoria continua em modo somente leitura. Migrações e conexões administrativas não devem ser executadas pelo frontend.

Importações novas criam um modelo identificado pelo hash da configuração e dos dados; avaliações de modelos anteriores são preservadas. O modelo só é exibido após verificação de importação concluída. A reimportação usa conflitos naturais/IDs estáveis. Misturar dados manualmente criados com os mesmos IDs de origem requer conciliação prévia; homônimos não são mesclados por suposição.

Para operar exclusivamente sobre o staging local, defina `LCM_STORAGE=sqlite` antes de iniciar o backend. `LCM_DB` seleciona o caminho do SQLite. Não há fallback silencioso para staging quando o Supabase falha.

## Testes e relatórios

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp data/test-local
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -m backend.report
.\.venv\Scripts\python.exe -m backend.audit
```

- [Relatório de implementação](docs/IMPLEMENTATION.md): resultados remotos, verificações e limitações.
- [Auditoria inicial](docs/AUDIT.md), [esquema real](docs/audit/supabase-schema.json), [fontes e licenças](docs/SOURCES.md), [metodologia](docs/METHODOLOGY.md).
- `data/supabase-verification.json`: contagens reais e reimportação amostral verificadas no Supabase.
- `data/report.json` e `data/ratings.csv`: relatório e fichas calculadas a partir do staging.
- [Jogadores do CBLOL](docs/REPORT.md).

API nova: `/api/v3/dashboard`, `/api/v3/filters`, `/api/v3/players?page=1&page_size=30&region=CBLOL&season=2026`, `/api/v3/players/{rating_uuid}`, `/api/v3/compare?left={uuid}&right={uuid}`, `/api/v3/teams`, `/api/v3/me`. Documentação em `/docs`. A API legada `/api/players` permanece apenas para compatibilidade com o protótipo e consulta o staging.

As tabelas existentes e as políticas RLS foram preservadas. Uma proposta de novas views/funções públicas foi recusada pela revisão automática e não foi aplicada; a aplicação usa as tabelas existentes. A migration em `supabase/migrations/` contém apenas índices opcionais e não foi aplicada remotamente. A proposta recusada está identificada em `docs/proposals/` e não é necessária à execução.

O licenciamento de redistribuição dos CSVs do espelho finalLOL não foi confirmado. A entrega é para desenvolvimento e análise; não representa autorização de redistribuição comercial. Projeto independente, sem afiliação com a Riot Games.

## Retratos (piloto)

A lista, ficha, comparação e equipes incluem retratos oficiais quando disponíveis, com avatar de iniciais como fallback. O piloto cobre 17 identidades da base, sendo 8 do histórico CBLOL/LTA Sul. Fonte e contexto aparecem na ficha; a foto não determina a equipe do snapshot. Veja [fontes, cobertura e atualização](docs/PORTRAITS.md). A expansão global ainda está pendente.

## Elencos revisados

A curadoria consolidada de 02/11/2026 cobre oito equipes na Copa, Split 1 e Split 2 (120 vagas históricas), mais nove movimentações, com fontes e datas. Contratos vigentes em novembro ainda não estão integralmente verificados. Veja [pesquisa, cobertura e limitações](docs/VERIFICATION_V04.md). Reimporte com `python -m backend.rosters config/rosters-reviewed.json`; API `/api/v3/roster-snapshots`.

## Primeira entrega v0.4

Novas telas: Elencos por data/competição, Central de transferências e Qualidade. O pipeline inspeciona candidatos antes da ingestão no staging, com hash e procedência. A entrega inicial usava o corte de abril; a consolidação acrescenta 3.643 partidas verificadas e recalcula as avaliações, com corte global de 22/07/2026 e CBLOL de 06/06/2026. Consulte [execução inicial](docs/V04.md) e [consolidação](docs/VERIFICATION_V04.md). [Pull requests](https://github.com/brunopeeeh/lol-championship-manager/pulls) organizadas em etapas encadeadas para revisão.

## Consolidação de 02/11/2026

Instalação limpa, reconstrução do staging, correções de configuração e nova fonte estatística foram auditadas. Consulte [verificação detalhada](docs/VERIFICATION_V04.md) e [estado operacional](docs/CONSOLIDATION_STATUS.md). A curadoria distingue observação em partida, anúncio e movimentação; contratos atuais continuam não verificados.
