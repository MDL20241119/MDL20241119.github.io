'use strict';
// Version-pinned official runtime. Domain rules remain in the Python Core.
const INDEX_URL='https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';
const PERSIST='/yoko-elevator-demo-v1';
let pyodide;
const sync=populate=>new Promise((resolve,reject)=>pyodide.FS.syncfs(populate,error=>error?reject(error):resolve()));
async function boot(){
  importScripts(INDEX_URL+'pyodide.js');
  pyodide=await loadPyodide({indexURL:INDEX_URL});
  await pyodide.loadPackage('tzdata');
  const [bundleResponse,runtimeResponse]=await Promise.all([fetch('./core-bundle.json'),fetch('./demo_runtime.py')]);
  if(!bundleResponse.ok||!runtimeResponse.ok)throw new Error('アプリのファイルを読み込めません');
  const bundle=await bundleResponse.json();
  for(const [name,source] of Object.entries(bundle.files)){
    if(!/^(app\/[a-z_]+\.py|fixtures\/synthetic-domain\.json)$/.test(name))throw new Error('Unexpected source path');
    const bytes=new TextEncoder().encode(source);
    const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');
    if(digest!==bundle.sha256[name])throw new Error('Source integrity mismatch');
    pyodide.FS.mkdirTree('/project/'+name.slice(0,name.lastIndexOf('/')));
    pyodide.FS.writeFile('/project/'+name,source);
  }
  pyodide.FS.writeFile('/project/demo_runtime.py',await runtimeResponse.text());
  pyodide.FS.writeFile('/project/fixtures/browser-seed.json',JSON.stringify(bundle.database_seed));
  pyodide.FS.mkdirTree(PERSIST);
  pyodide.FS.mount(pyodide.FS.filesystems.IDBFS,{},PERSIST);
  await pyodide.runPythonAsync("import sys\nsys.path.insert(0, '/project')\nfrom demo_runtime import dispatch_json");
  postMessage({type:'ready',version:bundle.version});
}
let queue=boot().catch(error=>{postMessage({type:'fatal',message:String(error)});throw error;});
onmessage=event=>{
  const {id,command}=event.data;
  queue=queue.then(async()=>{
    try{
      // The caller holds one origin-wide Web Lock until persistence completes.
      await sync(true);
      pyodide.globals.set('demo_command_json',JSON.stringify(command));
      const raw=pyodide.runPython("dispatch_json('/yoko-elevator-demo-v1/demo.sqlite3', demo_command_json)");
      await sync(false);
      postMessage({id,result:JSON.parse(raw)});
    }catch(error){postMessage({id,result:{status:503,data:{error:{code:'DEMO_STORAGE_ERROR',message:'保存を確認できません。ページを再読み込みして、同じ操作の結果を照合してください。'}}}});console.error(String(error));}
  });
};
