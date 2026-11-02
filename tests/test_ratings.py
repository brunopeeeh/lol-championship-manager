import copy
import pytest
from backend.ratings import ATTRS, WEIGHTS, overall, normalize, shrink, score_players, calibrate, home_regions

def fixture_rows():
    rows=[]
    for season in (2025,2026):
        for region,team in [('LCK','T1'),('CBLOL','RED')]:
            for player in range(4):
                for game in range(24):
                    rows.append(dict(game_id=f'{season}-{region}-{player}-{game}',player_id=f'{region}-{player}',
                      name=f'{region}{player}',team_id=team,team=team,position='mid',side='blue',
                      champion=['Ahri','Azir','Orianna'][game%3],result=1,season=season,league=region,
                      date=f'{season}-02-{game+1:02d} 12:00:00',patch='1',split='Spring',
                      metrics={'dpm':300+player*60+game*3,'dmgshare':.15+player*.04,'gd15':player*100+game,
                       'cs10':player*3+game,'xp15':player*80+game,'kills_pm':.1+player*.03,
                       'deaths_pm':.2-player*.02,'kp':.4+player*.1,'wpm':.2+player*.03,
                       'wcpm':.1+player*.01,'tower_pm':30+player*20}))
        for game in range(12):
            for side,region,team,result in [('blue','LCK','T1',1),('red','CBLOL','RED',0)]:
                for pos in ('top','jungle','mid','adc','support'):
                    rows.append(dict(game_id=f'int-{season}-{game}',player_id=f'int-{region}-{pos}',name=pos,
                      team_id=team,team=team,position=pos,side=side,champion='Ahri',result=result,season=season,
                      league='MSI',date=f'{season}-06-{game+1:02d} 12:00:00',patch='1',split='',metrics={}))
    return rows

def test_weights_and_missing_overall():
    assert all(sum(x)==100 for x in WEIGHTS.values())
    assert overall({},'mid') is None
    assert overall({k:90 for k in ATTRS},'mid')==90
    assert overall({k:1000 for k in ATTRS},'mid')==100
    assert overall({k:-10 for k in ATTRS},'mid')==1
    attrs={k:80 for k in ATTRS}; attrs['ada']=attrs['dec']=None
    assert overall(attrs,'mid')==80

def test_normalization_and_shrink():
    assert normalize(None,1,1) is None
    assert normalize(2,1,0) is None
    assert normalize(2,1,1)==1 and normalize(2,1,1,True)==-1
    assert shrink(None,20) is None
    assert shrink(90,0)==70 and shrink(90,20)==80

def test_calibration_uses_results_not_equal_region_means():
    rows=fixture_rows(); cal=calibrate(rows,2026,home_regions(rows))
    assert cal['regions']['LCK']['offset']>cal['regions']['CBLOL']['offset']
    assert cal['regions']['CBLOL']['connected']
    assert cal['games']==24

def test_ratings_hybrid_missing_and_form():
    ratings,_=score_players(fixture_rows())
    rated=[r for r in ratings if r['player_id']=='LCK-3']
    assert all(r['overall'] is not None for r in rated)
    current=next(r for r in rated if r['season']==2026)
    assert current['historical_games']==24
    assert current['attribute_details']['lan']['historical']
    assert current['form'] is not None
    assert current['potential'] is None
    assert current['attributes']['ada'] is None and current['attributes']['dec'] is None
    assert 0<current['confidence']<1
    assert all(v is None or 1<=v<=100 for v in current['attributes'].values())

def test_no_future_leak_and_deterministic_special_attributes():
    rows=fixture_rows()
    full,_=score_players(rows)
    past,_=score_players([r for r in rows if r['season']==2025])
    assert [r for r in full if r['season']==2025]==past
    reverse,_=score_players(list(reversed(rows)))
    # Sorting stable keys and frozen peer statistics prevents order-dependent normalization.
    assert {r['id']:r['attributes'] for r in full}=={r['id']:r['attributes'] for r in reverse}

def test_unconnected_and_sparse_evidence():
    rows=[r for r in fixture_rows() if r['league']=='CBLOL'][:1]
    ratings,_=score_players(rows)
    assert ratings[0]['overall'] is None
    assert ratings[0]['potential'] is None and ratings[0]['form'] is None
    assert all(v is None for v in ratings[0]['attributes'].values())

def test_attribute_uses_observed_count_not_total_games():
    rows=fixture_rows()
    for r in rows:
        if r['player_id']=='LCK-3' and not r['date'].startswith('2026-02-01'):
            r['metrics']['gd15']=None;r['metrics']['cs10']=None;r['metrics']['xp15']=None
    ratings,_=score_players(rows)
    r=next(r for r in ratings if r['player_id']=='LCK-3' and r['season']==2026)
    assert r['attribute_details']['lan']['games']==1
