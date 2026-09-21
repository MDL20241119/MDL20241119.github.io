"""Export the opt-in HTTPS interface; independent of MLIT standard contracts."""
import copy
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.export_local_openapi import build as base, obj, ref


def build():
    value=copy.deepcopy(base())
    value['info']={'title':'MDL 横のエレベーター HTTPS接続試験API','version':'0.12.0',
        'description':'Synthetic data and loopback HTTPS only. LINE code/PKCE/nonce login; pre-enrolled identities. OAuth tokens validated by authenticated RFC7662 introspection on each HTTP request. Core rechecks identity, approval and a <=15 second authorization lease. Not a production release or MLIT conformance claim.'}
    value['servers']=[{'url':'https://localhost:8768'}]
    value['components']['securitySchemes']={
        'WebCookie':{'type':'apiKey','in':'cookie','name':'__Host-yoko_session','description':'Server-issued Secure HttpOnly SameSite=Lax session after LINE Login. Demo passwords refused.'},
        'CsrfToken':{'type':'apiKey','in':'header','name':'X-CSRF-Token'},
        'OAuth':{'type':'openIdConnect','openIdConnectUrl':'https://identity.example.invalid/.well-known/openid-configuration','description':'Deployment-specific preregistered issuer. Token audience must contain the exact resource URL; read and execute scopes do not replace individual approval.'},
        'OperationApproval':{'type':'apiKey','in':'header','name':'X-Yoko-Approval','description':'Optional MDL-specific approval selector. If omitted, Core resolves an existing exact owner approval. Not an OAuth token or standard MCP/A2A field.'}}
    value['components']['schemas']['Session']['properties']['mode']={'const':'https_integration_synthetic'}
    for path in ('/api/session','/api/client-grants','/api/client-grants/revoke'):value['paths'].pop(path,None)
    for path,item in value['paths'].items():
        for method,operation in item.items():
            if method not in ('get','post','put','delete'):continue
            if path.startswith('/direct/'):
                execute='/actions/' in path
                operation['security']=[{'OAuth':['mobility:read']+(['mobility:execute'] if execute else [])}]
                if execute: operation.setdefault('parameters',[]).append({'name':'X-Yoko-Approval','in':'header','required':False,'schema':{'type':'string'},'description':'Optional approval selector; an existing exact owner approval is always required.'})
            else:
                operation['security']=[{'WebCookie':[],**({'CsrfToken':[]} if method!='get' else {})}]
    def response(schema):return {'description':'Successful response','content':{'application/json':{'schema':schema}}}
    def endpoint(schema,body=None,public=False):
        result={'responses':{'200':response(schema),'400':response(ref('Error')),'401':response(ref('Error')),'403':response(ref('Error')),'503':response(ref('Error'))},
            'security':[] if public else [{'WebCookie':[],**({'CsrfToken':[]} if body else {})}]}
        if body:result['requestBody']={'required':True,'content':{'application/json':{'schema':body}}}
        return result
    string={'type':'string'}
    operation=obj({'operation_id':string,'idempotency_key':string,'kind':{'enum':['request','book','change','cancel']},'payload':{'type':'object'}})
    # Core also accepts its explicitly exposed catalog operations for authorized
    # roles; rider agent tools continue to accept only their four operations.
    from app.catalog import CATALOG_COMMANDS
    operation['properties']['kind']['enum']+=sorted(CATALOG_COMMANDS)
    option=obj({'adapter':{'enum':['mcp','a2a','direct']},'identity_id':string,'resource':string,'clients':{'type':'array','items':string}})
    data=obj({'action':{'const':'execute'},'operation_id':string,'idempotency_key':string,'kind':string,'operation_digest':{'type':'string','pattern':'^[0-9a-f]{64}$'}})
    approval=obj({'approval_id':string,'resource':string,'client_id':string,'expires_at':{'type':'string','format':'date-time'},'a2a_data':data})
    body=obj({'adapter':{'enum':['mcp','a2a','direct']},'identity_id':string,'client_id':string,'operation':operation,'expires_in':{'type':'integer','minimum':1,'maximum':300}})
    value['paths']['/api/oauth-options']={'get':endpoint({'type':'array','items':option})}
    value['paths']['/api/oauth-approvals']={
        'get':endpoint({'type':'array','items':obj({'id':string,'client_id':string,'expires_at':{'type':'number'},'revoked':{'type':'integer','enum':[0,1]},'resource':string,'operation_json':string})}),
        'post':endpoint(approval,body)}
    value['paths']['/api/oauth-approvals/revoke']={'post':endpoint(obj({'revoked':{'const':True}}),obj({'grant_id':string}))}
    value['paths']['/api/openapi.json']['get']['security']=[]
    for path in ('/auth/line/start','/auth/line/callback'):
        item={'security':[],'responses':{'303':{'description':'Redirect with Secure HttpOnly cookie; no token in URL'},'401':{'description':'Login rejected; retry link'},'503':{'description':'Provider unavailable'}}}
        if path.endswith('/callback'):item['parameters']=[{'name':k,'in':'query','required':k=='state','schema':string} for k in ('state','code','error','error_description','friendship_status_changed')]
        value['paths'][path]={'get':item}
    for resource in ('mcp','a2a','direct/v1'):
        value['paths']['/.well-known/oauth-protected-resource/'+resource]={'get':endpoint(obj({'resource':string,'authorization_servers':{'type':'array','items':string},'scopes_supported':{'type':'array','items':string},'bearer_methods_supported':{'type':'array','items':{'const':'header'}}}),public=True)}
    return value


if __name__=='__main__':
    (ROOT/'api/https-integration.openapi.json').write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n')
    print('api/https-integration.openapi.json')
