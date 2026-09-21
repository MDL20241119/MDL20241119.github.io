"""Verify a saved A2A Card against an operator-approved trust pin; no network."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.agent_trust import verify_card

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--card',type=Path,required=True); p.add_argument('--trust',type=Path,required=True)
    args=p.parse_args()
    verify_card(args.card.read_bytes(),json.loads(args.trust.read_text()),time.time())
    print('Pinned Agent Card signature verified. This does not authorize a passenger operation.')
