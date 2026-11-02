"""Reviewed identity resolution. Raw observations and provider IDs remain immutable."""
import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / 'config' / 'player-identities.json'


def load_aliases():
    rows = json.loads(CATALOG.read_text(encoding='utf-8'))['aliases']
    aliases = {r['provider_id']: r for r in rows}
    if len(aliases) != len(rows) or any(r['canonical_id'] in aliases for r in rows):
        raise ValueError('Identity aliases must be unique and point directly to canonical IDs')
    return aliases


def resolve_rows(rows, aliases=None):
    aliases = load_aliases() if aliases is None else aliases
    seen = set()
    for row in rows:
        original = row['player_id']
        alias = aliases.get(original)
        if alias:
            row['metrics']['_provider_player_id'] = original
            row['player_id'] = alias['canonical_id']
            row['name'] = alias['name']
        key = (row['game_id'], row['player_id'])
        if key in seen:
            raise ValueError(f'Reviewed alias creates duplicate player slot: {key}')
        seen.add(key)
    return rows
