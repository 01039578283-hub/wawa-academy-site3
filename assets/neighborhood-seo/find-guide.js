/* Existing, reviewed routes only. This finder never decides enrollment availability. */
(() => {
  'use strict';
  const root = document.querySelector('[data-neighborhood-finder]');
  if (!root) return;
  const form = root.querySelector('form');
  const search = root.querySelector('[data-nf-search]');
  const areaSelect = root.querySelector('[data-nf-area]');
  const purpose = root.querySelector('[data-nf-purpose]');
  const subject = root.querySelector('[data-nf-subject]');
  const stage = root.querySelector('[data-nf-stage]');
  const category = root.querySelector('[data-nf-category]');
  const message = root.querySelector('[data-nf-message]');
  const result = root.querySelector('[data-nf-result]');
  const normalize = value => value.normalize('NFKC').replace(/\s+/g, '').toLocaleLowerCase('ko');
  let areas = [];
  const clearResult = () => { result.replaceChildren(); result.hidden = true; };
  function addLink(parent, item) {
    const a = document.createElement('a');
    a.className = 'nf-link';
    a.href = item.href;
    const label = document.createElement('span');
    label.textContent = item.label;
    a.append(label);
    if (item.unconfirmed) {
      a.classList.add('ns-grade-confirm-link');
      a.dataset.gradeConfirmation = 'source-empty';
      const status = document.createElement('span');
      status.className = 'ns-grade-confirm-status';
      status.textContent = '자료상 학년 확인 필요';
      a.append(status);
    }
    parent.append(a);
  }
  function render() {
    const comparison = purpose.value === 'comparison';
    root.querySelector('[data-nf-course-fields]').hidden = comparison;
    root.querySelector('[data-nf-comparison-field]').hidden = !comparison;
    clearResult();
    const area = areas.find(a => a.id === areaSelect.value);
    if (!area) return;
    const title = document.createElement('h3');
    title.textContent = area.name + ' · ' + (comparison ? '비교·선택 기준' : purpose.value === 'study' ? '진도·오답 점검' : '수강·위치 안내');
    const center = document.createElement('p');
    center.textContent = '상담에 참고할 지점: ' + area.center + ' · ' + area.region + ' ' + area.district;
    const note = document.createElement('p');
    note.className = 'nf-note';
    note.textContent = '동네 이름은 별도 지점 주소를 뜻하지 않습니다. 실제 주소·안내 학년·현재 모집 여부는 수강 안내에서 확인해 주세요.';
    const links = document.createElement('div');
    links.className = 'nf-results';
    if (comparison) addLink(links, area.comparison[category.value]);
    else if (purpose.value === 'enrollment') addLink(links, area.enrollment[subject.value][stage.value]);
    else {
      const grades = stage.value === '전체' ? ['초등', '중등', '고등'] : [stage.value];
      for (const grade of grades) addLink(links, area.study[subject.value][grade]);
    }
    const follow = document.createElement('div');
    follow.className = 'nf-follow';
    addLink(follow, {href:area.branch,label:area.center + ' 전체 학년·주소·교습비 확인'});
    addLink(follow, {href:area.overview,label:area.name + ' 과목·학년 전체 안내'});
    result.append(title,center,links,note,follow);
    result.hidden = false;
  }
  function filter() {
    const query = normalize(search.value);
    const selected = areaSelect.value;
    const matches = areas.filter(a => normalize([a.name,a.region,a.district,a.center].join(' ')).includes(query));
    areaSelect.replaceChildren(new Option('동네를 선택해 주세요', ''));
    for (const a of matches) areaSelect.add(new Option(a.name + ' · ' + a.region + ' ' + a.district + ' · ' + a.center, a.id));
    areaSelect.disabled = matches.length === 0;
    if (matches.some(a => a.id === selected)) areaSelect.value = selected;
    else if (matches.length === 1) areaSelect.value = matches[0].id;
    message.textContent = matches.length ? matches.length + '개 동네가 있습니다. 동네와 안내 목적을 선택해 주세요.' : '일치하는 동네가 없습니다. 동네명·지역명·지점명으로 다시 찾아보세요.';
    render();
  }
  form.addEventListener('submit', event => event.preventDefault());
  search.addEventListener('input', filter);
  for (const control of [areaSelect,purpose,subject,stage,category]) control.addEventListener('change', render);
  message.textContent = '동네 목록을 불러오고 있습니다.';
  fetch('/assets/neighborhood-seo/find-guide.json?v=20261001-v7', {credentials:'omit'})
    .then(response => {if (!response.ok) throw new Error('Finder data unavailable'); return response.json();})
    .then(data => {
      if (data.version !== '20261001-v7' || !Array.isArray(data.areas) || data.areas.length !== 371) throw new Error('Unexpected finder data');
      const scopeNode = root.querySelector('[data-nf-scope]');
      if (scopeNode) {
        const scope = JSON.parse(scopeNode.textContent);
        if (Object.keys(scope).length !== 1 || !Array.isArray(scope.ids) || !scope.ids.length || scope.ids.some(id => typeof id !== 'string')) throw new Error('Invalid finder scope');
        const ids = new Set(scope.ids);
        if (ids.size !== scope.ids.length) throw new Error('Duplicate finder scope');
        areas = data.areas.filter(area => ids.has(area.id));
        if (areas.length !== ids.size) throw new Error('Unknown finder scope');
      } else areas = data.areas;
      form.hidden = false;
      filter();
    })
    .catch(() => {
      clearResult();
      form.hidden = true;
      message.textContent = '동네 찾기를 불러오지 못했습니다. 아래 지역·분류 목록에서 같은 안내 페이지를 확인해 주세요.';
    });
})();
