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
    args=p.parse_args()
    for year in args.year or FILES:
        print(json.dumps(download(year)))

if __name__=='__main__':
    main()
