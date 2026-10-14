import {AppState,Command,DomainError} from './model';
export type TeamRole='manager'|'safety'|'operator'|'preparer'|'borrower'|'viewer';
export type ActorContext={subject:string;role:TeamRole};
export const ROLE_LABELS:Record<TeamRole,string>={manager:'管理者',safety:'安全・復旧確認者',operator:'運転・現場担当',preparer:'充電・準備担当',borrower:'利用申請担当',viewer:'閲覧のみ'};
export function authorize(s:AppState,c:Command,p:ActorContext){
 const deny=(message:string):never=>{throw new DomainError(403,message)};
 if(p.role==='viewer')deny('閲覧権限では記録を変更できません。');
 const manager=['configure_vehicle','configure_station','set_policy','set_staff','set_resources','approve_booking','reject_booking','reschedule_booking','create_booking','assign_ride','assign_charge','create_task','configure_product','set_return_receiver','release_vehicle'];
 if(manager.includes(c.type)&&p.role!=='manager')deny('管理者による確認が必要です。');
 if(c.type==='resolve_incident'&&!['manager','safety'].includes(p.role))deny('復旧確認の権限が必要です。');
 if(['task_action','receive_return'].includes(c.type)&&c.delegateReason&&p.role!=='manager')deny('代理受領は管理者が理由を記録してください。');
 if(c.type==='task_action'&&c.action==='reassign'&&p.role!=='manager')deny('再割当は管理者が行ってください。');
 if(p.role==='borrower'){
  if(!['save_booking_draft','request_booking','submit_booking','cancel_booking'].includes(c.type))deny('利用申請の権限で行える操作ではありません。');
  const b=s.bookings.find(x=>x.id===c.id);if(b&&b.requestedBy!==p.subject)deny('他の担当者の申請は変更できません。');
 }
 if(['check_in','check_out'].includes(c.type)){
  const b=s.bookings.find(x=>x.id===c.id);if(s.mode==='operational'&&b?.driverId!==p.subject)deny('割り当てられた運転・現場担当者本人が記録してください。');
 }
 if(['ticket_action','order_action','toggle_product','create_ticket','create_order','create_ride','record_contact','record_actuals','cancel_booking'].includes(c.type)&&!['manager','operator','safety','borrower'].includes(p.role))deny('運行・現場業務の権限が必要です。');
 if(['simulate','advance_clock','reset_demo','set_manual_policy'].includes(c.type)&&s.mode!=='demo')deny('実業務では模擬操作を使用できません。');
}
