"""Durable local agent tasks. Business writes use Core.mutate, never SQL here.

Only string references and a digest of the separately approved operation cross
the A2A data envelope. Credentials and full draft contents are not task history.
"""
import base64
import hashlib
import json
import math
import re
import time

from .core import DomainError, fail, packed, uid
from .delegation import verify_grant

TERMINAL = {'completed', 'failed', 'canceled', 'rejected'}
STATES = TERMINAL | {'input_required', 'working', 'submitted', 'auth_required'}
EXEC_KEYS = {'action', 'operation_id', 'idempotency_key', 'kind', 'operation_digest'}
MAX_ROUNDS = 8
TASK_TTL = 900
LEASE_SECONDS = 15


def operation_reference(operation):
    return {'action': 'execute', **{k: operation[k] for k in ('operation_id', 'idempotency_key', 'kind')},
        'operation_digest': hashlib.sha256(packed(operation).encode()).hexdigest()}


def name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        fail('INVALID_INPUT', '識別子の形式が不正です')
    return value


def command(value):
    if not isinstance(value, dict):
        fail('INVALID_INPUT', '構造化した操作指定が必要です')
    if value.get('action') == 'read_reservation' and set(value) == {'action', 'reservation_id'}:
        name(value['reservation_id'])
    elif value == {'action': 'execute'}:
        pass
    elif value.get('action') == 'execute' and set(value) == EXEC_KEYS:
        for key in ('operation_id', 'idempotency_key'):
            name(value[key])
        if value['kind'] not in ('request', 'book', 'change', 'cancel') or not isinstance(value['operation_digest'], str) or not re.fullmatch('[0-9a-f]{64}', value['operation_digest']):
            fail('INVALID_INPUT', '承認済み操作の参照が不正です')
    else:
        fail('INVALID_INPUT', '未対応の操作・入力項目です')
    return value


class AgentTasks:
    def __init__(self, core):
        self.core = core

    def principal(self, db, actor, authorization):
        if not authorization:
            fail('UNAUTHENTICATED', '本人の委任が必要です', 401)
        user = self.core.actor(db, actor, 'rider')
        grant = verify_grant(db, actor, authorization, self.core.clock())
        return user, grant

    def own(self, db, actor, authorization, task_id):
        user, grant = self.principal(db, actor, authorization)
        row = db.execute('SELECT * FROM agent_tasks WHERE id=? AND actor_id=? AND tenant_id=? AND client_id=?',
            (name(task_id), actor, user['tenant_id'], grant['client_id'])).fetchone()
        if not row:
            fail('TASK_NOT_FOUND', 'このTaskを確認できません', 404)
        return row

    def status(self, db, task_id, state, code, result=None):
        now = self.core.clock()
        db.execute('UPDATE agent_tasks SET state=?,code=?,updated_at=?,result_json=?,lease_owner=NULL,lease_until=NULL WHERE id=?',
            (state, code, now, packed(result) if result is not None else None, task_id))
        db.execute('INSERT INTO agent_task_events VALUES (?,?,?,?,?)', (uid('te'), task_id, state, code, now))

    def recover(self, db, row):
        from .agent_actions import reservation
        if row['state'] in TERMINAL:
            return
        if row['operation_id']:
            op = db.execute('SELECT * FROM operations WHERE actor_id=? AND operation_id=?',
                (row['actor_id'], row['operation_id'])).fetchone()
            ref = json.loads(row['command_json'])
            # An operation ID alone never establishes that a different payload
            # was executed. The task already bound the exact approved digest.
            if op and op['idempotency_key'] == ref.get('idempotency_key') and op['kind'] == ref.get('kind') and op['digest'] == row['operation_digest']:
                value = json.loads(op['result_json'])
                self.status(db, row['id'], 'completed', 'OPERATION_RECONCILED',
                    {'operation_id': op['operation_id'], 'replayed': True, 'current': reservation(value)})
                return
        now = self.core.clock()
        if row['expires_at'] <= now:
            self.status(db, row['id'], 'failed', 'TASK_EXPIRED')
        elif row['state'] == 'working' and row['lease_until'] <= now:
            self.status(db, row['id'], 'input_required', 'RETRY_SAME_APPROVAL')

    def view(self, db, row, history_length):
        if type(history_length) is not int or not 0 <= history_length <= 20:
            fail('INVALID_INPUT', '履歴件数は0〜20で指定してください')
        history = [dict(x) for x in db.execute('SELECT id,state,code,created_at FROM agent_task_events WHERE task_id=? ORDER BY rowid DESC LIMIT ?',
            (row['id'], history_length))][::-1]
        status_id = db.execute('SELECT id FROM agent_task_events WHERE task_id=? ORDER BY rowid DESC LIMIT 1', (row['id'],)).fetchone()[0]
        return {k: row[k] for k in ('id', 'context_id', 'state', 'code', 'created_at', 'updated_at')} | {
            'result': json.loads(row['result_json']) if row['result_json'] else None, 'history': history, 'status_message_id': status_id}

    def get(self, actor, authorization, task_id, history_length=20):
        with self.core.db(True) as db:
            row = self.own(db, actor, authorization, task_id)
            self.recover(db, row)
            return self.view(db, self.own(db, actor, authorization, task_id), history_length)

    def cancel(self, actor, authorization, task_id):
        with self.core.db(True) as db:
            row = self.own(db, actor, authorization, task_id)
            self.recover(db, row)
            row = self.own(db, actor, authorization, task_id)
            if row['state'] != 'input_required':
                fail('TASK_NOT_CANCELABLE', '実行中または終了済みのTaskは取り消せません', 409)
            self.status(db, task_id, 'canceled', 'TASK_ONLY_CANCELED')
            return self.view(db, self.own(db, actor, authorization, task_id), 20)

    def send(self, actor, authorization, message_id, value, task_id='', context_id='', history_length=20, return_immediately=False, schedule=None):
        name(message_id); command(value)
        if task_id: name(task_id)
        if context_id: name(context_id)
        if type(history_length) is not int or not 0 <= history_length <= 20:
            fail('INVALID_INPUT', '履歴件数は0〜20で指定してください')
        if return_immediately and schedule is None:
            fail('INVALID_INPUT', '非同期処理の実行窓口が必要です')
        digest = hashlib.sha256(packed([value, task_id, context_id]).encode()).hexdigest()
        operation = None
        lease = None
        with self.core.db(True) as db:
            if authorization and 'external' in authorization and set(value) == EXEC_KEYS:
                from .external_auth import bind_task_approval
                authorization = bind_task_approval(db, actor, authorization, value, self.core.clock())
            user, grant = self.principal(db, actor, authorization)
            old = db.execute('SELECT * FROM agent_messages WHERE actor_id=? AND client_id=? AND message_id=?',
                (actor, grant['client_id'], message_id)).fetchone()
            if old:
                if old['digest'] != digest:
                    fail('MESSAGE_REUSE', '同じメッセージIDの内容は変更できません', 409)
                task_id = old['task_id']
                row = self.own(db, actor, authorization, task_id)
                self.recover(db, row)
            else:
                if task_id:
                    row = self.own(db, actor, authorization, task_id)
                    self.recover(db, row)
                    row = self.own(db, actor, authorization, task_id)
                    if context_id and context_id != row['context_id']:
                        fail('INVALID_INPUT', 'TaskとcontextIdが一致しません')
                    previous = json.loads(row['command_json'])
                    if previous != {'action': 'execute'} and previous != value:
                        fail('TASK_COMMAND_MISMATCH', 'このTaskの操作内容は変更できません', 409)
                    if row['state'] in TERMINAL:
                        fail('TASK_TERMINAL', '終了したTaskは再開できません。結果を照会してください', 409)
                    if row['state'] == 'working':
                        fail('TASK_BUSY', '同じTaskの結果を照会してください', 409)
                    if row['rounds'] >= MAX_ROUNDS:
                        self.status(db, task_id, 'failed', 'ROUND_LIMIT')
                        return self.view(db, self.own(db, actor, authorization, task_id), history_length)
                else:
                    if context_id and not db.execute('SELECT 1 FROM agent_tasks WHERE context_id=? AND actor_id=? AND client_id=? AND tenant_id=?',
                            (context_id, actor, grant['client_id'], user['tenant_id'])).fetchone():
                        fail('TASK_NOT_FOUND', 'このcontextIdを確認できません', 404)
                    task_id = uid('task'); context_id = context_id or uid('ctx')
                    now = self.core.clock()
                    db.execute('INSERT INTO agent_tasks(id,tenant_id,actor_id,client_id,context_id,state,command_json,created_at,updated_at,expires_at,code) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (task_id, user['tenant_id'], actor, grant['client_id'], context_id, 'input_required', packed({'action': 'execute'}), now, now, now+TASK_TTL, 'INPUT_REQUIRED'))
                db.execute('INSERT INTO agent_messages VALUES (?,?,?,?,?)', (actor, grant['client_id'], message_id, digest, task_id))
                db.execute('UPDATE agent_tasks SET rounds=rounds+1 WHERE id=?', (task_id,))
                if value['action'] == 'execute':
                    if set(value) != EXEC_KEYS or 'mobility:execute' not in json.loads(grant['scopes_json']):
                        # Never bind an unverified caller-supplied operation ID.
                        self.status(db, task_id, 'input_required', 'OWNER_APPROVAL_REQUIRED')
                    else:
                        approved = json.loads(grant['operation_json'])
                        if operation_reference(approved) != value:
                            fail('APPROVAL_MISMATCH', '本人が承認した操作の参照と一致しません', 403)
                        operation = approved
                if value['action'] == 'read_reservation' or operation is not None:
                    lease = uid('lease')
                    now = self.core.clock()
                    self.status(db, task_id, 'working', 'PROCESSING')
                    business_digest = hashlib.sha256(packed({'kind': operation['kind'], 'payload': operation['payload']}).encode()).hexdigest() if operation else None
                    db.execute('UPDATE agent_tasks SET command_json=?,operation_id=?,operation_digest=?,lease_owner=?,lease_until=? WHERE id=?',
                        (packed(value), value.get('operation_id'), business_digest, lease, now+LEASE_SECONDS, task_id))
            initial = self.view(db, self.own(db, actor, authorization, task_id), history_length)
        if return_immediately:
            if lease and not schedule(lambda: self.run(actor, authorization, task_id, lease, value, operation)):
                self.finish(task_id, lease, 'input_required', 'RETRY_SAME_APPROVAL', None)
                return self.get(actor, authorization, task_id, history_length)
            return initial
        if lease:
            self.run(actor, authorization, task_id, lease, value, operation)
        # Duplicate sends wait briefly for the first worker; they do not run it.
        deadline = time.monotonic()+3
        while True:
            result = self.get(actor, authorization, task_id, history_length)
            if result['state'] != 'working': return result
            if time.monotonic() >= deadline:
                fail('TASK_BUSY', '同じTaskの結果を照会してください', 409)
            time.sleep(.02)

    def run(self, actor, authorization, task_id, lease, value, operation):
        from .agent_actions import execute, reservation
        fenced = {**authorization, 'task_execution': {'id': task_id, 'lease_owner': lease}}
        try:
            if operation is not None:
                result = execute(self.core, actor, operation, fenced)
            else:
                data = self.core.list_rides(actor, reservation_ids=[value['reservation_id']], authorization=fenced, owner_only=True)
                if not data['rides']: fail('NOT_FOUND', '本人の予約を確認できません', 404)
                result = {'current': reservation(data['rides'][0])}
            state, code = 'completed', 'OPERATION_COMPLETED' if operation else 'READ_COMPLETED'
        except DomainError as error:
            state, code, result = 'failed', error.code, None
        # Unexpected storage failures deliberately leave a recoverable lease.
        self.finish(task_id, lease, state, code, result)

    def finish(self, task_id, lease, state, code, result):
        with self.core.db(True) as db:
            row = db.execute('SELECT * FROM agent_tasks WHERE id=?', (task_id,)).fetchone()
            if row and row['state'] == 'working' and row['lease_owner'] == lease:
                self.status(db, task_id, state, code, result)

    def list(self, actor, authorization, context_id='', state='', page_size=20, page_token='', history_length=0, after=None, include_artifacts=False):
        if type(page_size) is not int or not 1 <= page_size <= 100 or state and state not in STATES:
            fail('INVALID_INPUT', '一覧の条件が不正です')
        if context_id: name(context_id)
        if type(history_length) is not int or not 0 <= history_length <= 20:
            fail('INVALID_INPUT', '履歴件数は0〜20で指定してください')
        # Cursor is a pagination position, never an authorization credential.
        fingerprint = hashlib.sha256(packed([actor, authorization['client_id'], context_id, state, after, include_artifacts]).encode()).hexdigest()
        cursor = None
        if page_token:
            try:
                updated_at, last_id, binding = json.loads(base64.urlsafe_b64decode(page_token))
                if type(updated_at) not in (float, int) or not math.isfinite(updated_at) or updated_at < 0 or binding != fingerprint: raise ValueError()
                name(last_id)
                cursor = (updated_at, last_id)
            except Exception:
                fail('INVALID_INPUT', 'ページ指定が不正です')
        with self.core.db(True) as db:
            user, grant = self.principal(db, actor, authorization)
            where = 'actor_id=? AND tenant_id=? AND client_id=?'
            args = [actor, user['tenant_id'], grant['client_id']]
            for row in db.execute('SELECT * FROM agent_tasks WHERE '+where+' AND state NOT IN (\'completed\',\'failed\',\'canceled\',\'rejected\')', args).fetchall():
                self.recover(db, row)
            if context_id: where += ' AND context_id=?'; args.append(context_id)
            if state: where += ' AND state=?'; args.append(state)
            if after is not None: where += ' AND updated_at>?'; args.append(after)
            total = db.execute('SELECT count(*) FROM agent_tasks WHERE '+where, args).fetchone()[0]
            if cursor:
                where += ' AND (updated_at<? OR (updated_at=? AND id<?))'
                args.extend([cursor[0], cursor[0], cursor[1]])
            rows = db.execute('SELECT * FROM agent_tasks WHERE '+where+' ORDER BY updated_at DESC,id DESC LIMIT ?', [*args, page_size+1]).fetchall()
            has_more = len(rows) > page_size
            rows = rows[:page_size]
            items = [self.view(db, row, history_length) for row in rows]
            if not include_artifacts:
                for item in items: item['result'] = None
            token = base64.urlsafe_b64encode(packed([rows[-1]['updated_at'], rows[-1]['id'], fingerprint]).encode()).decode() if has_more else ''
            return {'tasks': items, 'next_page_token': token, 'page_size': page_size, 'total_size': total}
