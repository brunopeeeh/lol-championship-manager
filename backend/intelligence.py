"""v0.4 evidence queries. Dated announcements are not current employment."""
import json
from datetime import date, datetime, timezone
from collections import Counter
from fastapi import APIRouter, Query
from . import db
from .rosters import load_catalog

router = APIRouter(prefix='/api/v4')
KINDS = {'departure_reported':'Saída noticiada', 'join_reported':'Entrada noticiada',
         'loan_reported':'Empréstimo noticiado', 'retirement_reported':'Aposentadoria noticiada',
         'bench_reported':'Reserva noticiada'}


def transfers_view(data, as_of, team=None, q='', kind=None):
    events = [e for e in data['events'] if e['reported_date'] <= as_of.isoformat()
        and (not team or e['team'] == team) and (not q or q.casefold() in e['name'].casefold())
        and (not kind or e['kind'] == kind)]
    return {'items':sorted(events,key=lambda e:(e['reported_date'],e['name']),reverse=True),
        'as_of':as_of.isoformat(), 'sources':data['sources'], 'kinds':KINDS,
        'teams':sorted({e['team'] for e in data['events']}),
        'warning':'Data do anúncio, não necessariamente início ou fim de contrato. Cobertura editorial parcial.'}


def roster_at(data, as_of, competition=None, team=None):
    # Return the latest available announcement per team, not an inferred current five.
    selected={}
    for snap in sorted(data['snapshots'],key=lambda s:(s['reference_date'],s['id'])):
        if snap['reference_date'] > as_of.isoformat() or (competition and snap['competition'] != competition):
            continue
        for entry in snap['teams']:
            if team and entry['name'] != team: continue
            players=[]
            for person in entry['players']:
                events=[e for e in data['events'] if person.get('player_id') and
                    e.get('player_id')==person['player_id'] and e['team']==entry['name'] and
                    snap['reference_date'] < e['reported_date'] <= as_of.isoformat()]
                players.append({**person,'subsequent_events':events})
            selected[entry['name']]={'name':entry['name'],'competition':snap['competition'],
                'reference_date':snap['reference_date'],'players':players,'status':'historical_announcement'}
    return {'items':list(selected.values()),'as_of':as_of.isoformat(),'sources':data['sources'],
        'competitions':sorted({s['competition'] for s in data['snapshots']}),
        'warning':'Último anúncio disponível até a data escolhida. Não reconstrói contratos nem escalação vigente. Saídas posteriores aparecem sem apagar o histórico.'}


@router.get('/transfers')
def transfers(as_of:date=Query(default_factory=date.today),team:str|None=None,
              q:str=Query('',max_length=100),kind:str|None=None):
    return transfers_view(load_catalog(),as_of,team,q,kind)


@router.get('/rosters-at')
def rosters_at(as_of:date=Query(default_factory=date.today),competition:str|None=None,team:str|None=None):
    return roster_at(load_catalog(),as_of,competition,team)


@router.get('/quality')
def quality():
    today=date.today();data=load_catalog()
    with db.connect() as c:
        coverage=[dict(r) for r in c.execute('SELECT season,league,COUNT(*) games,MIN(date) date_from,MAX(date) date_to FROM games_v3 GROUP BY season,league ORDER BY season DESC,league')]
        sources=[dict(r) for r in c.execute('SELECT filename,url,sha256,retrieved_at,license,stats_json FROM sources_v3 ORDER BY id DESC')]
        statuses=Counter();missing=Counter();ratings=0
        for row in c.execute('SELECT payload_json FROM ratings_v3'):
            payload=json.loads(row[0]);ratings+=1
            for key,value in payload['attribute_details'].items():
                statuses[value['status']]+=1
                if value['status']=='unavailable':missing[key]+=1
    for source in sources:source['import_counts']=json.loads(source.pop('stats_json'))
    cutoff=max((r['date_to'][:10] for r in coverage),default=None)
    from .updates import list_candidates
    return {'scope':'sqlite_staging','generated_at':datetime.now(timezone.utc).isoformat(),
        'warning':'Auditoria do staging local. As contagens não certificam sincronização com o Supabase nem atualização dos contratos.',
        'statistics_through':cutoff,'statistics_age_days':(today-date.fromisoformat(cutoff)).days if cutoff else None,
        'coverage':coverage,'sources':sources,'ratings':ratings,'attribute_status':dict(statuses),
        'missing_attributes':dict(missing),'roster_snapshots':len(data['snapshots']),
        'roster_slots':sum(len(t['players']) for s in data['snapshots'] for t in s['teams']),
        'reviewed_events':len(data['events']),'unresolved_identities':data.get('unresolved',[]),
        'current_contracts_verified':False,'update_candidates':list_candidates()}
