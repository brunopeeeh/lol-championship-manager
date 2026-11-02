"""Scouting read API. Supabase reads use only the publishable key and existing RLS."""
import json
import math
from collections import Counter
from typing import Literal
from fastapi import APIRouter, HTTPException, Query, Header
from . import db
from .settings import storage
from .supabase_client import request, select, DatabaseUnavailable
from .portraits import load_catalog,portrait_for
from .rosters import load_catalog as load_rosters, context_for
from .identities import load_aliases

router=APIRouter(prefix='/api/v3')
SUMMARY=('id','player_id','name','team','team_id','region','season','split','position','overall','potential','confidence','games','date_to')

def remote_model():
    models=select('rating_models',{'select':'id,version,config,created_at','config->>import_complete':'eq.true','order':'created_at.desc,id','limit':1})
    return models[0] if models else None

def local_rows():
    with db.connect() as c:
        return [json.loads(r[0]) for r in c.execute('SELECT payload_json FROM ratings_v3')]

def decode_remote(row):
    payload=dict(row['provenance'])
    payload.update(id=row['id'],player_id=row['player_id'],overall=row['overall'])
    return payload

def list_records(page=1,page_size=30,region=None,position=None,season=None,team=None,q='',sort='overall',direction='desc'):
    sort_key={'overall':'overall','name':'name','games':'games','confidence':'confidence'}[sort]
    if storage()=='supabase':
        model=remote_model()
        if not model:
            return {'items':[],'total':0,'page':page,'page_size':page_size,'storage':'supabase'}
        order={'name':'provenance->>name','games':'sample_games'}.get(sort,sort)
        params={'select':'id,player_id,overall,provenance','model_id':'eq.'+model['id'],
                'order':f'{order}.{direction}.nullslast,id.asc','limit':page_size,'offset':(page-1)*page_size}
        for field,value in [('season',season),('position',position.upper() if position else None),
                            ('provenance->>region',region),('provenance->>team_id',team)]:
            if value is not None and value!='': params[field]='eq.'+str(value)
        if q: params['provenance->>name']='ilike.*'+q.replace('*','').replace('%','')+'*'
        response=request('GET','/rest/v1/player_ratings',params=params,headers={'Prefer':'count=exact'})
        total=int(response.headers.get('content-range','0/0').rsplit('/',1)[-1])
        rows=[decode_remote(r) for r in response.json()]
    else:
        where=[];args=[]
        for key,value in [('region',region),('position',position),('season',season),('team_id',team)]:
            if value is not None and value!='':
                where.append(f"json_extract(payload_json,'$.{key}')=?");args.append(value)
        if q:
            where.append("lower(json_extract(payload_json,'$.name')) LIKE ? ESCAPE '\\'")
            args.append('%'+q.lower().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
        clause=' WHERE '+' AND '.join(where) if where else ''
        with db.connect() as c:
            total=c.execute('SELECT count(*) FROM ratings_v3'+clause,args).fetchone()[0]
            rows=[json.loads(r[0]) for r in c.execute('SELECT payload_json FROM ratings_v3'+clause+
                 f" ORDER BY json_extract(payload_json,'$.{sort_key}') {direction.upper()} NULLS LAST,id ASC LIMIT ? OFFSET ?",
                 [*args,page_size,(page-1)*page_size])]
    catalog=load_catalog(); rosters=load_rosters()
    return {'items':[{**{k:r.get(k) for k in SUMMARY},'portrait':portrait_for(r['player_id'],catalog=catalog),
                     'roster_context':context_for(r['player_id'],rosters)} for r in rows],
            'total':total,'page':page,'page_size':page_size,'storage':storage()}

@router.get('/players')
def players(page:int=Query(1,ge=1),page_size:int=Query(30,ge=1,le=100),region:str|None=None,
            position:Literal['top','jungle','mid','adc','support']|None=None,season:int|None=None,
            team:str|None=None,q:str=Query('',max_length=100),sort:Literal['overall','name','games','confidence']='overall',
            direction:Literal['asc','desc']='desc'):
    return list_records(page,page_size,region,position,season,team,q,sort,direction)

@router.get('/filters')
def filters():
    if storage()=='supabase':
        model=remote_model()
        return {**(model['config'].get('filters',{}) if model else {'regions':[],'seasons':[],'teams':[]}), 'storage':'supabase'}
    rows=local_rows()
    return {'regions':sorted({r['region'] for r in rows}),'seasons':sorted({r['season'] for r in rows},reverse=True),
            'teams':sorted({r['team_id']: {'id':r['team_id'],'name':r['team'],'region':r['region']} for r in rows}.values(),key=lambda r:r['name']), 'storage':'sqlite'}

@router.get('/dashboard')
def dashboard():
    if storage()=='supabase':
        model=remote_model()
        if not model:
            return {'storage':'supabase','players':0,'teams':0,'matches':0,'ratings':0,'regions':[],
                    'global_overalls':0,'distribution':[],'attribute_status':{},'calibration_status':'sem dados'}
        return {**model['config']['report'],'storage':'supabase','model':model['version']}
    rows=local_rows()
    with db.connect() as c:
        counts={'players':len({r['player_id'] for r in rows}),'matches':c.execute('SELECT count(*) FROM games_v3').fetchone()[0]}
        counts['teams']=c.execute('SELECT count(DISTINCT team_id) FROM observations_v3').fetchone()[0]
    return {**counts,'storage':'sqlite','ratings':len(rows),'global_overalls':sum(r['overall'] is not None for r in rows),
            'regions':sorted({r['region'] for r in rows}),'data_through':max((r['date_to'] for r in rows),default=None),
            'distribution':[{'from':n,'to':min(n+9,100),'count':sum(r['overall'] is not None and n<=r['overall']<=min(n+9,100) for r in rows)} for n in range(0,101,10)],
            'attribute_status':dict(Counter(d['status'] for r in rows for d in r['attribute_details'].values())),
            'calibration_status':'experimental'}

@router.get('/players/{rating_id:path}')
def detail(rating_id:str):
    if storage()=='supabase':
        try:
            import uuid
            uuid.UUID(rating_id)
        except ValueError:
            raise HTTPException(404,'Ficha não encontrada')
        approved=select('rating_models',{'select':'id','config->>import_complete':'eq.true','limit':200})
        if not approved:raise HTTPException(404,'Ficha não encontrada')
        model_filter='in.('+','.join(m['id'] for m in approved)+')'
        records=select('player_ratings',{'id':'eq.'+rating_id,'model_id':model_filter,'select':'id,player_id,overall,provenance'})
        if not records: raise HTTPException(404,'Ficha não encontrada')
        r=decode_remote(records[0])
        r['portrait']=portrait_for(r['player_id'])
        r['roster_context']=context_for(r['player_id'])
        histories=select('player_ratings',{'player_id':'eq.'+r['player_id'],'select':'id,season,position,overall,confidence,evaluated_at,model_id',
                                        'model_id':model_filter,'order':'season.asc,evaluated_at.asc','limit':200})
        r['rating_history']=histories
        career=select('rosters',{'player_id':'eq.'+r['player_id'],
              'start_date':'lte.'+str(r['season'])+'-12-31','select':'start_date,end_date,teams(name)',
              'order':'start_date.asc','limit':200})
        r['career']=[{'team':x['teams']['name'],'from':x['start_date'],'to':x['end_date']} for x in career if x.get('teams')]
        return r
    with db.connect() as c:
        row=c.execute('SELECT payload_json FROM ratings_v3 WHERE id=?',(rating_id,)).fetchone()
        if not row: raise HTTPException(404,'Ficha não encontrada')
        r=json.loads(row[0])
        r['portrait']=portrait_for(r['player_id'])
        r['roster_context']=context_for(r['player_id'])
        r['rating_history']=[{k:h.get(k) for k in ('season','position','overall','confidence','method')} for h in local_rows() if h['player_id']==r['player_id']]
        members=[r['player_id'],*[key for key,value in load_aliases().items() if value['canonical_id']==r['player_id']]]
        placeholders=','.join('?' for _ in members)
        r['career']=[dict(x) for x in c.execute(f'''SELECT o.team,MIN(g.date) AS "from",MAX(g.date) AS "to"
            FROM observations_v3 o JOIN games_v3 g ON g.id=o.game_id WHERE o.player_id IN ({placeholders}) AND g.season<=?
            GROUP BY g.season,o.team ORDER BY MIN(g.date)''',(*members,r['season']))]
        r['sources']=[dict(x) for x in c.execute(f'''SELECT DISTINCT s.url,s.filename,s.sha256,s.retrieved_at,s.license
          FROM sources_v3 s JOIN evidence_v3 e ON e.source_id=s.id JOIN games_v3 g ON g.id=e.game_id
          WHERE e.player_id IN ({placeholders}) AND g.season<=?''',(*members,r['season']))]
        if 'champion_pool' not in r:
            r['champion_pool']=[dict(x) for x in c.execute('''SELECT o.champion, count(*) games,
              SUM(o.result) wins FROM observations_v3 o JOIN games_v3 g ON g.id=o.game_id
              WHERE o.player_id=? AND g.season=? AND o.champion IS NOT NULL GROUP BY o.champion ORDER BY games DESC,o.champion''',(r['player_id'],r['season']))]
        return r

@router.get('/compare')
def compare(left:str,right:str):
    return {'left':detail(left),'right':detail(right),'warning':'Comparação experimental. Considere temporada, cobertura, adversários e incerteza regional.'}

@router.get('/teams')
def teams(region:str|None='CBLOL',season:int|None=None):
    first=list_records(1,100,region=region,season=season,sort='games')
    records=first['items']
    for page in range(2,math.ceil(first['total']/100)+1):
        records.extend(list_records(page,100,region=region,season=season,sort='games')['items'])
    current={}
    for r in sorted(records,key=lambda r:(r['season'],r['date_to'])):
        current[r['player_id']]=r
    grouped={}
    for r in current.values():grouped.setdefault(r['team_id'],[]).append(r)
    order={'top':0,'jungle':1,'mid':2,'adc':3,'support':4}
    return [{'id':key,'name':items[0]['team'],'region':items[0]['region'],
             'players':sorted(items,key=lambda r:(order[r['position']],r['name'])),
             'as_of':max(r['date_to'] for r in items)} for key,items in sorted(grouped.items(),key=lambda x:x[1][0]['team'])]

@router.get('/roster-snapshots')
def roster_snapshots():
    data=load_rosters(); portraits=load_catalog()
    snapshots=[]
    for snapshot in data['snapshots']:
        teams=[]
        for team in snapshot['teams']:
            players=[]
            for player in team['players']:
                context=context_for(player.get('player_id') or '',data)
                # Subsequent departures annotate the historical quintet, never erase it.
                later=[e for e in context['events'] if e['team']==team['name'] and e['reported_date']>snapshot['reference_date']]
                players.append({**player,'portrait':portrait_for(player.get('player_id') or '',catalog=portraits),
                                'later_events':later,'overall':None,'games':None})
            teams.append({**team,'players':players})
        snapshots.append({**snapshot,'teams':teams})
    return {**data,'snapshots':snapshots,'current_rosters_verified':False,
            'warning':'Elencos com data de referência. Contratos atuais não verificados; o corte estatístico depende da liga e aparece em Qualidade.'}

@router.get('/me')
def me(authorization:str|None=Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401,'Entre com sua conta para acessar suas carreiras')
    token=authorization[7:]
    try:
        user=request('GET','/auth/v1/user',token=token).json()
    except DatabaseUnavailable:
        raise HTTPException(401,'Sessão inválida ou expirada')
    saves=select('game_saves',{'select':'id,name,season,game_date,updated_at','order':'updated_at.desc','limit':50},token=token)
    return {'user_id':user['id'],'email':user.get('email'),'saves':saves}
