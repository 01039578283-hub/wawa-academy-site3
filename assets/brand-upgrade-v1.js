/* Only the home page loads this file. No video connection before a click. */
(() => {
  'use strict';
  const allowedIds = new Set(['avpJfW7eIV0', 'f_skFu40U04', 'UIXUaBZdNXU']);
  document.querySelectorAll('.upgrade-video-player[data-video]').forEach((player) => {
    const link = player.querySelector('.video-launch');
    const id = player.dataset.video;
    if (!link || !allowedIds.has(id)) return;
    const poster = link.cloneNode(true);
    let playerActions;

    function start(event) {
      // Modifier clicks retain the ordinary YouTube link behavior.
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button > 0) return;
      event.preventDefault();
      if (player.querySelector('iframe')) return;
      const frame = document.createElement('iframe');
      frame.src = `https://www.youtube-nocookie.com/embed/${id}?playsinline=1&rel=0`;
      frame.title = player.dataset.videoTitle;
      frame.allow = 'encrypted-media; picture-in-picture; fullscreen';
      frame.allowFullscreen = true;
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      frame.tabIndex = 0;
      player.replaceChildren(frame);
      player.classList.add('is-loaded');
      const closeButton = document.createElement('button');
      closeButton.type = 'button';
      closeButton.className = 'video-close';
      closeButton.textContent = '영상 닫기';
      closeButton.setAttribute('aria-label', `${frame.title} 닫기`);
      closeButton.addEventListener('click', stop);
      const openLink = document.createElement('a');
      openLink.href = poster.href;
      openLink.target = '_blank';
      openLink.rel = 'noopener';
      openLink.textContent = 'YouTube 열기';
      openLink.className = 'video-external';
      playerActions = document.createElement('div');
      playerActions.className = 'video-player-actions';
      playerActions.append(openLink, closeButton);
      player.after(playerActions);
      frame.focus({ preventScroll: true });
    }

    function stop() {
      const restored = poster.cloneNode(true);
      player.replaceChildren(restored);
      player.classList.remove('is-loaded');
      playerActions?.remove();
      restored.addEventListener('click', start);
      restored.focus({ preventScroll: true });
    }

    link.addEventListener('click', start);
  });
})();
