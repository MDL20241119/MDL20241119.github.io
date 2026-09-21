'use strict';

(() => {
  const byId = id => document.getElementById(id);
  const node = (tag, className, value) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (value !== undefined) el.textContent = value;
    return el;
  };
  const makeLink = (text, href) => {
    const a = node('a', '', text);
    a.href = href;
    return a;
  };

  async function start() {
    const response = await fetch('./data.json', {cache:'no-cache'});
    if (!response.ok) throw new Error('Evidence data unavailable');
    const data = await response.json();
    if (!Array.isArray(data.activities) || data.activities.length !== 35) throw new Error('Invalid activity data');
    const sourceMap = new Map(data.sources.map(source => [source.id, source]));
    const search = byId('activity-search');
    const stage = byId('stage-filter');

    Object.entries(data.stages).forEach(([value, title]) => {
      const option = node('option', '', title);
      option.value = value;
      stage.append(option);
    });

    const processList = byId('process-list');
    processList.replaceChildren();
    data.process.forEach((item, index) => {
      const li = node('li');
      li.append(node('span', 'number', String(index + 1).padStart(2, '0')), node('strong', '', item.title), node('p', '', item.detail));
      const firstActivity = String(item.activityNumbers[0]).padStart(2, '0');
      li.append(makeLink('活動記録を見る ↓', '#action-' + firstActivity));
      processList.append(li);
    });

    data.metrics.forEach(metric => {
      const article = node('article');
      article.append(node('h3', '', metric.value + (metric.valueSuffix || '') + ' ' + metric.label), node('p', '', metric.definition), node('p', '', '対象：' + metric.period), node('p', '', metric.limitation));
      const sourceText = metric.sourceIds.map(id => sourceMap.get(id)?.title).filter(Boolean).join(' ／ ');
      article.append(node('p', 'definition-source', '根拠：' + sourceText + '。' + metric.verification));
      byId('definition-list').append(article);
    });

    data.sources.forEach(source => {
      const li = node('li');
      li.id = 'source-' + source.id;
      const body = node('div');
      body.append(node('h3', '', source.title), node('p', '', source.publisher + ' ／ ' + source.type), node('p', '', '該当箇所：' + source.locator), node('p', 'access', source.access));
      if (source.url && /^https:\/\//.test(source.url)) body.append(makeLink('公開資料を読む ↗', source.url));
      li.append(body);
      byId('source-list').append(li);
    });
    [['confirmed-list', data.confirmed], ['unconfirmed-list', data.notYetProven], ['methodology-list', data.methodology.notes]].forEach(([id, values]) => values.forEach(value => byId(id).append(node('li', '', value))));

    const activityElement = item => {
      const detail = node('details', 'activity');
      detail.id = item.id;
      const summary = node('summary');
      const date = node('span', 'activity-date', item.dateDisplay);
      if (item.dateStatus === 'year_conflict') date.append(node('span', 'date-status', '原表に不整合'));
      const title = node('span');
      title.append(node('span', 'activity-title', item.title), node('span', 'activity-stage', item.stageLabel));
      summary.append(node('span', 'activity-number', String(item.number).padStart(2, '0')), date, title);
      const body = node('div', 'activity-body');
      body.append(node('p', 'place', item.place), node('p', '', item.description));
      const dateNote = item.dateStatus === 'recorded' ? item.dateNote : item.dateNote + (item.dateRaw ? ' 原表表記：' + item.dateRaw.replace(' 00:00:00', '') : '');
      body.append(node('p', 'date-note', dateNote));
      const source = node('p', 'activity-source', '根拠：' + item.sourceLocator + '。');
      source.append(makeLink('資料の確認範囲', '#source-event-register'));
      body.append(source);
      detail.append(summary, body);
      return detail;
    };

    function render() {
      const query = search.value.trim().normalize('NFKC').toLocaleLowerCase('ja');
      const selectedStage = stage.value;
      const items = data.activities.filter(item => {
        const text = [item.title, item.place, item.description, item.stageLabel, item.dateDisplay].join(' ').normalize('NFKC').toLocaleLowerCase('ja');
        return (!selectedStage || item.stage === selectedStage) && (!query || text.includes(query));
      });
      byId('activity-list').replaceChildren(...items.map(activityElement));
      if (!items.length) byId('activity-list').append(node('p', 'empty', '条件に合う活動はありません。検索語や活動の種類を変えてみてください。'));
      byId('result-count').textContent = items.length + ' / ' + data.activities.length + ' ACTIONS';
    }

    function revealHash() {
      if (location.hash === '#metric-definitions') {
        byId('metric-definitions').open = true;
        return;
      }
      if (!/^#action-\d{2}$/.test(location.hash)) return;
      const id = location.hash.slice(1);
      if (!data.activities.some(item => item.id === id)) return;
      if (!byId(id)) { search.value = ''; stage.value = ''; render(); }
      const el = byId(id);
      el.open = true;
      requestAnimationFrame(() => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
    }
    search.addEventListener('input', render);
    stage.addEventListener('change', render);
    byId('reset-filters').addEventListener('click', () => { search.value = ''; stage.value = ''; render(); search.focus(); });
    window.addEventListener('hashchange', revealHash);
    render();
    revealHash();
  }

  start().catch(() => {
    byId('load-error').hidden = false;
    byId('result-count').textContent = '活動データの読み込みを確認できませんでした。';
    byId('process-list').replaceChildren(node('li', '', '活動内容は公開活動報告、または構造化データで確認できます。'));
    byId('activity-search').disabled = true;
    byId('stage-filter').disabled = true;
    byId('reset-filters').disabled = true;
  });
})();
