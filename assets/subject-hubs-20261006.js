/* All destination links remain in the HTML; search progressively enhances them. */
(() => {
  const directory = document.querySelector('[data-subject-directory]');
  if (!directory) return;
  const form = directory.querySelector('.sh-search');
  const input = form.querySelector('input');
  const status = directory.querySelector('[data-sh-status]');
  const empty = directory.querySelector('.sh-empty');
  const regions = [...directory.querySelectorAll('[data-sh-region]')];
  const panels = [...directory.querySelectorAll('[data-sh-panel]')];
  const normalize = value => value.normalize('NFKC').replace(/\s+/g, '').toLowerCase();
  let selected = 'all';
  const apply = () => {
    const query = normalize(input.value);
    let visible = 0;
    panels.forEach(panel => {
      const allowed = selected === 'all' || selected === panel.dataset.shPanel;
      let matches = 0;
      panel.querySelectorAll('.sh-district').forEach(district => {
        let count = 0;
        district.querySelectorAll('.sh-local-link').forEach(link => {
          link.hidden = !allowed || (query && !normalize(link.dataset.shSearch).includes(query));
          if (!link.hidden) count++;
        });
        district.hidden = !count;
        district.open = Boolean(query && count);
        matches += count;
      });
      panel.hidden = !allowed || !matches;
      visible += matches;
    });
    regions.forEach(link => {
      if (link.dataset.shRegion === selected) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
    status.textContent = query ? `“${input.value.trim()}” 검색 결과 ${visible}개 동네` :
      selected === 'all' ? `전체 ${visible}개 동네 · 지역을 고른 뒤 시·군·구를 펼쳐보세요.` :
      `${selected} ${visible}개 동네 · 시·군·구를 펼쳐 동네를 선택하세요.`;
    empty.hidden = visible > 0;
  };
  regions.forEach(link => link.addEventListener('click', () => {
    selected = link.dataset.shRegion;
    input.value = '';
    apply();
  }));
  input.addEventListener('input', () => {
    selected = 'all';
    history.replaceState(null, '', '#hub-directory');
    apply();
  });
  form.addEventListener('reset', event => {
    event.preventDefault();
    input.value = '';
    selected = 'all';
    history.replaceState(null, '', '#hub-directory');
    apply();
    input.focus();
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    apply();
    const first = directory.querySelector('.sh-local-link:not([hidden])');
    if (first && input.value.trim()) location.href = first.href;
    else if (!input.value.trim()) { input.focus(); status.textContent = '먼저 동네 또는 시·군·구 이름을 입력해 주세요.'; }
  });
  // A saved region anchor also opens the right panel on a fresh visit.
  const initial = regions.find(link => link.dataset.shRegion !== 'all' && link.hash === location.hash);
  if (initial) selected = initial.dataset.shRegion;
  window.addEventListener('hashchange', () => {
    const choice = regions.find(link => link.hash === location.hash);
    if (!choice) return;
    selected = choice.dataset.shRegion;
    input.value = '';
    apply();
  });
  form.hidden = false;
  apply();
})();
