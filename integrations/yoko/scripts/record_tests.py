"""Run executable tests and retain their actual names, failures and scope."""
import argparse
import io
import json
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))

class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.passed=[]
    def addSuccess(self,test):
        super().addSuccess(test);self.passed.append(test.id())

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope',choices=['application','preparation'],required=True)
    args=parser.parse_args()
    folder='tests' if args.scope=='application' else 'checks'
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/folder))
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordedResult).run(suite)
    directory=ROOT/'artifacts/test-results';directory.mkdir(parents=True,exist_ok=True)
    report={'scope':args.scope,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'passed':result.passed,'failed':[{'test':test.id(),'traceback':trace} for test,trace in result.failures+result.errors],'skipped':[{'test':test.id(),'reason':reason} for test,reason in result.skipped],'standard_conformance':'NOT_TESTED','rendered_browser':'NOT_TESTED'}
    if args.scope=='application':
        report['standard_conformance']='NOT_ESTABLISHED_PARTIAL_LOCAL_CONTRACT_TESTS_ONLY'
        from app.mlit import SUPPORTED,BLOCKERS
        report['mlit_contract_test_scope']=f'19 authentication refusals; {len(BLOCKERS)} blocked operations; {len(SUPPORTED)} operation subsets with success and negative cases; not full conformance'
    (directory/f'{args.scope}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (directory/f'{args.scope}.txt').write_text(stream.getvalue())
    print(stream.getvalue())
    sys.exit(0 if result.wasSuccessful() else 1)
