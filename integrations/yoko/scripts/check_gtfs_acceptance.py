"""Reproduce a valid synthetic feed and real validator rejection cases."""
import argparse
import csv
import io
import json
import sys
import zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.gtfs import zip_bytes
from scripts.demo_gtfs import main as demo
from scripts.validate_gtfs import run

def check(jar,output):
    output=Path(output)
    if output.exists():raise FileExistsError('Choose a new acceptance output directory')
    demo(output/'feed');feed=output/'feed/synthetic-gtfs.zip'
    valid=run(feed,jar,output/'canonical','2026-09-19')
    if valid['status']!='PASS':raise RuntimeError('Positive feed validation failed')
    with zipfile.ZipFile(feed) as archive:files={n:archive.read(n) for n in archive.namelist()}
    bad=files.copy();reader=csv.DictReader(io.StringIO(bad['stop_times.txt'].decode()));rows=list(reader)
    rows[0]['stop_id']='missing-stop-negative-test'
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=reader.fieldnames,lineterminator='\r\n');writer.writeheader();writer.writerows(rows)
    bad['stop_times.txt']=stream.getvalue().encode();negative=output/'invalid-reference.zip';negative.write_bytes(zip_bytes(bad))
    rejected=run(negative,jar,output/'invalid-reference','2026-09-19')
    if rejected['status']!='FAIL' or not rejected['errors']:raise RuntimeError('Canonical validator failed to reject a broken stop reference')
    bad=files.copy();del bad['translations.txt'];negative=output/'missing-readings.zip';negative.write_bytes(zip_bytes(bad))
    domestic=run(negative,jar,output/'missing-readings','2026-09-19')
    if domestic['status']!='FAIL' or not domestic['domestic']['errors']:raise RuntimeError('Domestic checker failed to reject missing readings')
    report={'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),'synthetic':True,'production_conformance':'NOT_ESTABLISHED','checks':[
        'fixed-stop synthetic feed exported through Core','canonical 8.0.1 positive feed has zero ERROR/system notices',
        'JP v4 limited mandatory-field checks pass','canonical rejects unknown stop reference even with process exit 0',
        'domestic checker rejects absent translations','all canonical warnings retained'],
        'feed_sha256':valid['feed_sha256'],'canonical_error_count':sum(n['totalNotices'] for n in valid['errors']),
        'canonical_warning_count':sum(n['totalNotices'] for n in valid['warnings']),
        'canonical_warning_codes':[n['code'] for n in valid['warnings']],
        'negative_feeds':'Expected FAIL examples only. Do not use as transport feeds.',
        'remaining':['real source/master approval','live booking and contact URLs','consumer semantic interoperability','full applicable domestic rules','Realtime source/disclosure','full MLIT API conformance','MCP','A2A','P5']}
    (output/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jar',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();print(json.dumps(check(args.jar,args.output),ensure_ascii=False,indent=2))
