/* Render the supplied Kakao roughmap identity; keep attribution, omit outbound actions. */
(() => {
  'use strict';
  const settings = JSON.parse(document.getElementById('km-config').textContent);
  const root = document.getElementById('daumRoughmapContainer' + settings.timestamp);
  const notify = type => { if (parent !== window) parent.postMessage({type}, location.origin); };
  let ready = false;
  let map;
  const clean = () => {
    root.querySelectorAll('.cont,.wrap_btn_roadview,.btn_big_map').forEach(node => node.remove());
    root.querySelectorAll('a').forEach(link => { link.removeAttribute('href'); link.removeAttribute('target'); link.removeAttribute('onclick'); link.removeAttribute('role'); link.removeAttribute('tabindex'); });
    if (!ready && map?.jsMap && [...root.querySelectorAll('.map img')].some(image => image.complete && image.naturalWidth >= 128)) {
      ready = true;
      if (map?.jsMap) { map.jsMap.setDraggable(false); map.jsMap.setZoomable(false); }
      root.setAttribute('data-ready','');
      notify('km-ready');
    }
  };
  const mutations = new MutationObserver(clean);
  mutations.observe(root, {childList:true,subtree:true});
  root.addEventListener('load', clean, true);
  let resizeFrame = 0;
  addEventListener('resize', () => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      if (!map?.jsMap) return;
      const center = map.jsMap.getCenter();
      map.jsMap.relayout();
      map.jsMap.setCenter(center);
    });
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.btn_zoom_in,.btn_zoom_out,.btn_reset')) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  try {
    map = new daum.roughmap.Lander({timestamp:settings.timestamp,key:settings.key,mapWidth:String(Math.max(240,document.documentElement.clientWidth)),mapHeight:'360'});
    map.render();
  } catch (_) { notify('km-error'); }
  setTimeout(() => { if (!ready) { mutations.disconnect(); notify('km-error'); } }, 20000);
})();
