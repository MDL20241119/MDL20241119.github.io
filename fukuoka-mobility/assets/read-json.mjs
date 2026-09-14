/** Read a same-origin JSON snapshot, explicitly decompressing .gz assets. */
export async function readJSON(url){
  const response=await fetch(url);
  if(!response.ok)throw Error('データを取得できません（'+response.status+'）：'+url);
  if(!String(url).split('?')[0].endsWith('.gz'))return response.json();
  if(typeof DecompressionStream==='undefined')throw Error('圧縮データに対応したブラウザーが必要です');
  return new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();
}
