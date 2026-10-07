export const TEXT_SIZES=[13,14,15,16,18,20] as const;
export const TEXT_SIZE_KEY='omc-text-size-px';
export function readTextPreference(current:string|null,legacy:string|null):number|null {
 if(current==='default')return null;
 if(current!==null){const n=Number(current);if(TEXT_SIZES.some(v=>v===n))return n;}
 if(legacy!==null&&['0','1','2'].includes(legacy))return [15,16,18][Number(legacy)];
 return null;
}
export function stepTextSize(current:number,direction:number){
 return direction<0?[...TEXT_SIZES].reverse().find(n=>n<current)??TEXT_SIZES[0]:TEXT_SIZES.find(n=>n>current)??TEXT_SIZES[TEXT_SIZES.length-1];
}
