"""Operator-only external identity enrollment/revocation; no self-registration."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core import Core
from app.external_auth import Identities


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--identity-file', type=Path, help='Private JSON with issuer, audience, subject, actor')
    p.add_argument('--revoke', help='Existing identity ID')
    args = p.parse_args()
    if not args.db.is_file() or bool(args.identity_file) == bool(args.revoke): p.error('Supply an existing database and exactly one enrollment file or revocation ID')
    identities = Identities(Core(args.db))
    if args.revoke: identities.revoke(args.revoke); print('External identity revoked.')
    else:
        values = json.loads(args.identity_file.read_text())
        if set(values) != {'issuer', 'audience', 'subject', 'actor'}: p.error('Unexpected identity fields')
        print(json.dumps({'identity_id': identities.bind(**values)}))
