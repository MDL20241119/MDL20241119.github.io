// Candidate lists reuse a task's shared memo; there is no second address book.
export function candidateRows(note:string){
 const section=note.split('【説明・参画打診候補】')[1];if(!section)return [];
 return section.split(/\n【/)[0].split('\n').map(line=>line.trim().replace(/^[-・]\s*/,''))
  .filter(line=>line.includes('｜')).map(line=>{const [category,name,...action]=line.split('｜').map(s=>s.trim());return {category,name,nextAction:action.join('｜')}}).filter(r=>r.name&&r.category);
}
