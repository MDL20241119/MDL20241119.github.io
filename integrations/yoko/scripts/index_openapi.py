#!/usr/bin/env python3
"""Index a locally acquired OpenAPI file. No network, no dereferencing, no API execution."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

METHODS = {'get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace'}

def load_document(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    if len(raw) > 25_000_000:
        raise ValueError('input exceeds 25 MB safety limit')
    try:
        if path.suffix.lower() == '.json':
            obj = json.loads(raw.decode('utf-8-sig'))
        elif path.suffix.lower() in {'.yaml', '.yml'}:
            try:
                import yaml
            except ImportError as exc:
                raise ValueError('YAML requires an already installed PyYAML; no auto-install is performed') from exc
            obj = yaml.safe_load(raw.decode('utf-8-sig'))
        else:
            raise ValueError('select a .json, .yaml or .yml source')
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'could not parse input: {exc}') from exc
    if not isinstance(obj, dict):
        raise ValueError('OpenAPI root must be an object')
    if not str(obj.get('openapi', '')).startswith('3.'):
        raise ValueError('this helper supports OpenAPI 3.x only; do not convert an official source silently')
    if not isinstance(obj.get('paths'), dict) or not isinstance(obj.get('info'), dict):
        raise ValueError('OpenAPI paths and info objects are required')
    return obj, raw

def build_index(doc: dict) -> dict:
    ops, refs = [], set()
    seen: set[int] = set()
    def walk(node):
        if not isinstance(node, (dict, list)) or id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, dict):
            if isinstance(node.get('$ref'), str):
                refs.add(node['$ref'])
            for val in node.values():
                walk(val)
        else:
            for val in node:
                walk(val)
    walk(doc)
    for path, item in sorted(doc['paths'].items()):
        if not isinstance(path, str) or not isinstance(item, dict):
            raise ValueError('invalid path item')
        for method, op in sorted(item.items()):
            if method not in METHODS:
                continue
            if not isinstance(op, dict):
                raise ValueError('operation must be an object')
            ops.append({'method': method.upper(), 'path': path, 'operation_id': op.get('operationId'),
                        'summary': op.get('summary'), 'request_body': op.get('requestBody'),
                        'path_parameters': item.get('parameters', []), 'operation_parameters': op.get('parameters', []),
                        'responses': op.get('responses', {}), 'security': op.get('security', doc.get('security', [])),
                        'applicability': 'NOT_REVIEWED', 'core_operation': None,
                        'test_id': None, 'test_status': 'NOT_RUN'})
    return {'openapi_version': doc['openapi'], 'api_info': doc['info'], 'operations': ops,
            'references': sorted(refs), 'external_references': sorted(r for r in refs if not r.startswith('#')),
            'note': 'INDEX ONLY. References are not resolved; no full schema, conformance, auth or interoperability validation was performed.'}

def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path)
    ap.add_argument('--source-url',required=True)
    ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args()
    url=urlparse(a.source_url)
    if url.scheme != 'https' or not url.netloc or url.username or url.password:
        ap.error('source-url must be an HTTPS provenance URL without credentials')
    try:
        doc, raw=load_document(a.source)
        idx=build_index(doc)
        if a.output.exists():
            raise ValueError('output exists; choose a new evidence directory to avoid overwrite')
        a.output.mkdir(parents=True)
        record={'indexed_at_utc':datetime.now(timezone.utc).isoformat(), 'source_url':a.source_url,
                'filename':a.source.name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                'official_provenance_independently_verified':False,'redistribution_terms':'NOT_VERIFIED',
                'source_acquisition_time':'NOT_RECORDED_BY_THIS_LOCAL_INDEXER'}
        (a.output/'source.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (a.output/'operations.json').write_text(json.dumps(idx,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'operations':len(idx['operations']),'sha256':record['sha256'],'output':str(a.output),'conformance_test':'NOT_RUN'},ensure_ascii=False))
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
if __name__=='__main__':
    main()
