/* One near-viewport map, isolated from the page's images and other scripts. */
(() => {
  'use strict';
  const frames = new Set();
  function start(frame) {
    if (!frame.isConnected || frame.getAttribute('src')) return;
    frame.src = frame.dataset.kmSrc;
    frame.closest('.km-map').dataset.state = 'loading';
    if (observer) observer.unobserve(frame);
  }
  const observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
    entries.forEach(entry => { if (entry.isIntersecting) start(entry.target); });
  }, {rootMargin:'300px 0px'}) : null;
  function observe(root) {
    root.querySelectorAll('iframe[data-km-src]').forEach(frame => {
      frames.add(frame);
      if (observer) observer.observe(frame); else start(frame);
    });
  }
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || !event.data || !['km-ready','km-error'].includes(event.data.type)) return;
    for (const frame of frames) {
      if (!frame.isConnected) { frames.delete(frame); continue; }
      if (event.source !== frame.contentWindow) continue;
      const wrap = frame.closest('.km-map');
      wrap.dataset.state = event.data.type === 'km-ready' ? 'ready' : 'error';
      if (event.data.type === 'km-error') wrap.querySelector('.km-map-status').textContent = '지도를 불러오지 못했습니다. 기존 지도 이미지와 주소를 확인해 주세요.';
    }
  });
  observe(document);
  document.querySelectorAll('[data-km-chooser]').forEach(hub => {
    const select = hub.querySelector('select');
    const result = hub.querySelector('.km-hub-result');
    const status = hub.querySelector('.km-hub-status');
    let request = null;
    let sequence = 0;
    select.addEventListener('change', async () => {
      const token = ++sequence;
      if (request) request.abort();
      result.querySelectorAll('iframe').forEach(frame => { if (observer) observer.unobserve(frame); frames.delete(frame); });
      result.replaceChildren();
      if (!select.value) { status.textContent = '방문할 지점을 선택하면 지도와 주변 교통편을 확인할 수 있습니다.'; return; }
      request = new AbortController();
      status.textContent = '선택한 지점의 위치를 확인하고 있습니다.';
      try {
        const response = await fetch(select.value, {signal:request.signal});
        if (!response.ok) throw new Error('Visit information unavailable');
        const data = await response.json();
        if (token !== sequence) return;
        result.innerHTML = data.html;
        observe(result);
        status.textContent = select.selectedOptions[0].textContent + '의 지도와 주변 교통편입니다.';
      } catch (error) {
        if (error.name !== 'AbortError' && token === sequence) status.textContent = '위치 정보를 불러오지 못했습니다. 아래 지점 안내에서 주소와 지도 이미지를 확인해 주세요.';
      }
    });
  });
})();
