"""Connect retained enrollment/study URLs through existing public hubs."""
from collections import defaultdict
import json
from lxml import html,etree
import improve_neighborhood_pages as impl

def save(path,doc):
 path.write_text(html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n','utf-8')
def main():
 groups=defaultdict(list)
 for r in impl.SUBJECTS:
  if r['subject']=='수학':groups[r['path'].strip('/').split('/')[1],r['center']].append(r)
 changed=[];target_count=0
 for key,rows in groups.items():
  c=impl.CENTERS[key];rel=impl.center_path(c);path=impl.ROOT/rel.strip('/')/'index.html'
  doc=html.document_fromstring(path.read_text('utf-8'));guard=impl.protect(doc)
  if impl.byid(doc,'local-grade-guides') is not None:continue
  body=impl.paragraph('수강 조건은 학년·과목별 지점 안내에서, 학습 상태를 점검하는 방법은 동네 학습 가이드에서 확인할 수 있습니다.')
  for r in rows:
   r={**r,'region':key[0]}
   body+='<h3>'+impl.E(r['neighborhood'])+'</h3><div class="ns-link-grid">'
   for subject in ['영어','수학']:
    for stage in ['초등','중등','고등']:
     p=impl.branch_path(r,subject,stage);assert (impl.ROOT/p.strip('/')/'index.html').exists()
     body+=impl.anchor(p,stage+' '+subject+' 수강 안내');target_count+=1
   body+=impl.anchor('/전국센터/'+impl.norm(r['neighborhood'])+'/',r['neighborhood']+' 학습·비교 안내')+'</div>'
  section=impl.section('local-grade-guides','동네별 학년·과목 안내 바로 찾기',body)
  main=doc.xpath('//main')[0];previous=impl.byid(doc,'neighborhood-pages')
  main.insert(main.index(previous)+1 if previous is not None else 1,section)
  doc.xpath('//head')[0].append(impl.node('<link rel="stylesheet" href="/assets/neighborhood-seo/local.css">'))
  doc.xpath('//body')[0].set('data-neighborhood-hub',impl.VERSION)
  for p in doc.xpath('//main/p[contains(@class,"cl-revised")]'):
   p.text='학년·과목별 안내 연결 수정 2026.09.30 · 현재 모집 여부는 지점에 확인해 주세요.'
   for child in list(p):p.remove(child)
  for script in doc.xpath('//script[@type="application/ld+json"]'):
   data=json.loads(script.text)
   for n in data.get('@graph',[]):
    if n.get('@type') in ['WebPage','CollectionPage']:n['dateModified']=impl.DAY
   script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
  assert impl.protect(doc)==guard
  save(path,doc);changed.append(rel)
 for rel in ['/지점안내/','/전국센터/','/과목별학원/']:
  path=impl.ROOT/rel.strip('/')/'index.html';doc=html.document_fromstring(path.read_text('utf-8'));guard=impl.protect(doc)
  if impl.byid(doc,'choose-guide-purpose') is not None:continue
  body=impl.paragraph('현재 수강 가능한 학년과 실제 주소·교육비를 알아보려면 지점 안내를, 진도와 오답을 점검하거나 수업을 비교하려면 학습 가이드를 살펴보세요.')
  body+='<div class="ns-link-grid">'+impl.anchor('/지점안내/','실제 지점·수강 조건 찾기')+impl.anchor('/전국센터/','동네별 학습 점검 가이드')+impl.anchor('/과목별학원/','과목·학교급별 비교 기준')+'</div>'
  doc.xpath('//main')[0].insert(1,impl.section('choose-guide-purpose','필요한 정보를 골라 찾아보세요',body))
  doc.xpath('//head')[0].append(impl.node('<link rel="stylesheet" href="/assets/neighborhood-seo/local.css">'));doc.xpath('//body')[0].set('data-neighborhood-hub',impl.VERSION)
  assert impl.protect(doc)==guard;save(path,doc);changed.append(rel)
 # Lastmod changes correspond only to changed content; loc values remain intact.
 sitemap=etree.parse(str(impl.ROOT/'sitemap.xml'));before=sitemap.xpath('//*[local-name()="loc"]/text()')
 changed_paths={r['path'] for r in impl.inventory()}|set(changed)
 for entry in sitemap.getroot():
  url=entry.find('{*}loc')
  if url is not None and impl.unquote(impl.urlsplit(url.text).path) in changed_paths:
   last=entry.find('{*}lastmod')
   if last is None:last=etree.SubElement(entry,'{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
   last.text=impl.DAY
 assert sitemap.xpath('//*[local-name()="loc"]/text()')==before
 sitemap.write(str(impl.ROOT/'sitemap.xml'),encoding='utf-8',xml_declaration=True,pretty_print=True)
 impl.dump(impl.REPORT/'hubs.json',{'changedHubs':len(changed),'centerHubs':len(groups),'directGradeLinksAdded':target_count,'paths':changed,'sitemapLocationsPreserved':len(before)})
 print(json.dumps({'changedHubs':len(changed),'directGradeLinksAdded':target_count,'sitemapPages':len(before)},ensure_ascii=False))
if __name__=='__main__':main()
