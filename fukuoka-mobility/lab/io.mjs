export function parseCSV(text) {
  text=text.replace(/^\uFEFF/,'');const grid=[];let row=[],field='',quoted=false,closed=false;
  for(let i=0;i<=text.length;i++){
    const c=text[i];
    if(quoted){if(c===undefined)throw Error('CSVの引用符が閉じていません');if(c==='"'){if(text[i+1]==='"'){field+='"';i++}else{quoted=false;closed=true}}else field+=c;continue}
    if(c==='"'&&!field&&!closed){quoted=true;continue}
    if(c===','||c==='\r'||c==='\n'||c===undefined){row.push(field);field='';closed=false;if(c!==','){if(row.some(x=>x!==''))grid.push(row);row=[];if(c==='\r'&&text[i+1]==='\n')i++}continue}
    if(closed||c==='"')throw Error('CSVの引用符または区切りが不正です');field+=c;
  }
  if(!grid.length)return [];
  const headers=grid.shift().map(x=>x.trim());if(new Set(headers).size!==headers.length||headers.some(x=>!x||['__proto__','constructor','prototype'].includes(x)))throw Error('CSVの列名が空・重複・予約語です');
  return grid.map((r,i)=>{if(r.length!==headers.length)throw Error(`CSV ${i+2}行目の列数が一致しません`);return Object.fromEntries(headers.map((h,j)=>[h,r[j]]))});
}
export function csvText(rows,{safe=false,headers=null}={}){
  headers=headers??[...new Set(rows.flatMap(r=>Object.keys(r)))];
  const cell=v=>{let s=String(v??'');if(safe&&/^[\s\u0000-\u001f]*[=+\-@＝＋－＠]/u.test(s))s="'"+s;return /[",\r\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s};
  return headers.map(cell).join(',')+'\r\n'+rows.map(r=>headers.map(h=>cell(r[h])).join(',')).join('\r\n')+'\r\n';
}
const crcTable=Uint32Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0});
export function crc32(bytes){let c=0xffffffff;for(const b of bytes)c=crcTable[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0}
export async function unzip(buffer){
  const bytes=new Uint8Array(buffer),v=new DataView(buffer);let end=bytes.length-22;
  for(;end>=Math.max(0,bytes.length-65557);end--)if(v.getUint32(end,true)===0x06054b50)break;
  if(end<0||v.getUint32(end,true)!==0x06054b50)throw Error('ZIPの終端を確認できません');
  const count=v.getUint16(end+10,true);if(count>1000||v.getUint16(end+4,true)!==0)throw Error('このZIP形式またはファイル数には対応していません');
  let p=v.getUint32(end+16,true),size=0;const out={};
  for(let i=0;i<count;i++){
    if(p+46>bytes.length||v.getUint32(p,true)!==0x02014b50)throw Error('ZIP目次が不正です');
    const flags=v.getUint16(p+8,true),method=v.getUint16(p+10,true),crc=v.getUint32(p+16,true),packed=v.getUint32(p+20,true),unpacked=v.getUint32(p+24,true),nl=v.getUint16(p+28,true),xl=v.getUint16(p+30,true),cl=v.getUint16(p+32,true),off=v.getUint32(p+42,true);
    const name=new TextDecoder().decode(bytes.subarray(p+46,p+46+nl));p+=46+nl+xl+cl;if(name.endsWith('/')||name.startsWith('__MACOSX/'))continue;
    size+=unpacked;if(size>80*1024*1024)throw Error('展開後80MBを超えます。対象データを分けてください');
    if(flags&1)throw Error('暗号化ZIPは読み込めません');if(off+30>bytes.length||v.getUint32(off,true)!==0x04034b50)throw Error('ZIPのファイル情報が不正です');
    const start=off+30+v.getUint16(off+26,true)+v.getUint16(off+28,true);if(start+packed>bytes.length)throw Error('ZIPのデータが欠けています');
    const source=bytes.slice(start,start+packed);let plain;
    if(method===0)plain=source;else if(method===8){
      if(typeof DecompressionStream==='undefined')throw Error('このブラウザはZIP展開に未対応です。新しいSafari・Chrome等をご利用ください');
      const stream=new Blob([source]).stream().pipeThrough(new DecompressionStream('deflate-raw'));const reader=stream.getReader(),chunks=[];let total=0;
      while(true){const r=await reader.read();if(r.done)break;total+=r.value.length;if(total>unpacked||total>80*1024*1024){await reader.cancel();throw Error('ZIPの展開サイズが不正です')}chunks.push(r.value)}
      plain=new Uint8Array(total);let o=0;for(const chunk of chunks){plain.set(chunk,o);o+=chunk.length}
    }else throw Error('未対応のZIP圧縮方式です');
    if(plain.length!==unpacked||crc32(plain)!==crc)throw Error('ZIPのサイズまたはCRC検証に失敗しました');
    const base=name.split('/').at(-1);if(out[base])throw Error(`ZIP内のファイル名が重複しています：${base}`);out[base]=plain;
  }return out;
}
export function zip(entries){
  const enc=new TextEncoder(),parts=[],central=[];let offset=0;
  for(const [name,value]of Object.entries(entries)){
    const n=enc.encode(name),b=typeof value==='string'?enc.encode(value):value,c=crc32(b),h=new Uint8Array(30+n.length),v=new DataView(h.buffer);
    v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);v.setUint32(14,c,true);v.setUint32(18,b.length,true);v.setUint32(22,b.length,true);v.setUint16(26,n.length,true);h.set(n,30);parts.push(h,b);
    const d=new Uint8Array(46+n.length),w=new DataView(d.buffer);w.setUint32(0,0x02014b50,true);w.setUint16(4,20,true);w.setUint16(6,20,true);w.setUint16(8,0x800,true);w.setUint32(16,c,true);w.setUint32(20,b.length,true);w.setUint32(24,b.length,true);w.setUint16(28,n.length,true);w.setUint32(42,offset,true);d.set(n,46);central.push(d);offset+=h.length+b.length;
  }
  const e=new Uint8Array(22),v=new DataView(e.buffer),cs=central.reduce((s,b)=>s+b.length,0);v.setUint32(0,0x06054b50,true);v.setUint16(8,central.length,true);v.setUint16(10,central.length,true);v.setUint32(12,cs,true);v.setUint32(16,offset,true);return new Blob([...parts,...central,e],{type:'application/zip'});
}
export async function sha256(buffer){const digest=await crypto.subtle.digest('SHA-256',buffer);return [...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join('')}
export function download(name,content,type='text/plain;charset=utf-8'){const b=content instanceof Blob?content:new Blob([content],{type});const url=URL.createObjectURL(b),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000)}
