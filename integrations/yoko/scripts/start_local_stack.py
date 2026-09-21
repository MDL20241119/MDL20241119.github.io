"""Start the local web/API process and optional agent adapters; Ctrl+C stops all."""
import argparse
import importlib.util
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=ROOT/'var/yoko.sqlite3')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--agents',action='store_true')
    parser.add_argument('--enable-mlit-local',action='store_true')
    args=parser.parse_args()
    if os.environ.get('YOKO_ENV','local')!='local' or not 1<=args.port<=(65533 if args.agents else 65535):
        parser.error('ローカル検証用の有効なポートを指定してください。')
    modules=['app']+(['app.mcp_local','app.a2a_local'] if args.agents else [])
    required=(['mcp','a2a','uvicorn'] if args.agents else [])+(['jsonschema'] if args.enable_mlit_local else [])
    if any(importlib.util.find_spec(name) is None for name in required):
        parser.error('先にrequirements-agents.lock（MLITのみならrequirements-mlit.lock）の依存をインストールしてください。')
    reservations=[]
    try:
        for index in range(len(modules)):
            sock=socket.socket();reservations.append(sock);sock.bind(('127.0.0.1',args.port+index))
    except OSError:
        parser.error('指定ポートは使用中です。既存のプロセスを確認するか、別の--portを指定してください。')
    finally:
        for sock in reservations:sock.close()
    os.umask(0o077)
    from app.db import initialize
    initialize(args.db)
    children=[]
    def stop(signum,frame): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    try:
        for index,module in enumerate(modules):
            cmd=[sys.executable,'-m',module,'--db',str(args.db.resolve()),'--port',str(args.port+index)]
            if index==0 and args.enable_mlit_local:cmd.append('--enable-mlit-local')
            children.append(subprocess.Popen(cmd,cwd=ROOT))
        while True:
            for child in children:
                if child.poll() is not None:
                    print('構成プロセスが終了したため、全体を停止します。DBは保持します。',file=sys.stderr)
                    return 1
            time.sleep(.1)
    except KeyboardInterrupt:
        return 0
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(5)
            except subprocess.TimeoutExpired:child.kill();child.wait()


if __name__=='__main__':sys.exit(main())
