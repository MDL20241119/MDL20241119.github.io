/* Public evidence only. This page never connects to a booking or vehicle API. */
'use strict';
const STATUS = {
  'IMPLEMENTED': {label: '実装済み', className: 'implemented'},
  'PARTIAL': {label: '部分実装', className: 'partial'},
  'NOT IMPLEMENTED': {label: '未実装', className: 'missing'},
  'NOT APPLICABLE': {label: '対象外', className: 'na'},
  'NEEDS VERIFICATION': {label: '追加確認が必要', className: 'unknown'}
};
const STANDARD_LABELS = {commmmons: 'COMmmmONS', gtfs: 'GTFS-JP', maas: 'MaaS', mcp: 'MCP', a2a: 'A2A', other: '共通・その他'};
const state = {rows: [], loaded: false};
const $ = (id) => document.getElementById(id);
const plain = (value) => typeof value === 'string' || typeof value === 'number' ? String(value) : '';
function list(value) {
  if (Array.isArray(value)) return value.map(item => plain(item) || plain(item?.summary) || plain(item?.description) || plain(item?.requirement)).filter(Boolean);
  return plain(value) ? [plain(value)] : [];
}
function safeUrl(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  try { const url = new URL(value, location.href); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; } catch { return null; }
}
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function statusValue(value) {
  const raw = plain(value) || plain(value?.status) || plain(value?.implementation_status);
  const normalized = raw.trim().toUpperCase().replaceAll('_', ' ').replaceAll('-', ' ').replace(/\s+/g, ' ');
  if (STATUS[normalized]) return normalized;
  const aliases = {'実装済み': 'IMPLEMENTED', '部分実装': 'PARTIAL', '未実装': 'NOT IMPLEMENTED', '対象外': 'NOT APPLICABLE', '追加確認必要': 'NEEDS VERIFICATION', '追加確認が必要': 'NEEDS VERIFICATION', '未確認': 'NEEDS VERIFICATION'};
  return aliases[raw] || 'NEEDS VERIFICATION';
}
function standardOf(row) {
  const label = [row.standard, row.standard_id, row.specification, row.operation_id, row.operationId, row.id].map(plain).join(' ').toLowerCase();
  if (row.method || /commmmons|c-api|m16-if|com-/.test(label)) return 'commmmons';
  if (/gtfs|g4-/.test(label)) return 'gtfs';
  if (/maas|m3-/.test(label)) return 'maas';
  if (/mcp/.test(label)) return 'mcp';
  if (/a2a/.test(label)) return 'a2a';
  return 'other';
}
function normalize(row, index) {
  const standard = standardOf(row);
  const source = row.source_status ?? row.source_application_status ?? row.local_status ?? row.status ?? row.implementation_status;
  const demo = row.demo_status ?? row.public_demo_status;
  const requirement = plain(row.requirement) || plain(row.title) || plain(row.summary) || plain(row.name) || `${plain(row.method)} ${plain(row.path)}`.trim() || '確認項目';
  const id = plain(row.operation_id) || plain(row.operationId) || plain(row.id) || `item-${index + 1}`;
  const notes = list(row.notes);
  const gaps = list(row.gaps ?? row.remaining_work ?? row.remaining_issues);
  const sourceStatus = statusValue(source);
  const demoStatus = statusValue(demo);
  return {...row, key: index, standardKey: standard, requirementText: requirement, itemId: id,
    sourceStatus, demoStatus, notesList: notes, gapsList: gaps,
    sourceNote: plain(source?.note) || plain(source?.summary) || plain(row.source_note),
    demoNote: plain(demo?.note) || plain(demo?.summary) || plain(row.demo_note),
    searchable: [requirement, id, STANDARD_LABELS[standard], row.method, row.path, row.rule, ...notes, ...gaps].map(plain).join(' ').toLocaleLowerCase('ja')};
}
function badge(value) {
  const info = STATUS[value];
  return node('span', `badge ${info.className}`, info.label);
}
function appendTextList(parent, values, empty = '追加確認が必要です。') {
  if (!values.length) { parent.append(node('p', '', empty)); return; }
  if (values.length === 1) { parent.append(node('p', '', values[0])); return; }
  const ul = node('ul'); values.forEach(value => ul.append(node('li', '', value))); parent.append(ul);
}
function detailItem(label, values, className = '', empty) {
  const item = node('div', className); item.append(node('dt', '', label));
  const dd = node('dd'); appendTextList(dd, values, empty); item.append(dd); return item;
}
function testText(row) {
  const value = row.test_status ?? row.tests?.status ?? row.test?.status;
  const text = plain(value) || plain(value?.status) || '未確認';
  const norm = text.toUpperCase();
  const labels = {PASS: '記載範囲で試験通過', PASSED: '記載範囲で試験通過', FAIL: '要修正', FAILED: '要修正', UNTESTED: '未試験', 'NOT TESTED': '未試験', 'NOT EXECUTED': '未試験', 'NEEDS VERIFICATION': '追加確認が必要', 'NOT APPLICABLE': '対象外'};
  return {label: labels[norm] || text, pass: ['PASS', 'PASSED'].includes(norm)};
}
function buildRow(row) {
  const tr = node('tr');
  const first = node('td');
  const button = node('button', 'requirement-button'); button.type = 'button';
  const panelId = `requirement-${row.key}`;
  button.setAttribute('aria-expanded', 'false'); button.setAttribute('aria-controls', panelId);
  const icon = node('span', 'expand-icon', '+'); icon.setAttribute('aria-hidden', 'true');
  const text = node('span'); text.append(node('span', 'requirement-title', row.requirementText));
  const identifier = [STANDARD_LABELS[row.standardKey], plain(row.id) !== row.itemId ? plain(row.id) : '', row.itemId, [row.method, row.path].map(plain).filter(Boolean).join(' ')].filter(Boolean).join(' / ');
  text.append(node('span', 'requirement-id', identifier));
  const priority = plain(row.priority ?? row.mdl_priority_proposal ?? row.applicability);
  if (priority) text.append(node('span', 'requirement-tag', priority));
  button.append(icon, text); first.append(button); tr.append(first);
  const demo = node('td'); demo.append(badge(row.demoStatus));
  if (row.demoNote) demo.append(node('span', 'cell-note', row.demoNote));
  tr.append(demo);
  const source = node('td'); source.append(badge(row.sourceStatus));
  if (row.sourceNote) source.append(node('span', 'cell-note', row.sourceNote));
  tr.append(source);
  const test = node('td'); const tested = testText(row);
  test.append(node('span', `test-label${tested.pass ? ' pass' : ''}`, tested.label));
  const testScope = plain(row.test_scope) || plain(row.tests?.scope) || plain(row.test?.scope);
  if (testScope) test.append(node('span', 'cell-note', testScope));
  tr.append(test);
  const expanded = node('tr', 'details-row'); expanded.id = panelId; expanded.hidden = true;
  const expandedCell = node('td'); expandedCell.colSpan = 4;
  const dl = node('dl', 'details-grid');
  dl.append(detailItem('要求事項と適用条件', [plain(row.rule), plain(row.applicability_condition)].filter(Boolean), '', row.requirementText));
  dl.append(detailItem('残る課題・未確認の範囲', row.gapsList, '', 'この記録には個別の残課題が記載されていません。外部本番接続の状況は別途確認が必要です。'));
  if (row.notesList.length) dl.append(detailItem('確認記録', row.notesList));
  const testEvidence = list(row.test_evidence ?? row.test_details ?? row.tests?.description ?? row.test?.description);
  if (testEvidence.length) dl.append(detailItem('試験の根拠', testEvidence));
  const sourceItem = node('div', 'wide'); sourceItem.append(node('dt', '', '一次資料・公開できる根拠'));
  const sourceBody = node('dd'); const links = node('div', 'source-links');
  const refs = [
    [row.source_url ?? row.spec_url ?? row.official_url, '公式仕様を開く'],
    [row.code_url ?? row.evidence_url, '公開コード・確認記録を開く'],
    [row.test_url, '試験記録を開く']
  ];
  for (const [value, label] of refs) {
    const url = safeUrl(value); if (!url) continue;
    const link = node('a', '', label + ' ↗'); link.href = url; links.append(link);
  }
  sourceBody.append(links);
  const locator = plain(row.source_locator ?? row.spec_section);
  if (locator) sourceBody.append(node('p', 'cell-note', locator));
  if (!links.childElementCount) sourceBody.append(node('p', '', '公開可能な根拠は確認中です。'));
  sourceItem.append(sourceBody); dl.append(sourceItem); expandedCell.append(dl); expanded.append(expandedCell);
  button.addEventListener('click', () => { const open = button.getAttribute('aria-expanded') !== 'true'; button.setAttribute('aria-expanded', String(open)); expanded.hidden = !open; icon.textContent = open ? '−' : '+'; });
  return [tr, expanded];
}
function render() {
  if (!state.loaded) return;
  const words = $('search').value.trim().toLocaleLowerCase('ja').split(/\s+/).filter(Boolean);
  const standard = $('standard-filter').value; const status = $('status-filter').value;
  const rows = state.rows.filter(row => (standard === 'all' || row.standardKey === standard) && (status === 'all' || row.sourceStatus === status) && words.every(word => row.searchable.includes(word)));
  const fragment = document.createDocumentFragment();
  rows.forEach(row => fragment.append(...buildRow(row)));
  if (!rows.length) { const tr = node('tr'); const td = node('td', 'empty-state', '条件に合う項目がありません。キーワードや絞り込みを変更してください。'); td.colSpan = 4; tr.append(td); fragment.append(tr); }
  $('matrix-body').replaceChildren(fragment);
  $('data-status').textContent = `${state.rows.length}項目中 ${rows.length}項目を表示`;
}
function nonnegativeInteger(...values) { return values.find(value => Number.isSafeInteger(value) && value >= 0); }
function applySummary(data) {
  const checked = plain(data.checked_on ?? data.checked_at).slice(0, 10);
  if (/^\d{4}-\d{2}-\d{2}$/.test(checked)) { $('checked-date').dateTime = checked; $('checked-date').textContent = checked.replaceAll('-', '.'); }
  const reports = data.test_report || {};
  const summary = data.summary || {};
  const operations = data.operations || [];
  const count = nonnegativeInteger(summary.successful_operation_count, summary.tested_operations, summary.operations_tested, reports.successful_operation_count, Array.isArray(reports.successful_operations) ? reports.successful_operations.length : undefined);
  // A count is shown only when the evidence explicitly reports successful operations.
  if (count !== undefined && count <= 19) $('operation-count').textContent = String(count);
  const tests = nonnegativeInteger(reports.tests, reports.test_count, summary.tests, summary.test_count);
  if (tests !== undefined) $('test-count').textContent = String(tests);
  const demoVersion = plain(data.public_demo?.version);
  const sourceVersion = plain(data.source_application?.base_version ?? data.source_application?.version);
  const versions = [demoVersion ? `公開デモ v${demoVersion}` : '', sourceVersion ? `元アプリ v${sourceVersion} を元にしたローカル実装` : ''].filter(Boolean);
  if (versions.length) $('code-scope').textContent = '今回照合したコード：' + versions.join(' / ') + '。実行環境を分けて確認しています。';
  const scopeText = plain(reports.scope);
  if (scopeText) $('test-scope').textContent = scopeText;
  const reportUrl = safeUrl(reports.report_url);
  if (reportUrl) { $('test-report-link').href = reportUrl; $('test-report-link').hidden = false; }
  // No inference of production connectivity from a passing local test.
  const production = data.production_connection ?? reports.production_connection;
  $('production-state').textContent = production === false ? '外部との本番接続は未実施' : '本番接続は追加確認が必要';
  const dependencies = list(data.external_dependencies);
  if (dependencies.length) $('dependencies-list').replaceChildren(...dependencies.map(value => node('li', '', value)));
  if (operations.length > 19) $('operation-count').textContent = '—';
}
async function load() {
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch('status.json', {signal: controller.signal, cache: 'no-cache'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!data || typeof data !== 'object' || (!Array.isArray(data.operations) && !Array.isArray(data.requirements))) throw new Error('Invalid public evidence schema');
    const rows = [...(data.operations || []), ...(data.requirements || [])].filter(row => row && typeof row === 'object');
    if (!rows.length || rows.length > 1000) throw new Error('Invalid number of requirements');
    state.rows = rows.map(normalize); state.loaded = true; applySummary(data); render();
  } catch {
    $('data-status').textContent = '確認データを取得できませんでした。';
    const tr = node('tr'); const td = node('td', 'empty-state', '確認表を読み込めませんでした。ページを再読み込みするか、公開データ JSON を開いてください。'); td.colSpan = 4; tr.append(td); $('matrix-body').replaceChildren(tr);
  } finally { clearTimeout(timeout); }
}
$('search').addEventListener('input', render);
$('standard-filter').addEventListener('change', render);
$('status-filter').addEventListener('change', render);
$('reset').addEventListener('click', () => { $('search').value = ''; $('standard-filter').value = 'all'; $('status-filter').value = 'all'; render(); $('search').focus(); });
load();
