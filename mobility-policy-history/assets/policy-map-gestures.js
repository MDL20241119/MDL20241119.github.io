(() => {
  'use strict';
  const main = document.getElementById('main');
  if (!main) return;
  const selector = '.policy-front-graphic';
  const bound = new WeakSet();
  const maxZoom = 4;
  const step = 1.4;
  const threshold = 7;
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  const dist = (p, q) => Math.hypot(p.clientX - q.clientX, p.clientY - q.clientY);
  const mid = (p, q) => ({x:(p.clientX + q.clientX) / 2, y:(p.clientY + q.clientY) / 2});
  const icon = path => '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+path+'"/></svg>';

  function init(frame) {
    const map = frame.querySelector('svg.japan-map');
    const native = map?.viewBox.baseVal;
    if (!native?.width || !native?.height || bound.has(frame)) return;
    bound.add(frame);
    frame.classList.add('p-map-interactive');
    frame.tabIndex = 0;
    frame.setAttribute('role','group');
    frame.setAttribute('aria-label','日本地図の操作');
    frame.setAttribute('aria-describedby','policy-map-keys');
    const help = document.createElement('span');
    help.className = 'p-map-sr';
    help.id = 'policy-map-keys';
    help.textContent = '矢印キーで移動、プラス・マイナスで拡大縮小、0で全体表示。地図は指で移動・ピンチで拡大縮小できます。都道府県は地図の下の選択欄でも開けます。';
    const status = document.createElement('span');
    status.className = 'p-map-sr';
    status.setAttribute('role','status');
    const toolbar = document.createElement('div');
    toolbar.className = 'p-map-tools';
    toolbar.setAttribute('role','group');
    toolbar.setAttribute('aria-label','地図の表示を調整');
    function button(classes,label,text,art) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = classes;
      b.setAttribute('aria-label',label);
      b.title = label;
      if (art) b.innerHTML = art;
      else b.textContent = text;
      toolbar.append(b);
      return b;
    }
    const plus = button('p-map-zoom','地図を拡大','＋');
    const minus = button('p-map-zoom','地図を縮小','−');
    const reset = button('p-map-reset','日本全体を表示','',icon('M4 9V4h5m6 0h5v5m0 6v5h-5m-6 0H4v-5'));
    frame.append(toolbar,help,status);

    const full = {x:native.x,y:native.y,w:native.width,h:native.height};
    let current = {...full,z:1};
    let drag = null;
    let pinch = null;
    let moved = false;
    let suppress = false;
    let unblock;
    const pointers = new Map();
    function draw(x, y, z) {
      if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) return;
      z = clamp(z,1,maxZoom);
      const w = full.w/z, h = full.h/z;
      current = {x:clamp(x,full.x,full.x+full.w-w),y:clamp(y,full.y,full.y+full.h-h),w,h,z};
      const round = n => +n.toFixed(3);
      map.setAttribute('viewBox',[current.x,current.y,w,h].map(round).join(' '));
      frame.classList.toggle('p-map-can-pan',z>1.0001);
      // Keep buttons focused at the bounds; announce availability without dropping focus.
      plus.setAttribute('aria-disabled',String(z>=maxZoom-0.0001));
      minus.setAttribute('aria-disabled',String(z<=1.0001));
      reset.setAttribute('aria-disabled',String(z<=1.0001));
    }
    function say(text) { status.textContent = text; }
    function sayZoom(){ say('表示倍率 '+Math.round(current.z*100)+'パーセント'); }
    function zoomAt(z, xRatio=.5, yRatio=.5) {
      z=clamp(z,1,maxZoom);
      draw(current.x+(current.w-full.w/z)*xRatio,current.y+(current.h-full.h/z)*yRatio,z);
      sayZoom();
    }
    const changeZoom = factor => zoomAt(current.z*factor);
    function resetAll(){draw(full.x,full.y,1);say('日本全体を表示');}
    plus.addEventListener('click',()=>changeZoom(step));
    minus.addEventListener('click',()=>changeZoom(1/step));
    reset.addEventListener('click',resetAll);
    frame.addEventListener('keydown',ev=>{
      if (ev.target!==frame) return;
      const shift = ev.shiftKey ? .3 : .13;
      const dirs={ArrowLeft:[-shift,0],ArrowRight:[shift,0],ArrowUp:[0,-shift],ArrowDown:[0,shift]};
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      if (ev.key in dirs && current.z>1) {
        const [dx,dy]=dirs[ev.key];draw(current.x+dx*current.w,current.y+dy*current.h,current.z);
      } else if (['+','='].includes(ev.key)) changeZoom(step);
      else if (['-','−'].includes(ev.key)) changeZoom(1/step);
      else if (ev.key==='0' || ev.key==='Home') resetAll();
      else return;
      ev.preventDefault();
    });
    const capture = id => {
      try { frame.setPointerCapture(id); } catch {}
    };
    function beginDrag(point) {
      const svgScale = map.getScreenCTM()?.a;
      if (!(svgScale>0)) return null;
      return { point, x:current.x,y:current.y, scale:svgScale };
    }
    function beginPinch(a,b) {
      const point = mid(a,b);
      const rect = map.getScreenCTM();
      if (!(rect?.a>0)) return null;
      const gap = dist(a,b);
      if (!(gap>0)) return null;
      return {
        gap,point,z:current.z,x:current.x,y:current.y,w:current.w,h:current.h,
        anchorX:(point.x-rect.e)/rect.a,anchorY:(point.y-rect.f)/rect.a,scale:rect.a
      };
    }
    frame.addEventListener('pointerdown',ev=>{
      if (ev.target.closest('svg.japan-map')!==map || ev.button!==0) return;
      if (!pointers.size) {
        clearTimeout(unblock);
        suppress=false;
        moved=false;
      }
      pointers.set(ev.pointerId,{clientX:ev.clientX,clientY:ev.clientY,type:ev.pointerType});
      if (pointers.size===1) {
        drag=beginDrag(pointers.get(ev.pointerId));
      } else if (pointers.size===2) {
        pinch=beginPinch(...pointers.values());
        if (pinch) for (const id of pointers.keys()) capture(id);
      }
    });
    frame.addEventListener('pointermove',ev=>{
      if (!pointers.has(ev.pointerId)) return;
      const point={clientX:ev.clientX,clientY:ev.clientY,type:ev.pointerType};
      pointers.set(ev.pointerId,point);
      if (pinch && pointers.size>=2) {
        const [a,b]=[...pointers.values()];
        const center=mid(a,b);
        const pinchDist=dist(a,b);
        if (moved || Math.abs(pinchDist-pinch.gap)>=threshold || Math.hypot(center.x-pinch.point.x,center.y-pinch.point.y)>=threshold) {
          moved=true;
          const z=clamp(pinch.z*pinchDist/pinch.gap,1,maxZoom);
          const rel=pinch.z/z;
          const scale=pinch.scale/rel;
          const localX=(pinch.anchorX-pinch.x)/pinch.w;
          const localY=(pinch.anchorY-pinch.y)/pinch.h;
          draw(pinch.anchorX-localX*full.w/z-(center.x-pinch.point.x)/scale,pinch.anchorY-localY*full.h/z-(center.y-pinch.point.y)/scale,z);
          frame.classList.add('p-map-dragging');
        }
      } else if (drag && pointers.size===1 && (moved || dist(point,drag.point)>=threshold)) {
        if (!moved) capture(ev.pointerId);
        moved=true;
        draw(drag.x-(point.clientX-drag.point.clientX)/drag.scale,drag.y-(point.clientY-drag.point.clientY)/drag.scale,current.z);
        frame.classList.add('p-map-dragging');
      }
    });
    function end(ev) {
      if (!pointers.delete(ev.pointerId)) return;
      if (pinch) {
        if (moved) sayZoom();
        pinch=null;
        drag=pointers.size===1 ? beginDrag(pointers.values().next().value) : null;
      }
      if (!pointers.size) {
        suppress=moved;
        clearTimeout(unblock);
        unblock=setTimeout(()=>{suppress=false;},420);
        moved=false;
        drag=null;
        frame.classList.remove('p-map-dragging');
      }
    }
    frame.addEventListener('pointerup',end);
    frame.addEventListener('pointercancel',end);
    frame.addEventListener('lostpointercapture',ev=>{if (ev.target===frame) end(ev);});
    frame.addEventListener('pointerleave',ev=>{if (!frame.hasPointerCapture(ev.pointerId)) end(ev);});
    frame.addEventListener('click',ev=>{
      if (!suppress || !ev.detail || !ev.target.closest('svg.japan-map a')) return;
      ev.preventDefault();
      ev.stopImmediatePropagation();
    },true);
    frame.addEventListener('dragstart',ev=>{if (ev.target.closest('svg.japan-map')) ev.preventDefault();});
    draw(full.x,full.y,1);
  }
  function scan(){main.querySelectorAll(selector).forEach(init);}
  new MutationObserver(scan).observe(main,{childList:true,subtree:true});
  scan();
})();
