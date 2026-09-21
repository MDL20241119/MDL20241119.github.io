"""Validate the unchanged, SHA-256 pinned official OpenAPI 3.0.4 contract.

Loaded only when the optional MLIT local adapter is enabled. Authentication and
approval headers belong to the separate MDL local integration profile.
"""
import copy
import hashlib
import re
from urllib.parse import parse_qs
from .core import fail
from .db import ROOT

SOURCE=ROOT/"artifacts/standards/mlit/extracted/API/commmmons_doc_003-07_ver01.yaml"
SOURCE_SHA256="d0462291f46f8353f4a1d7ee7fd40562137b3e3d4e36af40fab945f1a679f0bc"

class Contract:
    def __init__(self):
        import yaml
        from openapi_schema_validator import OAS30Validator
        raw=SOURCE.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
            raise RuntimeError("Official source hash changed; review required")
        self.spec=yaml.safe_load(raw)
        self.validator=OAS30Validator
        self.operations=[]
        for path,methods in self.spec["paths"].items():
            pattern=re.compile("^"+re.escape(path).replace(r"\{id\}",r"(?P<id>[^/]+)")+"$")
            for method,op in methods.items():
                if method in ("get","post","put","delete"):
                    self.operations.append((method.upper(),path,pattern,op))

    def match(self,method,path):
        for verb,template,pattern,op in self.operations:
            match=pattern.fullmatch(path)
            if verb==method and match:
                return template,op,match.groupdict()
        return None

    def validate(self,schema,value,response=False):
        errors=self.validator(schema,format_checker=self.validator.FORMAT_CHECKER).iter_errors(value)
        if next(errors,None) is not None:
            # Never return validation messages containing passenger inputs.
            fail("RESPONSE_CONTRACT_ERROR" if response else "SCHEMA_INVALID",
                 "標準応答の整合性を確認できません" if response else "国交省原本の項目・型・形式に一致しません",500 if response else 400)

    def request(self,matched,query,body):
        _,op,path_values=matched
        try:
            raw=parse_qs(query,keep_blank_values=True,strict_parsing=True,max_num_fields=100)
        except ValueError:
            fail("INVALID_QUERY","クエリの形式が不正です")
        params={x["name"]:x for x in op.get("parameters",[]) if x["in"]=="query"}
        if set(raw)-set(params) or any(len(v)!=1 for v in raw.values()):
            fail("INVALID_QUERY","未定義または重複したクエリです")
        # A default radius does not mean the caller explicitly supplied it.
        # The official GET /stops prose forbids radius without location,
        # including radius=500 and requests which also specify stop_ids.
        if op['operationId']=='getStops' and 'radius' in raw and 'location' not in raw:
            fail('INVALID_QUERY','半径検索には位置を指定してください')
        result={}
        for name,p in params.items():
            schema=p["schema"]
            if name not in raw:
                if p.get("required"):
                    fail("INVALID_QUERY","必須クエリが不足しています")
                if "default" in schema:
                    result[name]=copy.deepcopy(schema["default"])
                continue
            val=raw[name][0]
            if schema.get("type")=="integer":
                if not re.fullmatch(r"-?[0-9]{1,10}",val):
                    fail("INVALID_QUERY","整数のクエリが必要です")
                val=int(val)
            elif schema.get("type")=="array":
                val=val.split(",")
            self.validate(schema,val)
            result[name]=val
        for p in op.get("parameters",[]):
            if p["in"]=="path":
                self.validate(p["schema"],path_values[p["name"]])
        if "requestBody" in op:
            self.validate(op["requestBody"]["content"]["application/json"]["schema"],body)
        elif body is not None:
            fail("UNEXPECTED_BODY","この操作に本文はありません")
        return result

    def response(self,matched,status,data):
        op=matched[1]
        response=op["responses"].get(str(status))
        if response is None:
            fail("RESPONSE_CONTRACT_ERROR","原本にない応答コードです",500)
        content=response.get("content",{})
        if content:
            self.validate(content["application/json"]["schema"],data,True)
        elif data is not None:
            fail('RESPONSE_CONTRACT_ERROR','この応答には本文を含められません',500)

    def problem(self,matched,error):
        declared=matched[1]["responses"]
        status=error.status
        if str(status) not in declared:
            status=400 if status<500 and status!=429 and '400' in declared else 500
        data={"type":"urn:mdl:yoko:error:"+error.code.lower(),"title":error.code,"status":status,"detail":error.message}
        self.response(matched,status,data)
        return status,data
