import pytest
from fastapi.testclient import TestClient
from backend import db
from backend.main import app
from backend.importer import load_csv
from backend.ratings import rebuild
from test_importer import write

def test_api_filters_detail_comparison(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB',tmp_path/'api.db')
    row=dict(gameid='one',playername='<Real name>',playerid='p1',teamname='A',position='mid',
             league='CBLOL',year=2026,date='2026-01-01',side='Blue',gamelength=1800,dpm=500)
    load_csv(write(tmp_path/'one.csv',[row]));rebuild()
    with TestClient(app) as client:
        assert client.get('/api/health').json()['version']=='0.3.0'
        assert client.get('/api/filters').json()['seasons']==[2026]
        records=client.get('/api/players?region=CBLOL&season=2026&team=A&position=mid').json()
        assert len(records)==1 and records[0]['overall'] is None
        key=records[0]['id']
        detail=client.get('/api/players/'+key).json()
        assert detail['sources'][0]['sha256'] and detail['career'][0]['team']=='A'
        assert client.get('/api/compare',params={'left':key,'right':key}).status_code==200
        assert client.get('/api/players?season=2025').json()==[]
        assert client.get('/api/players/missing').status_code==404
        assert client.get('/').status_code==200
        assert client.get('/static/app.js').status_code==200
