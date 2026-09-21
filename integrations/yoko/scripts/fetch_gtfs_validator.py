"""Fetch only the pinned official CLI JAR; verify the release SHA-256 before use."""
import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from scripts.validate_gtfs import JAR_URL,JAR_SHA256

def fetch(target):
    target=Path(target)
    if target.exists():raise FileExistsError('Existing files are not overwritten')
    request=urllib.request.Request(JAR_URL,headers={'User-Agent':'Yoko-Elevator-Local-Validation'})
    with urllib.request.urlopen(request,timeout=30) as response:data=response.read(50*1024*1024+1)
    if len(data)>50*1024*1024 or hashlib.sha256(data).hexdigest()!=JAR_SHA256:raise ValueError('Download size or hash mismatch')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(data)
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('var/gtfs-validator-8.0.1-cli.jar'))
    print(fetch(p.parse_args().output))
