(() => {
  'use strict';
  const form = document.querySelector('[data-workbook]');
  const metadata = window.ATLAS_WORKBOOKS || {};
  const storageKey = 'mdl-atlas-workbook-v1';
  const blank = () => ({version: 1, projectTitle: '', updatedAt: '', sheets: {}});
  let state = blank();
  let storageAvailable = true;
  function validate(raw) {
    if (!raw || raw.version !== 1 || typeof raw.sheets !== 'object' || Array.isArray(raw.sheets) || !raw.sheets) throw new Error('このサイトのバックアップファイルを選んでください。');
    const safe = blank();
    safe.projectTitle = typeof raw.projectTitle === 'string' ? raw.projectTitle.slice(0,150) : '';
    safe.updatedAt = typeof raw.updatedAt === 'string' ? raw.updatedAt.slice(0,50) : '';
    for (const [id, definition] of Object.entries(metadata)) {
      const sheet = raw.sheets[id];
      if (!sheet || typeof sheet !== 'object') continue;
      const fields = {};
      for (const f of definition.fields) {
        if (typeof sheet.fields?.[f.key] === 'string') fields[f.key] = sheet.fields[f.key].slice(0,4000);
      }
      safe.sheets[id] = {fields, review: definition.review.map((_,i) => sheet.review?.[i] === true)};
    }
    return safe;
  }
  if (form) {
    const id = form.dataset.workbook;
    const fields = [...form.querySelectorAll('[data-field]')];
    const checks = [...form.querySelectorAll('[data-review]')];
    const title = form.querySelector('[data-project-title]');
    const status = form.querySelector('[data-save-state]');
    const feedback = form.querySelector('[data-feedback]');
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) state = validate(JSON.parse(raw));
    } catch (_) {
      storageAvailable = false;
      status.textContent = '保存データを利用できません。ファイルに保存してください。';
    }
    function refreshCount() {
      const count = fields.filter(el => el.value.trim()).length;
      form.querySelector('[data-field-count]').textContent = `${count} / ${fields.length}項目を記入`;
      for (const el of fields) el.nextElementSibling.textContent = el.value || '（未記入）';
    }
    function render() {
      title.value = state.projectTitle;
      const sheet = state.sheets[id] || {fields:{},review:[]};
      fields.forEach(el => { el.value = sheet.fields[el.dataset.field] || ''; });
      checks.forEach(el => { el.checked = sheet.review[Number(el.dataset.review)] === true; });
      refreshCount();
      if (storageAvailable && state.updatedAt) status.textContent = 'このブラウザの入力を復元しました';
    }
    function collect() {
      state.projectTitle = title.value.slice(0,150);
      state.updatedAt = new Date().toISOString();
      state.sheets[id] = {fields:Object.fromEntries(fields.map(el => [el.dataset.field,el.value.slice(0,4000)])), review:checks.map(el => el.checked)};
    }
    function save({replaceAll = false, titleChanged = false} = {}) {
      // Other tabs may be editing other stages. Merge only this stage into the
      // latest saved workbook, preserving the rest of the user's work.
      if (!replaceAll) {
        try {
          const latest = localStorage.getItem(storageKey);
          if (latest) {
            const fresh = validate(JSON.parse(latest));
            if (!titleChanged) title.value = fresh.projectTitle;
            state = fresh;
          }
        } catch (_) { /* Keep the in-memory draft available for export. */ }
      }
      collect();
      refreshCount();
      try {
        localStorage.setItem(storageKey,JSON.stringify(state));
        storageAvailable = true;
        status.textContent = 'このブラウザに保存済み';
      } catch (_) {
        storageAvailable = false;
        status.textContent = '自動保存できません。下のボタンでファイルに保存してください。';
      }
    }
    function download(content, type, extension) {
      const blob = new Blob([content], {type});
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `mdl-atlas-${extension === 'json' ? 'all-sheets' : id}-${new Date().toISOString().slice(0,10)}.${extension}`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url),1000);
    }
    form.addEventListener('input', event => {
      if (event.target.matches('[data-field],[data-project-title],[data-review]')) save({titleChanged:event.target.matches('[data-project-title]')});
    });
    form.querySelectorAll('[data-export]').forEach(button => button.addEventListener('click', () => {
      save();
      if (button.dataset.export === 'json') {
        download(JSON.stringify(state,null,2),'application/json;charset=utf-8','json');
        feedback.textContent = '全シートのバックアップをダウンロードしました。別の端末ではこのファイルを読み込めます。';
      } else {
        const sheet = state.sheets[id];
        const definition = metadata[id];
        const lines = [`# ${definition.title}`, '', `案件名：${state.projectTitle || '未記入'}`, `更新日時：${state.updatedAt}`, ''];
        definition.fields.forEach(f => lines.push(`## ${f.label}`,'',sheet.fields[f.key] || '未記入',''));
        lines.push('## 自分で確認する','');
        definition.review.forEach((text,i) => lines.push(`- [${sheet.review[i] ? 'x' : ' '}] ${text}`));
        lines.push('','記入数は進捗の目安であり、内容の妥当性を自動で判定するものではありません。',`教材：https://mobilitydlab.com/co-creation-atlas/learn/${id === 'project-plan' ? 'workbook' : id}/`,'');
        download(lines.join('\n'),'text/markdown;charset=utf-8','md');
        feedback.textContent = 'このシートを文章ファイルに保存しました。';
      }
    }));
    form.querySelector('[data-import]').addEventListener('change', async event => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        if (file.size > 4 * 1024 * 1024) throw new Error('ファイルが大きすぎます。4MB以下のバックアップを選んでください。');
        const incoming = validate(JSON.parse(await file.text()));
        if (!Object.keys(incoming.sheets).length) throw new Error('読み込めるシートがありません。');
        // Recheck storage at the moment of replacement: this tab may have been
        // opened before another tab created a draft.
        let hasDraft = true;
        try {
          const latest = localStorage.getItem(storageKey);
          const current = latest ? validate(JSON.parse(latest)) : state;
          hasDraft = Boolean(current.projectTitle.trim() || Object.values(current.sheets).some(s => Object.values(s.fields).some(v => v.trim()) || s.review.some(Boolean)));
        } catch (_) { /* If storage cannot be checked, ask before replacement. */ }
        if (hasDraft && !window.confirm('このブラウザの全シートを、選んだバックアップに置き換えます。現在の入力を残すには、キャンセルして先にバックアップしてください。置き換えますか？')) return;
        state = incoming;
        render();
        save({replaceAll:true});
        feedback.textContent = 'バックアップを読み込みました。ほかの工程のシートも復元されています。';
      } catch (error) {
        feedback.textContent = error instanceof SyntaxError ? 'JSON形式を読み取れません。このサイトで保存したバックアップを選んでください。' : error.message;
      } finally { event.target.value = ''; }
    });
    form.querySelector('[data-print]').addEventListener('click', () => {
      save();
      document.body.classList.add('print-workbook');
      window.print();
    });
    window.addEventListener('afterprint',() => document.body.classList.remove('print-workbook'));
    render();
  }
  const fitSearch = document.querySelector('#fit-search');
  if (fitSearch) {
    const unit = document.querySelector('#fit-unit');
    const exit = document.querySelector('#fit-exit');
    const selectedOnly = document.querySelector('#fit-selected-only');
    const cards = [...document.querySelectorAll('[data-fit-id]')];
    const norm = value => String(value).normalize('NFKC').toLowerCase();
    function apply() {
      const terms = norm(fitSearch.value).trim().split(/\s+/).filter(Boolean);
      let count = 0;
      const selected = cards.filter(card => card.querySelector('input').checked).length;
      cards.forEach(card => {
        const visible = (!unit.value || card.dataset.unit === unit.value) && (!exit.value || card.dataset.exits.split(' ').includes(exit.value)) && (!selectedOnly.checked || card.querySelector('input').checked) && terms.every(term => norm(card.dataset.search).includes(term));
        card.hidden = !visible;
        if (visible) count++;
      });
      document.querySelector('#fit-count').textContent = `${count}件を表示 / ${selected}件を比較に選択`;
      document.querySelector('#fit-empty').hidden = count > 0;
    }
    fitSearch.addEventListener('input',apply);
    [unit,exit,selectedOnly].forEach(el => el.addEventListener('change',apply));
    cards.forEach(card => card.querySelector('input').addEventListener('change',apply));
    document.querySelector('#fit-reset').addEventListener('click',() => {fitSearch.value='';unit.value='';exit.value='';selectedOnly.checked=false;cards.forEach(card => card.querySelector('input').checked=false);apply();});
    apply();
  }
})();
