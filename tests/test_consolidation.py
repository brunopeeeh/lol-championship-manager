import json
import pytest
from fastapi.testclient import TestClient
from backend import db
from backend.importer import load_csv
from backend.main import app
from backend.reconcile import reconcile
from backend.rosters import compile_catalog,load_catalog
from backend.intelligence import roster_at
from datetime import date
from test_importer import write
from backend.identities import resolve_rows,load_aliases


def test_missing_supabase_configuration_is_a_controlled_service_error(monkeypatch,tmp_path):
    monkeypatch.setattr(db,'DB',tmp_path/'config.db')
    monkeypatch.setenv('LCM_STORAGE','supabase');monkeypatch.setenv('SUPABASE_URL','');monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','')
    with TestClient(app) as c:
        response=c.get('/api/v3/players')
        assert response.status_code==503 and 'não configurado' in response.json()['detail']


def test_reconciliation_exports_only_post_cutoff_and_import_is_idempotent(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB',tmp_path/'baseline.db')
    one=dict(gameid='a',playername='Fixture',playerid='p',teamname='A',position='mid',league='CBLOL',year=2026,date='2026-04-01',side='Blue')
    source=write(tmp_path/'first.csv',[one]);load_csv(source)
    candidate=write(tmp_path/'candidate.csv',[{**one,'date':'2026-04-02'},{**one,'gameid':'b','date':'2026-06-01'}])
    report=reconcile(candidate,db.DB,tmp_path/'selected.csv')
    assert report['counts']['overlap_changed']==1 and report['new_games']==1
    imported=load_csv(candidate,after='2026-04-01 00:00:00')
    assert imported.get('conflicts',0)+imported.get('game_conflicts',0)==1
    assert imported['inserted']==1
    again=load_csv(candidate,after='2026-04-01 00:00:00')
    assert again.get('inserted',0)==0


def test_provider_id_review_resolves_homonym_without_merging():
    catalog=load_catalog()
    assert not catalog['unresolved'] and len(catalog['snapshots'])==3
    july=roster_at(catalog,date(2026,7,24),team='paiN Gaming')['items'][0]
    august=roster_at(catalog,date(2026,8,29),team='paiN Gaming')['items'][0]
    assert not july['team_events']
    assert {e['name'] for e in august['team_events']}=={'Keine','Namiru'}
    assert all(e['effective_date'] is None for e in august['team_events'])


def test_reviewed_alias_preserves_provider_identity_and_rejects_slot_collision():
    aliases=load_aliases();old,next_alias=next(iter(aliases.items()))
    row={'game_id':'g','player_id':old,'name':'zekas','metrics':{}}
    result=resolve_rows([row],aliases)[0]
    assert result['player_id']==next_alias['canonical_id']
    assert result['metrics']['_provider_player_id']==old
    with pytest.raises(ValueError,match='duplicate player slot'):
        resolve_rows([{'game_id':'g','player_id':old,'metrics':{}},
                      {'game_id':'g','player_id':next_alias['canonical_id'],'metrics':{}}],aliases)
    homonym={'game_id':'h','player_id':'unreviewed','name':'Envy','metrics':{}}
    assert resolve_rows([homonym])[0]['player_id']=='unreviewed'


def test_remote_detail_excludes_unapproved_models(monkeypatch):
    from backend.scouting import detail
    monkeypatch.setenv('LCM_STORAGE','supabase')
    def select(table,params):
        if table=='rating_models':
            assert params['config->>import_complete']=='eq.true'
            return [{'id':'approved'}]
        if table=='rosters':return []
        assert params['model_id']=='in.(approved)'
        if 'player_id' in params:return []
        return [{'id':'00000000-0000-0000-0000-000000000001','player_id':'p','overall':None,'provenance':{'season':2026}}]
    monkeypatch.setattr('backend.scouting.select',select)
    assert detail('00000000-0000-0000-0000-000000000001')['rating_history']==[]
