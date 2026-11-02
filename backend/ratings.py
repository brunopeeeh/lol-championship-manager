"""Experimental global model v0.3. All skill attributes are proxy estimates."""
import json
import math
import statistics
from collections import defaultdict, Counter
from .db import init, connect
from pathlib import Path
from .opponents import opponent_context

ATTRS = ('mec','lan','agr','sob','mac','vis','obj','tf','con','ver','ada','dec')
WEIGHTS = {
 'top': (18,20,0,12,12,2,5,18,7,3,1,2),
 'jungle': (10,3,0,10,22,8,18,13,8,3,2,3),
 'mid': (18,18,0,9,16,4,5,18,7,3,1,1),
 'adc': (23,20,0,14,7,1,3,21,6,3,1,1),
 'support': (6,7,0,9,22,20,12,13,6,2,1,2),
}
INTERNATIONAL = {'MSI','WCS','WLDS','FST','EWC','Americas Cup','LTA','DCUP','KESPA','ASIA MASTER'}
HOME = {'LTA S':'CBLOL','LTA N':'LCS'}
PROXIES = {
 'mec': [('dpm',.5),('dmgshare',.5)],
 'lan': [('gd15',.4),('cs10',.3),('xp15',.3)],
 'agr': [('kills_pm',.6),('kp',.4)],
 'sob': [('deaths_pm',1)], 'mac':[('kp',1)],
 'vis': [('wpm',.55),('wcpm',.45)], 'obj':[('tower_pm',1)],
 'tf': [('dpm',.5),('kp',.5)], 'con':[('stability',1)], 'ver':[('entropy',1)],
 'ada': [], 'dec': []}
METRICS = tuple(sorted({m for pairs in PROXIES.values() for m,_ in pairs} - {'stability','entropy'}))

def clamp(x, low=1, high=100):
    return max(low,min(high,x))

def normalize(x, mean, sd, invert=False):
    if x is None or sd is None or sd <= 0:
        return None
    return max(-3,min(3,(-1 if invert else 1)*(x-mean)/sd))

def shrink(value,n,baseline=70,strength=20):
    return None if value is None else baseline+(value-baseline)*n/(n+strength)

def overall(attrs,position,weights=None):
    available = [(attrs.get(k),w) for k,w in zip(ATTRS,(weights or WEIGHTS)[position]) if attrs.get(k) is not None and w]
    coverage = sum(w for _,w in available)
    # Never emit a composite dominated by missing evidence.
    if coverage < 60:
        return None
    return round(clamp(sum(v*w for v,w in available)/coverage))

def read_rows(c):
    rows = [dict(r) for r in c.execute('''SELECT o.*,g.season,g.league,g.date,g.patch,g.split,i.name
        FROM observations_v3 o JOIN games_v3 g ON g.id=o.game_id
        JOIN identities_v3 i ON i.id=o.player_id ORDER BY g.date,g.id,o.player_id''')]
    for r in rows:
        r['metrics'] = json.loads(r.pop('metrics_json'))
    return rows

def home_regions(rows):
    counts = defaultdict(Counter)
    for r in rows:
        if r['league'] not in INTERNATIONAL:
            counts[(r['team_id'],r['season'])][HOME.get(r['league'],r['league'])] += 1
    return {k:v.most_common(1)[0][0] for k,v in counts.items()}

def calibrate(rows,season,homes):
    """Ridge logistic region effects from valid international games, with recency decay.
    Team selection bias is NOT resolved by this simple bridge. No manual region bonuses.
    """
    games = defaultdict(list)
    for r in rows:
        if r['season'] <= season and r['league'] in INTERNATIONAL:
            games[r['game_id']].append(r)
    pairs = []
    support = Counter()
    graph = defaultdict(set)
    for game in games.values():
        sides = [[r for r in game if r['side']==side] for side in ('blue','red')]
        if any(len(s)!=5 or len({r['team_id'] for r in s})!=1 or len({r['result'] for r in s})!=1 for s in sides):
            continue
        a,b = (s[0] for s in sides)
        ra,rb = (homes.get((r['team_id'],r['season'])) for r in (a,b))
        if not ra or not rb or ra==rb or a['result'] is None or b['result'] != 1-a['result']:
            continue
        weight = .5**(season-a['season'])
        pairs.append((ra,rb,a['result'],weight))
        support[ra]+=1; support[rb]+=1
        graph[ra].add(rb); graph[rb].add(ra)
    connected = set()
    queue = ['LCK'] if 'LCK' in graph else []
    while queue:
        r = queue.pop()
        if r not in connected:
            connected.add(r); queue.extend(graph[r]-connected)
    effects = {r:0.0 for r in graph}
    # L2 prior of 4 pseudo-observations per region. Fixed-step gradient on a convex objective.
    lr = .5 / (max(support.values(),default=1)+4)
    for _ in range(800):
        gradient = {r:-4*v for r,v in effects.items()}
        for a,b,y,w in pairs:
            p = 1/(1+math.exp(-max(-20,min(20,effects[a]-effects[b]))))
            gradient[a] += w*(y-p); gradient[b] -= w*(y-p)
        for r in effects:
            effects[r] += lr*gradient[r]
    return {'method':'ridge-logistic-international-v1','games':len(pairs),
            'regions':{r:{'offset':round(8*effects[r],4),'games':support[r],
                          'connected':r in connected and support[r]>=5,
                          'confidence':round(min(.8,support[r]/(support[r]+30)),3)} for r in effects},
            'limitations':'Team strength and qualification bias confound region effects; scale 70/10 and 8 points/logit are design choices, not validated skill units.'}

def benchmarks(rows):
    values = defaultdict(lambda:defaultdict(list))
    for r in rows:
        for context in ((r['season'],r['position'],r['league'],r['patch']),
                        (r['season'],r['position'],r['league'],'')):
            for m in METRICS:
                if r['metrics'].get(m) is not None:
                    values[context][m].append(r['metrics'][m])
    return {key:{m:(statistics.mean(v),statistics.pstdev(v),len(v)) for m,v in fields.items()}
            for key,fields in values.items()}

def load_config(path=None):
    config=json.loads(Path(path or Path(__file__).resolve().parent.parent/'config'/'ratings.json').read_text(encoding='utf-8-sig'))
    if config['shrink_strength']<=0 or not 0<config['history_decay']<=1:
        raise ValueError('Invalid smoothing/history parameters')
    if set(config['weights'])!=set(WEIGHTS) or any(len(w)!=12 or sum(w)!=100 or any(v<0 for v in w) for w in config['weights'].values()):
        raise ValueError('Position weights must have 12 nonnegative values summing to 100')
    if any(w[2]!=0 for w in config['weights'].values()):
        raise ValueError('Aggressiveness is style and must not contribute to overall')
    return config

def score_players(rows,config=None):
    """Rebuild all seasons together; historical ratings never consume future seasons."""
    if not rows:
        return [], {}
    config=config or load_config()
    rows=sorted(rows,key=lambda r:(r['date'],r['game_id'],r['player_id']))
    strengths=opponent_context(rows,config['elo_k'])
    weights=config['weights']
    homes = home_regions(rows)
    calibrations = {s:calibrate(rows,s,homes) for s in sorted({r['season'] for r in rows})}
    reference = benchmarks(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[(r['player_id'],r['position'],r['season'])].append(r)
    summaries = {}
    for key,games in groups.items():
        z = defaultdict(list)
        observations = defaultdict(list)
        for r in games:
            for m in METRICS:
                x = r['metrics'].get(m)
                if x is not None:
                    observations[m].append(x)
                context = (r['season'],r['position'],r['league'],r['patch'])
                ref = reference.get(context,{}).get(m)
                if ref is None or ref[2]<20:
                    ref = reference.get((*context[:3],''),{}).get(m)
                v = normalize(x,ref[0],ref[1],m=='deaths_pm') if ref and ref[2]>=20 else None
                if v is not None:
                    opp=strengths.get((r['game_id'],r['player_id']))
                    if opp:
                        v+=max(-.5,min(.5,config['opponent_team_weight']*(opp['team']-1500)/400+
                                      config['opponent_player_weight']*(opp['player']-1500)/400))
                    z[m].append((r['date'],v))
        # Consistency is dispersion of context-normalized damage, not a fixed arbitrary CV score.
        if len(z['dpm'])>=8:
            z['stability'] = [('summary',-statistics.pstdev(v for _,v in z['dpm']))]
        champs = Counter(r['champion'] for r in games if r['champion'])
        n = sum(champs.values())
        if n>=10:
            z['entropy'] = [('summary',-sum((v/n)*math.log(v/n) for v in champs.values()))]
        summaries[key] = (z,observations)
    special = {key:{m:(z[m][0][1] if z[m] else None) for m in ('stability','entropy')}
               for key,(z,_) in summaries.items()}
    # Pool consistency/diversity by position, season and home region, requiring >=3 peers.
    for key,(z,_) in summaries.items():
        games = groups[key]
        region = homes.get((games[-1]['team_id'],key[2]),games[-1]['league'])
        for m in ('stability','entropy'):
            if not z[m]:
                continue
            peers = [v[m] for k,v in special.items()
                     if k[1:]==key[1:] and v[m] is not None and
                     homes.get((groups[k][-1]['team_id'],k[2]),groups[k][-1]['league'])==region]
            z[m] = [('summary',normalize(special[key][m],statistics.mean(peers),statistics.pstdev(peers)))] if len(peers)>=3 else []
            if z[m] and z[m][0][1] is None:
                z[m] = []
    results = []
    for key,games in sorted(groups.items()):
        pid,pos,season = key
        games = sorted(games,key=lambda r:(r['date'],r['game_id']))
        latest = games[-1]
        z,observed = summaries[key]
        domestic=[r for r in games if r['league'] not in INTERNATIONAL]
        split=domestic[-1].get('split','') if domestic else latest.get('split','')
        split_start=min((r['date'] for r in domestic if r.get('split')==split),default=games[0]['date'])
        current_series=defaultdict(list,{m:[(date,v) for date,v in values if m in ('stability','entropy') or not config['current_split'] or date>=split_start] for m,values in z.items()})
        attrs,details = {},{}
        def proxy(series,k):
            pairs = [(statistics.mean(v for _,v in series[m]),w,len(series[m])) for m,w in PROXIES[k] if series[m]]
            if not pairs:
                return None,0,0
            return sum(v*w for v,w,_ in pairs)/sum(w for _,w,_ in pairs), min(n for _,_,n in pairs),sum(w for _,w,_ in pairs)
        history_keys = [k for k in groups if k[0]==pid and k[1]==pos and k[2]<season]
        region = homes.get((latest['team_id'],season),latest['league'])
        cal = calibrations[season]['regions'].get(region,{})
        for k in ATTRS:
            current,n,cov = proxy(current_series,k)
            # CON/VER use game count rather than the single summary as support.
            if k in ('con','ver') and current is not None:
                n = len(z['dpm']) if k=='con' else sum(bool(r['champion']) for r in games)
            past = []
            for hk in history_keys:
                value,hn,hcov = proxy(summaries[hk][0],k)
                if value is not None:
                    valid_n=hn if k not in ('con','ver') else len(groups[hk])
                    past.append((value, min(config['history_cap'],valid_n)*config['history_decay']**(season-hk[2]),hcov))
            historical = sum(v*w for v,w,_ in past)/sum(w for _,w,_ in past) if past else None
            if current is None:
                attrs[k] = None
                details[k] = {'status':'unavailable','games':0,'metrics':[m for m,_ in PROXIES[k]]}
                continue
            current_weight = n/(n+config['shrink_strength']) if historical is not None else 1
            hybrid = current*current_weight+(historical or 0)*(1-current_weight)
            support = n + (sum(w for _,w,_ in past)*(1-current_weight) if past else 0)
            # Shrink only observed proxies. Missing attributes NEVER receive the baseline.
            attrs[k] = round(clamp(shrink(config['baseline']+config['scale']*hybrid,support,
                                      config['baseline'],config['shrink_strength'])+cal.get('offset',0)),1)
            details[k] = {'status':'estimated','games':n,'coverage':round(cov,3),
                          'current_weight':round(current_weight,3),'historical':historical is not None,
                          'metrics':[m for m,_ in PROXIES[k]]}
        score = overall(attrs,pos,weights)
        coverage = sum(w*details[k].get('coverage',0) for k,w in zip(ATTRS,weights[pos]))/100
        effective = [details[k]['games'] for k,w in zip(ATTRS,weights[pos]) if w and attrs[k] is not None]
        sample = statistics.mean(effective) if effective else 0
        quality=1-.25*sum(bool(r['metrics'].get('_partial')) for r in games)/len(games)
        confidence = round(sample/(sample+config['shrink_strength'])*coverage*(.5+.5*cal.get('confidence',0))*quality,3)
        # Form = recent-vs-earlier normalized damage/KP, requiring >=10 games each side.
        recent = games[-10:]
        previous = games[:-10]
        form = None
        if len(previous)>=10:
            vals = []
            for m in ('dpm','kp'):
                recent_dates = {r['date'] for r in recent}
                a = [v for date,v in z[m] if date in recent_dates]
                b = [v for date,v in z[m] if date not in recent_dates]
                if len(a)>=8 and len(b)>=10:
                    vals.append(statistics.mean(a)-statistics.mean(b))
            if vals:
                form = round(10*statistics.mean(vals),1)
        history = []
        for r in games:
            if not history or history[-1]['team_id']!=r['team_id']:
                history.append({'team_id':r['team_id'],'team':r['team'],'from':r['date'],'to':r['date']})
            history[-1]['to'] = r['date']
        champion_pool=[]
        for champion,count in Counter(r['champion'] for r in games if r['champion']).most_common():
            picks=[r for r in games if r['champion']==champion]
            dates={r['date'] for r in picks}
            normalized=[v for date,v in z['dpm'] if date in dates]
            wins=sum(r['result'] for r in picks if r['result'] is not None)
            known=sum(r['result'] is not None for r in picks)
            champion_pool.append({'champion':champion,'games':count,'wins':wins if known==count else None,
                                 'win_rate':round(wins/known,3) if known else None,
                                 'score':round(clamp(shrink(70+10*statistics.mean(normalized),len(normalized),strength=config['shrink_strength'])),1) if len(normalized)>=8 else None,
                                 'status':'estimated' if len(normalized)>=8 else 'unavailable'})
        results.append({'id':f'{pid}|{season}|{pos}','player_id':pid,'name':latest['name'],
          'team':latest['team'],'team_id':latest['team_id'],'region':region,'league':latest['league'],
          'leagues':sorted({r['league'] for r in games}),'regions':sorted({homes.get((r['team_id'],season),r['league']) for r in games}),
          'season':season,'split':split,'split_games':sum(r['date']>=split_start for r in games),'position':pos,'overall':score if cal.get('connected') else None,
          'context_overall':score,'potential':None,'form':form,'games':len(games),
          'historical_games':sum(len(groups[k]) for k in history_keys),'confidence':confidence,
          'partial_games':sum(bool(r['metrics'].get('_partial')) for r in games),
          'attributes':attrs,'attribute_details':details,'measured_metrics':{m:{'mean':round(statistics.mean(v),4),'games':len(v)} for m,v in observed.items() if v},
          'calibration':{**cal,'status':'experimental' if cal.get('connected') else 'unconnected'},
          'teams':sorted({r['team'] for r in games}),'stints':history,
          'date_from':games[0]['date'],'date_to':latest['date'],'method':'v'+config['version'],
          'opponent_games':sum((r['game_id'],pid) in strengths for r in games),
          'champion_pool':champion_pool,
          'estimated_attributes':[k for k in ATTRS if attrs[k] is not None],
          'unobserved_attributes':[k for k in ATTRS if attrs[k] is None]})
    return results,calibrations

def rebuild():
    init()
    with connect() as c:
        results,cal = score_players(read_rows(c))
        c.execute('DELETE FROM ratings_v3')
        c.execute('DELETE FROM calibration_v3')
        for r in results:
            c.execute('INSERT INTO ratings_v3 VALUES(?,?,?,?,?)',(r['id'],r['player_id'],r['season'],r['position'],json.dumps(r,allow_nan=False)))
        for season,payload in cal.items():
            c.execute('INSERT INTO calibration_v3 VALUES(?,?)',(season,json.dumps(payload,allow_nan=False)))
    return {'ratings':len(results),'global_overalls':sum(r['overall'] is not None for r in results)}

if __name__ == '__main__':
    print(rebuild())
