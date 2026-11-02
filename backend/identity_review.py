"""Review queue for similar handles. Suggestions never merge identities automatically."""
import json
from collections import defaultdict
from difflib import SequenceMatcher
from .db import connect
from .importer import clean
from .settings import ROOT

def candidates(records,threshold=.88):
    buckets=defaultdict(list)
    for record in records:
        name=clean(record['name']).casefold()
        if name:buckets[name[0]].append((name,record))
    result=[]
    for bucket in buckets.values():
        for i,(name,a) in enumerate(bucket):
            for other,b in bucket[i+1:]:
                if abs(len(name)-len(other))>2:continue
                score=SequenceMatcher(None,name,other).ratio()
                if score>=threshold and a['id']!=b['id']:
                    result.append({'left':a,'right':b,'similarity':round(score,3),'action':'manual_review_only'})
    return sorted(result,key=lambda r:(-r['similarity'],r['left']['id'],r['right']['id']))

def main():
    with connect() as c:records=[dict(r) for r in c.execute('SELECT id,name FROM identities_v3 ORDER BY id')]
    result=candidates(records)
    (ROOT/'data'/'identity-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print({'identity_candidates':len(result),'automatic_merges':0})
if __name__=='__main__':main()
