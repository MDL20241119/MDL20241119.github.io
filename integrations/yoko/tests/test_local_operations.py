"""Local operational acceptance: invariant detection, safe backup, supervisor."""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from app.db import connect
from scripts.inspect_local_health import inspect
from scripts.backup_local import backup
from scripts.mcp_test_support import http
from tests.test_p3 import Fixture


class LocalOperationsTests(Fixture):
    def test_readonly_health_and_seat_divergence_detection(self):
        ride=self.driver('accept',self.create(count=2))
        before=self.sql('SELECT count(*) FROM operations')
        result=inspect(self.path)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['pending_fake_notifications']['outbox'],2)
        self.assertEqual(self.sql('SELECT count(*) FROM operations'),before)
        self.assertNotIn(ride['id'],json.dumps(result))
        self.sql('UPDATE runs SET reserved=1')
        self.assertFalse(inspect(self.path)['checks']['seat_ledger'])
        self.assertEqual(inspect(self.path)['status'],'FAIL')

    def test_backup_omits_credentials_and_keeps_domain_and_task(self):
        self.create();grant=self.grant();auth=self.authz(grant)
        task=self.core.tasks.send('rider-a1',auth,'backup-message',{'action':'execute'})
        target=Path(self.temp.name)/'backup.sqlite3';backup(self.path,target)
        db=connect(target)
        try:
            self.assertEqual(db.execute('SELECT count(*) FROM client_grants').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT id FROM agent_tasks').fetchone()[0],task['id'])
        finally:db.close()
        self.assertEqual(inspect(target)['status'],'PASS')
        self.assertEqual(os.stat(target).st_mode & 0o777,0o600)
        with self.assertRaises(ValueError):backup(self.path,target)

    def test_supervisor_starts_all_ports_and_sigterm_stops_all(self):
        reservations=[]
        try:
            for port in range(19000,19998,3):
                try:
                    for p in (port,port+1,port+2):
                        sock=socket.socket();reservations.append(sock);sock.bind(('127.0.0.1',p))
                    break
                except OSError:
                    for sock in reservations:sock.close()
                    reservations=[]
            else:self.fail('No local test ports available')
        finally:
            for sock in reservations:sock.close()
        log=Path(self.temp.name)/'stack.log'
        with log.open('w+') as output:
            process=subprocess.Popen([sys.executable,'scripts/start_local_stack.py','--agents','--enable-mlit-local','--db',str(self.path),'--port',str(port)],stdout=output,stderr=output)
            try:
                deadline=time.monotonic()+10
                while True:
                    try:
                        self.assertEqual(http(port,'/')[0],200)
                        self.assertEqual(http(port+1,'/mcp')[0],405)
                        self.assertEqual(http(port+2,'/.well-known/agent-card.json')[0],200)
                        break
                    except (ConnectionError,OSError):
                        if process.poll() is not None or time.monotonic()>deadline:
                            self.fail('Local stack did not start: '+log.read_text())
                        time.sleep(.05)
                process.terminate();self.assertEqual(process.wait(10),0)
            finally:
                if process.poll() is None:process.terminate();process.wait(10)
        for p in (port,port+1,port+2):
            with socket.socket() as sock:self.assertNotEqual(sock.connect_ex(('127.0.0.1',p)),0)
        self.assertEqual(inspect(self.path)['status'],'PASS')
