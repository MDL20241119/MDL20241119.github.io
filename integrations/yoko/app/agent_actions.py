"""Shared agent adapter projection; all business writes remain in Core.mutate."""
from .core import exact, fail

RESERVATION_KEYS = ('id', 'service_id', 'origin_stop_id', 'destination_stop_id', 'origin_name', 'destination_name',
    'passengers', 'status', 'status_label', 'version', 'fare', 'created_at', 'updated_at', 'next_action')
ACTION_KINDS = {'request', 'book', 'change', 'cancel'}


def reservation(view):
    return {key: view[key] for key in RESERVATION_KEYS}


def owner(core, actor, authorization):
    if authorization is None:
        fail('APPROVAL_REQUIRED', '本人の個別委任が必要です', 403)
    with core.db() as db:
        core.actor(db, actor, 'rider')
        core.check_authorization(db, actor, authorization)


def execute(core, actor, operation, authorization):
    owner(core, actor, authorization)
    exact(operation, ['operation_id', 'idempotency_key', 'kind', 'payload'])
    if not isinstance(operation['kind'], str) or operation['kind'] not in ACTION_KINDS:
        fail('OPERATION_UNSUPPORTED', 'この代理入口は本人の依頼・予約・変更・取消に限定しています', 403)
    # Exact grant contents, expiry, actor, current fare/eligibility/version and
    # cross-adapter idempotency are checked atomically by the existing Core.
    result = core.mutate(actor, operation['operation_id'], operation['idempotency_key'],
        operation['kind'], operation['payload'], authorization)
    return {'operation_id': result['operation_id'], 'replayed': result['replayed'], 'current': reservation(result['current'])}


def receipt(core, actor, operation_id, authorization):
    owner(core, actor, authorization)
    result = core.operation(actor, operation_id, authorization)
    if not set(RESERVATION_KEYS) <= set(result['current']):
        fail('OPERATION_UNSUPPORTED', 'この入口は本人の予約操作だけを照会できます', 403)
    return {'operation_id': result['operation_id'], 'current': reservation(result['current'])}
