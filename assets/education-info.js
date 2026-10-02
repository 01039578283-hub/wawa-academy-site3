(() => {
  'use strict';
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko-KR').trim();
  const filter = document.querySelector('[data-education-filter]');
  if (filter) {
    const search = filter.querySelector('#ei-search');
    const category = filter.querySelector('#ei-category');
    const audience = filter.querySelector('#ei-audience');
    const cards = [...document.querySelectorAll('[data-education-list] [data-education-card]')];
    const count = filter.querySelector('[data-education-count]');
    const empty = document.querySelector('[data-education-empty]');
    const update = () => {
      const terms = normalize(search.value).split(/\s+/).filter(Boolean);
      let visible = 0;
      for (const card of cards) {
        const match = (!category.value || category.value === card.dataset.category) &&
          (!audience.value || card.dataset.audience.includes(audience.value)) &&
          terms.every(term => normalize(card.dataset.search).includes(term));
        card.hidden = !match;
        visible += Number(match);
      }
      count.textContent = `${visible}개 글 · 전체 ${cards.length}개`;
      empty.hidden = visible !== 0;
    };
    filter.addEventListener('submit', event => event.preventDefault());
    filter.addEventListener('input', update);
    filter.addEventListener('change', update);
    filter.addEventListener('reset', () => setTimeout(update, 0));
    filter.hidden = false;
    update();
  }
  const locator = document.querySelector('[data-education-locator]');
  if (!locator) return;
  const region = locator.querySelector('#ei-location-region');
  const kind = locator.querySelector('#ei-location-kind');
  const place = locator.querySelector('#ei-location-place');
  const go = locator.querySelector('[data-location-go]');
  const status = locator.querySelector('[data-location-status]');
  go.tabIndex = -1;
  locator.addEventListener('submit', event => event.preventDefault());
  go.addEventListener('click', event => {
    if (go.getAttribute('aria-disabled') === 'true') event.preventDefault();
  });
  fetch('/assets/education-locations.json', {credentials: 'same-origin'})
    .then(response => {
      if (!response.ok) throw new Error('Location data unavailable');
      return response.json();
    })
    .then(data => {
      if (!Array.isArray(data)) return;
      const locations = data.filter(row => ['neighborhood', 'center'].includes(row.kind) &&
        typeof row.region === 'string' && typeof row.label === 'string' &&
        typeof row.path === 'string' && row.path.startsWith('/') && !row.path.startsWith('//'));
      if (!locations.length) return;
      for (const value of [...new Set(locations.map(row => row.region))].sort((a,b) => a.localeCompare(b,'ko'))) {
        region.add(new Option(value, value));
      }
      const setLink = () => {
        const selected = locations.find(row => row.path === place.value && row.region === region.value && row.kind === kind.value);
        go.href = selected ? selected.path : (kind.value === 'center' ? '/지점안내/' : '/전국센터/');
        go.setAttribute('aria-disabled', String(!selected));
        go.tabIndex = selected ? 0 : -1;
        go.textContent = selected ? `${selected.label} 안내로 이동` : '선택한 안내로 이동';
        if (selected) status.textContent = `${selected.region} · ${selected.label} ${kind.value === 'center' ? '지점' : '동네'} 안내를 선택했습니다.`;
      };
      const updatePlaces = () => {
        const matches = locations.filter(row => row.region === region.value && row.kind === kind.value);
        place.replaceChildren(new Option(region.value ? '동네·지점을 선택하세요' : '지역을 먼저 선택하세요', ''));
        for (const row of matches) place.add(new Option(row.label, row.path));
        place.disabled = !matches.length;
        status.textContent = region.value ? `${region.value}의 ${kind.value === 'center' ? '지점' : '동네'} 안내 ${matches.length}개에서 선택하세요.` : '지역을 고르면 홈페이지에 있는 동네와 지점 안내를 찾을 수 있습니다.';
        setLink();
      };
      region.addEventListener('change', updatePlaces);
      kind.addEventListener('change', updatePlaces);
      place.addEventListener('change', setLink);
      locator.hidden = false;
      updatePlaces();
    }).catch(() => { /* The ordinary neighborhood and branch links remain available. */ });
})();
