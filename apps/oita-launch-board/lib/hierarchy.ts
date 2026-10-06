import type {RecordItem} from './model';
export const TASK_GROUPS = [
  {
    "id": "establish",
    "title": "団体を発足する",
    "color": "#ff8a00",
    "children": [
      {
        "id": "purpose",
        "title": "目的・設立条件"
      },
      {
        "id": "foundation",
        "title": "発起人・制度・予算"
      },
      {
        "id": "coordination",
        "title": "県・ぷらっととの役割調整"
      },
      {
        "id": "participants",
        "title": "参加者・参画区分"
      },
      {
        "id": "launch-plan",
        "title": "計画・総会・公表準備"
      }
    ]
  },
  {
    "id": "vehicle",
    "title": "車両活用・披露目を進める",
    "color": "#d8d0f0",
    "children": [
      {
        "id": "ip",
        "title": "現行利用・将来IP"
      },
      {
        "id": "investment",
        "title": "協議・投資判断"
      },
      {
        "id": "vehicle-ready",
        "title": "装飾・管理・披露目"
      }
    ]
  },
  {
    "id": "projects",
    "title": "共創案件を育てる",
    "color": "#58f21b",
    "children": [
      {
        "id": "needs",
        "title": "利用ニーズ・初期候補"
      },
      {
        "id": "project-plan",
        "title": "実施条件・検証・優先順位"
      }
    ]
  },
  {
    "id": "operations",
    "title": "運営を支える",
    "color": "#efe9d8",
    "children": [
      {
        "id": "secretariat",
        "title": "事務局・記録・共通ルール"
      },
      {
        "id": "training",
        "title": "契約・検収・証憑"
      },
      {
        "id": "contract",
        "title": "人材育成・研修成果"
      }
    ]
  }
];
const existingGroups:Record<string,string> = {
  "OMC-001": "purpose",
  "OMC-002": "purpose",
  "OMC-007": "purpose",
  "OMC-032": "purpose",
  "OMC-003": "foundation",
  "OMC-005": "foundation",
  "OMC-006": "foundation",
  "OMC-008": "coordination",
  "OMC-009": "coordination",
  "OMC-011": "coordination",
  "OMC-012": "coordination",
  "OMC-013": "participants",
  "OMC-014": "participants",
  "OMC-015": "participants",
  "OMC-016": "participants",
  "OMC-017": "participants",
  "OMC-018": "participants",
  "OMC-034": "launch-plan",
  "OMC-038": "launch-plan",
  "OMC-039": "launch-plan",
  "OMC-042": "launch-plan",
  "OMC-019": "ip",
  "OMC-025": "ip",
  "OMC-041": "ip",
  "OMC-020": "investment",
  "OMC-021": "investment",
  "OMC-022": "vehicle-ready",
  "OMC-023": "vehicle-ready",
  "OMC-024": "vehicle-ready",
  "OMC-010": "needs",
  "OMC-026": "needs",
  "OMC-027": "needs",
  "OMC-028": "needs",
  "OMC-029": "needs",
  "OMC-030": "project-plan",
  "OMC-031": "project-plan",
  "OMC-004": "secretariat",
  "OMC-036": "secretariat",
  "OMC-037": "secretariat",
  "OMC-033": "training",
  "OMC-040": "training",
  "OMC-035": "contract"
};

export const GROUP_OPTIONS=TASK_GROUPS.flatMap(g=>g.children.map(s=>[s.id,`${g.title} / ${s.title}`] as [string,string]));
export function groupKey(r:RecordItem):string {
 if(r.groupKey&&GROUP_OPTIONS.some(([id])=>id===r.groupKey))return r.groupKey;
 if(existingGroups[r.id])return existingGroups[r.id];
 const defaults:Record<string,string>={'枠組み・運営':'foundation','県・ぷらっと調整':'coordination','参加メンバー':'participants','e-palette':'vehicle-ready','車両活用':'vehicle-ready','個別プロジェクト':'needs','設立準備':'launch-plan','人材育成':'training','契約・事業管理':'contract'};
 return defaults[r.area]||'unclassified';
}
export function groupPath(r:RecordItem){const key=groupKey(r);for(const g of TASK_GROUPS){const sub=g.children.find(s=>s.id===key);if(sub)return `${g.title} / ${sub.title}`}return r.kind==='task'?'未分類':r.area||''}
export function taskSummary(tasks:RecordItem[]){const open=tasks.filter(r=>r.status!=='done');return {done:tasks.length-open.length,total:tasks.length,undated:open.filter(r=>!r.dueDate).length,next:open.filter(r=>r.dueDate).sort((a,b)=>a.dueDate!.localeCompare(b.dueDate!))[0]}}
export function dependencyIds(r:RecordItem,all:RecordItem[]){return r.dependencies.filter(id=>all.find(x=>x.id===id)?.status!=='done')}
