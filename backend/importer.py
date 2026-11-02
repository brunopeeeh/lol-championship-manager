"""Strict transactional CSV ingestion; no imputation. First evidence wins conflicts."""
import argparse
import csv
import hashlib
import json
import math
import unicodedata
import logging
import pandas as pd
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .db import init, connect

POSITIONS = {'top':'top','jng':'jungle','jg':'jungle','jungle':'jungle','mid':'mid',
             'middle':'mid','bot':'adc','bottom':'adc','adc':'adc','sup':'support','support':'support'}
LEAGUES = {'cblol':'CBLOL','lck':'LCK','lpl':'LPL','lec':'LEC','lcs':'LCS',
           'lta s':'LTA S','lta n':'LTA N','lta':'LTA','lcp':'LCP',
           'msi':'MSI','worlds':'WCS','wcs':'WCS','fst':'FST','ewc':'EWC','americas cup':'Americas Cup'}
FIELDS = {
 'gd15':('golddiffat15','gdat15'), 'cs10':('csdiffat10','csdat10'),
 'xp15':('xpdiffat15','xpdat15'), 'dpm':('dpm',), 'kp':('kp',),
 'deaths':('deaths',), 'kills':('kills',), 'assists':('assists',),
 'teamkills':('teamkills',), 'wpm':('wpm',), 'wcpm':('wcpm',),
 'dmgshare':('damageshare','dmgshare'), 'goldshare':('earnedgoldshare',),
 'duration':('gamelength',), 'damage':('damagetochampions',),
 'tower_damage':('damagetotowers',), 'wards':('wardsplaced',), 'wardkills':('wardskilled',)}

def source_rows(path,chunk_size=5000):
    # String input preserves empty cells, IDs, zero values and decimal conventions.
    for chunk in pd.read_csv(path,encoding='utf-8-sig',dtype=str,keep_default_na=False,na_filter=False,chunksize=chunk_size):
        yield from chunk.to_dict(orient='records')

def clean(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).split())

def number(value):
    try:
        s = str(value).strip()
        n = float(s.rstrip('%')) / (100 if s.endswith('%') else 1)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None

def normalize_row(row, aliases=None):
    aliases = aliases or {}
    r = {clean(k).lower(): clean(v) for k,v in row.items() if k is not None}
    def alias(kind, value):
        value = clean(value)
        return aliases.get(kind, {}).get(value.casefold(), value)
    pos = POSITIONS.get(r.get('position',r.get('role','')).lower())
    if not pos:
        return None, 'team_or_position'
    if r.get('datacompleteness','').lower() not in ('','complete','partial'):
        return None, 'incomplete'
    name = alias('players', r.get('playername') or r.get('player'))
    team = alias('teams', r.get('teamname') or r.get('team'))
    league = alias('leagues', r.get('league'))
    league = LEAGUES.get(league.casefold(), league.upper())
    year = number(r.get('year') or r.get('season'))
    game = r.get('gameid') or r.get('game_id')
    date = r.get('date','')
    side = r.get('side','').lower()
    if not all((name,team,league,game,date)) or year is None or year != int(year) or side not in ('blue','red'):
        return None, 'missing_identity'
    try:
        parsed = datetime.fromisoformat(date.replace('Z','+00:00'))
        if parsed.year != int(year):
            return None, 'invalid_date'
        date = parsed.replace(tzinfo=None).isoformat(sep=' ')
    except ValueError:
        return None, 'invalid_date'
    metrics = {}
    if r.get('datacompleteness','').lower() == 'partial':
        metrics['_partial'] = 1
    for field, names in FIELDS.items():
        metrics[field] = next((number(r[n]) for n in names if number(r.get(n)) is not None), None)
        if field not in ('gd15','cs10','xp15') and metrics[field] is not None and metrics[field] < 0:
            metrics[field] = None
    for field in ('kp','dmgshare','goldshare'):
        if metrics[field] is not None and not 0 <= metrics[field] <= 1:
            metrics[field] = None
    duration = metrics['duration']
    for target, source in (('dpm','damage'),('wpm','wards'),('wcpm','wardkills')):
        if metrics[target] is None and duration and metrics[source] is not None:
            metrics[target] = metrics[source] * 60 / duration
    if metrics['kp'] is None and metrics['teamkills'] and metrics['kills'] is not None and metrics['assists'] is not None:
        kp = (metrics['kills'] + metrics['assists']) / metrics['teamkills']
        metrics['kp'] = kp if 0 <= kp <= 1 else None
    for target, field in (('deaths_pm','deaths'),('kills_pm','kills'),('tower_pm','tower_damage')):
        metrics[target] = metrics[field]*60/duration if duration and metrics[field] is not None else None
    player_id = alias('player_ids', r.get('playerid')) or 'name:' + name.casefold()
    team_id = alias('team_ids', r.get('teamid')) or 'name:' + team.casefold()
    result = number(r.get('result'))
    return dict(game_id=game, player_id=player_id, name=name, team_id=team_id, team=team,
                position=pos, league=league, season=int(year), date=date, patch=r.get('patch',''),
                split=r.get('split',''), side=side, champion=r.get('champion') or None,
                result=int(result) if result in (0,1) else None, metrics=metrics), None

def load_csv(path, league=None, season=None, *, source_url=None, retrieved_at=None,
             license='unknown; redistribution not validated', aliases=None):
    init()
    path = Path(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    counts = Counter()
    with connect() as c, path.open(encoding='utf-8-sig',newline='') as f:
        cursor = c.execute('INSERT INTO sources_v3(filename,sha256,url,retrieved_at,imported_at,license,stats_json) VALUES(?,?,?,?,?,?,?)',
                           (path.name,sha,source_url or path.resolve().as_uri(),retrieved_at or now,now,license,'{}'))
        source_id = cursor.lastrowid
        reader = csv.DictReader(f)
        headers = {clean(k).lower() for k in reader.fieldnames or []}
        if not ({'gameid','game_id'} & headers) or not ({'player','playername'} & headers):
            raise ValueError('CSV must include gameid/game_id and player/playername; aggregates are not game evidence')
        for raw in source_rows(path):
            counts['rows'] += 1
            r, reason = normalize_row(raw, aliases)
            if reason:
                counts[reason] += 1
                continue
            if (league and r['league'].casefold()!=league.casefold()) or (season and r['season']!=int(season)):
                counts['filtered'] += 1
                continue
            game_values = (r['game_id'],r['season'],r['league'],r['date'],r['patch'],r['split'])
            previous = c.execute('SELECT * FROM games_v3 WHERE id=?',(r['game_id'],)).fetchone()
            if previous and tuple(previous) != game_values:
                counts['game_conflicts'] += 1
                continue
            metrics = json.dumps(r['metrics'],sort_keys=True,allow_nan=False)
            values = (r['game_id'],r['player_id'],r['team_id'],r['team'],r['position'],r['side'],r['champion'],r['result'],metrics)
            old = c.execute('SELECT * FROM observations_v3 WHERE game_id=? AND player_id=?',values[:2]).fetchone()
            if old:
                if tuple(old) != values:
                    counts['conflicts'] += 1
                    continue
                counts['duplicates'] += 1
            else:
                slot = c.execute('SELECT 1 FROM observations_v3 WHERE game_id=? AND side=? AND position=?',
                                 (r['game_id'],r['side'],r['position'])).fetchone()
                if slot:
                    counts['slot_conflicts'] += 1
                    continue
                c.execute('INSERT OR IGNORE INTO identities_v3 VALUES(?,?)',(r['player_id'],r['name']))
                c.execute('INSERT OR IGNORE INTO games_v3 VALUES(?,?,?,?,?,?)',game_values)
                c.execute('INSERT INTO observations_v3 VALUES(?,?,?,?,?,?,?,?,?)',values)
                counts['inserted'] += 1
                if r['player_id'].startswith('name:'):
                    counts['fallback_id'] += 1
            c.execute('INSERT OR IGNORE INTO evidence_v3 VALUES(?,?,?)',(source_id,r['game_id'],r['player_id']))
            if r['metrics'].get('_partial'):
                counts['partial_accepted'] += 1
        c.execute('UPDATE sources_v3 SET stats_json=? WHERE id=?',(json.dumps(dict(counts)),source_id))
    logging.getLogger('lcm.importer').info(json.dumps({'event':'csv_imported','sha256':sha,'counts':dict(counts)}))
    return dict(counts)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('files',nargs='+')
    p.add_argument('--league'); p.add_argument('--season',type=int)
    p.add_argument('--source-url'); p.add_argument('--retrieved-at'); p.add_argument('--aliases')
    p.add_argument('--license',default='unknown; redistribution not validated')
    p.add_argument('--no-ratings',action='store_true')
    a = p.parse_args()
    aliases = json.loads(Path(a.aliases).read_text(encoding='utf-8')) if a.aliases else None
    for path in a.files:
        print(path, load_csv(path,a.league,a.season,source_url=a.source_url,retrieved_at=a.retrieved_at,license=a.license,aliases=aliases))
    if not a.no_ratings:
        from .ratings import rebuild
        print(rebuild())

if __name__ == '__main__':
    main()
