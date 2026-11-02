"""Local scouting API; filters refer to evidence in the selected season."""
import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .db import init, connect
from .scouting import router
from .supabase_client import DatabaseUnavailable
from fastapi.responses import JSONResponse

@asynccontextmanager
async def lifespan(app):
    from .logging_config import configure
    configure()
    init()
    yield

app = FastAPI(title='LoL Championship Manager',version='0.3.0',lifespan=lifespan)
app.include_router(router)
from .intelligence import router as intelligence_router
app.include_router(intelligence_router)

@app.exception_handler(DatabaseUnavailable)
async def database_error(request,exc):
    return JSONResponse(status_code=503,content={'detail':str(exc)})
FRONT = Path(__file__).resolve().parent.parent/'frontend'

def all_players():
    with connect() as c:
        return [json.loads(r[0]) for r in c.execute('SELECT payload_json FROM ratings_v3')]

@app.get('/api/health')
def health():
    return {'ok':True,'version':'0.3.0'}

@app.get('/api/filters')
def filters():
    rows = all_players()
    return {'regions':sorted({v for r in rows for v in r['regions']}),
            'seasons':sorted({r['season'] for r in rows},reverse=True),
            'teams':sorted({v for r in rows for v in r['teams']})}

@app.get('/api/regions')
def regions():
    return [{'id':x,'name':x} for x in filters()['regions']]

@app.get('/api/teams')
def teams(region=None,season=None):
    rows = players(region=region,season=season)
    return [{'name':v} for v in sorted({v for r in rows for v in r['teams']})]

@app.get('/api/players')
def players(region=None,position=None,season=None,team=None):
    rows = all_players()
    if season:
        rows = [r for r in rows if str(r['season'])==str(season)]
    if region:
        rows = [r for r in rows if region in r['regions']]
    if position:
        rows = [r for r in rows if r['position']==position.lower()]
    if team:
        rows = [r for r in rows if team in r['teams']]
    return sorted(rows,key=lambda r:(-(r['overall'] or 0),r['name'],r['season']))

@app.get('/api/compare')
def compare(left:str,right:str):
    return {'left':player(left),'right':player(right),
            'warning':'Estimativas experimentais; compare cobertura, temporada e conexão regional.'}

@app.get('/api/players/{player_id:path}')
def player(player_id:str):
    with connect() as c:
        record = c.execute('SELECT payload_json FROM ratings_v3 WHERE id=?',(player_id,)).fetchone()
        if record is None:
            raise HTTPException(404,'Player-season-position not found')
        r = json.loads(record[0])
        r['sources'] = [dict(x) for x in c.execute('''SELECT DISTINCT s.id,s.filename,s.sha256,s.url,s.retrieved_at,s.imported_at,s.license
          FROM sources_v3 s JOIN evidence_v3 e ON e.source_id=s.id JOIN games_v3 g ON g.id=e.game_id
          WHERE e.player_id=? AND g.season<=? ORDER BY s.id''',(r['player_id'],r['season']))]
        r['career'] = [dict(x) for x in c.execute('''SELECT g.season,o.team,o.team_id,MIN(g.date) AS first_seen,
          MAX(g.date) AS last_seen,COUNT(*) AS games FROM observations_v3 o JOIN games_v3 g ON g.id=o.game_id
          WHERE o.player_id=? AND g.season<=? GROUP BY g.season,o.team,o.team_id ORDER BY first_seen''',(r['player_id'],r['season']))]
        return r

@app.get('/api/calibration')
def calibration():
    with connect() as c:
        return {r['season']:json.loads(r['payload_json']) for r in c.execute('SELECT * FROM calibration_v3')}

@app.get('/')
def home():
    return FileResponse(FRONT/'dist'/'index.html' if (FRONT/'dist'/'index.html').exists() else FRONT/'legacy'/'index.html')

app.mount('/static',StaticFiles(directory=FRONT/'legacy'),name='static')
app.mount('/assets',StaticFiles(directory=FRONT/'dist'/'assets',check_dir=False),name='assets')
