"""Start the loopback HTTPS integration server with explicit TLS and providers."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit

from .connected import configuration, create_app
from .core import Core


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--cert', type=Path, required=True)
    parser.add_argument('--key', type=Path, required=True)
    parser.add_argument('--card-signing-key', type=Path)
    parser.add_argument('--card-key-id')
    args = parser.parse_args()
    for path in (args.db, args.config, args.cert, args.key):
        if not path.is_file(): parser.error('Database, configuration and TLS files must already exist')
    config = configuration(args.config)
    if bool(args.card_signing_key) != bool(args.card_key_id): parser.error('Supply both Card signing options')
    from .agent_trust import signer
    card_signer = signer(args.card_signing_key, args.card_key_id) if args.card_signing_key else None
    app = create_app(Core(args.db), config, card_signer=card_signer)
    uvicorn.run(app, host='127.0.0.1', port=urlsplit(config['origin']).port,
        ssl_certfile=str(args.cert), ssl_keyfile=str(args.key), proxy_headers=False,
        access_log=False, server_header=False, log_level='warning', timeout_keep_alive=5,
        timeout_graceful_shutdown=20, limit_concurrency=32, h11_max_incomplete_event_size=16384)


if __name__ == '__main__': main()
