import concurrent.futures, sqlite3, tempfile, pathlib, re, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
SQL=re.findall(r"db\(\)\.prepare\('([^']+)'\)", (ROOT/'lib/store.ts').read_text())
insert=next(x for x in SQL if x.startswith('INSERT INTO receipts'))
update=next(x for x in SQL if x.startswith('UPDATE workspaces'))
audit=next(x for x in SQL if x.startswith('INSERT INTO audit'))
class Concurrency(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=self.temp.name+'/db.sqlite';self.db=sqlite3.connect(self.path)
  self.db.executescript((ROOT/'drizzle/0000_jazzy_ultragirl.sql').read_text());self.db.execute('INSERT INTO workspaces VALUES (?,?,?)',('a','initial',1));self.db.execute('INSERT INTO workspaces VALUES (?,?,?)',('b','other tenant',1));self.db.commit()
 def tearDown(self):self.db.close();self.temp.cleanup()
 def write(self,key,command):
  con=sqlite3.connect(self.path,timeout=10)
  try:
   con.execute('BEGIN IMMEDIATE');con.execute(insert,('a',key,command,2,'digest','now','a',1));changed=con.execute(update,('changed',2,'a',1,'a',key,command)).rowcount;con.execute(audit,(command,'a','tester','command','{}','now','a',key,command));con.commit();return changed
  except sqlite3.IntegrityError:con.rollback();return 0
  finally:con.close()
 def test_simultaneous_confirmations_only_one_wins(self):
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:r=list(p.map(lambda i:self.write('key'+str(i),'cmd'+str(i)),[1,2]))
  self.assertEqual(sum(r),1);self.assertEqual(self.db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],1)
 def test_duplicate_retry_records_once(self):
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:r=list(p.map(lambda i:self.write('same-key','cmd'+str(i)),[1,2]))
  self.assertEqual(sum(r),1);self.assertEqual(self.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],1)
 def test_other_tenant_is_unchanged(self):
  self.write('key','cmd');self.assertEqual(self.db.execute('SELECT state FROM workspaces WHERE owner=?',('b',)).fetchone()[0],'other tenant')
 def test_stale_request_has_no_side_effect(self):
  self.write('a','cmd1');self.assertEqual(self.write('b','cmd2'),0);self.assertEqual(self.db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],1)
if __name__=='__main__':unittest.main()
