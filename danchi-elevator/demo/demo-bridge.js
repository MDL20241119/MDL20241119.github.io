'use strict';
(() => {
  const buttons=[...document.querySelectorAll('[data-login],#reset-demo')];
  buttons.forEach(button=>{button.disabled=true;});
  const roles={'user':'rider-a1','driver':'driver-a1','admin':'admin-a1'};
  let actor=roles[new URL(location.href).searchParams.get('role')]||null;
  let worker,ready=false,sequence=0;
  const pending=new Map();
  const nativeFetch=window.fetch.bind(window);
  const reply=(status,data)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
  document.getElementById('demo-roles').addEventListener('click',event=>{if(!ready)event.preventDefault();});
  document.getElementById('demo-reload').addEventListener('click',()=>location.reload());
  function rpc(command){return new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,{resolve,reject});worker.postMessage({id,command});});}
  function dispatch(command){return navigator.locks.request('yoko-elevator-demo-v1',()=>rpc(command));}
  window.fetch=async(url,options={})=>{
    // Only the known app routes use the in-browser demo adapter. The public
    // website receives no passenger API request, token or entered form data.
    if(typeof url!=='string'||!(url.startsWith('/api/')||url==='/demo/reset'))return nativeFetch(url,options);
    if(options.signal?.aborted)throw new DOMException('Aborted','AbortError');
    const body=options.body?JSON.parse(options.body):undefined;
    if(url==='/api/session'){
      if(!Object.values(roles).includes(body?.username))return reply(401,{error:{code:'DEMO_ROLE_REQUIRED',message:'上の3つの入口から選んでください。'}});
      actor=body.username;
      const result=await dispatch({actor,path:'/api/me',method:'GET'});return reply(result.status,result.data);
    }
    if(url==='/api/logout'){actor=null;return reply(200,{logged_out:true});}
    const result=await dispatch({actor,path:url,method:options.method||'GET',body});
    if(url==='/demo/reset'&&result.status===200)actor=null;
    return reply(result.status,result.data);
  };
  async function main(){
    if(!window.Worker||!window.indexedDB||!navigator.locks||!window.crypto?.subtle)throw new Error('このブラウザーではデモの保存機能を利用できません。新しいSafari、Chrome、Edgeで開いてください。');
    worker=new Worker('./demo-worker.js');
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('読み込みに時間がかかっています。通信を確認して、もう一度読み込んでください。')),60000);
      worker.onerror=event=>{clearTimeout(timer);reject(new Error(event.message||'デモを起動できませんでした'));for(const p of pending.values())p.reject(new Error('Worker stopped'));pending.clear();};
      worker.onmessage=event=>{
        const value=event.data;
        if(value.type==='ready'){clearTimeout(timer);resolve();}
        else if(value.type==='fatal'){clearTimeout(timer);reject(new Error(value.message));}
        else if(pending.has(value.id)){pending.get(value.id).resolve(value.result);pending.delete(value.id);}
      };
    });
    document.getElementById('demo-boot-title').textContent='保存データを準備しています…';
    const result=await dispatch({path:'/demo/initialize',method:'POST'});
    if(result.status!==200)throw new Error(result.data.error.message);
    await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='./app.js';script.onload=resolve;script.onerror=()=>reject(new Error('画面を読み込めませんでした'));document.head.append(script);});
    ready=true;buttons.forEach(button=>{button.disabled=false;});document.getElementById('demo-boot').hidden=true;
  }
  main().catch(error=>{
    worker?.terminate();
    document.getElementById('demo-boot-title').textContent='デモを起動できませんでした';
    document.getElementById('demo-boot-message').textContent=error.message;
    document.getElementById('demo-reload').hidden=false;
    console.error(error);
  });
})();
