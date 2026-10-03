(() => {
  'use strict';
  const filter = document.querySelector('[data-curriculum-filter]');
  if (filter) {
    const cards = [...document.querySelectorAll('[data-cc-card][data-grade]')];
    const search = filter.querySelector('#cc-search');
    const grade = filter.querySelector('#cc-grade');
    const subject = filter.querySelector('#cc-subject');
    const count = filter.querySelector('[data-cc-count]');
    const empty = document.querySelector('[data-cc-empty]');
    const compact = (value) => value.toLocaleLowerCase('ko-KR').replace(/\s/g, '');
    const update = () => {
      const query = compact(search.value);
      let visible = 0;
      cards.forEach((card) => {
        const matches = (!grade.value || card.dataset.grade === grade.value) &&
          (!subject.value || card.dataset.subject === subject.value) &&
          (!query || compact(card.dataset.search).includes(query));
        card.hidden = !matches;
        if (matches) visible += 1;
      });
      count.textContent = `${visible}개 안내 · 전체 ${cards.length}개`;
      empty.hidden = visible !== 0;
    };
    const preset = new URLSearchParams(location.search).get('subject');
    if ([...subject.options].some((option) => option.value === preset)) subject.value = preset;
    filter.hidden = false;
    filter.addEventListener('input', update);
    filter.addEventListener('change', update);
    filter.addEventListener('submit', (event) => event.preventDefault());
    filter.addEventListener('reset', () => setTimeout(update, 0));
    update();
  }
  const locator = document.querySelector('[data-curriculum-locator]');
  if (!locator) return;
  const region = locator.querySelector('#cc-region');
  const kind = locator.querySelector('#cc-kind');
  const place = locator.querySelector('#cc-place');
  const go = locator.querySelector('[data-cc-location-go]');
  const status = locator.querySelector('[data-cc-location-status]');
  go.addEventListener('click', (event) => {
    if (go.getAttribute('aria-disabled') === 'true') event.preventDefault();
  });
  fetch('/assets/education-locations.json', { cache: 'no-cache' }).then((response) => {
    if (!response.ok) throw new Error('location-list');
    return response.json();
  }).then((locations) => {
    if (!Array.isArray(locations) || !locations.every((row) => typeof row.path === 'string' && /^\/(?:%[0-9A-Fa-f]{2}|[^\s?#\\])+\/$/.test(row.path))) throw new Error('location-data');
    [...new Set(locations.map((row) => row.region))].sort().forEach((label) => region.add(new Option(label, label)));
    const setDestination = () => {
      const selected = locations.find((row) => row.region === region.value && row.kind === kind.value && row.path === place.value);
      go.href = selected ? selected.path : (kind.value === 'center' ? '/지점안내/' : '/전국센터/');
      go.setAttribute('aria-disabled', selected ? 'false' : 'true');
      go.textContent = selected ? `${selected.label} 안내로 이동` : '선택한 안내로 이동';
      status.textContent = selected ? `${selected.region} ${selected.label}의 기존 안내 페이지로 이동합니다.` : '동네·지점을 선택하세요.';
    };
    const updatePlaces = () => {
      const rows = locations.filter((row) => row.region === region.value && row.kind === kind.value);
      place.replaceChildren(new Option(region.value ? '동네·지점을 선택하세요' : '지역을 먼저 선택하세요', ''));
      rows.forEach((row) => place.add(new Option(row.label, row.path)));
      place.disabled = !region.value || rows.length === 0;
      setDestination();
      if (region.value && !rows.length) status.textContent = '선택한 지역의 안내가 없습니다. 다른 지역이나 동네 안내를 선택해 보세요.';
    };
    region.addEventListener('change', updatePlaces);
    kind.addEventListener('change', updatePlaces);
    place.addEventListener('change', setDestination);
    locator.addEventListener('submit', (event) => event.preventDefault());
    locator.hidden = false;
    updatePlaces();
  }).catch(() => {
    // Static directory links remain available if the optional picker cannot load.
    locator.hidden = true;
  });
})();
