"""Public roster portrait importer. Exact unique handles only; no face recognition.
Images remain at the official CDN. No image bytes are downloaded or rehosted.
"""
import argparse
import json
import unicodedata
from collections import defaultdict
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse,parse_qs,urlencode
import httpx
from .db import connect
from .sync import uid

ROOT=Path(__file__).resolve().parent.parent
CATALOG=ROOT/'data'/'player-portraits.json'
HOSTS={'am-a.akamaihd.net','static.lolesports.com'}

def normalized(name):return unicodedata.normalize('NFKC',name).strip().casefold()

def safe_image(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in HOSTS:return False
    if parsed.hostname=='am-a.akamaihd.net':
        target=urlparse(parse_qs(parsed.query).get('f',[''])[0])
        return target.hostname=='static.lolesports.com' and target.path.startswith('/players/')
    return parsed.path.startswith('/players/')

class RosterParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.depth=0;self.article=None;self.heading=False;self.players=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='article':
            self.depth+=1
            if self.depth==1:self.article={'name':'','image_url':None,'source_name':None}
        if self.article is not None:
            if tag=='h3':self.heading=True
            if tag=='img' and safe_image(attrs.get('src','')):
                self.article['image_url']=attrs['src'];self.article['source_name']=attrs.get('alt')
    def handle_data(self,data):
        if self.article is not None and self.heading:self.article['name']+=data
    def handle_endtag(self,tag):
        if tag=='h3':self.heading=False
        if tag=='article' and self.depth:
            self.depth-=1
            if self.depth==0:
                if self.article and self.article['name'].strip() and self.article['image_url']:
                    self.article['name']=self.article['name'].strip();self.players.append(self.article)
                self.article=None

def load_catalog():
    if not CATALOG.exists():return {'portraits':{},'unmatched':[],'sources':[]}
    return json.loads(CATALOG.read_text(encoding='utf-8'))

def portrait_for(player_id,external_id=None,catalog=None):
    portraits=(catalog if catalog is not None else load_catalog())['portraits']
    record=portraits.get(player_id) or (portraits.get(uid('player',external_id or player_id)))
    return record if record and safe_image(record.get('image_url','')) else None

def merge_roster(catalog,roster,identities,source_url):
    by_name=defaultdict(list)
    for person in identities:by_name[normalized(person['name'])].append(person)
    matched=0
    for player in roster:
        candidates=by_name.get(normalized(player['name']),[])
        if len(candidates)!=1:
            catalog['unmatched'].append({'handle':player['name'],'source_url':source_url,
                'reason':'ambiguous' if candidates else 'not_in_dataset'})
            continue
        person=candidates[0]
        if not safe_image(player['image_url']):continue
        url=player['image_url'];parsed=urlparse(url)
        if parsed.hostname=='am-a.akamaihd.net':
            query=parse_qs(parsed.query);query['resize']=['320:']
            url=parsed._replace(query=urlencode(query,doseq=True)).geturl()
        catalog['portraits'][uid('player',person['id'])]={
           'image_url':url,'source_url':source_url,'provider':'LoL Esports / Riot Games',
           'retrieved_at':datetime.now(timezone.utc).isoformat(),'handle':person['name'],
           'source_full_name':player.get('source_name'),'external_player_id':person['id'],
           'match_method':'exact_unique_normalized_handle_on_official_roster',
           'photo_season':None,'rights_status':'copyright_riot_or_respective_owner; reuse_license_unconfirmed',
           'note':'Retrato de arquivo; a camisa não determina a equipe na temporada dos dados.'}
        matched+=1
    if source_url not in catalog['sources']:catalog['sources'].append(source_url)
    return matched

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',action='append',required=True)
    p.add_argument('--html',help='Use an already downloaded official roster HTML; one source only')
    args=p.parse_args()
    if args.html and len(args.source)!=1:raise ValueError('--html requires exactly one source')
    with connect() as c:identities=[dict(r) for r in c.execute('SELECT id,name FROM identities_v3')]
    catalog=load_catalog();results=[]
    for source in args.source:
        parsed=urlparse(source)
        if parsed.scheme!='https' or parsed.hostname!='lolesports.com' or '/teams/' not in parsed.path:
            raise ValueError('Only explicit official LoL Esports roster pages are supported')
        if args.html:body=Path(args.html).read_text(encoding='utf-8')
        else:
            response=httpx.get(source,timeout=30,follow_redirects=False)
            if response.status_code in (403,429):raise RuntimeError('Source restricted or rate limited; stopped without bypassing restrictions')
            response.raise_for_status();body=response.text
        parser=RosterParser();parser.feed(body)
        results.append({'source':source,'matched':merge_roster(catalog,parser.players,identities,source),'found':len(parser.players)})
    catalog['updated_at']=datetime.now(timezone.utc).isoformat()
    CATALOG.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'results':results,'total_portraits':len(catalog['portraits']),'unmatched':len(catalog['unmatched'])},ensure_ascii=False))

if __name__=='__main__':main()
