"""Read-only integrity/queue counts. Emits no identities, tokens or ride locations."""
import argparse
import json
import sqlite3
import time
from datetime import datetime,timezone
from pathlib import Path


def inspect(path):
    path=Path(path)
    if not path.is_file():raise ValueError('Database does not exist')
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        db.execute('BEGIN')
        metadata=dict(db.execute('SELECT key,value FROM meta'))
        if metadata.get('data_mode')!='synthetic' or metadata.get('schema_version')!='8':
            raise ValueError('Start the normal local application to migrate a synthetic database first')
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        foreign_keys=list(db.execute('PRAGMA foreign_key_check'))==[]
        capacity=db.execute('SELECT count(*) FROM runs r JOIN vehicles v ON v.id=r.vehicle_id WHERE r.reserved>v.capacity OR r.reserved<0').fetchone()[0]
        seats=db.execute("SELECT count(*) FROM runs r WHERE r.reserved != (SELECT COALESCE(sum(passengers),0) FROM rides WHERE run_id=r.id AND status IN ('assigned','arrived','onboard'))").fetchone()[0]
        missing=db.execute('SELECT count(*) FROM events e LEFT JOIN outbox o ON e.id=o.event_id WHERE o.event_id IS NULL').fetchone()[0]
        missing_catalog=db.execute('SELECT count(*) FROM catalog_events e LEFT JOIN catalog_outbox o ON e.id=o.event_id WHERE o.event_id IS NULL').fetchone()[0]
        queues={table:db.execute('SELECT count(*) FROM '+table+' WHERE delivered=0').fetchone()[0] for table in ('outbox','catalog_outbox')}
        tasks=dict(db.execute('SELECT state,count(*) FROM agent_tasks GROUP BY state'))
        expired=db.execute("SELECT count(*) FROM agent_tasks WHERE state='working' AND lease_until<=?",(time.time(),)).fetchone()[0]
        checks={'sqlite_integrity':integrity,'foreign_keys':foreign_keys,'capacity':capacity==0,'seat_ledger':seats==0,
            'ride_event_outbox':missing==0,'catalog_event_outbox':missing_catalog==0}
        return {'status':'PASS' if all(checks.values()) else 'FAIL','checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'LOCAL_SYNTHETIC_READ_ONLY','schema_version':8,'checks':checks,'pending_fake_notifications':queues,
            'task_state_counts':tasks,'expired_task_leases':expired,'production_monitoring':False}
    finally:db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',type=Path,default=Path('var/yoko.sqlite3'))
    args=parser.parse_args()
    try:report=inspect(args.db)
    except (ValueError,sqlite3.Error) as error:parser.error(str(error))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['status']=='PASS' else 1)
