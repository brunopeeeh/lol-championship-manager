"""Deterministic export into the audited Supabase schema; client-side ingestion only.
Use --apply with SUPABASE_SERVICE_KEY in environment, or --sql INDEX for reviewed MCP ingestion.
"""
import argparse
import hashlib
import json
import logging
import math
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID,uuid5
import pandas as pd
from .db import connect
from .ratings import read_rows,home_regions,load_config,ATTRS
from .supabase_client import request

ROOT=Path(__file__).resolve().parent.parent
NS=UUID('c3f7be2d-42af-44bb-a3ca-a7e1b03ecdd0')
TABLES=('regions','teams','players','data_sources','tournaments','matches','player_match_stats','rosters','rating_models','player_ratings','champion_proficiency')

def uid(kind,key):return str(uuid5(NS,kind+':'+str(key)))

def observation_origins(c):
    sources={r['id']:dict(r) for r in c.execute('SELECT * FROM sources_v3')}
    origins={};seasons=defaultdict(set);used=set()
    for row in c.execute('''SELECT e.game_id,e.player_id,e.source_id,g.season FROM evidence_v3 e
        JOIN games_v3 g ON g.id=e.game_id ORDER BY e.source_id'''):
        source=sources[row['source_id']]
        origins.setdefault((row['game_id'],row['player_id']),source)
        seasons[source['sha256']].add(row['season']);used.add(row['source_id'])
    return origins,seasons,[sources[key] for key in sorted(used)]

def build(batch_size=250):
    with connect() as c:
        rows=read_rows(c)
        ratings=[json.loads(r[0]) for r in c.execute('SELECT payload_json FROM ratings_v3 ORDER BY id')]
        origins,source_seasons,source_rows=observation_origins(c)
    config=load_config();homes=home_regions(rows)
    tables={t:{} for t in TABLES}
    digest=hashlib.sha256(json.dumps({'config':config,'sources':sorted({r['sha256'] for r in source_rows}),
        'ratings':ratings},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    model_version='v'+config['version']+'-'+digest[:12];model_id=uid('model',model_version)
    now=datetime.now(timezone.utc).isoformat()
    by_game=defaultdict(list);by_player=defaultdict(list);team_homes=defaultdict(Counter)
    for source in source_rows:
        sha=source['sha256']
        tables['data_sources'][sha]={'id':uid('source',sha),'name':source['filename'],'url':source['url'],
            'license':source['license'],'retrieved_at':source['retrieved_at'],'checksum':sha,
            'metadata':{'provider':'Oracle’s Elixir via finalLOL','snapshot_commit':'192a8783278f7d1fb6e688d5525b702b8bbe6ec1','imported_at':now,'license_status':'unconfirmed'}}
    for r in rows:
        by_game[r['game_id']].append(r);by_player[r['player_id']].append(r)
        region=homes.get((r['team_id'],r['season']))
        if region:team_homes[r['team_id']][region]+=1
    for region in sorted({h for h in homes.values()}):
        tables['regions'][region]={'id':uid('region',region),'code':region,'name':region}
    for r in rows:
        pid=uid('player',r['player_id']);tid=uid('team',r['team_id']);gid=uid('match',r['game_id'])
        home=team_homes[r['team_id']].most_common(1)
        tables['teams'][tid]={'id':tid,'name':r['team'],'slug':'oe-'+hashlib.sha256(r['team_id'].encode()).hexdigest()[:24],
                              'region_id':uid('region',home[0][0]) if home else None}
        tables['players'][pid]={'id':pid,'handle':r['name'],'primary_position':r['position'].upper()}
        tkey=f"{r['league']}|{r['season']}|{r['split']}"
        tables['tournaments'][tkey]={'id':uid('tournament',tkey),'name':r['league'],'season':r['season'],'split':r['split'] or None,
             'external_id':tkey,'region_id':uid('region',homes[(r['team_id'],r['season'])]) if r['league'] not in {'MSI','WCS','WLDS','FST','EWC','LTA','Americas Cup','DCUP','ASIA MASTER','KESPA'} and (r['team_id'],r['season']) in homes else None}
        m=r['metrics'];source=origins.get((r['game_id'],r['player_id']))
        raw={**m,'side':r['side'],'result':r['result'],'external_player_id':r['player_id'],
             'external_team_id':r['team_id'],'source_id':uid('source',source['sha256']) if source else None,
             'source_sha256':source['sha256'] if source else None,'league':r['league'],'season':r['season'],'split':r['split']}
        tables['player_match_stats'][(gid,pid)]={'match_id':gid,'player_id':pid,'team_id':tid,'position':r['position'].upper(),
           'champion':r['champion'],'kills':int(m['kills']) if m.get('kills') is not None else None,
           'deaths':int(m['deaths']) if m.get('deaths') is not None else None,
           'assists':int(m['assists']) if m.get('assists') is not None else None,
           'damage':int(m['damage']) if m.get('damage') is not None else None,'gd15':m.get('gd15'),'xpd15':m.get('xp15'),
           'kill_participation':m.get('kp'),'raw_metrics':raw}
    for gid,game in by_game.items():
        first=game[0];sides={side:{r['team_id'] for r in game if r['side']==side} for side in ('blue','red')}
        if any(len(t)!=1 for t in sides.values()):raise ValueError(f'Inconsistent teams: {gid}')
        winners={r['team_id'] for r in game if r['result']==1}
        source=origins.get((first['game_id'],first['player_id']))
        key=f"{first['league']}|{first['season']}|{first['split']}"
        duration=first['metrics'].get('duration')
        tables['matches'][gid]={'id':uid('match',gid),'external_id':gid,'tournament_id':uid('tournament',key),
          'played_at':first['date'].replace(' ','T')+'Z','patch':first['patch'] or None,
          'duration_seconds':int(duration) if duration else None,'blue_team_id':uid('team',next(iter(sides['blue']))),
          'red_team_id':uid('team',next(iter(sides['red']))),'winner_team_id':uid('team',next(iter(winners))) if len(winners)==1 else None,
          'source':source['url'] if source else None}
    for external,games in by_player.items():
        stints=[]
        for r in games:
            if not stints or stints[-1]['team']!=r['team_id']:
                stints.append({'team':r['team_id'],'start':r['date'][:10],'end':r['date'][:10]})
            stints[-1]['end']=r['date'][:10]
        for s in stints:
            key=f"{external}|{s['team']}|{s['start']}"
            tables['rosters'][key]={'id':uid('roster',key),'player_id':uid('player',external),'team_id':uid('team',s['team']),
                                   'start_date':s['start'],'end_date':s['end']}
    for r in ratings:
        original_id=r['id'];external=r['player_id'];rid=uid('rating',model_version+'|'+original_id)
        provenance={**r,'external_id':original_id,'external_player_id':external,'id':rid,'player_id':uid('player',external),
                    'team_id':uid('team',r['team_id']),'model_version':model_version}
        provenance['sources']=[{'url':s['url'],'filename':s['filename'],'sha256':s['sha256'],
              'license':s['license'],'retrieved_at':s['retrieved_at']} for s in {s['sha256']:s for s in source_rows}.values()
              if any(season<=r['season'] for season in source_seasons[s['sha256']])]
        tables['player_ratings'][rid]={'id':rid,'player_id':uid('player',external),'model_id':model_id,
            'position':r['position'].upper(),'season':r['season'],'evaluated_at':now,
            **{a:round(r['attributes'][a]) if r['attributes'][a] is not None else None for a in ATTRS},
            'overall':r['overall'],'potential':None,'form':None,'sample_games':r['games'],'confidence':r['confidence'],
            'calibration_status':'provisional','provenance':provenance}
        for champion in r.get('champion_pool',[]):
            key=f"{external}|{r['season']}|{champion['champion']}"
            # Aggregate original observations across positions rather than adding per-position proxies.
            picks=[x for x in by_player[external] if x['season']==r['season'] and x['champion']==champion['champion']]
            tables['champion_proficiency'][key]={'id':uid('champion',key),'player_id':uid('player',external),
                'model_id':model_id,'champion':champion['champion'],'season':r['season'],'games':len(picks),'score':None}
    report={'players':len(tables['players']),'teams':len(tables['teams']),'matches':len(tables['matches']),
      'ratings':len(ratings),'global_overalls':sum(r['overall'] is not None for r in ratings),
      'regions':sorted(tables['regions']),'last_import':now,'data_through':max(r['date'] for r in rows),
      'calibration_status':'experimental','model':model_version,
      'cblol_players':len({r['player_id'] for r in ratings if 'CBLOL' in r['regions']}),
      'attribute_status':dict(Counter(d['status'] for r in ratings for d in r['attribute_details'].values())),
      'distribution':[{'from':i,'to':min(100,i+9),'count':sum(r['overall'] is not None and i<=r['overall']<=min(i+9,100) for r in ratings)} for i in range(0,101,10)]}
    filters={'regions':sorted({r['region'] for r in ratings}),'seasons':sorted({r['season'] for r in ratings},reverse=True),
      'teams':sorted({uid('team',r['team_id']):{'id':uid('team',r['team_id']),'name':r['team'],'region':r['region']} for r in ratings}.values(),key=lambda t:t['name'])}
    tables['rating_models'][model_id]={'id':model_id,'version':model_version,'description':'Experimental proxy model; no nationality modifiers; unavailable attributes remain NULL',
         'config':{**config,'snapshot_sha256':digest,'filters':filters,'report':report,'import_complete':False},'created_at':now}
    folder=ROOT/'data'/'supabase-import';folder.mkdir(exist_ok=True)
    batches=[]
    for table in TABLES:
        records=list(tables[table].values())
        for offset in range(0,len(records),batch_size):
            path=folder/f'{len(batches):05d}.json'
            path.write_text(json.dumps(records[offset:offset+batch_size],ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
            batches.append({'table':table,'file':path.name,'rows':min(batch_size,len(records)-offset)})
    manifest={'model_id':model_id,'model_version':model_version,'counts':{t:len(v) for t,v in tables.items()},'report':report,'batches':batches}
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    logging.info(json.dumps({'event':'export_prepared','model':model_version,'counts':manifest['counts'],'batches':len(batches)}))
    return manifest

def sql_batch(index):
    folder=ROOT/'data'/'supabase-import'
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    batch=manifest['batches'][index];records=json.loads((folder/batch['file']).read_text(encoding='utf-8'))
    table=batch['table'];columns=list(records[0]);quoted=','.join('"'+c+'"' for c in columns)
    payload=json.dumps(records,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    if '$lcm$' in payload:raise ValueError('Unsafe delimiter')
    conflict='match_id,player_id' if table=='player_match_stats' else 'id'
    action='DO NOTHING'
    if table=='champion_proficiency': action='DO UPDATE SET games=excluded.games,score=excluded.score,model_id=excluded.model_id'
    return f'INSERT INTO public."{table}" ({quoted}) SELECT {quoted} FROM jsonb_populate_recordset(NULL::public."{table}",$lcm${payload}$lcm$::jsonb) ON CONFLICT ({conflict}) {action};'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--batch-size',type=int,default=250)
    p.add_argument('--sql',type=int);p.add_argument('--apply',action='store_true');a=p.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    if a.prepare:build(a.batch_size)
    if a.sql is not None:print(sql_batch(a.sql));return
    if a.apply:
        folder=ROOT/'data'/'supabase-import';manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        for i,batch in enumerate(manifest['batches']):
            records=json.loads((folder/batch['file']).read_text(encoding='utf-8'))
            conflict='match_id,player_id' if batch['table']=='player_match_stats' else 'id'
            request('POST','/rest/v1/'+batch['table'],params={'on_conflict':conflict},json=records,admin=True,
                headers={'Prefer':'resolution='+('merge-duplicates' if batch['table']=='champion_proficiency' else 'ignore-duplicates')+',return=minimal'})
            logging.info(json.dumps({'event':'batch_imported','batch':i,'table':batch['table'],'rows':len(records)}))
        expected=manifest['counts']['player_ratings']
        check=request('GET','/rest/v1/player_ratings',params={'model_id':'eq.'+manifest['model_id'],'select':'id','limit':1},admin=True,headers={'Prefer':'count=exact'})
        actual=int(check.headers['content-range'].split('/')[-1])
        if actual!=expected:raise RuntimeError(f'Rating verification failed: {actual} != {expected}')
        model=json.loads((folder/next(b['file'] for b in manifest['batches'] if b['table']=='rating_models')).read_text(encoding='utf-8'))[0]
        request('PATCH','/rest/v1/rating_models',params={'id':'eq.'+manifest['model_id']},
                json={'config':{**model['config'],'import_complete':True}},admin=True)
if __name__=='__main__':main()
