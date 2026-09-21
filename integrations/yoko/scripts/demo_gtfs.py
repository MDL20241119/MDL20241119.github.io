"""Create a synthetic fixed-stop Flex feed from an isolated temporary Core DB."""
import argparse
import copy
import json
import secrets
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.core import Core
from scripts.configure_payment_demo import create
from scripts.configure_booking_demo import configure
from scripts.export_gtfs import export

def setup(core):
    configure(core)
    profile=copy.deepcopy(json.loads((ROOT/'fixtures/synthetic-catalog.json').read_text())['service'])
    profile['operating_hours']={d:[{'start_time_offset_sec':8*3600,'end_time_offset_sec':20*3600}] for d in profile['operating_hours']}
    profile['operating_hours']['holidays']=[]
    # Synthetic calendar exceptions, not Japan's official holiday calendar.
    profile['holiday_dates']=['2026-09-23']
    profile['special_operating_hours']=[{'date':'2026-12-31','time_slots':[{'start_time_offset_sec':23*3600,'end_time_offset_sec':26*3600}]},{'date':'2027-01-01','time_slots':[]}]
    draft=core.prepare('admin-a1','service_configure',profile);op=secrets.token_hex(16)
    core.mutate('admin-a1',op,op,'service_configure',{'draft_id':draft['id'],'details':draft['details']})

def main(output):
    with tempfile.TemporaryDirectory() as temporary:
        db=create(Path(temporary)/'synthetic.sqlite3');setup(Core(db))
        return export(db,json.loads((ROOT/'fixtures/synthetic-gtfs.json').read_text()),output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    result=main(p.parse_args().output);print(json.dumps({'synthetic':True,'rows':result['rows'],'sha256':result['feed_sha256']},ensure_ascii=False))
