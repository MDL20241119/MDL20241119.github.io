"""Bundle both static pages and lazy data into one portable review HTML."""
import argparse, base64, gzip, json, mimetypes, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args()
def packed(b):return base64.b64encode(gzip.compress(b,compresslevel=9,mtime=0)).decode()
def inline_css(p):
    s=p.read_text()
    def replace(m):
        asset=(p.parent/m.group(1)).resolve()
        return 'url(data:font/woff2;base64,'+base64.b64encode(asset.read_bytes()).decode()+')' if asset.is_file() else m.group(0)
    return re.sub(r"url\(['\"]?([^'\"\)]+)['\"]?\)",replace,s)
def document(folder,mode):
    p=ROOT/folder/'index.html';html=p.read_text();scripts=[]
    def script(m):
        src=(p.parent/m.group(1).split('?')[0]).resolve();scripts.append(src.read_text().replace('</script','<\\/script'));return ''
    html=re.sub(r'<script src="([^"]+)" defer></script>',script,html)
    html=re.sub(r'<link rel="stylesheet" href="([^"]+)">',lambda m:'<style>'+inline_css((p.parent/m.group(1).split('?')[0]).resolve())+'</style>',html)
    shim='''<base href="https://review.invalid/FOLDER/"><script>
window.fetch = async input => parent.reviewFetch(new URL(typeof input==='string'?input:input.url,document.baseURI).pathname);
try { history.replaceState(null,'',parent.reviewRequestedHash||'#home'); } catch { location.hash=parent.reviewRequestedHash||'#home'; }
document.addEventListener('click',event=>{
 const a=event.target.closest('a[href]');if(!a||a.getAttribute('href').startsWith('#'))return;
 const u=new URL(a.getAttribute('href'),document.baseURI);if(u.hostname!=='review.invalid')return;
 event.preventDefault();event.stopImmediatePropagation();
 if(u.pathname==='/municipal-mobility-history/'||u.pathname==='/municipal-mobility-history/index.html')parent.reviewNavigate('municipal',u.hash||'#home');
 else if(u.pathname==='/mobility-policy-history/'||u.pathname==='/mobility-policy-history/index.html')parent.reviewNavigate('policy',u.hash||'#home');
 else parent.reviewDownload(u.pathname);
},true);
window.addEventListener('hashchange',()=>parent.reviewTrack('MODE',location.hash));
</script>'''.replace('FOLDER',folder).replace('MODE',mode)
    html=html.replace('<head>','<head>'+shim)
    html=html.replace('</body>',''.join('<script>'+s+'</script>' for s in scripts)+'</body>')
    return html
assets={}
for folder in ['municipal-mobility-history/data','municipal-mobility-history/verification']:
    for p in (ROOT/folder).rglob('*.json'):
        assets['/'+p.relative_to(ROOT).as_posix()]={'gzip':packed(p.read_bytes()),'mime':'application/json'}
for rel in ['mobility-policy-history/data/mobility_history_data.json','mobility-policy-history/downloads/mobility-history-report.pdf','mobility-policy-history/downloads/mobility-history-ledger.xlsx']:
    p=ROOT/rel;assets['/'+rel]={'gzip':packed(p.read_bytes()),'mime':mimetypes.guess_type(p.name)[0] or 'application/octet-stream'}
docs={mode:packed(document(folder,mode).encode()) for folder,mode in [('municipal-mobility-history','municipal'),('mobility-policy-history','policy')]}
html='''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>モビリティ政策史・自治体の結果と変遷｜検討版</title><style>
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#0b0b0d;color:#fff;font-family:Arial,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif}header{height:65px;display:flex;align-items:center;gap:10px;padding:8px 16px;border-bottom:1px solid #42454e;background:#15161c}header span{font-size:12px;color:#bbb;margin-right:auto}button{border:1px solid #616675;background:transparent;color:white;min-height:43px;padding:8px 17px;font-weight:800;cursor:pointer}button[aria-pressed=true]{background:#e7ff38;color:#101014;border-color:#e7ff38}iframe{border:0;width:100%;height:calc(100dvh - 65px);display:block}#error{padding:30px;color:#ff73bc}#error:empty{display:none}@media(max-width:600px){header{padding:6px 8px;gap:6px}header span{font-size:10px;max-width:60px}button{font-size:12px;padding:7px 10px}} </style></head><body><header><span>検討版<br>本番未反映</span><button id="municipal" aria-pressed="true" onclick="reviewNavigate('municipal','#home')">自治体別</button><button id="policy" aria-pressed="false" onclick="reviewNavigate('policy','#home')">政策別</button><button onclick="reviewNavigate('municipal','#scope')">照合結果</button></header><div id="error" role="alert"></div><iframe id="screen" title="政策史・自治体の結果と変遷 プレビュー"></iframe><script>
const assets=__REVIEW_PACKED_ASSETS__, documents=__REVIEW_PACKED_DOCUMENTS__, memo=new Map();let active='',serial=0;window.reviewRequestedHash='#home';
async function unzip(encoded){const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());}
window.reviewFetch=async path=>{const asset=assets[path];if(!asset)return new Response('Preview asset not found',{status:404});if(!memo.has(path))memo.set(path,unzip(asset.gzip));const bytes=await memo.get(path);return new Response(bytes,{headers:{'Content-Type':asset.mime}});};
window.reviewTrack=(mode,hash)=>{history.replaceState(null,'','#'+mode+'/'+encodeURIComponent(hash));};
window.reviewNavigate=async(mode,hash='#home')=>{const seq=++serial;document.getElementById('error').textContent='';try{
 reviewRequestedHash=hash;const html=new TextDecoder().decode(await unzip(documents[mode]));if(seq!==serial)return;
 active=mode;document.querySelectorAll('header button[id]').forEach(b=>b.setAttribute('aria-pressed',String(b.id===mode)));reviewTrack(mode,hash);document.getElementById('screen').srcdoc=html;
}catch(e){document.getElementById('error').textContent='プレビューを開けませんでした。現在のChromeまたはSafariでファイルを開いてください。'+e.message;}};
window.reviewDownload=async path=>{try{const r=await reviewFetch(path);if(!r.ok)throw Error('ファイル未収録');const b=await r.blob(),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=path.split('/').pop();document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),60000);}catch(e){document.getElementById('error').textContent=e.message;}};
const [mode,encoded]=(location.hash.slice(1)||'municipal/').split('/');reviewNavigate(documents[mode]?mode:'municipal',encoded?decodeURIComponent(encoded):'#home');
</script></body></html>'''.replace('__REVIEW_PACKED_ASSETS__',json.dumps(assets,separators=(',',':'))).replace('__REVIEW_PACKED_DOCUMENTS__',json.dumps(docs,separators=(',',':')))
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(html)
print(json.dumps({'output':str(a.output),'bytes':a.output.stat().st_size,'bundled_data_assets':len(assets),'documents':list(docs)},ensure_ascii=False))
