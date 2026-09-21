#!/usr/bin/env python3
"""Fetch the known official MLIT bundle; inspect archives without executing any content."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
import zipfile

URL='https://www.mlit.go.jp/commmmons/document/003/commmmons_doc_003_ver01.zip'
MAX_DOWNLOAD=80*1024*1024
MAX_EXTRACTED=150*1024*1024
MAX_MEMBERS=5000
ALLOWED_SUFFIXES={'.json','.yaml','.yml'}

def safe_member(info: zipfile.ZipInfo) -> bool:
    name=info.filename
    path=PurePosixPath(name)
    mode=info.external_attr >> 16
    return bool(name) and not path.is_absolute() and '..' not in path.parts and '\\' not in name and ':' not in name and not stat.S_ISLNK(mode)

class OfficialRedirectOnly(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urlparse(newurl)
        if p.scheme!='https' or p.hostname!='www.mlit.go.jp' or p.username or p.password:
            raise ValueError('refusing redirect outside official HTTPS host')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def process_archive(archive: Path, output: Path) -> dict:
    extracted=[]
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist()
        if len(infos)>MAX_MEMBERS or sum(x.file_size for x in infos)>MAX_EXTRACTED:
            raise ValueError('archive exceeds safety limits')
        names=set()
        for x in infos:
            if not safe_member(x) or x.filename in names:
                raise ValueError('unsafe or duplicate archive path')
            names.add(x.filename)
            if x.file_size > 25_000_000:
                # Large files are permitted in the listing but are never extracted.
                continue
            if x.file_size > 1_000_000 and x.file_size/max(x.compress_size,1)>200:
                raise ValueError('suspicious compression ratio')
        entries=[{'path':x.filename,'bytes':x.file_size} for x in infos]
        for x in infos:
            if x.is_dir() or x.file_size>25_000_000 or PurePosixPath(x.filename).suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            p=output/'extracted'/x.filename
            p.parent.mkdir(parents=True,exist_ok=True)
            raw=z.read(x)
            with p.open('xb') as f:
                f.write(raw)
            extracted.append({'path':p.relative_to(output).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    return {'members':entries,'json_yaml_candidates':extracted,'provenance_or_conformance_verified':False}

def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists():
        ap.error('output already exists; choose a new directory (no implicit overwrite)')
    try:
        opener=build_opener(OfficialRedirectOnly())
        req=Request(URL,headers={'User-Agent':'Yoko-Elevator-Source-Preparation/1.1'})
        with tempfile.TemporaryDirectory() as temp:
            archive=Path(temp)/'official.zip'
            total=0
            with opener.open(req,timeout=30) as resp, archive.open('xb') as f:
                if resp.status != 200:
                    raise ValueError(f'HTTP {resp.status}')
                while True:
                    block=resp.read(1024*1024)
                    if not block:break
                    total+=len(block)
                    if total>MAX_DOWNLOAD:raise ValueError('download exceeds safety limit')
                    f.write(block)
            if not zipfile.is_zipfile(archive):
                raise ValueError('response is not a ZIP; do not use HTML/error output as a specification')
            a.output.mkdir(parents=True)
            report=process_archive(archive,a.output)
            raw=archive.read_bytes()
            target=a.output/'commmmons_doc_003_ver01.zip'
            with target.open('xb') as f:f.write(raw)
            report.update({'source_url':URL,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
                           'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                           'redistribution_terms':'NOT_VERIFIED','official_openapi_selected':False})
            (a.output/'acquisition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({'output':str(a.output),'candidates':len(report['json_yaml_candidates']),
                              'next':'Select the official schema, retain references and review terms; then run index_openapi.py. No conformance claim.'},ensure_ascii=False))
    except Exception as exc:
        ap.exit(1,f'Acquisition failed: {exc}\nNo official conformance has been established. Inspect partial output before retrying.\n')
if __name__=='__main__':
    main()
