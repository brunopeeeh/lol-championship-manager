"""Additive v0.3 schema: legacy tables are retained, never reused as evidence."""
import os
import sqlite3
from pathlib import Path
DB = Path(os.environ.get('LCM_DB', Path(__file__).resolve().parent.parent / 'data' / 'manager.db'))

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY);
        INSERT OR IGNORE INTO schema_versions VALUES(3);
        CREATE TABLE IF NOT EXISTS sources_v3(
          id INTEGER PRIMARY KEY, filename TEXT, sha256 TEXT NOT NULL,
          url TEXT NOT NULL, retrieved_at TEXT NOT NULL, imported_at TEXT NOT NULL,
          license TEXT NOT NULL, stats_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS identities_v3(id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS games_v3(
          id TEXT PRIMARY KEY, season INTEGER NOT NULL, league TEXT NOT NULL,
          date TEXT NOT NULL, patch TEXT, split TEXT);
        CREATE TABLE IF NOT EXISTS observations_v3(
          game_id TEXT REFERENCES games_v3(id), player_id TEXT REFERENCES identities_v3(id),
          team_id TEXT NOT NULL, team TEXT NOT NULL, position TEXT NOT NULL,
          side TEXT NOT NULL, champion TEXT, result INTEGER, metrics_json TEXT NOT NULL,
          PRIMARY KEY(game_id,player_id), UNIQUE(game_id,side,position));
        CREATE TABLE IF NOT EXISTS evidence_v3(
          source_id INTEGER REFERENCES sources_v3(id), game_id TEXT, player_id TEXT,
          PRIMARY KEY(source_id,game_id,player_id),
          FOREIGN KEY(game_id,player_id) REFERENCES observations_v3(game_id,player_id));
        CREATE TABLE IF NOT EXISTS ratings_v3(
          id TEXT PRIMARY KEY, player_id TEXT REFERENCES identities_v3(id),
          season INTEGER, position TEXT, payload_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS calibration_v3(season INTEGER PRIMARY KEY, payload_json TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS observations_player ON observations_v3(player_id);
        ''')
