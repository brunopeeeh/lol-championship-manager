"""Generate an auditable coverage report from the database, not hand-entered counts."""
import json
import csv
from collections import Counter
from pathlib import Path
from .db import connect
from .ratings import read_rows

def generate():
    with connect() as c:
        rows = read_rows(c)
        ratings = [json.loads(r[0]) for r in c.execute('SELECT payload_json FROM ratings_v3')]
        sources = [dict(r) for r in c.execute('SELECT * FROM sources_v3')]
        integrity = c.execute('PRAGMA integrity_check').fetchone()[0]
        foreign_keys = [tuple(r) for r in c.execute('PRAGMA foreign_key_check')]
        calibration = {r['season']:json.loads(r['payload_json']) for r in c.execute('SELECT * FROM calibration_v3')}
    report = {'players':len({r['player_id'] for r in rows}),'games':len({r['game_id'] for r in rows}),
      'observations':len(rows),'ratings':len(ratings),'global_overalls':sum(r['overall'] is not None for r in ratings),
      'seasons':sorted({r['season'] for r in rows}),'regions':sorted({v for r in ratings for v in r['regions']}),
      'integrity':integrity,'foreign_key_errors':foreign_keys,'sources':sources,'calibration':calibration,
      'coverage':{str(y):{'players':len({r['player_id'] for r in rows if r['season']==y}),
         'games':len({r['game_id'] for r in rows if r['season']==y}),
         'date_from':min(r['date'] for r in rows if r['season']==y),
         'date_to':max(r['date'] for r in rows if r['season']==y),
         'leagues':dict(Counter(r['league'] for r in rows if r['season']==y))} for y in sorted({r['season'] for r in rows})},
      'cblol':[{k:r[k] for k in ('name','player_id','team','teams','position','season','games','overall','confidence')}
               for r in ratings if 'CBLOL' in r['regions']],
      'missing_attributes':dict(Counter(k for r in ratings for k in r['unobserved_attributes'])),
      'missing_metrics':{k:sum(r['metrics'].get(k) is None for r in rows) for k in sorted({k for r in rows for k in r['metrics']})}}
    target = Path(__file__).resolve().parent.parent/'data'/'report.json'
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    fields = ['name','player_id','team','region','season','position','games','partial_games',
              'overall','context_overall','confidence','potential','form']
    with (target.parent/'ratings.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=fields+list(ratings[0]['attributes'] if ratings else []))
        writer.writeheader()
        for r in ratings:
            writer.writerow({**{k:r.get(k) for k in fields},**r['attributes']})
    lines = ['# Relatório de execução v0.3','',f"Jogadores únicos: {report['players']}. Partidas: {report['games']}. Observações: {len(rows)}.",
      f"Fichas jogador/posição/temporada: {len(ratings)}; Overall global experimental disponível: {report['global_overalls']}.",
      f"Integridade SQLite: {integrity}; erros de chave estrangeira: {len(foreign_keys)}.",'',
      'Contagens, hashes, URLs, métricas ausentes e auditoria detalhada em [data/report.json](../data/report.json).','',
      '## Cobertura','', '| Temporada | Jogadores | Partidas | Primeiro registro | Último registro |','|---|---:|---:|---|---|']
    for y,v in report['coverage'].items():
        lines.append(f"| {y} | {v['players']} | {v['games']} | {v['date_from']} | {v['date_to']} |")
    lines += ['', 'Ligas e regiões observadas: '+', '.join(report['regions'])+'.','',
       'A cobertura de 2026 é parcial. Não representa elencos atuais de novembro. Ausência no arquivo não significa inatividade.',
       '', '## Jogadores identificados no CBLOL / LTA Sul', '',
       'Região CBLOL inclui LTA S em 2025; a liga original é preservada. Equipe exibida é a última observada na temporada.', '',
       '| Jogador | Temporada | Posição | Equipe | Jogos | OVR experimental | Confiança |','|---|---|---|---|---:|---:|---:|']
    for r in report['cblol']:
        lines.append(f"| {r['name']} | {r['season']} | {r['position']} | {r['team']} | {r['games']} | {r['overall'] if r['overall'] is not None else 'N/D'} | {r['confidence']:.1%} |")
    lines += ['', '## Limitações', '',
       'Todos os atributos disponíveis são estimativas por proxies; os valores medidos são as estatísticas de partida. ADA e DEC ficam ausentes. Potencial não é gerado. Forma é uma variação de desempenho observado, não previsão.',
       'A calibração regional usa resultados de equipes classificadas em torneios internacionais: sofre viés de seleção, confunde elenco e região e não possui validação externa. Regiões sem ligação suficiente com LCK não recebem Overall global. A escala 1–100 é uma convenção do modelo.',
       'Partidas parciais são preservadas com lacunas explícitas; conflitos preservam a primeira versão. Datas incompatíveis com a temporada são excluídas conservadoramente. IDs ausentes usam nomes normalizados e podem confundir homônimos. Mudanças de ID e renomes exigem revisão de aliases. Nenhuma ausência é preenchida com zero.',
       'Licença de redistribuição dos CSVs do espelho finalLOL não confirmada; consulte docs/SOURCES.md antes de distribuir os dados.']
    (target.parent.parent/'docs'/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print({k:report[k] for k in ('players','games','observations','ratings','global_overalls','integrity')})

if __name__=='__main__':
    generate()
