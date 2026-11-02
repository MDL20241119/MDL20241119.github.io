/* One content collection drives profiles, timelines, comparisons and the map. */
(() => {
  'use strict';
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeURL = value => { try { const u = new URL(value, location.href); return ['https:', 'http:'].includes(u.protocol) ? esc(u.href) : '#'; } catch { return '#'; } };
  const external = (url, label, className = '') => `<a href="${safeURL(url)}" target="_blank" rel="noopener noreferrer"${className ? ` class="${esc(className)}"` : ''}>${esc(label)} <span aria-hidden="true">↗</span></a>`;
  const plain = value => Array.isArray(value) ? value.join(' / ') : String(value ?? '');
  const norm = value => plain(value).normalize('NFKC').toLocaleLowerCase('ja');
  let data, photos = {}, people = [], statements = [], pById, sById, sources, topicById;
  let currentMatches = [], expanded = false, spotlightIndex = 0;

  async function init() {
    try {
      const response = await fetch('content.json');
      if (!response.ok) throw new Error(`Content: ${response.status}`);
      data = await response.json();
      const photoResponse = await fetch('photos.json');
      if (photoResponse.ok) photos = await photoResponse.json();
      if (photos.photos && !Array.isArray(photos.photos)) photos = photos.photos;
      if (Array.isArray(photos)) photos = Object.fromEntries(photos.map(p => [p.id || p.personId || p.slug, p]));
      people = data.people || [];
      statements = (data.statements || []).slice().sort((a, b) => b.date.localeCompare(a.date));
      pById = new Map(people.map(p => [p.id, p]));
      sById = new Map(statements.map(s => [s.id, s]));
      sources = new Map((data.sources || []).map(s => [s.id, s]));
      topicById = new Map((data.topics || []).map(t => [Number(t.id), t]));
      renderIntro(); renderHero(); renderQuestionPortrait(); renderSpotlights(); renderFilterOptions(); renderPeople(); renderComparisons(); renderQuadrants(); renderSources(); renderCredits(); bindEvents();
      $('#hero-portrait').setAttribute('aria-busy', 'false');
      if (location.hash.startsWith('#statement-') || location.hash.startsWith('#person-')) requestAnimationFrame(() => openHash(location.hash));
    } catch (error) {
      $('#load-error').hidden = false;
      $('#result-count').textContent = 'データを読み込めませんでした。';
      $('#hero-portrait').setAttribute('aria-busy', 'false');
      console.error('Feature data could not be loaded.', error);
    }
  }

  function personStatements(person) { return statements.filter(s => s.personIds.includes(person.id)); }
  function personLabel(statement) { return statement.authorsLabel || statement.personIds.map(id => pById.get(id)?.nameJa || id).join('・'); }
  function photoOf(person) {
    const direct = photos[person?.id];
    if (direct && (direct.file || direct.path || direct.src)) return direct;
    return null;
  }
  function portrait(person, opts = {}) {
    const photo = photoOf(person);
    if (!photo) return `<div class="portrait-unavailable"><span>THE PERSON / ${esc(person?.nameEn || '')}</span><strong>${esc(person?.nameJa || '')}</strong><span>写真は利用条件を確認中。<br>経歴と発言は、本人の原典から読む。</span></div>`;
    const imagePath = photo.file || photo.path || photo.src;
    const src = imagePath.startsWith('photos/') || imagePath.startsWith('assets/') ? imagePath : `photos/${imagePath.split('/').pop()}`;
    const credit = `${photo.photographer || photo.author || '撮影者は出典参照'} / ${photo.license || '利用条件は出典参照'}`;
    return `<img src="${esc(src)}" alt="${esc(person.nameJa)}（${esc(person.nameEn)}）の本人写真" width="${Number(photo.width) || 900}" height="${Number(photo.height) || 1100}" ${opts.eager ? 'fetchpriority="high" loading="eager"' : 'loading="lazy"'} decoding="async"${photo.objectPosition || photo.position ? ` style="object-position:${esc(photo.objectPosition || photo.position)}"` : ''}>${opts.credit === false ? '' : `<div class="photo-short-credit">${external(photo.sourcePage || photo.sourceURL || photo.originalURL, credit)}</div>`}`;
  }
  function renderIntro() {
    const mainPeople = people.filter(p => !p.supporting).length;
    const photoCount = people.filter(p => photoOf(p)).length;
    $('#feature-counts').innerHTML = `<div class="count-item"><strong>${mainPeople}</strong><span>主要プロフィール</span></div><div class="count-item"><strong>${statements.length}</strong><span>日付付きの発言</span></div><div class="count-item"><strong>${photoCount}</strong><span>本人写真</span></div>`;
  }
  function renderHero() {
    let person = people.find(p => p.id === 'reid-hoffman');
    if (!photoOf(person)) person = people.find(p => p.id === 'sam-altman' && photoOf(p)) || people.find(p => photoOf(p)) || person || people[0];
    if (!person) return;
    const statement = personStatements(person).find(s => s.recent) || personStatements(person)[0];
    $('#hero-portrait').innerHTML = `${portrait(person, {eager: true, credit: false})}<div class="hero-caption"><p class="portrait-kicker">IN THIS ISSUE / ${esc(statement?.dateLabel || statement?.date)}</p><h2>${esc(person.nameJa)}</h2><p class="portrait-en">${esc(person.nameEn)}</p><p>${esc(statement?.summary || person.bio)}</p></div>`;
    const photo = photoOf(person);
    if (photo) $('#hero-portrait').insertAdjacentHTML('beforeend', `<a class="hero-photo-source" href="${safeURL(photo.sourcePage || photo.sourceURL)}" target="_blank" rel="noopener noreferrer">写真出典 ↗</a>`);
  }
  function spotlightStatements() {
    const desired = ['reid-hoffman', 'sam-altman', 'takahiro-anno'];
    const chosen = desired.map(id => statements.find(s => s.recent && s.personIds.includes(id))).filter(Boolean);
    for (const s of statements.filter(s => s.recent)) if (chosen.length < 3 && !chosen.includes(s)) chosen.push(s);
    return chosen;
  }
  function renderQuestionPortrait() {
    const person = pById.get('yusuke-narita');
    if (!person) return;
    const statement = personStatements(person)[0];
    $('#question-portrait').innerHTML = `${portrait(person, {credit:false})}<a href="#statement-${esc(statement.id)}" class="question-photo-caption statement-jump"><span>${esc(person.nameJa)} / ${esc(person.nameEn)}</span><strong>自分の時間を、守る。</strong><span>本人の経験・選好を読む ↗</span></a>`;
  }
  function renderSpotlights() {
    const selection = spotlightStatements();
    if (!selection.length) return;
    const s = selection[spotlightIndex];
    const person = pById.get(s.personIds[0]);
    $('#spotlight').innerHTML = `<div class="spotlight-copy"><span class="date-label">${esc(s.dateLabel || s.date)}</span><p class="micro-label spotlight-keyword-label">編集キーワード</p><h3>${esc(s.keyword || s.title)}</h3><p class="spotlight-person">${esc(personLabel(s))}</p><p>${esc(s.summary)}</p><p class="spotlight-caveat">${esc(s.type)}。${esc(s.caveat)}</p><a href="#statement-${esc(s.id)}" class="arrow-link statement-jump">発言と原典を読む <span aria-hidden="true">↗</span></a></div><div class="spotlight-image">${portrait(person)}</div>`;
    $('#spotlight-tabs').innerHTML = selection.map((item, i) => `<button type="button" data-spotlight="${i}" aria-pressed="${i === spotlightIndex}"><strong>${esc(personLabel(item))}</strong><span>${esc(item.dateLabel || item.date)}<br>${esc(item.title)}</span></button>`).join('');
  }
  function renderFilterOptions() {
    $('#topic-filter').insertAdjacentHTML('beforeend', (data.topics || []).map(t => `<option value="${Number(t.id)}">${esc(t.short || t.title)}</option>`).join(''));
    const categories = [...new Set(people.map(p => p.category))];
    $('#category-filter').insertAdjacentHTML('beforeend', categories.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join(''));
  }
  function filteredStatements(person) {
    const query = norm($('#search').value.trim());
    const category = $('#category-filter').value;
    const topic = Number($('#topic-filter').value);
    const period = $('#date-filter').value;
    if (category && person.category !== category) return [];
    const personMatch = query && norm([person.nameJa, person.nameEn, person.company, person.bio]).includes(query);
    return personStatements(person).filter(s => {
      if (topic && !(s.topics || []).map(Number).includes(topic)) return false;
      if (period === 'october' && s.date < '2026-10') return false;
      if (period === 'recent' && s.date < '2026-05') return false;
      if (period === '2026' && !s.date.startsWith('2026')) return false;
      if (period === 'older' && s.date >= '2026') return false;
      return !query || personMatch || norm([s.title, s.keyword, s.summary, s.detail, s.authorsLabel, s.coauthors]).includes(query);
    });
  }
  function renderPeople() {
    currentMatches = people.map((person, index) => ({person, index, matches: filteredStatements(person)})).filter(r => r.matches.length);
    const totalStatements = new Set(currentMatches.flatMap(r => r.matches.map(s => s.id))).size;
    $('#result-count').textContent = `${currentMatches.length}人 / ${totalStatements}件の発言`;
    $('#empty-state').hidden = currentMatches.length !== 0;
    $('#people-list').innerHTML = currentMatches.map(({person, index, matches}) => {
      const latest = matches[0];
      const bioLinks = (person.bioSources || []).map((url, i) => external(typeof url === 'string' ? url : url.url, `経歴の出典${(person.bioSources || []).length > 1 ? ` ${i + 1}` : ''}`)).join(' / ');
      return `<article class="person-card${person.supporting ? ' supporting-person' : ''}" id="person-${esc(person.id)}" aria-labelledby="name-${esc(person.id)}"><div class="person-main"><div class="person-topline"><span class="person-number">${String(index + 1).padStart(2,'0')}</span><span>${esc(person.category)}${person.supporting ? '<br><span class="supporting-label">共著・対談の発言を収録</span>' : ''}</span></div><h3 class="person-name" id="name-${esc(person.id)}">${esc(person.nameJa)}</h3><p class="person-en">${esc(person.nameEn)}</p><p class="person-bio">${esc(person.bio)}${bioLinks ? `<br>${bioLinks}` : ''}</p><p class="profile-keyword-label">編集キーワード / ${esc(latest.dateLabel || latest.date)}</p><p class="profile-keyword">${esc(latest.keyword || latest.title)}</p><p class="person-latest-summary">${esc(latest.summary)}</p><p class="person-latest-meta">${esc(latest.type)}${latest.personIds.length > 1 || latest.coauthors?.length ? ` / ${esc(personLabel(latest))}` : ''}</p></div><div class="person-image">${portrait(person)}</div><details class="person-timeline"${expanded ? ' open' : ''}><summary><span>発言を時系列で読む / ${matches.length}件${matches.length < personStatements(person).length ? `（全${personStatements(person).length}件から絞り込み）` : ''}</span><span class="timeline-indicator" aria-hidden="true">＋</span></summary><div>${matches.map(s => statementHTML(s, person)).join('')}</div></details></article>`;
    }).join('');
    $('#expand-all').textContent = expanded ? '表示中の発言を閉じる −' : '表示中の発言を開く ＋';
  }
  function statementHTML(s, person) {
    const links = (s.sourceIds || []).map(id => sources.get(id)).filter(Boolean).map(src => external(src.url, `${src.id} ${src.title}`)).join('');
    return `<section class="statement" id="${esc(person.id)}--${esc(s.id)}" tabindex="-1" aria-labelledby="title-${esc(person.id)}-${esc(s.id)}"><div class="statement-date">${esc(s.dateLabel || s.date)}<span class="statement-type">${esc(s.type)}</span></div><div class="statement-body"><p class="statement-authors">${esc(personLabel(s))}</p><h3 id="title-${esc(person.id)}-${esc(s.id)}">${esc(s.title)}</h3><p>${esc(s.summary)}</p>${s.detail ? `<p class="statement-detail">${esc(s.detail)}</p>` : ''}<p class="statement-caveat"><strong>読む際の条件・留保</strong><br>${esc(s.caveat)}</p>${s.attention ? `<p class="attention"><strong>注目の根拠</strong> ${esc(s.attention)}</p>` : ''}<div class="statement-source-links">${links}</div><div class="topic-tags">${(s.topics || []).map(id => topicById.get(Number(id))).filter(Boolean).map(t => `<a href="#topic-${t.id}" class="tag">${esc(t.short || t.title)}</a>`).join('')}</div></div></section>`;
  }
  function renderComparisons() {
    $('#topic-comparisons').innerHTML = (data.topics || []).map((t, index) => {
      const ids = t.statementIds?.length ? t.statementIds : statements.filter(s => s.topics.includes(Number(t.id))).map(s => s.id);
      const examples = ids.map(id => sById.get(id)).filter(Boolean);
      const exampleLink = s => `<a class="statement-jump" href="#statement-${esc(s.id)}"><strong>${esc(personLabel(s))}</strong><span>${esc(s.keyword || s.title)}</span><span>${esc(s.dateLabel || s.date)} ↗</span></a>`;
      return `<details class="topic-row" id="topic-${t.id}"${index === 0 ? ' open' : ''}><summary><span class="topic-no">${String(t.id).padStart(2,'0')}</span><h3>${esc(t.title)}</h3><span class="topic-toggle" aria-hidden="true">＋</span></summary><div class="topic-content"><div class="topic-text-grid"><div><h4>共通する問い・接点</h4><p>${esc(t.agreement || t.description)}</p></div><div><h4>意見が分かれるところ</h4><p>${esc(t.difference)}</p></div></div><p class="topic-caveat"><strong>確かめたい条件</strong><br>${esc(t.caveat)}</p><div class="topic-evidence">${examples.slice(0,6).map(exampleLink).join('')}</div>${examples.length > 6 ? `<details class="comparison-more"><summary>関連する発言をさらに読む / ${examples.length - 6}件 ＋</summary><div class="topic-evidence">${examples.slice(6).map(exampleLink).join('')}</div></details>` : ''}</div></details>`;
    }).join('');
  }
  function renderQuadrants() {
    const order = [2,4,1,3];
    $('#quadrant-grid').innerHTML = order.map(id => {
      const q = (data.quadrants || []).find(item => Number(item.id) === id);
      if (!q) return '';
      let entries = (q.statementIds || []).map(sid => sById.get(sid)).filter(Boolean);
      if (!entries.length) entries = statements.filter(s => (s.quadrants || []).map(Number).includes(id));
      entries = entries.slice().sort((a,b) => b.date.localeCompare(a.date));
      const axes = `${id === 2 || id === 4 ? '関係・社会の仕組み' : '個人の能力・選択'} × ${id === 1 || id === 2 ? '仕事・事業の成果' : '仕事だけでは測れない価値'}`;
      const card = s => `<a class="quadrant-statement statement-jump" href="#statement-${esc(s.id)}"><strong>${esc(personLabel(s))}</strong><span class="q-date">${esc(s.dateLabel || s.date)}${(s.quadrants || []).length > 1 ? ` / ${(s.quadrants || []).join('・')}にまたがる` : ''}</span><span class="q-keyword">${esc(s.keyword || s.title)} ↗</span></a>`;
      return `<div class="quadrant-cell q${id}" data-axes="${esc(axes)}"><span class="q-number">0${id}</span><h3>${esc(q.title)}</h3><p>${esc(q.description || q.subtitle)}</p>${entries.slice(0,3).map(card).join('')}${entries.length > 3 ? `<details class="quadrant-more"><summary>この視点の発言をさらに読む / ${entries.length - 3}件</summary>${entries.slice(3).map(card).join('')}</details>` : ''}</div>`;
    }).join('');
  }
  function renderSources() {
    $('#source-count').textContent = `${sources.size}資料 ＋`;
    $('#source-list').innerHTML = [...sources.values()].map(src => `<div class="source-entry" id="source-${esc(src.id)}"><span class="source-id">${esc(src.id)}</span><div>${external(src.url, src.title)}<p class="source-meta">${esc(src.publisher)} / ${esc(src.date || '')}<br>${esc(src.kind || '')}</p></div></div>`).join('');
  }
  function renderCredits() {
    const withPhotos = people.filter(p => photoOf(p));
    const missing = people.filter(p => !photoOf(p));
    $('#photo-count').textContent = `${withPhotos.length}人 ＋`;
    $('#photo-credits').innerHTML = withPhotos.map(person => {
      const p = photoOf(person);
      return `<div class="photo-credit-entry"><h3>${esc(person.nameJa)} / ${esc(person.nameEn)}</h3><p>撮影・提供：${esc(p.photographer || p.author || '出典参照')}<br>利用条件：${p.licenseURL ? external(p.licenseURL, p.license) : esc(p.license)}<br>${external(p.sourcePage || p.sourceURL || p.originalURL, '写真の出典・本人確認')}<br>加工：${esc(p.changes || 'WebP形式への変換・レイアウトに合わせたトリミング')}</p></div>`;
    }).join('') + (missing.length ? `<p class="photo-missing-list"><strong>利用条件を確認できる本人写真を収集できなかった人物</strong><br>${missing.map(p => esc(p.nameJa)).join('、')}。無断転載や生成肖像は使用していません。</p>` : '');
  }
  function bindEvents() {
    $('#filters').addEventListener('submit', e => e.preventDefault());
    $('#search').addEventListener('input', renderPeople);
    ['topic-filter','date-filter','category-filter'].forEach(id => $(`#${id}`).addEventListener('change', renderPeople));
    $('#filters').addEventListener('reset', event => { event.preventDefault(); clearFilters(); expanded = false; renderPeople(); });
    $('#expand-all').addEventListener('click', () => { expanded = !expanded; $$('.person-timeline').forEach(el => {el.open = expanded;}); $('#expand-all').textContent = expanded ? '表示中の発言を閉じる −' : '表示中の発言を開く ＋'; });
    $('#see-recent').addEventListener('click', () => { clearFilters(); $('#date-filter').value = 'recent'; renderPeople(); });
    document.addEventListener('click', e => {
      const tab = e.target.closest('[data-spotlight]');
      if (tab) { spotlightIndex = Number(tab.dataset.spotlight); renderSpotlights(); return; }
      const jump = e.target.closest('a.statement-jump');
      if (jump) { e.preventDefault(); const hash = jump.getAttribute('href'); history.pushState(null, '', hash); openHash(hash); }
    });
    window.addEventListener('hashchange', () => openHash(location.hash));
  }
  function clearFilters() {
    $('#search').value = '';
    $('#topic-filter').value = '';
    $('#date-filter').value = '';
    $('#category-filter').value = '';
    expanded = false;
  }
  function openHash(hash) {
    if (hash.startsWith('#statement-')) {
      const statement = sById.get(decodeURIComponent(hash.slice(11)));
      if (!statement) return;
      const person = pById.get(statement.personIds[0]);
      if (!person) return;
      let target = document.getElementById(`${person.id}--${statement.id}`);
      if (!target) { clearFilters(); renderPeople(); target = document.getElementById(`${person.id}--${statement.id}`); }
      if (target) {
        target.closest('details').open = true;
        requestAnimationFrame(() => { target.scrollIntoView({block:'start'}); target.focus({preventScroll:true}); target.classList.add('highlight-target'); setTimeout(() => target.classList.remove('highlight-target'), 1800); });
      }
    } else if (hash.startsWith('#person-')) {
      const id = decodeURIComponent(hash.slice(8));
      let target = document.getElementById(`person-${id}`);
      if (!target) { clearFilters(); renderPeople(); target = document.getElementById(`person-${id}`); }
      target?.scrollIntoView({block:'start'});
    }
  }
  init();
})();
