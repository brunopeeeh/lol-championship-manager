"""Read-only audit of the existing local application; never connects to Supabase."""
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .db import DB

ROOT = Path(__file__).resolve().parent.parent

def audit():
    with sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True) as c:
        c.row_factory = sqlite3.Row
        count = lambda table: c.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        ratings = [json.loads(row[0]) for row in c.execute('SELECT payload_json FROM ratings_v3')]
        teams = c.execute('SELECT count(DISTINCT team_id) FROM observations_v3').fetchone()[0]
        status = Counter(detail['status'] for r in ratings for detail in r['attribute_details'].values())
        slots = sum(status.values())
        result = {
            'audited_at':datetime.now(timezone.utc).isoformat(),
            'scope':'local SQLite only; Supabase schema and counts NOT verified',
            'players':count('identities_v3'),'teams':teams,'matches':count('games_v3'),
            'observations':count('observations_v3'),'rating_records':len(ratings),
            'cblol_players':len({r['player_id'] for r in ratings if 'CBLOL' in r['regions']}),
            'seasons':sorted({r['season'] for r in ratings}),
            'global_overalls':sum(r['overall'] is not None for r in ratings),
            'overall_distribution':dict(sorted(Counter(str((r['overall']//10)*10)+'–'+str(min(100,(r['overall']//10)*10+9)) for r in ratings if r['overall'] is not None).items())),
            'attribute_counts':dict(status),
            'attribute_percentages':{key:round(value/slots*100,2) for key,value in status.items()},
            'integrity':c.execute('PRAGMA integrity_check').fetchone()[0],
            'foreign_key_errors':[tuple(row) for row in c.execute('PRAGMA foreign_key_check')],
            'source_import_attempts':count('sources_v3'),
            'latest_evidence_date':c.execute('SELECT max(date) FROM games_v3').fetchone()[0],
            'secrets_audit':'No values collected; connection env names and project env-file presence were checked separately.',
        }
    files = sorted(p for folder in ('backend','frontend','tests') for p in (ROOT/folder).rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.js','.html','.css','.ts','.tsx','.json'})
    files += [ROOT/name for name in ('README.md','requirements.txt','requirements-lock.txt','.gitignore') if (ROOT/name).exists()]
    result['source_inventory'] = [{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,
                                  'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    target = ROOT/'data'/'local_audit.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('players','teams','matches','rating_records','cblol_players','attribute_percentages','overall_distribution','integrity')},ensure_ascii=False))
    return result

if __name__=='__main__':
    audit()
