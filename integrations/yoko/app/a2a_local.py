"""Separate opt-in loopback process. No automatic initialization or publication."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='横のエレベーター：A2A 1.0 ローカル検証')
    parser.add_argument('--db', type=Path, default=Path('var/yoko.sqlite3'))
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    if args.host != '127.0.0.1' or os.environ.get('YOKO_ENV', 'local') != 'local' or not 1 <= args.port <= 65535:
        parser.error('ローカル検証専用です。本番モード・外部公開は無効です。')
    if not args.db.is_file(): parser.error('先に通常アプリで作成したローカルDBを指定してください。')
    try:
        import uvicorn
        from .core import Core
        from .a2a_adapter import create_app
        app = create_app(Core(args.db), args.port)
    except ImportError: parser.error('requirements-agents.lockの追加依存をインストールしてください。')
    except ValueError as error: parser.error(str(error))
    print(f'横のエレベーター A2A（架空データ・本人確認付き） http://127.0.0.1:{args.port}/a2a', flush=True)
    uvicorn.run(app, host=args.host, port=args.port, proxy_headers=False, access_log=False,
        log_level='critical', timeout_keep_alive=5, limit_concurrency=30)


if __name__ == '__main__': main()
