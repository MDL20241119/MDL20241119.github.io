"use strict";
(() => {
  const events = window.OITA_EVENTS, months = window.OITA_MONTHS, pending = window.OITA_PENDING, relations = window.OITA_RELATIONS, photos = window.OITA_PHOTOS;
  const state = {category:"all",relation:"all",after:false};
  const labels = {all:"すべて",mobility:"モビリティ候補",culture:"文化・観光",industry:"産業・人材",community:"福祉・地域"};
  const groupNames = {direct:"実施・運営への関与",support:"協賛・後援・補助",facility:"施設・広報との関係",related:"直接関与未確認"};
  const escape = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  const photo = key => photos[key] || photos.beppu;
  const tagColors = {culture:"#D8D0F0",industry:"#F23BC8",mobility:"#58F21B",community:"#FF8A00"};
  const role = id => relations.find(item => item.id === id);
  const matchesTopic = event => (state.category === "all" || (state.category === "mobility" ? event.mobility : event.category === state.category)) && (state.relation === "all" || event.prefecture.roles.includes(state.relation));
  const matches = event => matchesTopic(event) && (!state.after || event.end >= "2026-11-01");
  function roleBadges(event) {
    return `<div class="role-badges" aria-label="大分県の関わり">${event.prefecture.roles.map(id => {const item = role(id);return `<span class="role-badge role-${item.group}" title="${escape(item.explanation)}">${escape(item.label)}</span>`;}).join("")}</div>`;
  }
  function relationBlock(event) {
    return `<div class="prefecture-block"><span class="prefecture-label">PREFECTURE / 県の関わり</span>${roleBadges(event)}<p class="prefecture-summary">${escape(event.prefecture.summary)}</p></div>`;
  }
  function evidence(event, undated = false) {
    const phone = /^\d{2,4}(-\d+)+$/.test(event.phone || "") ? `<a href="tel:${escape(event.phone)}">${escape(event.phone)}</a>` : escape(event.phone);
    return `<div class="event-evidence"><div class="source-links">${event.sources.map((url,index) => `<a href="${escape(url)}" target="_blank" rel="noopener noreferrer" aria-label="${escape(event.title)}の公式情報${index+1}">公式情報${event.sources.length > 1 ? ` ${index+1}` : ""} <span aria-hidden="true">↗</span></a>`).join("")}</div><details class="event-details"><summary>${undated ? "確認事項・担当窓口" : "主催者・担当窓口・連携の視点"}</summary><dl>${event.prefecture.organizers ? `<dt>主催者・事業主体</dt><dd>${escape(event.prefecture.organizers)}</dd>` : ""}${event.contact ? `<dt>問い合わせ窓口</dt><dd>${escape(event.contact)}${phone ? `<br>${phone}` : ""}</dd>` : ""}${event.attention ? `<dt>参加・日程の留意点</dt><dd>${escape(event.attention)}</dd>` : ""}${event.mobilityIdea ? `<dt>モビリティ連携の視点</dt><dd>${escape(event.mobilityIdea)}</dd>` : ""}${event.nextCheck ? `<dt>次に確認すること</dt><dd>${escape(event.nextCheck)}</dd>` : ""}</dl><p class="evidence-date">整理基準日：2026.09.11</p></details></div>`;
  }
  function card(event) {
    const p = photo(event.photo);
    return `<article class="event-card${event.priority ? " is-priority" : ""}" id="event-${event.id}" aria-labelledby="title-${event.id}"><figure class="event-photo"><img src="${escape(p.src)}" alt="${escape(p.alt)}" width="800" height="500" loading="lazy" decoding="async"${p.position ? ` style="object-position:${escape(p.position)}"` : ""}><span class="event-category" style="--tag-color:${event.priority ? "#FFF200" : tagColors[event.category]}">${escape(event.tag)}</span>${event.priority ? `<span class="priority-badge" aria-label="優先候補${event.priority}">0${event.priority}</span>` : ""}<figcaption>${escape(p.caption)}</figcaption></figure><div class="event-body"><div class="event-date"><span>${escape(event.date)}</span><span class="date-year">${event.start.slice(0,4)}</span></div><div class="date-status${event.status.includes("予定") ? " is-planned" : ""}">${escape(event.status)}</div><p class="event-time">${escape(event.time)}</p><h3 class="event-title" id="title-${event.id}">${escape(event.title)}</h3><p class="event-place"><span class="location-icon" aria-hidden="true">◎</span><span>${escape(event.place)}</span></p><p class="event-description">${escape(event.description)}</p>${event.note ? `<p class="event-note ${escape(event.noteType || "")}">${escape(event.note)}</p>` : ""}${relationBlock(event)}${evidence(event)}<div class="event-bottom"><span>OITA EVENT WATCH</span><span class="listed-status">${event.start < "2026-11-01" ? (event.end >= "2026-11-01" ? "11/1をまたぐ開催" : "11/1より前") : "11/1以降"}</span></div></div></article>`;
  }
  function renderPending() {
    const selected = pending.filter(matchesTopic);
    document.getElementById("pending-count").textContent = String(selected.length).padStart(2,"0");
    document.getElementById("pending-events").innerHTML = selected.length ? selected.map(event => `<article class="pending-card" id="pending-${event.id}"><span class="pending-meta">${String(pending.indexOf(event)+1).padStart(2,"0")} <span>日程未確定</span></span><h3>${escape(event.title)}</h3><p class="pending-status">${escape(event.status)}</p><p>${escape(event.description)}</p>${relationBlock(event)}${evidence(event,true)}</article>`).join("") : '<p class="pending-empty">この条件に該当する日程未確定案件はありません。</p>';
  }
  function render() {
    const selected = events.filter(matches);
    document.getElementById("event-months").innerHTML = months.map(month => {
      const current = selected.filter(event => event.month === month.key);
      const carry = selected.filter(event => event.month < month.key && event.end >= `${month.key}-01`);
      const hasResults = current.length || carry.length;
      const link = document.querySelector(`[data-month="${month.key}"]`);
      link.classList.toggle("is-unavailable", !hasResults);link.setAttribute("aria-disabled", String(!hasResults));
      link.title = hasResults ? `${month.year}年${Number(month.number)}月へ` : "この月には該当するイベントがありません";
      if (!hasResults) return "";
      const divider = month.key === "2026-11" ? `<aside class="reveal-divider"><strong>11.01</strong><p>お披露目構想の基準日<span>この日以降の連携候補を優先して確認</span></p><span class="reveal-right">AFTER THE REVEAL</span></aside>` : "";
      const carryHtml = carry.length ? `<div class="carryover"><strong>この月も開催中</strong>${carry.map(event => `<a href="#event-${event.id}" data-event-jump="${event.id}">${escape(event.title)}<span>〜${Number(event.end.slice(5,7))}/${Number(event.end.slice(8,10))}</span></a>`).join("")}</div>` : "";
      return `${divider}<section class="month-section" id="month-${month.key}" aria-labelledby="heading-${month.key}"><header class="month-heading" style="--month-color:${month.color}"><h3 id="heading-${month.key}"><span class="year">${month.year}</span><span class="month-number">${month.number}</span><span class="month-name">${month.name}</span></h3><span class="event-count">${current.length}件${carry.length ? ` ＋ 継続${carry.length}件` : ""}</span><p class="month-note">${escape(month.note).replace(/\n/g,"<br>")}</p></header><div class="month-content"><div class="events-grid">${current.map(card).join("")}</div>${carryHtml}${month.key === "2027-02" ? '<p class="month-tail">02.26 / 今回のコンソーシアム事業期間の最終日</p>' : ""}</div></section>`;
    }).join("");
    document.getElementById("empty-state").hidden = !!selected.length;
    document.getElementById("result-count").textContent = `${selected.length}件の日程 / 未確定 ${pending.filter(matchesTopic).length}案件${state.category !== "all" ? ` / ${labels[state.category]}` : ""}${state.relation !== "all" ? ` / ${role(state.relation).label}` : ""}${state.after ? " / 日程は11月1日以降" : ""}`;
    document.querySelectorAll("[data-filter]").forEach(button => {const active = button.dataset.filter === state.category;button.classList.toggle("is-active", active);button.setAttribute("aria-pressed", String(active));});
    renderPending();
  }
  function resetFilters() {state.category="all";state.relation="all";state.after=false;document.getElementById("after-reveal").checked=false;document.getElementById("prefecture-filter").value="all";render();}
  function scrollToEvent(id) {
    const event = events.find(item => item.id === id);if (!event) return;
    if (!matches(event)) resetFilters();
    const target = document.getElementById(`event-${id}`);
    if (target) {target.scrollIntoView({behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",block:"start"});target.tabIndex=-1;target.focus({preventScroll:true});history.replaceState(null,"",`#event-${id}`);}
  }
  document.getElementById("prefecture-filter").innerHTML = '<option value="all">すべての関わり方</option>' + Object.entries(groupNames).map(([group,label]) => `<optgroup label="${label}">${relations.filter(item=>item.group===group).map(item=>`<option value="${item.id}">${item.label}</option>`).join("")}</optgroup>`).join("");
  document.getElementById("relation-definitions").innerHTML = relations.map(item=>`<div><dt><span class="role-badge role-${item.group}">${item.label}</span></dt><dd>${escape(item.explanation)}</dd></div>`).join("");
  document.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click",()=>{state.category=button.dataset.filter;render();}));
  document.getElementById("after-reveal").addEventListener("change",event=>{state.after=event.target.checked;render();});
  document.getElementById("prefecture-filter").addEventListener("change",event=>{state.relation=event.target.value;render();});
  document.getElementById("clear-filters").addEventListener("click",resetFilters);
  document.getElementById("reset-all").addEventListener("click",resetFilters);
  document.addEventListener("click",event=>{const jump=event.target.closest("[data-event-jump]");if(jump){event.preventDefault();scrollToEvent(jump.dataset.eventJump);}const month=event.target.closest("[data-month]");if(month?.getAttribute("aria-disabled")==="true")event.preventDefault();});
  document.getElementById("priority-events").innerHTML = events.filter(event=>event.priority).sort((a,b)=>a.priority-b.priority).map(event=>{const p=photo(event.photo);return `<article class="priority-card"><figure class="priority-photo"><img src="${escape(p.src)}" alt="${escape(p.alt)}" width="600" height="500" loading="lazy" decoding="async"${p.position ? ` style="object-position:${escape(p.position)}"` : ""}><span class="priority-number">0${event.priority}</span><figcaption>${escape(p.caption)}</figcaption></figure><div class="priority-copy"><span class="priority-date">${escape(event.priorityDate || event.date)}</span><h3>${escape(event.title)}</h3>${roleBadges(event)}<p>${escape(event.priorityText)}</p>${event.status.includes("予定") ? `<span class="priority-status">${escape(event.status)}</span>` : ""}<a href="#event-${event.id}" data-event-jump="${event.id}">日程・県の関わりを見る <span aria-hidden="true">↗</span></a></div></article>`;}).join("");
  const hero=document.getElementById("hero-photo");hero.src=photo("beppu").src;hero.alt=photo("beppu").alt;
  const credits=Object.values(photos).filter((p,index,list)=>list.findIndex(item=>item.src===p.src)===index);
  document.getElementById("credit-list").innerHTML=credits.map(p=>`<li><a href="${escape(p.source)}" target="_blank" rel="noopener noreferrer">${escape(p.title)}</a> — ${escape(p.author)} / <a href="${escape(p.licenseUrl)}" target="_blank" rel="noopener noreferrer">${escape(p.license)}</a>。${escape(p.edits || "表示時にトリミング")}</li>`).join("");
  render();
  const initialEvent=location.hash.match(/^#event-([a-z0-9-]+)$/)?.[1];if(initialEvent)requestAnimationFrame(()=>scrollToEvent(initialEvent));
  if(document.modelContext?.registerTool){const lifecycle=new AbortController();try{Promise.resolve(document.modelContext.registerTool({
    name:"filter_oita_events",title:"大分のイベントを絞り込む",description:"分類・大分県の関与・11月1日以降の条件でカレンダーを更新。日程未確定案件には日付条件を適用しません。",
    inputSchema:{type:"object",properties:{category:{type:"string",enum:Object.keys(labels)},relation:{type:"string",enum:["all",...relations.map(item=>item.id)]},afterNovember1:{type:"boolean"}},required:["category","afterNovember1"],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},
    execute(input){if(!input || typeof input!=="object" || !Object.keys(labels).includes(input.category) || typeof input.afterNovember1!=="boolean" || (input.relation!==undefined && !["all",...relations.map(item=>item.id)].includes(input.relation)) || Object.keys(input).some(key=>!["category","relation","afterNovember1"].includes(key)))throw new Error("有効な分類・県の関与・日付条件を指定してください。");state.category=input.category;state.relation=input.relation || "all";state.after=input.afterNovember1;document.getElementById("after-reveal").checked=state.after;document.getElementById("prefecture-filter").value=state.relation;render();return {events:events.filter(matches).map(event=>({id:event.id,title:event.title,start:event.start,end:event.end,place:event.place,status:event.status,prefecture:event.prefecture,sources:event.sources})),pending:pending.filter(matchesTopic).map(event=>({id:event.id,title:event.title,status:event.status,prefecture:event.prefecture,sources:event.sources})),asOf:"2026-09-11"};}
  },{signal:lifecycle.signal})).catch(()=>{});window.addEventListener("pagehide",()=>lifecycle.abort(),{once:true});}catch{}}
})();
