"""Download the audited snapshot; does not assume redistribution rights."""
import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

COMMIT='192a8783278f7d1fb6e688d5525b702b8bbe6ec1'
FILES={2025:('c6a82e5e3748f29b5fc64802233541f94a594fc5477aff74e1985dc635f1a907',96780579),
       2026:('7a35c56d4f08ebcf23d9986cca9cb26f2e897d1659c5f4d5a1c18760c20b40d5',21720421)}

def download(year,root=None):
    root=Path(root or Path(__file__).resolve().parent.parent/'data'/'raw')
    root.mkdir(parents=True,exist_ok=True)
    path=root/f'{year}.csv'
    expected,size=FILES[year]
    url=f'https://raw.githubusercontent.com/twodotone/finalLOL/{COMMIT}/data/csv/{year}_LoL_esports_match_data_from_OraclesElixir.csv'
    if path.exists():
        if path.stat().st_size!=size or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError(f'{path}: existing file differs from audited snapshot; move it aside before downloading')
        return {'year':year,'url':url,'sha256':expected,'bytes':size,'status':'verified-existing'}
    temp=path.with_suffix('.csv.part')
    try:
        with urllib.request.urlopen(url,timeout=90) as response,temp.open('wb') as f:
            while chunk:=response.read(1024*1024):
                f.write(chunk)
        if temp.stat().st_size!=size or hashlib.sha256(temp.read_bytes()).hexdigest()!=expected:
            raise ValueError('Downloaded data failed size/SHA-256 verification')
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()
    return {'year':year,'url':url,'sha256':expected,'bytes':size,'retrieved_at':datetime.now(timezone.utc).isoformat(),'status':'downloaded'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--year',choices=list(FILES),type=int,action='append')
    p.add_argument('--candidate',help='Explicit audited candidate from config/datasets.json; never assumes latest data')
    args=p.parse_args()
    if args.candidate:
        print(json.dumps(download_candidate(args.candidate)));return
    for year in args.year or FILES:
        print(json.dumps(download(year)))

def download_candidate(name):
    root=Path(__file__).resolve().parent.parent
    profiles=json.loads((root/'config'/'datasets.json').read_text(encoding='utf-8'))
    if name not in profiles:raise ValueError('Unknown audited candidate')
    profile=profiles[name];folder=root/'data'/'candidates';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(name+'.csv')
    if not path.exists():
        partial=path.with_suffix('.part')
        with urllib.request.urlopen(profile['url'],timeout=90) as response,partial.open('wb') as f:
            while block:=response.read(1024*1024):f.write(block)
        if partial.stat().st_size!=profile['bytes'] or hashlib.sha256(partial.read_bytes()).hexdigest()!=profile['sha256']:
            partial.unlink();raise ValueError('Candidate checksum/size mismatch')
        partial.replace(path)
    if path.stat().st_size!=profile['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=profile['sha256']:
        raise ValueError('Existing candidate differs from audited snapshot')
    return {**profile,'file':str(path),'status':'verified_candidate'}


if __name__=='__main__':
    main()
