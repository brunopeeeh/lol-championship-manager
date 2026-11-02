"""Inspect candidate match CSVs before ingestion. Never publishes ratings or remote data."""
import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from . import db
from .importer import normalize_row, load_csv

ROOT=Path(__file__).resolve().parent.parent
REPORTS=ROOT/'data'/'update-candidates'


def list_candidates():
    if not REPORTS.exists():return []
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(REPORTS.glob('*.json'))]


def inspect(path, source_url, license='unknown', season=None):
    if urlparse(source_url).scheme != 'https': raise ValueError('Supply the original HTTPS source URL')
    path=Path(path);sha=hashlib.sha256(path.read_bytes()).hexdigest()
    counts=Counter();dates=[];players=set();keys=set();regions=Counter()
    with sqlite3.connect(db.DB.resolve().as_uri()+'?mode=ro',uri=True) as connection:
        cutoff=connection.execute('SELECT MAX(date) FROM games_v3').fetchone()[0]
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            headers={h.strip().lower() for h in reader.fieldnames or []}
            if not headers.intersection({'gameid','game_id'}) or not headers.intersection({'player','playername'}):
                raise ValueError('Per-match player CSV required; aggregates cannot refresh match ratings')
            for raw in reader:
                counts['rows']+=1
                row,reason=normalize_row(raw,None)
                if reason:counts[reason]+=1;continue
                if season and row['season'] != season:counts['other_season']+=1;continue
                key=(row['game_id'],row['player_id'])
                dates.append(row['date']);players.add(row['player_id']);regions[row['league']]+=1
                counts['valid_rows']+=1
                if key in keys:
                    counts['repeated_candidate_key']+=1
                    continue
                keys.add(key)
                existing=connection.execute('SELECT 1 FROM observations_v3 WHERE game_id=? AND player_id=?',key).fetchone()
                counts['existing_keys' if existing else 'new_keys']+=1
                if cutoff and row['date'] > cutoff:counts['rows_after_current_cutoff']+=1
    return {'sha256':sha,'filename':path.name,'source_url':source_url,'license':license,
        'inspected_at':datetime.now(timezone.utc).isoformat(),'scope':'sqlite_staging',
        'status':'inspected_only','current_cutoff':cutoff,'date_from':min(dates,default=None),
        'date_to':max(dates,default=None),'players':len(players),'leagues':dict(regions),'counts':dict(counts),
        'note':'Existing keys are not necessarily identical rows; the importer independently checks conflicts. No ratings recalculated or Supabase writes.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv',type=Path);parser.add_argument('--source-url',required=True)
    parser.add_argument('--license',default='unknown; redistribution not validated')
    parser.add_argument('--season',type=int);parser.add_argument('--expected-sha256')
    parser.add_argument('--apply-staging',action='store_true')
    args=parser.parse_args()
    report=inspect(args.csv,args.source_url,args.license,args.season)
    if args.expected_sha256 and report['sha256'] != args.expected_sha256:
        raise ValueError('SHA-256 mismatch; nothing imported')
    if args.apply_staging:
        if not args.expected_sha256:raise ValueError('--apply-staging requires the reviewed --expected-sha256')
        report['import_counts']=load_csv(args.csv,season=args.season,source_url=args.source_url,license=args.license)
        report['status']='imported_staging_only'
    REPORTS.mkdir(parents=True,exist_ok=True)
    (REPORTS/(report['sha256']+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
