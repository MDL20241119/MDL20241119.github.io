"""The Web-only launcher is usable without the optional agent/LINE stack."""
import http.client
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


class WebStartTests(unittest.TestCase):
    def launch(self, db, cwd, port=0):
        return subprocess.Popen([sys.executable,'-S',str(ROOT/'start_web.py'),
            '--no-browser','--port',str(port),'--db',str(db)],
            cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)

    def test_web_only_starts_outside_project_without_site_packages_and_reuses_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'data/web.sqlite3'
            for run in range(2):
                process=self.launch(db,tmp)
                lines=queue.Queue()
                threading.Thread(target=lambda: [lines.put(line) for line in process.stdout],daemon=True).start()
                try:
                    line=lines.get(timeout=10)
                    self.assertIn('http://127.0.0.1:',line)
                    port=int(line.strip().rsplit(':',1)[1])
                    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                    connection.request('GET','/')
                    response=connection.getresponse()
                    html=response.read().decode()
                    connection.close()
                    self.assertEqual(response.status,200)
                    self.assertIn('Webアプリをはじめる',html)
                    self.assertNotIn('/auth/line',html)
                    self.assertTrue(db.is_file())
                    if run==0:
                        from app.core import Core
                        from tests.test_core import REQUEST
                        core=Core(db);draft=core.prepare('rider-a1','request',REQUEST)
                        core.mutate('rider-a1','web-start-operation','web-start-operation','request',{'draft_id':draft['id'],'details':draft['details']})
                    else:
                        from app.core import Core
                        self.assertEqual(len(Core(db).snapshot('rider-a1')['rides']),1)
                finally:
                    process.terminate();process.wait(5);process.stdout.close()

    def test_busy_port_does_not_open_a_different_server(self):
        with tempfile.TemporaryDirectory() as tmp, socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen()
            process=self.launch(Path(tmp)/'web.sqlite3',tmp,listener.getsockname()[1])
            output=process.communicate(timeout=10)[0]
            self.assertEqual(process.returncode,1)
            self.assertIn('起動できません',output)
            self.assertNotIn('http://127.0.0.1:',output)
