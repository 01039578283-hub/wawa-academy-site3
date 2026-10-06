/* Visible native images and original-file links work before enhancement. */
(() => {
  const dialog = document.querySelector('[data-cm-dialog]');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const slot = dialog.querySelector('[data-cm-slot]');
  const title = dialog.querySelector('[data-cm-title]');
  const original = dialog.querySelector('[data-cm-original]');
  const zoom = dialog.querySelector('[data-cm-zoom]');
  const close = dialog.querySelector('[data-cm-close]');
  let trigger;
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-cm-source]');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    trigger = link;
    const image = document.createElement('img');
    const thumb = link.querySelector('img');
    image.alt = thumb.alt;
    image.width = Number(thumb.getAttribute('width'));
    image.height = Number(thumb.getAttribute('height'));
    image.style.setProperty('--cm-natural-width', image.width + 'px');
    image.src = link.dataset.cmSource;
    slot.replaceChildren(image);
    title.textContent = image.alt;
    original.href = link.href;
    original.textContent = link.dataset.cmWhole === 'body' ? '본문 전체 원본 열기' : '원본 파일 열기';
    dialog.classList.remove('is-actual-size');
    zoom.textContent = '100% 원본 크기';
    zoom.setAttribute('aria-pressed', 'false');
    dialog.showModal();
    close.focus();
  });
  zoom.addEventListener('click', () => {
    const actual = dialog.classList.toggle('is-actual-size');
    zoom.textContent = actual ? '화면에 맞추기' : '100% 원본 크기';
    zoom.setAttribute('aria-pressed', String(actual));
  });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    slot.replaceChildren();
    if (trigger && trigger.isConnected) trigger.focus();
  });
})();
