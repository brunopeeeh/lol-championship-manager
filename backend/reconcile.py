"""Read-only reconciliation; export only observations from games after the old cutoff."""
import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from .importer import normalize_row


def reconcile(csv_path, baseline, output):
    csv_path=Path(csv_path);output=Path(output)
    with sqlite3.connect(Path(baseline).resolve().as_uri()+'?mode=ro',uri=True) as c:
        c.row_factory=sqlite3.Row
        cutoff=c.execute('SELECT MAX(date) FROM games_v3').fetchone()[0]
        if not cutoff:raise ValueError('A populated baseline is required')
        old={(r['game_id'],r['player_id']):dict(r) for r in c.execute('''SELECT o.*,g.date,g.league,g.season FROM observations_v3 o JOIN games_v3 g ON g.id=o.game_id''')}
    fingerprints={(r['date'],r['league'],r['team'],r['side'],r['position']):r['game_id'] for r in old.values()}
    counts=Counter();differences=Counter();new_games=set();suspect=set();seen=set();leagues=Counter();dates=[]
    with csv_path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        for raw in reader:
            row,reason=normalize_row(raw)
            counts['raw_rows']+=1
            if reason:counts['excluded_'+reason]+=1;continue
            counts['valid_observations']+=1
            key=(row['game_id'],row['player_id']);previous=old.get(key)
            if key in seen:counts['repeated_key']+=1;suspect.add(row['game_id'])
            seen.add(key)
            fingerprint=(row['date'],row['league'],row['team'],row['side'],row['position'])
            collision=fingerprints.get(fingerprint)
            if collision and collision!=row['game_id']:suspect.update([row['game_id'],collision])
            fingerprints[fingerprint]=row['game_id']
            if previous:
                changed=[k for k in ('team_id','team','position','side','champion','result','date','league','season') if previous[k]!=row[k]]
                if json.loads(previous['metrics_json'])!=row['metrics']:changed.append('metrics')
                counts['overlap_changed' if changed else 'overlap_identical']+=1
                differences.update(changed)
            elif row['date']<=cutoff:counts['new_key_before_cutoff']+=1
            else:
                new_games.add(row['game_id']);counts['eligible_observations']+=1;leagues[row['league']]+=1;dates.append(row['date'])
    # Old timestamp corrections can collide with another old game's fingerprint.
    # They remain quarantined because this export never rewrites pre-cutoff games.
    if suspect & new_games:raise ValueError('Possible repeated new games/keys require review: '+','.join(sorted(suspect & new_games)[:10]))
    output.parent.mkdir(parents=True,exist_ok=True)
    # Preserve raw fields and team rows for every selected game. No metric synthesis.
    with csv_path.open(encoding='utf-8-sig',newline='') as f,output.open('w',encoding='utf-8',newline='') as dest:
        reader=csv.DictReader(f);writer=csv.DictWriter(dest,fieldnames=reader.fieldnames);writer.writeheader()
        for raw in reader:
            if raw.get('gameid',raw.get('game_id')) in new_games:writer.writerow(raw)
    return {'mode':'append_after_cutoff_only','baseline_cutoff':cutoff,'counts':dict(counts),
        'changed_fields':dict(differences),'quarantined_old_fingerprint_ids':sorted(suspect),
        'new_games':len(new_games),'leagues_observations':dict(leagues),
        'date_from':min(dates,default=None),'date_to':max(dates,default=None),'source_sha256':hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'note':'Changed overlap retained in baseline; not silently overwritten. Natural fingerprint checks supplement original IDs; not a universal cross-provider deduplicator.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('csv');p.add_argument('--baseline',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();r=reconcile(a.csv,a.baseline,a.output)
    Path(a.output).with_suffix('.reconciliation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False))


if __name__=='__main__':main()
