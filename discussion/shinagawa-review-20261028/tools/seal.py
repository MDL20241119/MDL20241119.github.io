#!/usr/bin/env python3
"""Seal an offline document package. No passphrase or content is written to source."""
import argparse, base64, getpass, gzip, hashlib, json, os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def seal_html(html_path, files, password, template_path, output_path):
    payload={"html":Path(html_path).read_text(),"files":{}}
    for key,entry in files.items():
        p=Path(entry["path"])
        payload["files"][key]={"filename":entry.get("filename",p.name),"mime":entry["mime"],"data":base64.b64encode(p.read_bytes()).decode()}
    salt=os.urandom(16);iv=os.urandom(12)
    kdf=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=600000)
    key=kdf.derive(password.encode())
    packed=gzip.compress(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode(),compresslevel=9,mtime=0)
    ciphertext=AESGCM(key).encrypt(iv,packed,b"internal-discussion-v1")
    b64=lambda x:base64.b64encode(x).decode()
    envelope={"version":1,"kdf":"PBKDF2-SHA256","iterations":600000,"cipher":"AES-256-GCM","salt":b64(salt),"iv":b64(iv),"ciphertext":b64(ciphertext)}
    template=Path(template_path).read_text()
    if template.count("{{SEALED_JSON}}")!=1:raise ValueError("Invalid gate template")
    Path(output_path).write_text(template.replace("{{SEALED_JSON}}",json.dumps(envelope,separators=(',',':'))))
    return {"output":str(output_path),"bytes":Path(output_path).stat().st_size,"sha256":hashlib.sha256(Path(output_path).read_bytes()).hexdigest()}

def main():
    p=argparse.ArgumentParser();p.add_argument("--html",required=True);p.add_argument("--files",required=True);p.add_argument("--template",default=str(Path(__file__).with_name("gate.template.html")));p.add_argument("--out",required=True)
    a=p.parse_args();password=getpass.getpass("Package password: ")
    if len(password)<16:raise ValueError("Use a passphrase of at least 16 characters.")
    again=getpass.getpass("Confirm password: ")
    if again!=password:raise ValueError("Passphrases differ.")
    result=seal_html(a.html,json.loads(Path(a.files).read_text()),password,a.template,a.out);print(json.dumps(result))
if __name__=="__main__":main()

