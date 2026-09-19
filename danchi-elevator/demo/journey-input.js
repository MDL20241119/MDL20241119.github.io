/* Local, deterministic input assistance. Never submits a reservation. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.YokoJourneyInput=factory();})(typeof window==='undefined'?this:window,function(){
  'use strict';
  const aliases={'stop-a':['中央広場','ちゅうおうひろば'],'stop-b':['駅前ロータリー','駅前','ロータリー'],'stop-c':['ふれあいセンター','ふれあい']};
  const normalize=value=>String(value).normalize('NFKC').trim().replace(/[\s、,。！!？?]+/g,'');
  const numbers={'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10};
  function parse(text,{stops,selection={},target='origin'}){
    let value=normalize(text).replace(/(?:お願いします|お願い|です)$/,'');
    const fail=message=>({ok:false,message});
    if(!value)return fail('場所名や人数を入力してください。');
    if(['やり直す','最初から','リセット'].includes(value))return {ok:true,command:'reset'};
    if(['戻る','ひとつ戻る','一つ戻る'].includes(value))return {ok:true,command:'undo'};
    if(/^(OK|ok|はい|依頼|予約)$/.test(value))return fail('送信だけでは依頼しません。場所と人数をそろえ、「内容を確認する」から進んでください。');
    value=value.replace(/ひとり/g,'1人').replace(/ふたり/g,'2人').replace(/さんにん/g,'3人');
    let count=null;
    const found=[...value.matchAll(/(-?\d+(?:\.\d+)?|[一二三四五六七八九十]+)(?:人|名)/g)];
    if(found.length>1)return fail('人数は一つだけ入力してください。例：2人');
    if(found.length){count=numbers[found[0][1]]??Number(found[0][1]);value=value.replace(found[0][0],'').replace(/で$/,'');if(/^(?:人数|乗る人数)(?:は|:)?$/.test(value))value='';}
    else if(/^(-?\d+(?:\.\d+)?|[一二三四五六七八九十]+)$/.test(value)){count=numbers[value]??Number(value);value='';}
    if(count!==null&&(!Number.isInteger(count)||count<1||count>3))return fail('このデモでは1〜3人で選んでください。');
    const update={};if(count!==null)update.passengers=count;
    const resolve=name=>{
      const exact=normalize(name);
      const matches=stops.filter(s=>s.active!==false&&[s.name,...(aliases[s.id]||[])].some(a=>normalize(a)===exact));
      return matches.length===1?matches[0].id:null;
    };
    const unknown='その場所は見つかりませんでした。地図の緑のピンか、表示された場所名から選んでください。';
    if(value){
      if(value.includes('から')&&!value.endsWith('から')){
        const parts=value.split('から');if(parts.length!==2)return fail('「中央広場から駅前ロータリーへ2人」のように入力してください。');
        const from=parts[0].replace(/^(?:出発|乗る場所)(?:は|:)?/,'');
        const to=parts[1].replace(/(?:まで|へ|に)$/,'');
        update.origin=resolve(from);update.destination=resolve(to);
        if(!update.origin||!update.destination)return fail(unknown);
      }else{
        let field=target,name=value;
        const origin=value.match(/^(?:出発|乗る場所|乗車場所)(?:は|:)?(.+)$/);
        const destination=value.match(/^(?:到着|目的地|降りる場所|降車場所)(?:は|:)?(.+)$/);
        if(origin){field='origin';name=origin[1];}
        else if(destination){field='destination';name=destination[1];}
        else if(value.endsWith('から')){field='origin';name=value.slice(0,-2);}
        else if(/(?:まで|へ)$/.test(value)){field='destination';name=value.replace(/(?:まで|へ)$/,'');}
        if(!['origin','destination'].includes(field))return fail('変更する場所は「出発は中央広場」「目的地は駅前」のように入力してください。');
        const id=resolve(name);if(!id)return fail(unknown);update[field]=id;
      }
    }
    if(!Object.keys(update).length)return fail('場所名か「2人」のように入力してください。');
    const next={...selection,...update};
    if(next.origin&&next.origin===next.destination)return fail('乗る場所と降りる場所は、別の場所を選んでください。');
    return {ok:true,update};
  }
  return {parse,normalize};
});
