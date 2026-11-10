#!/usr/bin/env python3
"""Package private Yufuin source into the existing encrypted publication.

The HTML and PDF must be prepared outside the public checkout. Supply the
shared password through stdin; no plaintext asset or password is committed.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def package(repo, html_path, pdf_path, password):
    root = Path(repo).resolve()
    access = root / 'oita-mirai-mobility-consortium/dialogue/yufuin/access'
    if not (access / 'manifest.json').is_file():
        raise ValueError('Existing Yufuin publication not found')
    # Public source must not accidentally include the private working files.
    for path in (html_path, pdf_path):
        if Path(path).resolve().is_relative_to(root):
            raise ValueError('Prepare plaintext sources outside the public checkout')
    old = json.loads((access / 'manifest.json').read_text())
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password, salt, 600000, 32)
    manifest = {
        'version': 1, 'kdf': 'PBKDF2-SHA256', 'iterations': 600000,
        'cipher': 'AES-256-GCM', 'salt': base64.b64encode(salt).decode(),
        'key_id': os.urandom(16).hex(), 'assets': {},
    }
    written = []
    for name, source in (('content', html_path), ('proposal', pdf_path)):
        plain = Path(source).read_bytes()
        expected = b'<!doctype html' if name == 'content' else b'%PDF-'
        if not plain.lstrip().lower().startswith(expected.lower()):
            raise ValueError('Unexpected source format: ' + name)
        iv = os.urandom(12)
        ciphertext = AESGCM(key).encrypt(
            iv, gzip.compress(plain, compresslevel=9, mtime=0),
            ('yufuin-mec-v1:' + name).encode(),
        )
        if len(ciphertext) > 67108864:
            raise ValueError('Asset exceeds viewer limit')
        digest = hashlib.sha256(ciphertext).hexdigest()
        chunks = []
        for i, start in enumerate(range(0, len(ciphertext), 131072)):
            relative = f'payload/{name}-{digest[:12]}-{i:03d}.bin'
            path = access / relative
            path.write_bytes(ciphertext[start:start + 131072])
            chunks.append(relative)
            written.append(relative)
        manifest['assets'][name] = {
            'iv': base64.b64encode(iv).decode(), 'bytes': len(ciphertext),
            'sha256': digest, 'chunks': chunks,
        }
        # Verify an exact byte roundtrip before replacing the manifest.
        recovered = gzip.decompress(AESGCM(key).decrypt(
            iv, b''.join((access / f).read_bytes() for f in chunks),
            ('yufuin-mec-v1:' + name).encode(),
        ))
        if recovered != plain:
            raise ValueError('Roundtrip mismatch: ' + name)
    temp = access / 'manifest.json.tmp'
    temp.write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')) + '\n')
    temp.replace(access / 'manifest.json')
    # Remove only assets referenced by the previous manifest, within payload/.
    for asset in old['assets'].values():
        for relative in asset['chunks']:
            path = access / relative
            if path.parent == access / 'payload' and relative not in written:
                path.unlink(missing_ok=True)
    return {n: {'bytes': a['bytes'], 'chunks': len(a['chunks'])}
            for n, a in manifest['assets'].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--html', required=True)
    parser.add_argument('--pdf', required=True)
    args = parser.parse_args()
    previous = None
    if sys.stdin.isatty():
        import termios
        previous = termios.tcgetattr(sys.stdin.fileno())
        hidden = previous.copy()
        hidden[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, hidden)
    try:
        print('Ready for shared password on stdin (input hidden).', flush=True)
        password = sys.stdin.buffer.readline().rstrip(b'\r\n')
        if not password:
            raise ValueError('A password is required')
        result = package(args.repo, args.html, args.pdf, password)
        print(json.dumps(result))
    finally:
        if previous is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, previous)


if __name__ == '__main__':
    main()
