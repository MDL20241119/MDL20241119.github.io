// The comparison is evaluated by SQLite inside the same statement as the write.
// Only dependency-changing writes need it; unrelated edits remain independent.
export const GRAPH_SIGNATURE_SQL="COALESCE((SELECT group_concat(id || ':' || COALESCE(json_extract(payload, '$.dependencies'), '[]'), '|') FROM (SELECT id, payload FROM records ORDER BY id)), '')";
export function graphSignature(records:{id:string;dependencies:string[]}[]){return [...records].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0).map(r=>r.id+':'+JSON.stringify(r.dependencies)).join('|')}
