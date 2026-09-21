'use strict';
// Loaded only by the HTTPS profile. The normal local page keeps its test login.
(() => {
  const loginCard = document.querySelector('.login-card');
  loginCard.querySelector('h2').textContent = 'LINEでログイン';
  loginCard.querySelector('.eyebrow').textContent = 'LOGIN';
  loginCard.querySelector('.muted').textContent = '運営担当者が登録したアカウントで、この試験環境に入れます。';
  $('login-form').hidden = true;
  $('web-entry').hidden = true;
  const link = document.createElement('a');
  link.href = '/auth/line/start'; link.className = 'primary wide'; link.textContent = 'LINEのログイン画面へ';
  loginCard.insertBefore(link, $('login-form'));

  const panel = document.createElement('section'); panel.id = 'delegate-panel'; panel.hidden = true;
  const label = document.createElement('label'); label.htmlFor = 'delegate-target'; label.textContent = 'この操作を任せる登録済みの接続先';
  const select = document.createElement('select'); select.id = 'delegate-target';
  const note = document.createElement('p'); note.className = 'hint'; note.textContent = '上の内容だけを、最長3分間委任します。委任の登録時点では依頼・変更・取消はまだ完了しません。';
  const button = document.createElement('button'); button.type = 'button'; button.id = 'delegate-confirm'; button.className = 'secondary wide'; button.textContent = 'この内容で委任する';
  panel.append(label, select, note, button); $('confirm-dialog').querySelector('.dialog-content').append(panel);
  const receipt = document.createElement('section'); receipt.id = 'delegate-receipt'; receipt.className = 'card'; receipt.hidden = true;
  const title = document.createElement('h2'); title.textContent = '委任の確認';
  const status = document.createElement('p'); status.setAttribute('aria-live', 'polite');
  const output = document.createElement('pre'); output.style.whiteSpace = 'pre-wrap'; output.style.overflowWrap = 'anywhere';
  const revoke = document.createElement('button'); revoke.type = 'button'; revoke.className = 'secondary'; revoke.id = 'delegate-revoke'; revoke.textContent = 'この委任を取り消す';
  receipt.append(title, status, output, revoke); $('workspace').append(receipt);
  const inspect = document.createElement('button'); inspect.type = 'button'; inspect.id = 'inspect-delegations'; inspect.className = 'secondary'; inspect.textContent = '委任の状況を確認する';
  const existing = document.createElement('section'); existing.id = 'existing-delegations';
  $('workspace').append(inspect, existing);
  inspect.addEventListener('click', async () => {
    const actor = state.user?.id; if (!actor) return;
    inspect.disabled = true;
    try {
      const values = await api('/api/oauth-approvals'); if (state.user?.id !== actor) return;
      existing.replaceChildren();
      const heading = document.createElement('p'); heading.textContent = values.length ? '期限内の委任（最新20件）' : '期限内の委任はありません。'; existing.append(heading);
      for (const value of values) {
        const row = document.createElement('p'); const text = document.createElement('span');
        const operation = JSON.parse(value.operation_json);
        text.textContent = `${value.client_id} / ${operation.kind} / ${operation.operation_id} / ${value.revoked ? '取消済み' : '委任中'}`;
        const cancel = document.createElement('button'); cancel.type = 'button'; cancel.className = 'text-button'; cancel.textContent = '委任を取り消す'; cancel.disabled = Boolean(value.revoked);
        cancel.addEventListener('click', async () => {
          cancel.disabled = true;
          try { await api('/api/oauth-approvals/revoke', {grant_id:value.id}); inspect.click(); message('委任を取り消しました。予約の状態は操作IDで確認してください。'); }
          catch (error) { cancel.disabled = false; message(error.message, true); }
        });
        row.append(text, cancel); existing.append(row);
      }
    } catch (error) { message(error.message, true); }
    finally { inspect.disabled = false; }
  });
  let targets = [], approval = null, owner = null, pendingDraft = null;
  const originalShowDraft = showDraft;
  showDraft = function(draft) {
    originalShowDraft(draft); panel.hidden = true; targets = []; select.replaceChildren();
    pendingDraft = draft; const actor = state.user?.id;
    if (state.user?.role !== 'rider' || !['request','book','change','cancel'].includes(draft.kind)) return;
    api('/api/oauth-options').then(options => {
      if (state.user?.id !== actor || state.draft?.id !== draft.id || pendingDraft?.id !== draft.id) return;
      targets = options.flatMap(item => item.clients.map(client => ({...item, client})));
      for (const [index, target] of targets.entries()) {
        const option = document.createElement('option'); option.value = String(index); option.textContent = `${target.client} / ${target.adapter.toUpperCase()}`; select.append(option);
      }
      panel.hidden = !targets.length;
    }).catch(() => { panel.hidden = true; });
  };
  button.addEventListener('click', async () => {
    if (state.busy || state.pending || !state.draft || !targets[Number(select.value)]) return;
    const draft = state.draft, target = targets[Number(select.value)], actor = state.user.id;
    const id = crypto.randomUUID(), operation = {operation_id:id,idempotency_key:id,kind:draft.kind,payload:{draft_id:draft.id,details:draft.details}};
    state.busy = true; button.disabled = true; $('commit').disabled = true;
    try {
      const value = await api('/api/oauth-approvals', {adapter:target.adapter,identity_id:target.identity_id,client_id:target.client,operation,expires_in:180});
      if (state.user?.id !== actor) return;
      approval = value; owner = actor; receipt.hidden = false; revoke.disabled = false;
      status.textContent = '委任を登録しました。接続先での実行後に、同じ操作IDで結果を照合してください。';
      output.textContent = JSON.stringify({...value, operation}, null, 2);
      // Existing recovery UI keeps this exact operation across refreshes. A
      // manual retry and agent execution therefore share one idempotency key.
      state.pending = {path:`/api/actions/${draft.kind}`,body:{operation_id:id,idempotency_key:id,payload:operation.payload}};
      savePending(); renderRecovery(); state.draft = null; $('confirm-dialog').close();
      message('委任を登録しました。依頼の実行結果はまだ確認していません。');
    } catch (error) {
      message(error.message || '委任の結果を確認できません。確認一覧で状態を照合してください。', true);
    } finally { state.busy = false; button.disabled = false; $('commit').disabled = false; renderRecovery(); }
  });
  revoke.addEventListener('click', async () => {
    if (!approval || owner !== state.user?.id || state.busy) return;
    revoke.disabled = true;
    try {
      await api('/api/oauth-approvals/revoke', {grant_id:approval.approval_id});
      status.textContent = '委任を取り消しました。実行済みの予約は取り消されません。操作IDで結果を確認してください。';
    } catch (error) { message(error.message, true); revoke.disabled = false; }
  });
  const originalSignedOut = signedOut;
  signedOut = function() { originalSignedOut(); receipt.hidden = true; output.textContent = ''; existing.replaceChildren(); approval = null; owner = null; targets = []; panel.hidden = true; };
})();
