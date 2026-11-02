from datetime import date
from fastapi.testclient import TestClient
from backend.main import app
from backend.intelligence import roster_at,transfers_view
from backend.rosters import load_catalog


def test_timeline_uses_announcements_known_by_date_and_does_not_hide_departures():
    data=load_catalog()
    assert roster_at(data,date(2026,1,1))['items']==[]
    july=roster_at(data,date(2026,7,24),team='Vivo Keyd Stars')['items'][0]
    assert july['players'][0]['name']=='ZekaS'
    assert july['players'][0]['subsequent_events']==[]
    november=roster_at(data,date(2026,11,1),team='Vivo Keyd Stars')['items'][0]
    assert november['players'][0]['subsequent_events'][0]['reported_date']=='2026-10-06'
    assert november['status']=='announced_opening_roster'
    assert roster_at(data,date(2026,11,1),competition='missing')['items']==[]


def test_transfer_filters_do_not_leak_later_announcements():
    data=load_catalog()
    assert transfers_view(data,date(2026,5,27))['items']==[]
    results=transfers_view(data,date(2026,5,28),q='wIzEr')['items']
    assert len(results)==1 and results[0]['name']=='Wizer'
    assert transfers_view(data,date(2026,11,1),kind='join_reported')['items']==[]


def test_endpoints_validate_dates_and_quality_explicitly_audits_staging():
    with TestClient(app) as c:
        assert c.get('/api/v4/rosters-at?as_of=not-a-date').status_code==422
        assert c.get('/api/v4/transfers?as_of=2026-05-27').json()['items']==[]
        assert c.get('/api/v4/transfers').status_code==200
        result=c.get('/api/v4/quality').json()
    assert result['scope']=='sqlite_staging'
    assert result['current_contracts_verified'] is False
    assert 'coverage' in result and 'attribute_status' in result
