"use strict";
(() => {
  const form = document.querySelector("[data-teacher-filter]");
  if (!form) return;
  const cards = Array.from(document.querySelectorAll("[data-teacher-branch]"));
  const search = form.querySelector("#teacher-search");
  const region = form.querySelector("#teacher-region");
  const focus = form.querySelector("#teacher-focus");
  const count = form.querySelector("[data-teacher-count]");
  const empty = document.querySelector("[data-teacher-empty]");
  const normalize = value => value.normalize("NFKC").toLocaleLowerCase("ko-KR").replace(/\s+/g, "");
  const update = () => {
    const query = normalize(search.value);
    let found = 0;
    cards.forEach(card => {
      const visible = (!query || normalize(card.dataset.search).includes(query)) &&
        (!region.value || card.dataset.region === region.value) &&
        (!focus.value || card.dataset.focus.split("|").includes(focus.value));
      card.hidden = !visible;
      if (visible) found++;
    });
    count.textContent = `${found}개 지점 · 전체 ${cards.length}개 지점`;
    empty.hidden = found !== 0;
  };
  form.hidden = false;
  form.addEventListener("submit", event => event.preventDefault());
  form.addEventListener("input", update);
  form.addEventListener("change", update);
  form.addEventListener("reset", () => setTimeout(update, 0));
  update();
})();
