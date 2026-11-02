import json
import pytest
from fastapi.testclient import TestClient
from backend import db
from backend.main import app
from backend.importer import load_csv
from backend.ratings import rebuild,load_config,score_players
from backend.opponents import opponent_context
from backend.sync import uid
from test_importer import write
from test_ratings import fixture_rows

def test_pagination_sort_filters_and_detail(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB',tmp_path/'new-api.db')
    row=dict(gameid='a',playername='Fixture',playerid='p',teamname='Team',position='mid',league='CBLOL',year=2026,date='2026-01-01',side='Blue',gamelength=1800,dpm=500,champion='Ahri')
    load_csv(write(tmp_path/'fixture.csv',[row]));rebuild()
    with TestClient(app) as c:
        page=c.get('/api/v3/players?region=CBLOL&season=2026&page_size=1&sort=name&direction=asc').json()
        assert page['total']==1 and len(page['items'])==1
        assert c.get('/api/v3/players?page=2&page_size=1').json()['items']==[]
        assert c.get('/api/v3/players?page_size=101').status_code==422
        assert c.get('/api/v3/players?sort=untrusted').status_code==422
        assert c.get('/api/v3/players?q=%25').json()['total']==0
        p=c.get('/api/v3/players/'+page['items'][0]['id']).json()
        assert p['champion_pool'][0]['champion']=='Ahri' and p['champion_pool'][0]['score'] is None
        assert p['rating_history'] and p['sources']
        assert c.get('/api/v3/me').status_code==401
        assert c.get('/static/.env.local').status_code==404

def test_remote_failures_are_visible(monkeypatch):
    from backend.supabase_client import DatabaseUnavailable
    monkeypatch.setenv('LCM_STORAGE','supabase')
    def fail(*args,**kwargs):raise DatabaseUnavailable('Sem conexão')
    monkeypatch.setattr('backend.scouting.select',fail)
    with TestClient(app) as c:
        assert c.get('/api/v3/players').status_code==503

def test_config_validation_and_sample_strength(tmp_path):
    config=load_config();config['shrink_strength']=0
    path=tmp_path/'invalid.json';path.write_text(json.dumps(config))
    with pytest.raises(ValueError):load_config(path)
    config=load_config();config['weights']['mid'][2]=5
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):load_config(path)

def test_opponent_strength_is_pre_game_and_order_independent():
    rows=fixture_rows();context=opponent_context(rows)
    first=next(r for r in rows if r['game_id']=='int-2025-0')
    assert context[(first['game_id'],first['player_id'])]['team']==1500
    assert context==opponent_context(list(reversed(rows)))
    second=next(r for r in rows if r['game_id']=='int-2025-1' and r['side']=='red')
    assert context[(second['game_id'],second['player_id'])]['team']>1500
    changed=[dict(r, result=1-r['result']) if r['game_id']=='int-2026-11' else r for r in rows]
    assert opponent_context(changed)==context

def test_ids_are_stable_and_namespaced():
    assert uid('player','OE-1')==uid('player','OE-1')
    assert uid('player','OE-1')!=uid('team','OE-1')

def test_recent_split_and_champion_counts():
    rows=fixture_rows()
    for r in rows:
        if r['league'] not in ('MSI',) and r['date'][8:10]>'12':r['split']='Summer'
    results,_=score_players(rows)
    current=next(r for r in results if r['player_id']=='LCK-3' and r['season']==2026)
    assert current['split']=='Summer' and current['split_games']==12
    assert current['attribute_details']['lan']['games']==12
    assert sum(c['games'] for c in current['champion_pool'])==current['games']

def test_auth_validates_user_and_delegates_the_same_token(monkeypatch):
    from types import SimpleNamespace
    calls=[]
    def user_request(method,path,token=None,**kwargs):
        assert method=='GET' and path=='/auth/v1/user'
        return SimpleNamespace(json=lambda:{'id':'user-'+token,'email':None})
    def private_select(table,params,token=None):
        calls.append((table,token))
        return [{'id':'save-'+token,'name':'Fixture','season':2026}]
    monkeypatch.setattr('backend.scouting.request',user_request)
    monkeypatch.setattr('backend.scouting.select',private_select)
    with TestClient(app) as c:
        one=c.get('/api/v3/me',headers={'Authorization':'Bearer one'}).json()
        two=c.get('/api/v3/me',headers={'Authorization':'Bearer two'}).json()
    assert one['user_id']!=two['user_id']
    assert calls==[('game_saves','one'),('game_saves','two')]

def test_similar_handles_are_reviewed_without_merging():
    from backend.identity_review import candidates
    records=[{'id':'one','name':'Ｆａｋｅｒ'},{'id':'two','name':'faker'},{'id':'three','name':'unrelated'}]
    result=candidates(records)
    assert len(result)==1 and result[0]['similarity']==1
    assert result[0]['action']=='manual_review_only'
    assert len(records)==3

def test_provenance_uses_evidence_not_filename_or_year(tmp_path,monkeypatch):
    from backend.sync import observation_origins
    monkeypatch.setattr(db,'DB',tmp_path/'origins.db')
    row=dict(gameid='one',playername='Fixture',playerid='p1',teamname='A',position='mid',league='CBLOL',year=2026,date='2026-01-01',side='Blue')
    load_csv(write(tmp_path/'arbitrary-name.csv',[row]),source_url='https://example.org/first')
    load_csv(write(tmp_path/'another-snapshot.csv',[{**row,'gameid':'two','date':'2026-02-01'}]),source_url='https://example.org/second')
    with db.connect() as c:origins,seasons,sources=observation_origins(c)
    assert origins[('one','p1')]['url']=='https://example.org/first'
    assert origins[('two','p1')]['url']=='https://example.org/second'
    assert len(sources)==2 and all(value=={2026} for value in seasons.values())
