"""Pre-game strength only: chronology, team Elo and the opponent in the same role."""
import math
from collections import defaultdict

def opponent_context(rows,k=24):
    games=defaultdict(list)
    for r in rows: games[r['game_id']].append(r)
    team_elo=defaultdict(lambda:1500.0)
    player_elo=defaultdict(lambda:1500.0)
    contexts={}
    for gid,game in sorted(games.items(),key=lambda item:(item[1][0]['date'],item[0])):
        blue=[r for r in game if r['side']=='blue'];red=[r for r in game if r['side']=='red']
        if len(blue)!=5 or len(red)!=5 or len({r['position'] for r in blue})!=5 or len({r['position'] for r in red})!=5:
            continue
        if len({r['team_id'] for r in blue})!=1 or len({r['team_id'] for r in red})!=1:
            continue
        a,b=blue[0]['team_id'],red[0]['team_id']
        y=blue[0]['result']
        if y not in (0,1) or any(r['result']!=y for r in blue) or any(r['result']!=1-y for r in red):
            continue
        for own,opp in ((blue,red),(red,blue)):
            by_role={r['position']:r for r in opp}
            for r in own:
                opponent=by_role[r['position']]
                contexts[(gid,r['player_id'])]={'team':team_elo[opponent['team_id']],
                    'player':player_elo[(opponent['player_id'],opponent['position'])]}
        expected=1/(1+10**((team_elo[b]-team_elo[a])/400))
        delta=k*(y-expected)
        team_elo[a]+=delta;team_elo[b]-=delta
        for own,sign in ((blue,1),(red,-1)):
            for r in own: player_elo[(r['player_id'],r['position'])]+=sign*delta
    return contexts
