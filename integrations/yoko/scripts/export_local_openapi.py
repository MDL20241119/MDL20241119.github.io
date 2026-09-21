"""Export the MDL local contract. This is NOT the MLIT standard interface."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
STR={"type":"string"}
INT={"type":"integer"}
def obj(properties,required=None,extra=False):
    return {"type":"object","properties":properties,"required":list(properties) if required is None else required,"additionalProperties":extra}
def ref(name):return {"$ref":"#/components/schemas/"+name}
def arr(schema):return {"type":"array","items":schema}

def build():
    schemas={
        "Fare":obj({"amount":{"type":["integer","null"],"minimum":0},"currency":STR,"basis":STR},["amount","currency"]),
        "RequestInput":obj({"service_id":STR,"origin_stop_id":STR,"destination_stop_id":STR,"passengers":{"type":"integer","minimum":1,"maximum":3}}),
        "CancelInput":obj({"ride_id":STR}),
        "ChangeInput":obj({"ride_id":STR,"service_id":STR,"origin_stop_id":STR,"destination_stop_id":STR,"passengers":{"type":"integer","minimum":1,"maximum":3}}),
        "DriverPayload":obj({"ride_id":STR,"version":{"type":"integer","minimum":1},"stopped":{"const":True}}),
        "RequestDetails":obj({"service_id":STR,"origin_stop_id":STR,"destination_stop_id":STR,"passengers":{"type":"integer","minimum":1,"maximum":3},"origin_name":STR,"destination_name":STR,"fare":ref("Fare"),"service_revision":INT}),
        "CancelDetails":obj({"ride_id":STR,"version":INT,"origin_stop_id":STR,"destination_stop_id":STR,"passengers":INT,"cancellation_fee":ref("Fare")}),
        "User":obj({"id":STR,"role":{"enum":["rider","driver","admin"]},"tenant_id":STR}),
        "Session":obj({"user":ref("User"),"csrf":STR,"mode":{"const":"local_synthetic"}}),
        "Event":obj({"kind":{"enum":["request","book","change","accept","arrive","board","complete","cancel"]},"status":STR,"version":INT,"created_at":{"type":"string","format":"date-time"}}),
        "Error":obj({"error":obj({"code":STR,"message":STR,"retryable":{"type":"boolean"}},["code","message"])})
    }
    ride={k:STR for k in ["id","service_id","origin_stop_id","destination_stop_id","origin_name","destination_name","status_label","next_action","created_at","updated_at"]}
    ride.update({"passengers":INT,"version":INT,"vehicle_id":{"type":["string","null"]},"fare":ref("Fare"),"status":{"enum":["requested","assigned","arrived","onboard","completed","cancelled"]},"reservation_status":{"enum":["pending","confirmed","cancelled"]},"assignment_status":{"enum":["unassigned","assigned","released"]},"vehicle_location":{"type":"null"},"eta":{"type":"null"},"location_status":{"const":"not_acquired"},"eta_status":{"const":"not_acquired"},"synthetic":{"const":True},"events":arr(ref("Event"))})
    schemas["Ride"]=obj({**ride,"rider_id":STR},list(ride))
    schemas['CatalogResource']=obj({'resource_type':{'enum':['passenger','agreements','term','service','stop','route','dispatch_offer','payment']},'id':STR,'value':{'type':['object','null']},'deleted':{'type':'boolean'},'redacted':{'type':'boolean'}},['resource_type','id','value','deleted'])
    schemas["OperationResult"]=obj({"operation_id":STR,"replayed":{"type":"boolean"},"result":{"oneOf":[ref('Ride'),ref('CatalogResource'),{'type':'null'}]},"current":{"oneOf":[ref('Ride'),ref('CatalogResource')]}},["operation_id","result","current"])
    schemas["ChangeDetails"]=obj({**schemas["RequestDetails"]["properties"],"ride_id":STR,"version":INT,"status":{"enum":["requested","assigned"]}})
    schemas["Draft"]=obj({"id":STR,"kind":{"enum":["request","cancel","change"]},"details":{"oneOf":[ref("RequestDetails"),ref("CancelDetails"),ref("ChangeDetails")]},"expires_at":{"type":"string","format":"date-time"}})
    point=obj({'type':{'const':'Point'},'coordinates':{'type':'array','items':{'type':'number'},'minItems':2,'maxItems':2}})
    date_time={'type':'string','format':'date-time'}
    amount={'type':'integer','minimum':0,'maximum':2147483647}
    payment_status={'enum':['uncollected','received','excluded','cancelled']}
    schemas['PaymentRecord']=obj({'id':STR,'amount':amount,'payment_status':payment_status,'version':{'type':'integer','minimum':1},'created_at':date_time,'updated_at':date_time})
    schemas['PaymentSummary']=obj({'reservation_id':STR,'record':{'oneOf':[ref('PaymentRecord'),{'type':'null'}]},'expected_amount':{'oneOf':[amount,{'type':'null'}]},'currency':{'const':'JPY'},'review_required':{'type':'boolean'},'review_reason':{'enum':['refund_review_required','cancellation_update_required','fare_unknown','fare_update_required',None]},'basis':{'const':'synthetic_ledger_only'}})
    def nullable(s):return {'oneOf':[s,{'type':'null'}]}
    quality={'enum':['fresh','not_configured','not_acquired','stale','expired','stopped','source_changed','not_operating']}
    source_input=obj({'vehicle_id':STR,'source_id':STR,'label':STR,'location_ttl_seconds':{'type':'integer','minimum':1,'maximum':300},'delay_ttl_seconds':{'type':'integer','minimum':1,'maximum':3600},'enabled':{'type':'boolean'},'basis':{'const':'synthetic_test_only'}})
    source=obj({**source_input['properties'],'version':INT})
    delay_input=obj({'id':STR,'status':{'enum':['active','resolved']},'delay_minutes':nullable(amount),'delay_reason':{'enum':['traffic','operational','accident','weather','vehicle_issue','passenger_issue','other']},'started_at':date_time,'closed_at':nullable(date_time),'closed_reason':{'enum':['vehicle_moved','resolved','schedule_changed','cancelled',None]},'effective_end':date_time})
    delay_record=obj({**delay_input['properties'],'delay_minutes':amount,'closed_at':date_time,'closed_reason':{'enum':['vehicle_moved','resolved','schedule_changed','cancelled']},'vehicle_id':STR,'service_id':STR,'created_at':date_time,'updated_at':date_time},['id','status','delay_reason','started_at','effective_end','vehicle_id','service_id','created_at','updated_at'])
    schemas['DelayRecord']=delay_record
    observation_meta={'vehicle_id':STR,'service_id':STR,'run_id':nullable(STR),'source':nullable(source),'observed_at':nullable(date_time),'recorded_at':nullable(date_time),'version':INT,'location_status':quality,'delay_status':quality,'location_valid_until':nullable(date_time),'delay_valid_until':nullable(date_time),'delay_assessment':{'enum':['unknown','delayed','no_active_delay_reported']},'basis':{'const':'synthetic_test_only'}}
    schemas['ObservationQuality']=obj(observation_meta)
    schemas['Observation']=obj({**observation_meta,'location':nullable(point),'delays':arr(ref('DelayRecord'))})
    schemas['Ride']['properties'].update({'observation':nullable(ref('Observation')),'vehicle_location':nullable(point),'location_status':quality})
    schemas['CatalogResource']['properties']['resource_type']['enum']+=['observation_source','observation']
    observation_inputs={'observation_configure':source_input,'observation_publish':obj({'vehicle_id':STR,'run_id':STR,'source_id':STR,'observed_at':date_time,'location':nullable(point),'delays':nullable({'type':'array','items':delay_input,'maxItems':20})})}
    schemas['Ride']['properties']['payment']=ref('PaymentSummary')
    schemas['BookInput']=obj({'candidate_id':STR})
    booking_fields={'pickup_at':date_time,'dropoff_at':date_time,'pickup_location':point,'dropoff_location':point,
        'vehicle_name':STR,'vehicle_capacity':INT,'basis':{'const':'synthetic_plan_not_observation'}}
    schemas['Ride']['properties']['booking']=obj(booking_fields)
    schemas['BookDetails']=obj({**schemas['RequestDetails']['properties'],**booking_fields,
        'id':STR,'offer_id':STR,'vehicle_id':STR,'offer_version':INT,'profile_version':INT,'expires_at':date_time})
    schemas['CandidateSearch']=obj({**schemas['RequestInput']['properties'],'preferred_pickup_at':date_time,'vehicle_id':{'type':['string','null']}})
    schemas['CandidatePage']=obj({'candidates':arr(ref('BookDetails')),'no_candidate_reason':{'type':['string','null']},'availability_reason':{'type':['string','null']}})
    schemas['Draft']['properties']['kind']['enum'].append('book')
    schemas['Draft']['properties']['details']['oneOf'].append(ref('BookDetails'))
    period={'start_datetime':date_time,'end_datetime':{'oneOf':[date_time,{'type':'null'}]}}
    slot=obj({'start_time_offset_sec':{'type':'integer','minimum':0},'end_time_offset_sec':{'type':'integer','maximum':172800}})
    hour_map=obj({k:arr(slot) for k in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday','holidays']})
    profile_input=obj({**{k:STR for k in ['first_name','last_name','first_name_kana','last_name_kana','phone_number']},'gender':{'enum':['male','female','other','unspecified']},'birthdate':{'type':'string','format':'date'},'email':{'type':'string','format':'email'},'home_address':obj({**{k:STR for k in ['postal_code','state','city','street']},'location':point},[])},[])
    profile_input['anyOf']=[{'required':['first_name','last_name']},{'required':['first_name_kana','last_name_kana']}]
    catalog_inputs={
        'profile_create':profile_input,'profile_update':profile_input,'profile_delete':obj({}),
        'agreements_register':obj({'agreements':{'type':'array','minItems':1,'maxItems':50,'items':obj({'terms_id':STR,'agreed_at':date_time})}}),
        'terms_publish':obj({'service_id':{'type':['string','null']},'category':{'enum':['platform','provider','service','privacy','cancellation','user','third_party']},'name':STR,'url':{'type':'string','format':'uri'},'agreement_required':{'type':'boolean'}}),
        'service_configure':obj({'service_id':STR,'access_scope':{'enum':['public','resident_only','registered_user_only','private','other']},**period,'cities':arr(obj({'prefecture_code':STR,'prefecture_name':STR,'municipalities':arr(obj({'code':STR,'name':STR}))})),'operating_hours':hour_map,'special_operating_hours':arr(obj({'date':{'type':'string','format':'date'},'time_slots':arr(slot)})),'holiday_dates':arr({'type':'string','format':'date'})}),
        'stop_configure':obj({'stop_id':STR,'location':point,**period,'pictures':arr(obj({'url':{'type':'string','format':'uri'},'title':STR,'description':STR},['url']))})}
    catalog_inputs.update({
        'payment_update':obj({'ride_id':STR,'amount':amount,'payment_status':payment_status}),
        'route_configure':obj({'service_id':STR,'origin_stop_id':STR,'destination_stop_id':STR,'travel_seconds':{'type':'integer','minimum':60,'maximum':7200},'max_wait_seconds':{'type':'integer','minimum':60,'maximum':7200},'basis':{'const':'synthetic_test_only'}}),
        'offer_open':obj({'service_id':STR,'origin_stop_id':STR,'destination_stop_id':STR,'pickup_at':date_time,'vehicle_name':STR,'stopped':{'const':True}}),
        'offer_close':obj({'offer_id':STR,'stopped':{'const':True}})})
    catalog_inputs.update(observation_inputs)
    schemas['CatalogDetails']=obj({'input':{'type':'object'},'version':INT,'dependencies':arr({})})
    schemas['Draft']['properties']['kind']['enum']+=list(catalog_inputs)
    schemas['Draft']['properties']['details']['oneOf'].append(ref('CatalogDetails'))
    schemas["Snapshot"]=obj({"user":{"allOf":[{"type":"object"}],"description":"id / tenant_id / role / eligible / active"},"services":arr({"type":"object"}),"rides":arr(ref("Ride")),"vehicles":arr({"type":"object"}),"counts":{"type":"object"},"outbox_pending":{"type":["integer","null"]},"as_of":{"type":"string","format":"date-time"},"limit":{"const":200},"mode":{"const":"local_synthetic"},"capabilities":{"type":"object","additionalProperties":{"const":False}}})
    schemas['Snapshot']['properties']['offers']=arr({'type':'object'})
    schemas['Snapshot']['required'].append('offers')
    paths={}
    def endpoint(path,method,operation,response,body=None,anonymous=False):
        op={"operationId":operation,"responses":{"200":{"description":"Success; inspect current business state, never infer arrival from assignment.","content":{"application/json":{"schema":response}}}},"security":[] if anonymous else [{"LocalCookie":[]}],"parameters":[]}
        for status in [400,401,403,404,409,410,413,415,429,500,503]:
            op["responses"][str(status)]={"description":"Explicit rejection or unknown outcome; for timeout/5xx/429 reconcile by operation_id, retry only the same payload and key.","content":{"application/json":{"schema":ref("Error")}}}
        if "{id}" in path:op["parameters"].append({"name":"id","in":"path","required":True,"schema":STR})
        if body is not None:
            op["parameters"].append({"name":"X-Requested-With","in":"header","required":True,"schema":{"const":"YokoLocal"}})
            if not anonymous:op["security"]=[{"LocalCookie":[],"CsrfToken":[]}]
            op["requestBody"]={"required":True,"content":{"application/json":{"schema":body}}}
        paths.setdefault(path,{})[method]=op
    endpoint("/api/session","post","localLogin",ref("Session"),obj({"username":STR,"password":STR}),True)
    endpoint("/api/me","get","getSession",ref("Session"))
    endpoint("/api/logout","post","logout",obj({"logged_out":{"const":True}}),obj({}))
    endpoint("/api/snapshot","get","getSnapshot",ref("Snapshot"))
    endpoint('/api/catalog','get','getOwnCatalog',obj({'passenger':{'type':['object','null']},'terms':arr({'type':'object'}),'agreements':arr({'type':'object'}),'mode':{'const':'local_synthetic'}}))
    endpoint("/api/rides/{id}","get","getRide",ref("Ride"))
    endpoint('/api/payments/{id}','get','getOwnPayment',ref('PaymentSummary'))
    endpoint('/direct/v1/payments/{id}','get','getClientPayment',ref('PaymentSummary'))
    for kind,path,item,key in [('locations','vehicle-locations',obj({'vehicle_id':STR,'service_id':STR,'location':point,'timestamp':date_time}),'vehicle_locations'),('delays','operation-delays',ref('DelayRecord'),'operation_delays')]:
        response=obj({key:arr(item),'total':INT,'offset':INT,'limit':INT,'observations':arr(ref('ObservationQuality')),'as_of':date_time,'basis':{'const':'synthetic_test_only'},'availability':{'enum':['no_authorized_vehicles','complete','incomplete']}})
        endpoint('/direct/v1/'+path,'get','getClient_'+path.replace('-','_'),response)
        parameters=[{'name':name,'in':'query','style':'form','explode':False,'schema':arr(STR)} for name in ['vehicle_ids','service_ids']]
        parameters += [{'name':name,'in':'query','schema':schema} for name,schema in [('offset',{'type':'integer','minimum':0,'default':0}),('limit',{'type':'integer','minimum':1,'maximum':100,'default':20})]]
        if kind=='delays':parameters += [{'name':'status','in':'query','style':'form','explode':False,'schema':{'type':'array','items':{'enum':['active','resolved']},'default':['active']}}]+[{'name':name,'in':'query','schema':date_time} for name in ['started_at_from','started_at_to']]
        paths['/direct/v1/'+path]['get']['parameters']=parameters
    endpoint("/api/operations/{id}","get","getOperation",ref("OperationResult"))
    endpoint("/api/drafts/request","post","prepareRequest",ref("Draft"),ref("RequestInput"))
    endpoint("/api/drafts/cancel","post","prepareCancel",ref("Draft"),ref("CancelInput"))
    endpoint("/api/drafts/change","post","prepareChange",ref("Draft"),ref("ChangeInput"))
    endpoint('/api/drafts/book','post','prepareBook',ref('Draft'),ref('BookInput'))
    endpoint('/api/candidates','post','searchOwnCandidates',ref('CandidatePage'),ref('CandidateSearch'))
    endpoint('/direct/v1/candidates','post','searchClientCandidates',ref('CandidatePage'),ref('CandidateSearch'))
    action_bodies={}
    for kind in ["request","cancel","change","book","accept","arrive","board","complete"]:
        payload=obj({"draft_id":STR,"details":ref(kind.title()+"Details")}) if kind in ["request","cancel","change","book"] else ref("DriverPayload")
        op_id={"type":"string","pattern":"^[A-Za-z0-9_-]{8,100}$"}
        body=obj({"operation_id":op_id,"idempotency_key":op_id,"payload":payload})
        action_bodies[kind]=body
        endpoint("/api/actions/"+kind,"post",kind+"Ride",ref("OperationResult"),body)
    for kind,input_schema in catalog_inputs.items():
        name='CatalogInput_'+kind;schemas[name]=input_schema
        details=obj({'input':ref(name),'version':INT,'dependencies':arr({})})
        payload=obj({'draft_id':STR,'details':details})
        body=obj({'operation_id':op_id,'idempotency_key':op_id,'payload':payload});action_bodies[kind]=body
        endpoint('/api/drafts/'+kind,'post','prepare_'+kind,ref('Draft'),ref(name))
        endpoint('/api/actions/'+kind,'post','execute_'+kind,ref('OperationResult'),body)
    scopes=arr({"enum":["mobility:read","mobility:execute"]})
    approved={"oneOf":[obj({**action_bodies[k]["properties"],"kind":{"const":k}}) for k in ["request","change","cancel","book",*catalog_inputs]]+[{"type":"null"}]}
    grant_input=obj({"client_id":{"type":"string","pattern":"^[a-zA-Z0-9_-]{3,80}$"},"scopes":scopes,"expires_in":{"type":"integer","minimum":1,"maximum":300},"operation":approved})
    grant_output=obj({"grant_id":STR,"access_token":STR,"token_type":{"const":"Bearer"},"client_id":STR,"audience":{"const":"yoko-local-mobility"},"scopes":scopes,"expires_at":{"type":"string","format":"date-time"},"mode":{"const":"local_synthetic"}})
    endpoint("/api/client-grants","post","issueLocalClientGrant",grant_output,grant_input)
    endpoint("/api/client-grants/revoke","post","revokeLocalClientGrant",obj({"revoked":{"const":True}}),obj({"grant_id":STR}))
    schemas["RidePage"]=obj({"rides":arr(ref("Ride")),"total":INT,"offset":INT,"limit":INT})
    endpoint("/direct/v1/rides","get","listClientRides",ref("RidePage"))
    endpoint("/direct/v1/rides/{id}","get","getClientRide",ref("Ride"))
    endpoint("/direct/v1/operations/{id}","get","reconcileClientOperation",ref("OperationResult"))
    for kind in ["request","change","cancel","book",*catalog_inputs]:
        endpoint("/direct/v1/actions/"+kind,"post",kind+"ClientRide",ref("OperationResult"),action_bodies[kind])
    for path,methods in paths.items():
        if not path.startswith("/direct/"):continue
        for op in methods.values():
            op["security"]=[{"LocalClientBearer":[],"ClientID":[]}]
            op["parameters"]=[x for x in op["parameters"] if x["name"]!="X-Requested-With"]
            if path=="/direct/v1/rides":
                op["parameters"].extend([{"name":n,"in":"query","schema":s} for n,s in [("offset",{"type":"integer","minimum":0,"default":0}),("limit",{"type":"integer","minimum":1,"maximum":100,"default":20})]])
    endpoint("/api/openapi.json","get","getLocalContract",{"type":"object"},anonymous=True)
    return {"openapi":"3.1.1","info":{"title":"MDL 横のエレベーター ローカル検証API","version":"0.12.0","description":"Local synthetic data only. Independent MDL contract; not MLIT COMmmmONS. Cookie auth and client grants are test-only; no public hosting. No LLM required. Same-origin and loopback are mandatory. HTTP body maximum 16384 bytes. Draft/grant lifetime at most 300 seconds; session 3600 seconds. Client execution requires one exact owner-approved operation. Keys retained for lifetime of synthetic DB. Snapshot is limited to 200; direct API supports authorized pagination."},"servers":[{"url":"http://127.0.0.1:8765","description":"Loopback only; custom port supported by CLI"}],"paths":paths,"components":{"schemas":schemas,"securitySchemes":{"LocalCookie":{"type":"apiKey","in":"cookie","name":"yoko_session","description":"Synthetic test auth only. HttpOnly, SameSite=Strict, no public use."},"CsrfToken":{"type":"apiKey","in":"header","name":"X-CSRF-Token"},"LocalClientBearer":{"type":"http","scheme":"bearer","description":"Opaque local grant. Maximum 300 seconds; exact actor, client, audience and operation binding. Not production OAuth."},"ClientID":{"type":"apiKey","in":"header","name":"X-Client-ID"}}}}

if __name__=="__main__":
    path=ROOT/"api/mdl-local.openapi.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+"\n")
    print(path)
