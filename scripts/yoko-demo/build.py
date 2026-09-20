"""Build the GitHub Pages demo from the verified standalone Mobility Core."""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TARGET=ROOT/'danchi-elevator/demo'
MODULES=['__init__','core','db','catalog','booking','payments','observations','gtfs',
         'service_calendar','transport_data','agent_tasks','delegation']

def build_core(source):
    files={f'app/{name}.py':(source/f'app/{name}.py').read_text() for name in MODULES}
    fixture=json.loads((source/'fixtures/synthetic-domain.json').read_text())
    fixture['tenants'][0]['name']='ひだまり団地 デモ運営'
    fixture['services'][0]['name']='ひだまり団地 おでかけ便（架空）'
    names={'stop-a':'中央広場','stop-b':'駅前ロータリー','stop-c':'ふれあいセンター'}
    for stop in fixture['stops']:stop['name']=names[stop['id']]
    files['fixtures/synthetic-domain.json']=json.dumps(fixture,ensure_ascii=False,indent=2)+'\n'
    # Pyodide omits OpenSSL's PBKDF2. Bootstrap public fictional accounts with
    # the native, unchanged initializer at build time, never a weaker hash.
    with tempfile.TemporaryDirectory() as directory:
        temp=Path(directory)
        for name,content in files.items():
            target=temp/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
        subprocess.run([sys.executable,'-c',"from app.db import initialize; initialize('seed.sqlite3')"],cwd=temp,check=True)
        seed=(temp/'seed.sqlite3').read_bytes()
    bundle={'version':'0.15.0-demo','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip(),
        'scope':'Unmodified core modules; only fictional fixture display names changed. Browser-only demo, not a public reservation server.',
        'sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()},'files':files}
    bundle['database_seed']={'encoding':'zlib+base64','sha256':hashlib.sha256(seed).hexdigest(),'data':base64.b64encode(zlib.compress(seed,9)).decode()}
    (TARGET/'core-bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,separators=(',',':'))+'\n')

def build(source, ui_only=False):
    if not ui_only:
        build_core(source)
    html=(source/'app/static/index.html').read_text()
    html=html.replace('<title>横のエレベーター｜Webアプリ</title>', '<title>横のエレベーター｜3者の体験デモ</title>')
    html=html.replace('<meta name="color-scheme" content="light">', '<meta name="color-scheme" content="light"><meta name="referrer" content="no-referrer"><meta name="theme-color" content="#F8F7F3">')
    html=html.replace('width=device-width,initial-scale=1','width=device-width,initial-scale=1,viewport-fit=cover')
    html=html.replace('href="/style.css"','href="./style.css"').replace('<script src="/app.js" defer></script>',
        '<link rel="stylesheet" href="../../oita-mobility/assets/leaflet.css"><link rel="stylesheet" href="./demo.css?v=3"><link rel="stylesheet" href="./journey.css?v=14b"><link rel="stylesheet" href="./driver.css?v=15"><link rel="stylesheet" href="./neo-swiss.css?v=15c"><link rel="stylesheet" href="./line-chat.css?v=15"><link rel="stylesheet" href="./mobile.css?v=16b"><script src="../../oita-mobility/assets/leaflet.js" defer></script><script src="./journey-input.js?v=14" defer></script><script src="./journey.js?v=16b" defer></script><script src="./operations.js?v=16b" defer></script><script src="./driver.js?v=16b" defer></script><script src="./admin.js?v=15" defer></script><script src="./mobile.js?v=16b" defer></script><script src="./demo-bridge.js?v=16b" defer></script>')
    html=html.replace('href="/" aria-label','href="./" aria-label')
    html=html.replace('ローカル試験 <span class="strip-detail">架空データのみ・実際の送迎は行いません','体験デモ <span class="strip-detail">架空の地域・実際の送迎は行いません')
    html=html.replace('Webアプリをはじめる','3つの役割で、体験する')
    html=html.replace('入口を選ぶと、架空のアカウントで試せます。<br>保存した依頼は、3者の画面で共有されます。','ユーザー・ドライバー・管理者。<br>同じ依頼が、3つの画面をつなぎます。')
    html=html.replace('利用者として試す','ユーザー用').replace('ドライバーとして試す','ドライバー用').replace('管理者として試す','管理者用')
    html=html.replace('役割を変えるときはログアウトしてください。同時に試すときは別のブラウザーまたはプロファイルを使います。実際の利用者情報は入力しないでください。','同じブラウザー内で3つの役割を切り替えられます。実在する方の情報は入力しないでください。')
    html=html.replace('<div id="web-entry">','<div id="web-entry">')
    html=html.replace('<form id="login-form">','<form id="login-form" hidden>').replace('<button id="other-login"','<button hidden id="other-login"')
    html=html.replace('<main id="main" tabindex="-1">','''<div class="demo-shell">
<nav id="demo-roles" class="demo-roles" aria-label="デモの役割を切り替える"><a href="?role=user" data-demo-role="rider-a1">ユーザー用</a><a href="?role=driver" data-demo-role="driver-a1">ドライバー用</a><a href="?role=admin" data-demo-role="admin-a1">管理者用</a></nav>
<p class="demo-scope">このブラウザーだけに保存するデモです。端末間の共有はありません。</p>
<section id="demo-boot" class="notice" role="status"><b id="demo-boot-title">デモを準備しています…</b><p id="demo-boot-message">初回は動作に必要なファイルを読み込みます。そのままお待ちください。</p><button id="demo-reload" class="secondary" type="button" hidden>もう一度読み込む</button></section>
</div><main id="main" tabindex="-1">''')
    html=re.sub(r'      <div id="driver-safety".*?</div>\n','',html,count=1)
    panels='\n'.join((ROOT/f'scripts/yoko-demo/{role}.html').read_text() for role in ['journey','driver','admin'])
    html=html.replace('      <div class="work-grid" id="work-grid">',panels+'\n      <div class="work-grid" id="work-grid">')
    html=html.replace('Web試験版 0.12.0','公開体験デモ 0.16.0')
    html=html.replace('</footer>','<span><a href="./about.html">このデモについて</a> · <button id="reset-demo" class="text-button" type="button">デモを最初から</button></span></footer>')
    html=html.replace('</body>','''<dialog id="reset-dialog" aria-labelledby="reset-title"><div class="dialog-content"><h2 id="reset-title">デモを最初からやり直しますか？</h2><p>このブラウザーのデモ履歴を初期状態に戻します。他の端末や実際の運行には影響しません。</p><div class="actions"><button id="reset-back" class="secondary" type="button">戻る</button><button id="reset-confirm" class="primary" type="button">初期状態に戻す</button></div></div></dialog></body>''')
    (TARGET/'index.html').write_text(html)
    (TARGET/'style.css').write_text((source/'app/static/style.css').read_text())
    ui=(source/'app/static/app.js').read_text().replace('yoko-pending:','yoko-demo-pending:v1:')
    ui=ui.replace("rider:'利用者'","rider:'ユーザー'")
    ui=ui.replace('ログアウト</button>','入口へ戻る</button>')
    ui=ui.replace("${date(snap.as_of)} 時点（日本時間）","${date(snap.as_of)} 更新（このブラウザー）")
    ui += '\n' + (ROOT/'scripts/yoko-demo/ui-hooks.js').read_text()
    (TARGET/'app.js').write_text(ui)
    print(json.dumps({'ui_version':'0.16.0','core_rebuilt':not ui_only,'core_bytes':(TARGET/'core-bundle.json').stat().st_size}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--ui-only',action='store_true');args=parser.parse_args();build(args.source,args.ui_only)
