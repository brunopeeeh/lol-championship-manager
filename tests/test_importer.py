import csv
import json
import pytest
from backend import db
from backend.importer import normalize_row, load_csv, number

@pytest.fixture
def database(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB',tmp_path/'test.db')
    db.init()
    return tmp_path

@pytest.fixture
def row():
    return dict(gameid='match-1',playername=' Faker ',playerid='player-1',teamname=' T1 ',teamid='team-1',
                position='MID',league=' lck ',year='2025',date='2025-05-01 12:00:00',side='Blue',
                champion='Ahri',gamelength='1800',kills='4',assists='6',teamkills='20',deaths='0',
                golddiffat15='250',dpm='600',datacompleteness='complete',result='1')

def write(path,rows):
    keys=sorted(set().union(*(r.keys() for r in rows)))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    return path

def test_names_rates_and_missing(row):
    r,error=normalize_row(row)
    assert error is None
    assert (r['name'],r['team'],r['position'],r['league'])==('Faker','T1','mid','LCK')
    assert r['metrics']['kp']==.5
    assert r['metrics']['deaths_pm']==0
    assert r['metrics']['wpm'] is None
    assert r['metrics']['gd15']==250
    assert number('NaN') is None and number('inf') is None
    assert number('50%')==.5

def test_aliases_and_positions(row):
    row.update(position='BOT',teamname=' t one ',playername='Ｆａｋｅｒ')
    r,_=normalize_row(row,{'teams':{'t one':'T1'}})
    assert r['name']=='Faker' and r['team']=='T1' and r['position']=='adc'

def test_zero_denominator_and_incomplete(row):
    row['teamkills']='0'
    r,_=normalize_row(row)
    assert r['metrics']['kp'] is None
    row['datacompleteness']='partial'
    partial,error=normalize_row(row)
    assert error is None and partial['metrics']['_partial']==1
    row['datacompleteness']='corrupt'
    assert normalize_row(row)[1]=='incomplete'

def test_import_idempotence_provenance_transfer(database,row):
    path=write(database/'first.csv',[row,row])
    a=load_csv(path,source_url='https://example.org/data.csv')
    assert a['inserted']==1 and a['duplicates']==1
    assert load_csv(path)['duplicates']==2
    moved={**row,'gameid':'match-2','teamname':'New team','teamid':'team-2','date':'2025-06-01'}
    load_csv(write(database/'second.csv',[moved]))
    with db.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM identities_v3').fetchone()[0]==1
        assert c.execute('SELECT COUNT(DISTINCT team_id) FROM observations_v3').fetchone()[0]==2
        assert c.execute('SELECT COUNT(*) FROM observations_v3').fetchone()[0]==2
        source=dict(c.execute('SELECT * FROM sources_v3 LIMIT 1').fetchone())
        assert len(source['sha256'])==64 and source['url'].startswith('https:') and source['retrieved_at']
        assert c.execute('SELECT COUNT(*) FROM evidence_v3').fetchone()[0]==3

def test_conflicts_preserve_first_evidence(database,row):
    load_csv(write(database/'one.csv',[row]))
    a=load_csv(write(database/'two.csv',[{**row,'dpm':'999'}]))
    assert a['conflicts']==1
    b=load_csv(write(database/'three.csv',[{**row,'playerid':'other'}]))
    assert b['slot_conflicts']==1
    with db.connect() as c:
        assert json.loads(c.execute('SELECT metrics_json FROM observations_v3').fetchone()[0])['dpm']==600

def test_invalid_file_rolls_back(database):
    with pytest.raises(ValueError):
        load_csv(write(database/'bad.csv',[{'player':'x','dpm':500}]))
    with db.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM sources_v3').fetchone()[0]==0
