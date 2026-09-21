"""Run hash-pinned Canonical Validator locally and the domestic subset checks.

The Java process exit code alone does not indicate a valid GTFS feed. Inspect
ERROR notices, system errors and the reported version; retain all warnings.
The validator's network update check is disabled. No feed is uploaded.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.gtfs_validation import validate

VERSION='8.0.1'
JAR_SHA256='19293ddd9b6f954f216d4f12054bd8a3232921751c4484339e339764a91000e2'
JAR_URL='https://github.com/MobilityData/gtfs-validator/releases/download/v8.0.1/gtfs-validator-8.0.1-cli.jar'

def verify_jar(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=JAR_SHA256:raise ValueError('Canonical Validator JAR hash mismatch')

def summarize(report,system_errors,returncode):
    errors=[n for n in report.get('notices',[]) if n.get('severity')=='ERROR']
    warnings=[n for n in report.get('notices',[]) if n.get('severity')=='WARNING']
    system=system_errors.get('notices',['SYSTEM_REPORT_MISSING'])
    valid=returncode==0 and not errors and not system and report.get('summary',{}).get('validatorVersion')==VERSION and 'notices' in report
    return {'status':'PASS' if valid else 'FAIL','errors':errors,'warnings':warnings,'system_errors':system,'process_returncode':returncode}

def run(feed,jar,output,date):
    feed,jar,output=Path(feed),Path(jar),Path(output)
    verify_jar(jar);data=feed.read_bytes();domestic=validate(data)
    if output.exists():raise FileExistsError('Choose a new validation output directory')
    output.mkdir(parents=True,exist_ok=False)
    command=['java','-Duser.timezone=UTC','-jar',str(jar.resolve()),'-i',str(feed.resolve()),'-o',str(output.resolve()),'-c','JP','-d',date,'-svu','-p']
    with (output/'execution.log').open('w') as log:
        process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=False)
    report=json.loads((output/'report.json').read_text());system=json.loads((output/'system_errors.json').read_text())
    result=summarize(report,system,process.returncode)
    result.update({'checked_at_utc':datetime.now(timezone.utc).isoformat(),'validator_version':VERSION,'jar_url':JAR_URL,'jar_sha256':JAR_SHA256,'feed_sha256':hashlib.sha256(data).hexdigest(),'date_for_validation':date,'country_code':'JP','update_check_disabled':True,'uploaded':False,'domestic':domestic,'production_conformance':'NOT_ESTABLISHED'})
    if domestic['errors']:result['status']='FAIL'
    (output/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--feed',required=True,type=Path);p.add_argument('--jar',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--date',required=True)
    a=p.parse_args();result=run(a.feed,a.jar,a.output,a.date)
    print(json.dumps({k:result[k] for k in ('status','errors','warnings','system_errors','production_conformance')},ensure_ascii=False));sys.exit(0 if result['status']=='PASS' else 1)
