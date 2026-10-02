"""Whole-sitemap invariants and local intent/fact validation, independent of build."""
from pathlib import Path
from urllib.parse import unquote,urljoin,urlsplit
from collections import Counter,deque
from concurrent.futures import ThreadPoolExecutor
import json,re,hashlib,argparse,zipfile
from lxml import html,etree
import improve_neighborhood_pages as impl

ROOT=impl.ROOT;OUT=impl.REPORT
def nodes(value):
 if isinstance(value,list):
  for x in value:yield from nodes(x)
 elif isinstance(value,dict):
  yield value
  for x in value.values():yield from nodes(x)
def main():
 p=argparse.ArgumentParser();p.add_argument('--sample',action='store_true');p.add_argument('--root');args=p.parse_args()
 root=Path(args.root) if args.root else ROOT
 phase2_enabled=any(c.get('gradeAuthority')=='workbook' for c in impl.FACTS['centers'])
 if phase2_enabled:
  import improve_neighborhood_phase2 as phase2
  from audit_neighborhood_phase2 import paragraphs,overlap_result
  snapshot=zipfile.ZipFile(phase2.OUT/'phase1-before-phase2.zip')
  before_overlap={};after_overlap={};phase2_count=0;h1_values=Counter();hubs_checked=0
 OUT.mkdir(parents=True,exist_ok=True)
 roles={r['path']:r for r in impl.inventory()}
 urls=etree.parse(str(root/'sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
 errors=[];titles=Counter();descs=Counter();improved=0;families=Counter();ids={};links={};asset_exists={};source_note_pages=0
 def exists_asset(src):
  if src not in asset_exists:asset_exists[src]=(root/unquote(src).lstrip('/')).is_file()
  return asset_exists[src]
 manifest=json.loads((ROOT/'release-public-manifest.json').read_text('utf-8'))
 baseline=Path(r'C:\Users\1992k\Desktop\CodexData\worktrees\publish21-wawa-academy-site3-20260925')
 def read_current(url):
  path=unquote(urlsplit(url).path);file=root/path.strip('/')/'index.html' if path!='/' else root/'index.html'
  return path,file.read_text('utf-8') if file.is_file() else None
 with ThreadPoolExecutor(max_workers=8) as pool:
  current_html=dict(pool.map(read_current,urls))
 for index,url in enumerate(urls,1):
  path=unquote(urlsplit(url).path);file=root/path.strip('/')/'index.html' if path!='/' else root/'index.html'
  if current_html[path] is None:errors.append([path,'missing HTML']);continue
  doc=html.document_fromstring(current_html[path]);title=doc.findtext('.//title');desc=doc.xpath('//meta[@name="description"]/@content')
  titles[title]+=1;descs[desc[0] if desc else '']+=1
  canonical=doc.xpath('//link[@rel="canonical"]/@href')
  if canonical!=[url]:errors.append([path,'canonical changed/missing'])
  if len(doc.xpath('//h1'))!=1:errors.append([path,'h1 count'])
  if len(desc)!=1 or not (0<len(desc[0])<=80) or not re.search(r'[.!?]$',desc[0]):errors.append([path,'description length/sentence'])
  for key in ['og:description','twitter:description']:
   other=doc.xpath('//meta[@property=$k or @name=$k]/@content',k=key)
   if other!=desc:errors.append([path,'metadata disagreement: '+key])
  if doc.xpath('//meta[contains(translate(@content,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"noindex")]'):errors.append([path,'noindex'])
  all_ids=doc.xpath('//*[@id]/@id');ids[path]=set(all_ids)
  if len(all_ids)!=len(set(all_ids)):errors.append([path,'duplicate DOM ids'])
  links[path]=doc.xpath('//a/@href')
  for script in doc.xpath('//script[@type="application/ld+json"]'):
   try:data=json.loads(script.text)
   except Exception as exc:errors.append([path,'JSON-LD parse '+str(exc)]);continue
   for n in nodes(data):
    if n.get('@type') in ['WebPage','CollectionPage','Article','BlogPosting']:
     if n.get('description')!=desc[0]:errors.append([path,'page schema description mismatch'])
    if n.get('@type') in ['Review','AggregateRating']:errors.append([path,'unsupported review schema'])
  if path in roles:
   r=roles[path];c=impl.CENTERS[tuple(r['centerKey'])]
   marker=doc.xpath('//body/@data-neighborhood-seo')
   if marker==[impl.VERSION]:
    improved+=1;families[r['family']]+=1
    phase2_marker=doc.xpath('//body/@data-neighborhood-phase2') if phase2_enabled else []
    if phase2_enabled:
     old=html.document_fromstring(snapshot.read(path.strip('/')+'/index.html'))
     before_guard=impl.protect(old);after_guard=impl.protect(doc)
     if phase2_marker==[phase2.VERSION]:
      before_guard.pop('h1');after_guard.pop('h1');phase2_count+=1
      current_h1=doc.xpath('string(//h1)');h1_values[current_h1]+=1
      if current_h1!=phase2.heading(r):errors.append([path,'wrong page-role H1'])
      for script in doc.xpath('//script[@type="application/ld+json"]'):
       for n in nodes(json.loads(script.text)):
        if n.get('@type')=='Article' and n.get('headline')!=current_h1:errors.append([path,'article headline disagrees with page-role H1'])
      for value in paragraphs(old,r):before_overlap.setdefault(value,[]).append((path,r['role']))
      for value in paragraphs(doc,r):after_overlap.setdefault(value,[]).append((path,r['role']))
      if len(doc.xpath('//main//*[@class="ns-image-summary"]'))!=1:errors.append([path,'missing text explanation of brand image'])
      if r['role']=='comparison-guide':
       questions=impl.byid(doc,'reading-7');image=impl.byid(doc,'page-images');main=doc.xpath('//main')[0]
       if questions is None or main.index(questions)>=main.index(image):errors.append([path,'comparison questions buried after image'])
      if c.get('gradeAuthority')=='workbook' and '수강 학년 기준: 센터 데이터 엑셀.' not in doc.text_content():errors.append([path,'missing workbook source label'])
      if r['role'] in ['enrollment','overview']:
       conditions=impl.byid(doc,'center-conditions');image=impl.byid(doc,'page-images')
       if conditions is None or doc.xpath('//main')[0].index(conditions)>=doc.xpath('//main')[0].index(image):errors.append([path,'missing early operating conditions'])
       for item in doc.xpath('//main//*[@data-grade-subject]'):
        subject=item.get('data-grade-subject');value=item.xpath('./p/text()')
        if value!=[impl.pretty(impl.grades_for(r,c,subject))]:errors.append([path,'grade card disagrees with authoritative source'])
      if phase2.restricted(r,c):
       if any(n.get('@type')=='Service' for script in doc.xpath('//script[@type="application/ld+json"]') for n in nodes(json.loads(script.text))):errors.append([path,'separate course location asserted as local service'])
       if '수지점(W+)' in ' '.join(phase2.course_notes(r,c)) and '수지점(W+)' not in impl.byid(doc,'local-summary').text_content():errors.append([path,'missing early separate course location'])
       if '실제 수업 장소는 위 주소를 기준으로' in impl.byid(doc,'local-summary').text_content():errors.append([path,'separate course location contradicted in early facts'])
     elif not args.sample:errors.append([path,'phase 2 missing'])
     if before_guard!=after_guard:errors.append([path,'route/images/contact preservation'])
    else:
     old=html.document_fromstring((baseline/path.strip('/')/'index.html').read_text('utf-8'))
     if impl.protect(old)!=impl.protect(doc):errors.append([path,'route/images/contact preservation'])
    summary=impl.byid(doc,'local-summary')
    if summary is None:errors.append([path,'missing early facts']);continue
    if c['address'] not in summary.text_content() or c['displayName'] not in summary.text_content():errors.append([path,'wrong center mapping'])
    dd=summary.xpath('.//dt[text()="센터 자료의 안내 학년"]/following-sibling::dd/text()')
    expected=' / '.join(f'{s} {impl.pretty([g for g in c["subjects"].get(s,[]) if not r.get("stage") or g.startswith(r["stage"][0])])}' for s in impl.subjects_for(r))
    if dd!=[expected] and not (args.sample and phase2_enabled and phase2_marker!=[phase2.VERSION]):errors.append([path,'grade mapping'])
    if r['role']=='enrollment' and r.get('subject') and not impl.grades_for(r,c,r['subject']):
     if any(n.get('@type')=='Service' for script in doc.xpath('//script[@type="application/ld+json"]') for n in nodes(json.loads(script.text))):errors.append([path,'unconfirmed course asserted in schema'])
    conflict=impl.conflict_note(r,c)
    if conflict:
     source_note_pages+=1
     if conflict not in summary.text_content():errors.append([path,'missing source disagreement'])
    body=impl.byid(doc,'page-images');main=doc.xpath('//main')[0]
    if body is None or main.index(summary)>=main.index(body):errors.append([path,'facts after images'])
    if r['role'] in ['study-guide','comparison-guide']:
     guide=impl.byid(doc,'intent-guide')
     if guide is None or main.index(guide)>=main.index(body):errors.append([path,'guide after images'])
    if r['role']=='enrollment':
     fees=impl.byid(doc,'fees')
     if fees is None or main.index(fees)>=main.index(body):errors.append([path,'tuition after images'])
    if len(doc.xpath('//img[@data-role="body-image"]/parent::picture/source'))!=1:errors.append([path,'responsive image missing'])
    if c['photoMode']=='common' and '브랜드 공통 학습 공간 예시' not in impl.byid(doc,'learning-space').text_content():errors.append([path,'unlabeled common photos'])
    facts_nodes=doc.xpath('//main//*[@id="center-info" or @id="grades" or @id="center-grades"]')
    if not any(c['routeName'] in n.text_content() or impl.availability(r,c) in n.text_content() for n in facts_nodes):errors.append([path,'center information disappeared'])
   elif not args.sample:errors.append([path,'not improved'])
  elif phase2_enabled and path.startswith('/지점안내/') and len(path.strip('/').split('/'))==3:
   _,region,branch=path.strip('/').split('/');c=impl.CENTERS.get((region,branch))
   if c and doc.xpath('//body/@data-neighborhood-phase2')==[phase2.VERSION]:
    hubs_checked+=1
    if impl.protect(doc)!=impl.protect(html.document_fromstring(snapshot.read(path.strip('/')+'/index.html'))):errors.append([path,'hub preservation'])
    if len(doc.xpath('//main//*[@class="ns-image-summary"]'))!=1:errors.append([path,'hub missing brand image text'])
    if not doc.xpath('//link[@href="/assets/neighborhood-seo/local.css"]'):errors.append([path,'hub missing shared styles'])
    conditions=impl.byid(doc,'center-conditions');image=impl.byid(doc,'page-images')
    if conditions is None or doc.xpath('//main')[0].index(conditions)>=doc.xpath('//main')[0].index(image):errors.append([path,'hub missing early operating conditions'])
    for script in doc.xpath('//script[@type="application/ld+json"]'):
     for n in nodes(json.loads(script.text)):
      if n.get('@type')=='Service':
       subject=next((s for s in c['subjects'] if s in n.get('name','')),None)
       if not subject or not c['subjects'][subject] or phase2.restricted({'role':'enrollment','subject':subject},c):errors.append([path,'hub unconfirmed local course schema'])
    for item in doc.xpath('//main//*[@data-grade-subject]'):
     subject=item.get('data-grade-subject')
     if item.xpath('./p/text()')!=[impl.pretty(c['subjects'][subject])]:errors.append([path,'hub grade card disagrees with source'])
   elif not args.sample:errors.append([path,'center hub phase 2 missing'])
  for image in doc.xpath('//img[@src]'):
   src=urlsplit(image.get('src')).path
   if src.startswith('/') and not exists_asset(src):errors.append([path,'missing image '+src])
  for source in doc.xpath('//source[@srcset]'):
   for entry in source.get('srcset').split(','):
    src=entry.strip().split()[0]
    if not exists_asset(src):errors.append([path,'missing responsive image '+src])
  if index%1500==0:print('Validated',index,flush=True)
 # Internal URLs and all fragments are resolved according to the page URL.
 graph={p:set() for p in ids};fragment_failures=[]
 for path,hrefs in links.items():
  for href in hrefs:
   resolved=urlsplit(urljoin(impl.DOMAIN+impl.U(path),href))
   if resolved.netloc!=urlsplit(impl.DOMAIN).netloc:continue
   target=unquote(resolved.path);target=re.sub(r'index\.html$','',target)
   if not target.endswith('/'):
    if target+'/' in ids:target+='/'
   if target in ids:
    graph[path].add(target)
    if resolved.fragment and unquote(resolved.fragment) not in ids[target]:fragment_failures.append([path,href,'missing fragment'])
   elif not exists_asset(target):errors.append([path,href,'missing internal route'])
 # Old legacy anchor issues are distinguished from newly introduced issues.
 new_fragment_failures=fragment_failures if phase2_enabled else [e for e in fragment_failures if e[1].startswith('#') and e[1] in ['#local-summary','#intent-guide','#related-intents','#fees','#page-images']]
 errors.extend(new_fragment_failures)
 distance={'/':0};q=deque(['/'])
 while q:
  current=q.popleft()
  for target in graph.get(current,[]):
   if target not in distance:distance[target]=distance[current]+1;q.append(target)
 unreachable=sorted(set(ids)-set(distance));errors.extend([p,'unreachable from home'] for p in unreachable)
 for c in impl.FACTS['sources']:
  source=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\센터정보')/c['file']
  if hashlib.sha256(source.read_bytes()).hexdigest()!=c['sha256']:errors.append([c['file'],'source hash changed'])
 errors.extend(['duplicate title',t,n] for t,n in titles.items() if n>1)
 errors.extend(['duplicate description',t,n] for t,n in descs.items() if n>1)
 baseline_urls=etree.parse(str(baseline/'sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
 if urls!=baseline_urls:errors.append(['sitemap','existing URL set/order changed'])
 result={'sitemapPages':len(urls),'improvedPages':improved,'families':dict(families),'sourceDisagreementLabeledPages':source_note_pages,'descriptionsMax':max(map(len,descs)),'unreachablePages':len(unreachable),'legacyFragmentIssues':len(fragment_failures)-len(new_fragment_failures),'legacyFragmentExamples':fragment_failures[:12], 'branchGradeDistance':dict(Counter(distance.get(p) for p,r in roles.items() if r['family']=='branch-grade')),'errors':errors,'deployed':False}
 if phase2_enabled:
  from openpyxl import load_workbook
  wb=load_workbook(Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\센터정보\코칭센터_데이터_.xlsx'),read_only=True,data_only=True)
  workbook_rows={str(row[0]).strip():row for row in wb.active.values if row[0]};wb.close();matched=0
  for c in impl.FACTS['centers']:
   if c.get('gradeAuthority')!='workbook':continue
   row=workbook_rows[c['sourceName']];matched+=1
   for subject,column in zip(['국어','영어','수학','과학','사회'],range(16,21)):
    actual=re.findall(r'[초중고][1-6]',str(row[column] or ''))
    if actual!=c['subjects'][subject]:errors.append([c['routeName'],subject,'does not match confirmed workbook'])
  errors.extend(['duplicate phase-2 H1',value,count] for value,count in h1_values.items() if count>1)
  result.update(phase2Pages=phase2_count,phase2CenterHubs=hubs_checked,workbookCentersVerified=matched,phase2DuplicateH1Groups=sum(n>1 for n in h1_values.values()),editorialOverlapBefore=overlap_result(before_overlap),editorialOverlapAfter=overlap_result(after_overlap))
  snapshot.close()
 impl.dump(OUT/('sample-validation.json' if args.sample else 'validation.json'),result)
 summary={**result,'errors':errors[:15],'errorCount':len(errors)}
 for key in ['editorialOverlapBefore','editorialOverlapAfter']:
  if key in summary:summary[key]={k:v for k,v in summary[key].items() if k!='examples'}
 print(json.dumps(summary,ensure_ascii=False));raise SystemExit(bool(errors))
if __name__=='__main__':main()
