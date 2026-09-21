import argparse
import os
import threading
import webbrowser
from pathlib import Path
from .db import initialize
from .server import LocalServer
from .core import Core

def main(argv=None):
    parser=argparse.ArgumentParser(description="横のエレベーター：合成データ専用ローカルアプリ")
    parser.add_argument("--db",type=Path,default=Path("var/yoko.sqlite3"))
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--mode",choices=["local","production"],default="local")
    parser.add_argument("--deliver-fake",action="store_true")
    parser.add_argument("--simulate-notification-failure",action="store_true")
    parser.add_argument("--enable-mlit-local",action="store_true",help="Enable the partial MLIT adapter for local contract tests only")
    parser.add_argument("--open-browser",action="store_true",help="起動時にWebアプリをブラウザーで開く")
    parser.add_argument("--no-browser",action="store_false",dest="open_browser",help="ブラウザーを自動で開かない")
    args=parser.parse_args(argv)
    if args.mode!="local" or args.host!="127.0.0.1" or os.environ.get("YOKO_ENV","local")!="local":
        parser.error("ローカル検証専用です。本番モード・外部公開は無効です。")
    os.umask(0o077)
    initialize(args.db)
    if args.deliver_fake:
        print(Core(args.db).deliver_fake(args.simulate_notification_failure))
        return
    try:
        server=LocalServer((args.host,args.port),args.db,enable_mlit=args.enable_mlit_local)
    except OSError as error:
        parser.exit(1,f"起動できません。ポート {args.port} が使用中の場合は、前のアプリを停止するか --port 8865 を指定してください。\n{error}\n")
    url=f"http://127.0.0.1:{server.server_address[1]}"
    print(f"横のエレベーター Webアプリ（架空データのみ） {url}",flush=True)
    print(f"保存先: {args.db.resolve()}\n終了: この画面で Ctrl+C。保存した依頼は次回起動時も残ります。",flush=True)
    print("テストID: rider-a1 / driver-a1 / admin-a1  共通テストパスワード: local-test-only",flush=True)
    if args.open_browser:
        def open_browser():
            try:
                opened=webbrowser.open(url,new=2)
            except webbrowser.Error:
                opened=False
            if not opened: print(f"ブラウザーで {url} を開いてください。",flush=True)
        threading.Thread(target=open_browser,daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__=="__main__":
    main()
