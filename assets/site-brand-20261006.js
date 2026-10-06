/* The menu remains visible and navigable if JavaScript is unavailable. */
(() => {
  const header = document.querySelector('.brand-shell');
  const button = header?.querySelector('.brand-menu-toggle');
  const navigation = header?.querySelector('.brand-navigation');
  if (!header || !button || !navigation) return;
  const setExpanded = (expanded) => {
    header.dataset.expanded = String(expanded);
    button.setAttribute('aria-expanded', String(expanded));
    button.querySelector('.brand-menu-label').textContent = expanded ? '닫기' : '메뉴';
  };
  setExpanded(false);
  header.dataset.enhanced = 'true';
  button.addEventListener('click', () => setExpanded(header.dataset.expanded !== 'true'));
  header.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && header.dataset.expanded === 'true') {
      setExpanded(false);
      button.focus();
    }
  });
  navigation.addEventListener('click', (event) => {
    if (event.target.closest('a')) setExpanded(false);
  });
})();
