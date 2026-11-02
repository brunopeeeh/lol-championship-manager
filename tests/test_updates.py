import pytest
from backend import db
from backend.importer import load_csv
from backend.updates import inspect
from test_importer import write


def test_update_inspection_counts_newer_evidence_without_mutation(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB',tmp_path/'updates.db')
    base=dict(gameid='one',playername='Fixture',playerid='p1',teamname='A',position='mid',league='CBLOL',year=2026,date='2026-04-01',side='Blue')
    load_csv(write(tmp_path/'old.csv',[base]))
    candidate=write(tmp_path/'new.csv',[base,{**base,'gameid':'two','date':'2026-08-01'}])
    result=inspect(candidate,'https://example.org/match.csv',season=2026)
    assert result['status']=='inspected_only'
    assert result['counts']['new_keys']==1 and result['counts']['existing_keys']==1
    assert result['counts']['rows_after_current_cutoff']==1
    with db.connect() as c:assert c.execute('SELECT count(*) FROM games_v3').fetchone()[0]==1


def test_update_rejects_aggregates_and_non_https_provenance(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB',tmp_path/'updates.db');db.init()
    aggregate=tmp_path/'aggregate.csv';aggregate.write_text('player,games,dpm\nFixture,50,600\n')
    with pytest.raises(ValueError,match='Per-match'):inspect(aggregate,'https://example.org/file.csv')
    with pytest.raises(ValueError,match='HTTPS'):inspect(aggregate,'http://example.org/file.csv')
