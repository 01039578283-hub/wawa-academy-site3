(() => {
  'use strict';
  const filter = document.querySelector('form[data-guide-filter]');
  if (filter) {
    const search = filter.querySelector('#guide-search');
    const audience = filter.querySelector('#guide-audience');
    const category = filter.querySelector('#guide-category');
    const cards = [...document.querySelectorAll('[data-guide-card]')];
    const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko').trim();
    const indexed = cards.map(card => ({card, text: normalize(card.dataset.search)}));
    const update = () => {
      const terms = normalize(search.value).split(/\s+/).filter(Boolean);
      let count = 0;
      indexed.forEach(({card,text}) => {
        const show = terms.every(term => text.includes(term)) && (!audience.value || card.dataset.audiences.split(' ').includes(audience.value)) && (!category.value || card.dataset.category === category.value);
        card.hidden = !show; if (show) count++;
      });
      filter.querySelector('[data-guide-count]').textContent = `${count}개 가이드`;
      document.querySelector('[data-guide-empty]').hidden = count > 0;
    };
    filter.addEventListener('submit', event => event.preventDefault());
    filter.addEventListener('input', update);
    filter.addEventListener('change', update);
    filter.addEventListener('reset', () => setTimeout(update,0));
    filter.hidden = false;
    update();
  }
  const recorder = document.querySelector('form[data-guide-recorder]');
  if (!recorder) return;
  const fields = [...recorder.querySelectorAll('[data-record-field]')];
  const date = recorder.querySelector('[data-record-date]');
  const status = recorder.querySelector('[data-record-status]');
  const text = () => `${recorder.dataset.title}\n실천 기록\n\n실행한 날짜: ${date.value || '(미작성)'}\n\n${fields.map((field,i) => `${i+1}. ${field.dataset.label}\n${field.value || '(미작성)'}`).join('\n\n')}\n\n가이드: ${document.querySelector('link[rel="canonical"]').href}\n`;
  recorder.addEventListener('submit', event => event.preventDefault());
  recorder.querySelector('[data-record-download]').addEventListener('click', () => {
    const blob = new Blob(['\uFEFF',text()], {type:'text/plain;charset=utf-8'});
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl; anchor.download = `${recorder.dataset.slug}-기록.txt`;
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl),1000);
    status.textContent = '텍스트 파일 저장을 요청했습니다. 브라우저의 다운로드 목록을 확인하세요.';
  });
  const preparePrint = () => {
    recorder.querySelectorAll('.lg-print-value').forEach(element => element.remove());
    [date,...fields].forEach(field => {
      const value = document.createElement('div'); value.className = 'lg-print-value';
      value.textContent = field.value || '(미작성)'; field.after(value);
    });
  };
  recorder.querySelector('[data-record-print]').addEventListener('click', () => {
    preparePrint(); document.body.classList.add('lg-print-record'); window.print();
  });
  window.addEventListener('beforeprint',preparePrint);
  window.addEventListener('afterprint',() => document.body.classList.remove('lg-print-record'));
  recorder.addEventListener('reset', () => {
    recorder.querySelectorAll('.lg-print-value').forEach(element => element.remove());
    status.textContent = '작성 내용을 지웠습니다.';
  });
  recorder.hidden = false;
})();
