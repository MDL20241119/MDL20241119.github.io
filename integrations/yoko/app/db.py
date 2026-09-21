"""SQLite persistence, versioned schema and synthetic fixture bootstrap."""
import hashlib
import json
import secrets
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_PASSWORD = "local-test-only"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id), role TEXT NOT NULL,
 salt TEXT NOT NULL, password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
 eligible INTEGER NOT NULL DEFAULT 1 CHECK (eligible IN (0,1))
);
CREATE TABLE IF NOT EXISTS services (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id), name TEXT NOT NULL,
 timezone TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL DEFAULT 1,
 fare_json TEXT NOT NULL, policy_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stops (
 id TEXT PRIMARY KEY, service_id TEXT NOT NULL REFERENCES services(id), name TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1, photo_url TEXT
);
CREATE TABLE IF NOT EXISTS vehicles (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id),
 service_id TEXT NOT NULL REFERENCES services(id), driver_id TEXT NOT NULL REFERENCES users(id),
 capacity INTEGER NOT NULL CHECK(capacity>0), active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, vehicle_id TEXT NOT NULL REFERENCES vehicles(id),
 origin_stop_id TEXT NOT NULL, destination_stop_id TEXT NOT NULL,
 reserved INTEGER NOT NULL DEFAULT 0 CHECK(reserved>=0),
 accepting INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON runs(vehicle_id) WHERE active=1;
CREATE TABLE IF NOT EXISTS rides (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, rider_id TEXT NOT NULL REFERENCES users(id),
 service_id TEXT NOT NULL REFERENCES services(id), origin_stop_id TEXT NOT NULL REFERENCES stops(id),
 destination_stop_id TEXT NOT NULL REFERENCES stops(id), passengers INTEGER NOT NULL CHECK(passengers>0),
 fare_json TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('requested','assigned','arrived','onboard','completed','cancelled')),
 vehicle_id TEXT REFERENCES vehicles(id), driver_id TEXT REFERENCES users(id), run_id TEXT REFERENCES runs(id),
 version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rides_tenant ON rides(tenant_id,created_at);
CREATE TABLE IF NOT EXISTS drafts (
 id TEXT PRIMARY KEY, actor_id TEXT NOT NULL REFERENCES users(id), kind TEXT NOT NULL,
 details_json TEXT NOT NULL, expires_at REAL NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS operations (
 actor_id TEXT NOT NULL REFERENCES users(id), operation_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 kind TEXT NOT NULL, digest TEXT NOT NULL, ride_id TEXT NOT NULL REFERENCES rides(id),
 result_json TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(actor_id,operation_id), UNIQUE(actor_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, ride_id TEXT NOT NULL REFERENCES rides(id), actor_id TEXT NOT NULL,
 operation_id TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
 event_id TEXT PRIMARY KEY REFERENCES events(id), tenant_id TEXT NOT NULL,
 delivered INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT
);
CREATE TABLE IF NOT EXISTS fake_inbox (event_id TEXT PRIMARY KEY REFERENCES events(id), delivered_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, actor_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS client_grants (
 id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, actor_id TEXT NOT NULL REFERENCES users(id),
 client_id TEXT NOT NULL, audience TEXT NOT NULL, scopes_json TEXT NOT NULL,
 operation_json TEXT, expires_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS passenger_versions (actor_id TEXT PRIMARY KEY REFERENCES users(id), version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS passengers (
 id TEXT PRIMARY KEY REFERENCES users(id), tenant_id TEXT NOT NULL REFERENCES tenants(id),
 profile_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS terms (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id), service_id TEXT REFERENCES services(id),
 category TEXT NOT NULL, name TEXT NOT NULL, url TEXT NOT NULL, agreement_required INTEGER NOT NULL,
 active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS latest_term ON terms(tenant_id,COALESCE(service_id,''),category) WHERE active=1;
CREATE TABLE IF NOT EXISTS agreements (
 passenger_id TEXT NOT NULL REFERENCES passengers(id) ON DELETE CASCADE, terms_id TEXT NOT NULL REFERENCES terms(id),
 agreed_at TEXT NOT NULL, recorded_at TEXT NOT NULL, PRIMARY KEY(passenger_id,terms_id)
);
CREATE TABLE IF NOT EXISTS service_profiles (
 service_id TEXT PRIMARY KEY REFERENCES services(id), data_json TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stop_profiles (
 stop_id TEXT PRIMARY KEY REFERENCES stops(id), data_json TEXT NOT NULL, version INTEGER NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS catalog_operations (
 actor_id TEXT NOT NULL REFERENCES users(id), operation_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 kind TEXT NOT NULL, digest TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL,
 result_json TEXT NOT NULL, redacted INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
 PRIMARY KEY(actor_id,operation_id), UNIQUE(actor_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS catalog_events (
 id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, tenant_id TEXT NOT NULL, operation_id TEXT NOT NULL,
 kind TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS catalog_outbox (
 event_id TEXT PRIMARY KEY REFERENCES catalog_events(id), delivered INTEGER NOT NULL DEFAULT 0,
 attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT
);
CREATE TABLE IF NOT EXISTS catalog_fake_inbox (event_id TEXT PRIMARY KEY REFERENCES catalog_events(id));
CREATE TABLE IF NOT EXISTS route_policies (
 id TEXT PRIMARY KEY, service_id TEXT NOT NULL REFERENCES services(id),
 origin_stop_id TEXT NOT NULL REFERENCES stops(id), destination_stop_id TEXT NOT NULL REFERENCES stops(id),
 data_json TEXT NOT NULL, version INTEGER NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(service_id,origin_stop_id,destination_stop_id)
);
CREATE TABLE IF NOT EXISTS run_offers (
 run_id TEXT PRIMARY KEY REFERENCES runs(id), driver_id TEXT NOT NULL REFERENCES users(id),
 service_id TEXT NOT NULL REFERENCES services(id), plan_json TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (
 id TEXT PRIMARY KEY, passenger_id TEXT NOT NULL REFERENCES passengers(id) ON DELETE CASCADE,
 tenant_id TEXT NOT NULL, run_id TEXT NOT NULL REFERENCES runs(id),
 data_json TEXT NOT NULL, expires_at REAL NOT NULL, used_ride_id TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS own_candidates ON candidates(passenger_id,expires_at);
CREATE TABLE IF NOT EXISTS ride_bookings (
 ride_id TEXT PRIMARY KEY REFERENCES rides(id), candidate_id TEXT UNIQUE NOT NULL,
 data_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
 ride_id TEXT PRIMARY KEY REFERENCES rides(id),
 amount INTEGER NOT NULL CHECK(typeof(amount)='integer' AND amount BETWEEN 0 AND 2147483647),
 payment_status TEXT NOT NULL CHECK(payment_status IN ('uncollected','received','excluded','cancelled')),
 version INTEGER NOT NULL CHECK(version>=1), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observation_sources (
 vehicle_id TEXT PRIMARY KEY REFERENCES vehicles(id), data_json TEXT NOT NULL, version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS observation_snapshots (
 vehicle_id TEXT PRIMARY KEY REFERENCES vehicles(id), run_id TEXT NOT NULL REFERENCES runs(id),
 source_version INTEGER NOT NULL, observed_at REAL NOT NULL, data_json TEXT NOT NULL,
 version INTEGER NOT NULL, recorded_at TEXT NOT NULL, tenant_id TEXT NOT NULL REFERENCES tenants(id)
);
CREATE TABLE IF NOT EXISTS observation_delays (
 id TEXT PRIMARY KEY, vehicle_id TEXT NOT NULL REFERENCES vehicles(id), run_id TEXT NOT NULL REFERENCES runs(id),
 data_json TEXT NOT NULL, source_version INTEGER NOT NULL, observed_at REAL NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, tenant_id TEXT NOT NULL REFERENCES tenants(id)
);
CREATE INDEX IF NOT EXISTS delays_vehicle_run ON observation_delays(vehicle_id,run_id);
CREATE TABLE IF NOT EXISTS agent_tasks (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id), actor_id TEXT NOT NULL REFERENCES users(id),
 client_id TEXT NOT NULL, context_id TEXT NOT NULL, state TEXT NOT NULL,
 command_json TEXT NOT NULL, operation_id TEXT, operation_digest TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL,
 expires_at REAL NOT NULL, rounds INTEGER NOT NULL DEFAULT 0, lease_owner TEXT, lease_until REAL,
 result_json TEXT, code TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS own_agent_tasks ON agent_tasks(actor_id,client_id,created_at);
CREATE INDEX IF NOT EXISTS agent_task_cursor ON agent_tasks(actor_id,tenant_id,client_id,updated_at DESC,id DESC);
CREATE TABLE IF NOT EXISTS agent_messages (
 actor_id TEXT NOT NULL REFERENCES users(id), client_id TEXT NOT NULL, message_id TEXT NOT NULL,
 digest TEXT NOT NULL, task_id TEXT NOT NULL REFERENCES agent_tasks(id),
 PRIMARY KEY(actor_id,client_id,message_id)
);
CREATE TABLE IF NOT EXISTS agent_task_events (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES agent_tasks(id),
 state TEXT NOT NULL, code TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS external_identities (
 id TEXT PRIMARY KEY, issuer TEXT NOT NULL, audience TEXT NOT NULL, subject TEXT NOT NULL,
 actor_id TEXT NOT NULL REFERENCES users(id), active INTEGER NOT NULL DEFAULT 1,
 UNIQUE(issuer,audience,subject)
);
CREATE TABLE IF NOT EXISTS login_flows (
 state_hash TEXT PRIMARY KEY, browser_hash TEXT NOT NULL, nonce TEXT NOT NULL,
 verifier TEXT NOT NULL, expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS external_sessions (
 token_hash TEXT PRIMARY KEY REFERENCES sessions(token_hash) ON DELETE CASCADE,
 identity_id TEXT NOT NULL REFERENCES external_identities(id)
);
CREATE TABLE IF NOT EXISTS oauth_approvals (
 grant_id TEXT PRIMARY KEY REFERENCES client_grants(id) ON DELETE CASCADE,
 identity_id TEXT NOT NULL REFERENCES external_identities(id), resource TEXT NOT NULL
);
"""

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 210_000).hex()

def connect(path):
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("PRAGMA secure_delete=ON")
    return db

def initialize(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    try:
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if tables:
            if 'meta' not in tables:
                raise RuntimeError('Refusing to modify an unrelated database')
            metadata=dict(db.execute('SELECT key,value FROM meta'))
            if metadata.get('data_mode')!='synthetic' or metadata.get('schema_version') not in tuple(str(v) for v in range(1,9)):
                raise RuntimeError('Unsupported schema or non-synthetic database')
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if version:
            if version[0] not in ("1","2","3","4","5","6","7","8") or db.execute("SELECT value FROM meta WHERE key='data_mode'").fetchone()[0] != "synthetic":
                raise RuntimeError("Unsupported schema or non-synthetic database")
            db.execute("UPDATE meta SET value='8' WHERE key='schema_version'")
            db.commit()
            return
        fixture = json.loads((ROOT / "fixtures/synthetic-domain.json").read_text())
        if fixture["is_production"] or fixture["live_vehicle_access"]:
            raise RuntimeError("Only synthetic fixtures are supported")
        for item in fixture["tenants"]:
            db.execute("INSERT INTO tenants VALUES (?,?)", (item["id"], item["name"]))
        for item in fixture["users"]:
            salt = secrets.token_hex(16)
            db.execute("INSERT INTO users(id,tenant_id,role,salt,password_hash) VALUES (?,?,?,?,?)",
                       (item["id"], item["tenant_id"], item["role"], salt, password_hash(DEMO_PASSWORD, salt)))
        policy = {"call_mode":"immediate", "days":[0,1,2,3,4,5,6], "open":"00:00", "close":"24:00", "max_passengers":3}
        for item in fixture["services"]:
            db.execute("INSERT INTO services(id,tenant_id,name,timezone,fare_json,policy_json) VALUES (?,?,?,?,?,?)",
                       (item["id"], item["tenant_id"], item["name"], item["timezone"], json.dumps(item["fare"]), json.dumps(policy)))
        for item in fixture["stops"]:
            db.execute("INSERT INTO stops(id,service_id,name) VALUES (?,?,?)", (item["id"],item["service_id"],item["name"]))
        for item in fixture["vehicles"]:
            db.execute("INSERT INTO vehicles(id,tenant_id,service_id,driver_id,capacity) VALUES (?,?,?,?,?)",
                       (item["id"],item["tenant_id"],item["service_id"],item["driver_id"],item["capacity"]))
        db.executemany("INSERT INTO meta VALUES (?,?)", [("schema_version","8"),("data_mode","synthetic")])
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    path.chmod(0o600)
