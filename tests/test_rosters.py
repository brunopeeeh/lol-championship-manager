import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.rosters import compile_catalog, context_for, load_catalog
from backend.sync import uid


def fixture():
    return {'sources':{'s':{'url':'https://example.org/roster','retrieved_at':'2026-11-01'}},
        'snapshots':[{'reference_date':'2026-07-24','competition':'CBLOL 2026 Split 2',
            'teams':[{'name':'VKS','players':[{'name':'ＺｅｋａＳ','position':'top','source_ids':['s']}]}]}],
        'events':[{'name':'ZekaS','team':'VKS','kind':'departure_reported',
                   'reported_date':'2026-10-06','source_ids':['s']}]}


def test_dated_departure_does_not_erase_snapshot_or_invent_current_employer():
    catalog=compile_catalog(fixture(),[{'id':'oe:one','name':'ZekaS'}])
    context=context_for('oe:one',catalog)
    assert context==context_for(uid('player','oe:one'),catalog)
    assert context['snapshots'][0]['team']=='VKS'
    assert context['events'][0]['reported_date']=='2026-10-06'
    assert context['current_team'] is None and context['current_status']=='not_verified'


def test_homonym_unresolved_and_unknown_source_rejected():
    catalog=compile_catalog(fixture(),[{'id':'a','name':'ZekaS'},{'id':'b','name':'zekas'}])
    assert catalog['unresolved'] and catalog['events'][0]['player_id'] is None
    assert context_for('a',catalog)['events']==[]
    review=fixture();review['events'][0]['source_ids']=['missing']
    with pytest.raises(ValueError):compile_catalog(review,[])


def test_duplicate_starting_slot_rejected():
    review=fixture()
    review['snapshots'][0]['teams'][0]['players'].append({'name':'Other','position':'top','source_ids':['s']})
    with pytest.raises(ValueError):compile_catalog(review,[])


def test_real_roster_api_excludes_wizer_from_split2_and_keeps_departure_evidence():
    # Source-backed regression: old match snapshot must not define the newer roster.
    catalog=load_catalog()
    assert len(catalog['snapshots'][0]['teams'])==8 and not catalog['unresolved']
    with TestClient(app) as client:
        response=client.get('/api/v3/roster-snapshots')
    assert response.status_code==200
    data=response.json()
    team=next(t for t in data['snapshots'][0]['teams'] if t['name']=='Vivo Keyd Stars')
    assert [p['name'] for p in team['players']]==['ZekaS','Disamis','Mireu','Jeskla','scamber']
    assert team['players'][0]['later_events'][0]['reported_date']=='2026-10-06'
    assert all(p['overall'] is None and p['games'] is None for p in team['players'])
    wizer=next(e for e in data['events'] if e['name']=='Wizer')
    assert wizer['reported_date']=='2026-05-28' and wizer['effective_date'] is None
    assert data['current_rosters_verified'] is False
