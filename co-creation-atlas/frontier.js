/* Filters are progressive enhancement. No reader storage or existing explorer state is touched. */
(() => {
  'use strict';
  const controls = document.getElementById('frontier-controls');
  if (!controls) return;
  const cards = Array.from(document.querySelectorAll('.frontier-card'));
  const buttons = Array.from(controls.querySelectorAll('[data-axis-filter]'));
  const stepSelect = document.getElementById('frontier-step-filter');
  const focusButtons = Array.from(controls.querySelectorAll('[data-focus-filter]'));
  const resetButton = document.getElementById('frontier-reset');
  const status = document.getElementById('frontier-result-status');
  const empty = document.getElementById('frontier-empty');
  const axes = {all: 'すべての切り口', hard: 'ハード', soft: 'ソフト', partners: 'パートナー'};
  const focuses = {all: 'すべてのテーマ', 'shared-labs': '共用研究工場／試作拠点', 'physical-ai': 'フィジカルAIのラボ'};
  const stepNames = new Map(Array.from(stepSelect.options, option => [option.value, option.textContent.replace(/（\d+）$/, '')]));
  const records = cards.map(element => ({element, axis: element.dataset.axis, steps: element.dataset.steps.split(' '), focus: (element.dataset.focus || '').split(' ').filter(Boolean)}));
  let state = {axis: 'all', step: 'all', focus: 'all'};
  function readLocation() {
    const params = new URL(location.href).searchParams;
    const axis = params.get('lens');
    const step = params.get('step');
    const focus = params.get('focus');
    state = {axis: Object.hasOwn(axes, axis) ? axis : 'all', step: stepNames.has(step) ? step : 'all', focus: Object.hasOwn(focuses, focus) ? focus : 'all'};
  }
  function matches(record, axis = state.axis, step = state.step, focus = state.focus) {
    return (axis === 'all' || record.axis === axis) && (step === 'all' || record.steps.includes(step)) && (focus === 'all' || record.focus.includes(focus));
  }
  function render() {
    let visible = 0;
    records.forEach(record => {
      record.element.hidden = !matches(record);
      if (!record.element.hidden) visible++;
      record.element.querySelectorAll('.frontier-step').forEach(element => element.classList.toggle('is-selected', element.dataset.step === state.step));
    });
    buttons.forEach(button => {
      const axis = button.dataset.axisFilter;
      const count = records.filter(record => matches(record, axis, state.step)).length;
      button.setAttribute('aria-pressed', String(axis === state.axis));
      button.querySelector('[data-axis-count]').textContent = count;
    });
    Array.from(stepSelect.options).forEach(option => {
      const count = records.filter(record => matches(record, state.axis, option.value)).length;
      option.textContent = `${stepNames.get(option.value)}（${count}）`;
    });
    stepSelect.value = state.step;
    focusButtons.forEach(button => {
      const focus = button.dataset.focusFilter;
      button.setAttribute('aria-pressed', String(focus === state.focus));
      button.querySelector('[data-focus-count]').textContent = records.filter(record => matches(record, state.axis, state.step, focus)).length;
    });
    status.replaceChildren();
    const number = document.createElement('strong');
    number.textContent = visible;
    status.append(number, document.createTextNode(` 件 ／ ${axes[state.axis]}・${stepNames.get(state.step)}${state.focus === 'all' ? '' : `・${focuses[state.focus]}`}`));
    empty.hidden = visible !== 0;
    resetButton.disabled = state.axis === 'all' && state.step === 'all' && state.focus === 'all';
  }
  function update(next) {
    if (state.axis === next.axis && state.step === next.step && state.focus === next.focus) return;
    state = next;
    const url = new URL(location.href);
    state.axis === 'all' ? url.searchParams.delete('lens') : url.searchParams.set('lens', state.axis);
    state.step === 'all' ? url.searchParams.delete('step') : url.searchParams.set('step', state.step);
    state.focus === 'all' ? url.searchParams.delete('focus') : url.searchParams.set('focus', state.focus);
    history.pushState(null, '', url);
    render();
  }
  buttons.forEach(button => button.addEventListener('click', () => update({...state, axis: button.dataset.axisFilter})));
  stepSelect.addEventListener('change', () => update({...state, step: stepSelect.value}));
  focusButtons.forEach(button => button.addEventListener('click', () => update({...state, focus: button.dataset.focusFilter})));
  document.querySelectorAll('#frontier-reset, [data-frontier-reset]').forEach(button => button.addEventListener('click', () => {
    const fromEmpty = button.hasAttribute('data-frontier-reset');
    update({axis: 'all', step: 'all', focus: 'all'});
    if (fromEmpty) buttons[0].focus();
  }));
  addEventListener('popstate', () => { readLocation(); render(); });
  readLocation();
  render();
  controls.hidden = false;
})();
