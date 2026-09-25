/* Search only filters existing, crawlable links. No network request is needed. */
(() => {
  'use strict';
  const form = document.querySelector('[data-directory-search]');
  if (!form) return;
  const input = form.querySelector('input[type="search"]');
  const region = form.querySelector('select');
  const cards = [...document.querySelectorAll('[data-center-card]')];
  const status = document.querySelector('[data-search-status]');
  const empty = document.querySelector('[data-search-empty]');
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko').replace(/\s+/g, '');
  const searchable = cards.map(card => normalize(card.dataset.search || ''));
  function filter() {
    const tokens = input.value.normalize('NFKC').trim().split(/\s+/).filter(Boolean).map(normalize);
    let count = 0;
    cards.forEach((card, i) => {
      const matches = (!region?.value || region.value === card.dataset.region) && tokens.every(token => searchable[i].includes(token));
      card.hidden = !matches;
      if (matches) count += 1;
    });
    status.textContent = count === cards.length && !input.value.trim() && !region?.value ? `전체 ${count}개 지점을 살펴볼 수 있습니다.` : `검색 결과 ${count}개 지점`;
    empty.hidden = count > 0;
  }
  form.hidden = false;
  status.hidden = false;
  form.addEventListener('input', filter);
  form.addEventListener('change', filter);
  form.addEventListener('submit', event => { event.preventDefault(); filter(); });
  form.addEventListener('reset', () => { requestAnimationFrame(() => { filter(); input.focus(); }); });
  filter();
})();
