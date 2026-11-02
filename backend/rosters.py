"""Dated editorial roster evidence, independent of match statistics and contracts.

Import reviewed facts only. A snapshot never establishes today's employment.
"""
import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from . import db
from .portraits import normalized
from .sync import uid

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / 'data' / 'roster-evidence.json'


def load_catalog():
    if not CATALOG.exists():
        return {'snapshots': [], 'events': [], 'sources': {}, 'unresolved': []}
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def compile_catalog(review, identities):
    """Resolve only unambiguous handles; unresolved evidence remains visible."""
    by_name = defaultdict(list)
    for person in identities:
        by_name[normalized(person['name'])].append(person)
    result = json.loads(json.dumps(review))
    result['unresolved'] = []
    for source in result['sources'].values():
        if not source['url'].startswith('https://'):
            raise ValueError('Evidence requires an HTTPS source')
        date.fromisoformat(source['retrieved_at'][:10])
    def resolve(record):
        for key in ('source_ids',):
            if not record.get(key) or any(s not in result['sources'] for s in record[key]):
                raise ValueError('Unknown or missing evidence source')
        people = by_name[normalized(record['name'])]
        record['player_id'] = uid('player', people[0]['id']) if len(people) == 1 else None
        record['external_player_id'] = people[0]['id'] if len(people) == 1 else None
        record['identity_status'] = 'exact_unique_handle' if len(people) == 1 else 'needs_review'
        if len(people) != 1:
            result['unresolved'].append(record['name'])
    for snapshot in result['snapshots']:
        date.fromisoformat(snapshot['reference_date'])
        seen = set()
        for team in snapshot['teams']:
            positions = set()
            for person in team['players']:
                if person['position'] not in {'top','jungle','mid','adc','support'}:
                    raise ValueError('Unknown position')
                if person['position'] in positions or normalized(person['name']) in seen:
                    raise ValueError('Duplicate starting slot or player')
                positions.add(person['position']); seen.add(normalized(person['name']))
                resolve(person)
    for event in result['events']:
        date.fromisoformat(event['reported_date'])
        if event['kind'] not in {'departure_reported'}:
            raise ValueError('Unknown roster event')
        resolve(event)
    return result


def context_for(player_id, catalog=None):
    data = load_catalog() if catalog is None else catalog
    aliases = {player_id, uid('player', player_id)}
    snapshots = []
    for snap in data['snapshots']:
        for team in snap['teams']:
            for person in team['players']:
                if person.get('player_id') in aliases:
                    snapshots.append({'team':team['name'], 'competition':snap['competition'],
                        'reference_date':snap['reference_date'], 'source_ids':person['source_ids']})
    events = sorted([e for e in data['events'] if e.get('player_id') in aliases],
                    key=lambda e:e['reported_date'])
    source_ids = {s for entry in [*snapshots,*events] for s in entry['source_ids']}
    return {'current_team':None, 'current_status':'not_verified',
            'snapshots':snapshots, 'events':events,
            'sources':{key:data['sources'][key] for key in sorted(source_ids)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', type=Path)
    args = parser.parse_args()
    with db.connect() as connection:
        people = [dict(r) for r in connection.execute('SELECT id,name FROM identities_v3')]
    result = compile_catalog(json.loads(args.review.read_text(encoding='utf-8')), people)
    CATALOG.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'snapshots':len(result['snapshots']),
        'teams':sum(len(s['teams']) for s in result['snapshots']),
        'slots':sum(len(t['players']) for s in result['snapshots'] for t in s['teams']),
        'events':len(result['events']), 'unresolved':result['unresolved']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
