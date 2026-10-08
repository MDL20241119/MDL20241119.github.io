(() => {
  'use strict';
  if(window.top!==window.self){document.body.textContent='この設定画面は、MDLのページを直接開いてご利用ください。';return;}
  const form=document.querySelector('form'),first=document.getElementById('password'),second=document.getElementById('confirmation'),status=document.getElementById('status'),button=form.querySelector('button');
  let busy=false;
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if(busy)return;
    if(!first.value.trim()||first.value.length<4||first.value.length>128){status.textContent='この入口専用のパスワードを4〜128文字で入力してください。';return;}
    if(first.value!==second.value){status.textContent='2つの入力が一致しません。';return;}
    if(!document.getElementById('accept').checked){status.textContent='照合用設定が公開されることをご確認ください。';return;}
    busy=true;button.disabled=true;document.getElementById('accept').disabled=true;status.textContent='照合用の設定を作成しています…';
    try{
      const config=await OitaEntryCrypto.create(first.value);
      if(!(await OitaEntryCrypto.verify(second.value,config)))throw new Error('check');
      if(!document.getElementById('accept').checked)throw new Error('agreement');
      first.value='';second.value='';
      const title=document.createElement('h1');title.textContent='公開用の照合設定を作成しました';
      const message=document.createElement('p');message.id='setup-result';message.textContent='パスワードそのものは送信・保存していません。入力欄も消去しました。この画面を閉じずにチャットへ戻り、「設定した」とお知らせください。MDLの入口への反映を進めます。';
      const details=document.createElement('details');
      const summary=document.createElement('summary');summary.textContent='公開用の照合設定';
      const pre=document.createElement('pre');pre.id='public-verifier';pre.textContent=JSON.stringify(config,null,2);pre.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px';
      details.append(summary,pre);
      document.querySelector('main').replaceChildren(title,message,details);
      history.replaceState(null,'',location.pathname+'#result');
    }catch(_){first.value='';second.value='';status.textContent='設定を作成できませんでした。再入力してお試しください。';busy=false;button.disabled=false;document.getElementById('accept').disabled=false;}
  });
})();
