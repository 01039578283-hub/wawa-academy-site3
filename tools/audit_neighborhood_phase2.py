"""Preserve the first local release and measure substantive paragraph overlap."""
from pathlib import Path
from collections import Counter,defaultdict
from urllib.parse import unquote,urlsplit
import json,re,zipfile,hashlib
from lxml import html,etree
import improve_neighborhood_pages as impl

OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase2-20260930')
EDITORIAL={'grade-learning','learning-routine','consultation-prep','subject-learning','learning-plan','learning-steps','intent-guide','student-fit','consult-checklist','reading-2','reading-7','reading-9'}

def paragraphs(doc,r):
 values=set()
 for block in doc.xpath('//main//*[@id]'):
  if block.get('id') not in EDITORIAL:continue
  for p in block.xpath('.//p'):
   value=' '.join(p.text_content().split())
   if len(value)<70 or any(t in value for t in ['후기나','제안입니다','뜻하지','참고용','안내입니다','상담 참고 학교로는']):continue
   c=impl.CENTERS[tuple(r['centerKey'])]
   for token in sorted({r['neighborhood'],impl.norm(r['neighborhood']),c['displayName'],c['routeName'],c['address']},key=len,reverse=True):
    value=value.replace(token,'[지역정보]')
   values.add(value)
 return values

def overlap_result(groups):
 shared=[(t,rows) for t,rows in groups.items() if len({r[1] for r in rows})>1]
 return {'crossRoleParagraphGroups':len(shared),'crossRoleParagraphOccurrences':sum(len(rows) for _,rows in shared),'examples':[{'text':t,'occurrences':len(rows),'roles':dict(Counter(r[1] for r in rows))} for t,rows in sorted(shared,key=lambda v:len(v[1]),reverse=True)[:12]]}

def main():
 OUT.mkdir(exist_ok=True,parents=True);archive=OUT/'phase1-before-phase2.zip'
 assert not archive.exists(),'Keep the original phase-1 backup; do not replace it'
 roles={r['path']:r for r in impl.inventory()};groups=defaultdict(list);headings=Counter();pages=[]
 urls=etree.parse(str(impl.ROOT/'sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
  for i,url in enumerate(urls,1):
   path=unquote(urlsplit(url).path);rel=path.strip('/')+'/index.html' if path!='/' else 'index.html';raw=(impl.ROOT/rel).read_bytes();z.writestr(rel,raw)
   doc=html.document_fromstring(raw)
   if path in roles:
    r=roles[path];headings[doc.xpath('string(//h1)')]+=1
    for value in paragraphs(doc,r):groups[value].append((path,r['role']))
   pages.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest()})
   if i%2000==0:print('Backed up and audited',i,flush=True)
  for name in ['seo-descriptions.json','release-public-manifest.json','sitemap.xml']:
   z.write(impl.ROOT/name,name)
  for p in impl.DATA.glob('*.json'):z.write(p,'tools/data/neighborhood-seo/'+p.name)
  for p in impl.REPORT.glob('*.json'):z.write(p,'tools/reports/neighborhood-seo/'+p.name)
 result={'pages':len(urls),'neighborhoodPages':len(roles),'duplicateH1Groups':sum(n>1 for n in headings.values()),'duplicateH1Pages':sum(n for n in headings.values() if n>1),'overlap':overlap_result(groups),'backup':str(archive),'deployed':False}
 impl.dump(OUT/'before.json',result);impl.dump(OUT/'phase1-pages.json',pages)
 print(json.dumps({**result,'overlap':{k:v for k,v in result['overlap'].items() if k!='examples'}},ensure_ascii=False))

if __name__=='__main__':main()
