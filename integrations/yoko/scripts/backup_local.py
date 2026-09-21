"""Copy a synthetic SQLite database consistently, using SQLite's backup API."""
import argparse
import sqlite3
from pathlib import Path

def backup(source,target):
    source,target=Path(source),Path(target)
    if not source.is_file():raise ValueError("Source database is missing")
    if target.exists():raise ValueError("Destination already exists; choose a new file")
    src=sqlite3.connect(source.resolve().as_uri()+"?mode=ro",uri=True)
    try:
        mode=src.execute("SELECT value FROM meta WHERE key='data_mode'").fetchone()
        if not mode or mode[0]!="synthetic":raise ValueError("Only synthetic local databases are supported")
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb'):pass
        target.chmod(0o600)
        dst=sqlite3.connect(target)
        try:
            dst.execute('PRAGMA secure_delete=ON')
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("Integrity check failed")
            # Session credentials are not needed in a restored test database.
            dst.execute("DELETE FROM sessions")
            for table in ('external_sessions','login_flows','oauth_approvals'):
                if dst.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                    dst.execute('DELETE FROM '+table)
            if dst.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='external_identities'").fetchone():
                # Restores require deliberate re-enrollment before external access.
                dst.execute('DELETE FROM external_identities')
            if dst.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='client_grants'").fetchone():
                dst.execute("DELETE FROM client_grants")
            dst.commit()
            dst.execute('VACUUM')
        finally:dst.close()
    finally:src.close()

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path);p.add_argument("target",type=Path)
    a=p.parse_args();backup(a.source,a.target)
    print(f"Synthetic backup written: {a.target}. Start with --db to restore; log in again.")
