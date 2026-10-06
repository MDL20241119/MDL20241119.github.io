import type {RecordItem} from './model';
const metadata=new Set(['revision','archived','updatedAt','updatedBy']);
export function rebaseDraft(original:RecordItem,draft:RecordItem,current:RecordItem){
 const merged={...current} as RecordItem;const overlaps:string[]=[];
 for(const key of Object.keys(draft)){if(metadata.has(key))continue;const field=key as keyof RecordItem;if(JSON.stringify(draft[field])===JSON.stringify(original[field]))continue;if(JSON.stringify(current[field])!==JSON.stringify(original[field])&&JSON.stringify(current[field])!==JSON.stringify(draft[field]))overlaps.push(key);(merged as any)[key]=draft[field]}
 return {record:merged,overlaps};
}
export const FIELD_NAMES:Record<string,string>={title:'名前',owner:'担当',ownerCertainty:'担当の確度',status:'進み具合',dueDate:'期限',dueCertainty:'日付の確度',startDate:'開始日',startTime:'開始時刻',endTime:'終了時刻',nextAction:'次にすること',completion:'完了の条件',dependencies:'前の作業',priority:'優先度',note:'共有メモ',area:'区分',groupKey:'分類',options:'選択肢'};
