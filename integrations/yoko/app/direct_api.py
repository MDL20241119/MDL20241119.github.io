"""Shared direct API dispatch; all operations use Mobility Core."""
from urllib.parse import parse_qs
from .core import fail, exact
from .catalog import CATALOG_COMMANDS

def dispatch(core, method, path, query, data, actor, authorization):
    if method=='GET' and path in ('/direct/v1/vehicle-locations','/direct/v1/operation-delays'):
        from .observations import query_params
        kind='locations' if path.endswith('/vehicle-locations') else 'delays'
        return core.observations.read(actor,kind,query_params(query,kind),authorization)
    if path=="/direct/v1/rides" and method=="GET":
        try:
            params=parse_qs(query,keep_blank_values=True,strict_parsing=True,max_num_fields=2)
            if set(params)-{"offset","limit"} or any(len(v)!=1 for v in params.values()):
                raise ValueError()
            offset=int(params.get("offset",["0"])[0]); limit=int(params.get("limit",["20"])[0])
        except ValueError:
            fail("INVALID_QUERY","ページ指定が不正です")
        return core.list_rides(actor,offset,limit,authorization=authorization)
    if query:
        fail("INVALID_QUERY","この操作はクエリを受け付けません")
    if method=='POST' and path=='/direct/v1/candidates':
        return core.booking.search(actor,data,authorization)
    if method=="GET" and path.startswith("/direct/v1/rides/"):
        return core.get_ride(actor,path.removeprefix("/direct/v1/rides/"),authorization)
    if method=='GET' and path.startswith('/direct/v1/payments/'):
        return core.payments.read(actor,path.removeprefix('/direct/v1/payments/'),authorization)
    if method=="GET" and path.startswith("/direct/v1/operations/"):
        return core.operation(actor,path.removeprefix("/direct/v1/operations/"),authorization)
    if method=="POST" and path in tuple("/direct/v1/actions/"+k for k in ({"request","cancel","change","book"}|CATALOG_COMMANDS)):
        exact(data,["operation_id","idempotency_key","payload"])
        return core.mutate(actor,data["operation_id"],data["idempotency_key"],path.rsplit("/",1)[1],data["payload"],authorization)
    fail("NOT_FOUND","このクライアント操作は公開されていません",404)

