"""Explicit opt-in local MCP process; shares the existing database and Core."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='横のエレベーター：読取・本人確認付きMCP（ローカル専用）')
    parser.add_argument('--db', type=Path, default=Path('var/yoko.sqlite3'))
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    if args.host != '127.0.0.1' or os.environ.get('YOKO_ENV', 'local') != 'local' or not 1 <= args.port <= 65535:
        parser.error('ローカル検証専用です。本番モード・外部公開は無効です。')
    if not args.db.is_file():
        parser.error('先に通常アプリで作成したローカルDBを指定してください。MCPはDBを自動作成しません。')
    try:
        import uvicorn
        from .core import Core
        from .mcp_adapter import create_app
    except ImportError:
        parser.error('requirements-mcp.lockの追加依存をインストールしてください。')
    print(f'横のエレベーター MCP（架空データ・本人確認付き） http://127.0.0.1:{args.port}/mcp', flush=True)
    uvicorn.run(create_app(Core(args.db), args.port), host=args.host, port=args.port, proxy_headers=False,
        access_log=False, log_level='critical', timeout_keep_alive=5, limit_concurrency=30)


if __name__ == '__main__':
    main()
