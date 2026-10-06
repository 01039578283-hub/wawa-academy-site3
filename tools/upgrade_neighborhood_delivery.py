"""Bounded transforms of reviewed published HTML; originals and routes survive.

Use apply or verify. Keep the associated OUT before.zip and imported evidence.
Reject unexpected edits instead of replacing another author's work.
"""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote,quote,urlsplit
import argparse,copy,hashlib,json,re,sys,zipfile
from lxml import html,etree
import improve_neighborhood_pages as facts

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('C:/Users/1992k/Desktop/CodexData/outputs/site3-crawl-content-20261007')
DAY='2026-10-07'
load=lambda p:json.loads(p.read_text('utf-8-sig'))
digest=lambda b:hashlib.sha256(b).hexdigest()
E=lambda s:__import__('html').escape(str(s),quote=True)
U=lambda s:quote(s,safe='/#')
norm=lambda s:re.sub(r'\s+','',s)
FRAGMENTS=load(OUT/'jpeg-fragments.json')
MEDIA={p:g for g in FRAGMENTS.values() for p in g['originalPaths']}
ROWS={r['path'].strip('/')+'/index.html':r for r in facts.inventory()}
BRANCHES={facts.center_path(c).strip('/')+'/index.html':c for c in facts.FACTS['centers']}
TEACHERS=load(ROOT/'tools/data/teacher-finder/import.json')
TEACHER_BY_BRANCH={b['branchPath']:b for b in TEACHERS['branches'] if b.get('branchPath')}
BASE=load(OUT/'baseline-manifest.json')
CSS='assets/neighborhood-media-20261007.css';JS='assets/neighborhood-media-20261007.js'
VERSIONS={n:digest((ROOT/n).read_bytes())[:12] for n in [CSS,JS]}
PUBLIC=set(BASE['files'])|{CSS,JS}|{p['src'].lstrip('/') for g in FRAGMENTS.values() for p in g['parts']}
PAGE_TYPES={'WebPage','CollectionPage','Article','BlogPosting','AboutPage','ContactPage'}

def node(s):return html.fromstring(s)
def compact_text(n):return norm(n.text_content())
def content_container(section):
 nodes=section.xpath('./div[contains(concat(" ",normalize-space(@class)," ")," wrap ")]')
 return nodes[0] if nodes else section
def add_pairs(target,source):
 dl=target.find('.//dl')
 if dl is None:dl=etree.SubElement(target,'dl',{'class':'ns-fact-grid'})
 values={compact_text(n) for n in dl.xpath('.//dd')}
 for olddl in source.xpath('.//dl'):
  children=list(olddl)
  for i,child in enumerate(children):
   if child.tag!='dt' or i+1>=len(children) or children[i+1].tag!='dd':continue
   value=compact_text(children[i+1])
   if value and value not in values and value not in compact_text(target):
    dl.append(copy.deepcopy(child));dl.append(copy.deepcopy(children[i+1]));values.add(value)
def merge_references(main,summary):
 target=content_container(summary);removed=[];legacy=[];links={unquote(a.get('href','')) for a in target.xpath('.//a[@href]')}
 conditions=main.xpath('./section[@id="center-conditions"]');condition_text=compact_text(conditions[0]) if conditions else ''
 for section in list(main):
  ident=section.get('id')
  if section is summary or ident not in ['center-info','center-grades','grades']:continue
  legacy.extend(section.xpath('.//*[@id]/@id'));legacy.append(ident)
  add_pairs(target,section)
  for p in section.xpath('.//p[not(contains(@class,"eyebrow"))]'):
   text=compact_text(p)
   if not text or text in compact_text(target) or text in condition_text:continue
   # These repeat the summary's source, available grade range and separate
   # recruitment caveat; their information remains in the summary.
   if '수강학년은센터데이터엑셀' in text or '센터데이터엑셀기준' in text:continue
   if '실제주소는' in text and norm(ROWS.get(main.get('data-source-file'),{}).get('address','')) in text:continue
   target.append(copy.deepcopy(p))
  for table in section.xpath('.//table'):target.append(copy.deepcopy(table))
  for a in section.xpath('.//a[@href]'):
   href=unquote(a.get('href'))
   if href in links:continue
   group=target.xpath('./div[@class="cm-combined-links"]')
   group=group[0] if group else etree.SubElement(target,'div',{'class':'cm-combined-links'})
   link=copy.deepcopy(a);link.set('class','ns-link');group.append(link);links.add(href)
  main.remove(section);removed.append(ident)
 existing=set(main.xpath('.//*[@id]/@id'))
 for ident in legacy:
  if ident not in existing:target.append(node(f'<span id="{E(ident)}" class="cm-legacy-anchor"></span>'));existing.add(ident)
 return removed

def enrich_summary(summary,c,r):
 target=content_container(summary)
 pairs=[('찾아오는 길',c.get('locationGuide','')),('등록 학원명',c.get('registeredName','')),('등록번호',c.get('registrationNumber',''))]
 extra=node('<div><dl class="ns-fact-grid">'+''.join(f'<dt>{E(k)}</dt><dd>{E(v)}</dd>' for k,v in pairs if v)+'</dl></div>')
 add_pairs(target,extra)

def media_section(section,c):
 bodies=section.xpath('.//img[@data-role="body-image"]');maps=section.xpath('.//img[@data-role="map-image"]')
 assert len(bodies)==len(maps)==1
 image=bodies[0];original=image.get('src');g=MEDIA[unquote(original)]
 figure=image.xpath('ancestor::figure[1]')[0]
 for child in list(figure):figure.remove(child)
 block=etree.SubElement(figure,'div',{'class':'cm-segments','data-original-body':original})
 for index,p in enumerate(g['parts'],1):
  a=etree.SubElement(block,'a',{'href':original,'class':'cm-segment','data-cm-source':p['src'],'data-cm-whole':'body','aria-label':f'{image.get("alt")} {index}/{len(g["parts"])} 구간 확대','style':f'--cm-w:{p["width"]};--cm-h:{p["height"]}'})
  etree.SubElement(a,'img',{'src':p['src'],'alt':f'{image.get("alt")} · {index}/{len(g["parts"])} 구간','width':str(p['width']),'height':str(p['height']),'loading':'lazy','decoding':'async','data-role':'body-image','data-original-src':original,'data-source-top':str(p['top']),'data-source-bottom':str(p['bottom'])})
 etree.SubElement(figure,'figcaption',{'class':'cm-caption'}).text='본문 안내는 원래 가로 해상도를 유지한 연속 구간입니다. 이미지를 누르면 해당 구간을 확대할 수 있습니다.'
 image=maps[0];mapfigure=image.xpath('ancestor::figure[1]')[0]
 context=node('<div class="cm-map-context"><h3>지도에서 확인할 실제 방문 위치</h3>'+f'<p><strong>{E(c["displayName"])}</strong><br>{E(c["address"])}</p>'+ (f'<p>찾아오는 길: {E(c["locationGuide"])}</p>' if c.get('locationGuide') else '')+'<p>동네 이름은 상담 대상 생활권이며, 방문할 건물과 층은 실제 지점 주소로 확인해 주세요.</p><div class="cm-combined-links">'+facts.anchor(facts.center_path(c),'지점 주소·수강 안내')+'<a class="ns-link" href="tel:010-3957-8283">상담 전화 010-3957-8283</a></div></div>')
 mapfigure.addprevious(context)
 parent=image.getparent();index=parent.index(image);parent.remove(image)
 a=node(f'<a class="cm-image-link" href="{E(image.get("src"))}" data-cm-source="{E(image.get("src"))}" aria-label="{E(image.get("alt"))} 원본 크기로 확대"></a>');a.append(image);parent.insert(index,a)
 caption=mapfigure.find('figcaption')
 if caption is None:caption=etree.SubElement(mapfigure,'figcaption')
 caption.text=(caption.text or '찾아오시는 길')+' · 이미지를 누르면 확대할 수 있습니다.'
 return {'originalBody':original,'originalMap':image.get('src'),'bodyParts':len(g['parts'])}

def teacher_bridge(main,c):
 branch=TEACHER_BY_BRANCH.get(facts.center_path(c));bridges=main.xpath('./section[@data-teacher-bridge]')
 if not branch or not bridges:return 0
 target=bridges[0].xpath('./div')[0]
 if target.xpath('./ul[@data-cm-teachers]'):return len(target.xpath('./ul[@data-cm-teachers]/li'))
 links=''.join('<li>'+f'<a href="{E(U(branch["path"]))}#{E(t["id"])}">{E(t["name"])} 선생님 소개</a><span>{E(" · ".join(t["focus"]))}</span>'+'</li>' for t in branch['teachers'][:3])
 preview=node('<ul class="cm-teacher-preview" data-cm-teachers>'+links+'</ul>')
 target.insert(max(0,len(target)-1),preview)
 return min(3,len(branch['teachers']))

def curriculum_bridge(main,c,r):
 bridges=main.xpath('./section[@data-curriculum-bridge]')
 if not bridges:return []
 bridges=bridges[0].xpath('.//div[contains(@class,"cc-bridge-links")]')
 if not bridges:return []
 target=bridges[0];subjects=[r['subject']] if r and r.get('subject') else ['영어','수학'];stages=[r['stage']] if r and r.get('stage') else ['초등','중등','고등'];links=[]
 for stage in stages:
  for subject in subjects:
   grades=[v for v in facts.grades_for(r or {},c,subject) if v.startswith(stage[0])]
   if not grades:continue
   if stage=='고등':
    path=f'/공부커리큘럼/고등과목/{subject}/';assert path.strip('/')+'/index.html' in PUBLIC
    links.append((path,f'고등 {subject} 공부 범위·확인 과제'))
   else:
    for grade in grades:
     path=f'/공부커리큘럼/{stage}/{grade}/{subject}/';assert path.strip('/')+'/index.html' in PUBLIC
     links.append((path,f'{grade} {subject} 공부 범위·확인 과제'))
 if links:
  for child in list(target):target.remove(child)
  for path,label in links:target.append(node(f'<a href="{E(U(path))}">{E(label)}<span aria-hidden="true">→</span></a>'))
 return [p for p,_ in links]

def dialog():
 return '<dialog class="cm-dialog" data-cm-dialog aria-labelledby="cm-image-title"><div class="cm-dialog-header"><h2 id="cm-image-title" class="cm-dialog-title" data-cm-title>이미지 확대</h2><button type="button" data-cm-close>닫기</button></div><div class="cm-dialog-slot" data-cm-slot></div><div class="cm-dialog-tools"><button type="button" data-cm-zoom aria-pressed="false">100% 원본 크기</button><a data-cm-original target="_blank" rel="noopener noreferrer">원본 파일 열기</a></div></dialog>'

def transform(name,raw):
 r=ROWS.get(name);c=facts.CENTERS[tuple(r['centerKey'])] if r else BRANCHES[name]
 text=raw.decode('utf-8');doc=html.document_fromstring(raw);main=doc.find('.//main');before_ids=set(main.xpath('.//*[@id]/@id'))
 summary=main.xpath('./section[@id="local-summary"]')
 summary=summary[0] if summary else main.xpath('./section[@id="center-info"]')[0]
 main.set('data-source-file',name)
 enrich_summary(summary,c,r)
 merged=merge_references(main,summary) if r else []
 del main.attrib['data-source-file']
 sections=main.xpath('./section[@id="page-images"]');assert len(sections)==1
 images=sections[0];record=media_section(images,c);main.remove(images);main.insert(main.index(summary)+1,images)
 record.update(file=name,family=r['family'] if r else 'branch-center',mergedSections=merged,teacherPreviewRows=teacher_bridge(main,c),curriculumPaths=curriculum_bridge(main,c,r),center=c['routeName'],region=c['region'])
 for p in main.xpath('.//p[contains(@class,"cl-revised")]'):
  if p.text:p.text=re.sub(r'내용 수정 \d{4}\.\d{2}\.\d{2}','내용 수정 2026.10.07',p.text)
 assert before_ids<=set(main.xpath('.//*[@id]/@id'))
 rendered=html.tostring(main,encoding='unicode',method='html')
 text=re.sub(r'<main\b[^>]*>[\s\S]*?</main>',lambda _:rendered,text,count=1)
 text=re.sub(r'<body\b([^>]*)>',lambda m: '<body'+re.sub(r'class="([^"]*)"',lambda c:'class="'+c[1]+' crawl-updated"',m[1])+'>' if 'class=' in m[1] else '<body'+m[1]+' class="crawl-updated">',text,count=1)
 def update_schema(match):
  value=json.loads(match[2]);modified=False
  def walk(v):
   nonlocal modified
   if isinstance(v,list):
    for x in v:walk(x)
   elif isinstance(v,dict):
    types=v.get('@type',[]);types=[types] if isinstance(types,str) else types
    if set(types)&PAGE_TYPES:v['dateModified']=DAY;modified=True
    for x in v.values():walk(x)
  walk(value)
  return match[1]+(json.dumps(value,ensure_ascii=False,separators=(',',':')) if modified else match[2])+match[3]
 text=re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)([\s\S]*?)(</script>)',update_schema,text)
 text=text.replace('</head>',f'<link rel="stylesheet" href="/{CSS}?v={VERSIONS[CSS]}"></head>',1)
 text=text.replace('</body>',dialog()+f'<script defer src="/{JS}?v={VERSIONS[JS]}"></script></body>',1)
 return text.encode('utf-8'),record

def execute(action):
 assert load(OUT/'source-verification.json')['errors']==[]
 records=[];changed=[];errors=[]
 with zipfile.ZipFile(OUT/'before.zip') as z:
  for number,name in enumerate(sorted(set(ROWS)|set(BRANCHES)),1):
   before=z.read(name);after,record=transform(name,before);path=ROOT/name;current=path.read_bytes()
   if action=='apply':
    previous=load(OUT/'partial-apply-v1.json')
    assert current in [before,after] or digest(current)==previous.get(name),('Unreviewed change: preserve it',name)
    if current!=after:
     with path.open('r+b') as f:f.seek(0);f.write(after);f.truncate()
   else:
    if current!=after:errors.append(name)
   records.append(record);changed.append(name)
   if number%2000==0:print(action,'neighborhood/branch pages',number,flush=True)
 report={'changedHtmlPages':len(changed),'neighborhoodPages':len(ROWS),'branchCenterPages':len(BRANCHES),'families':dict(Counter(r['family'] for r in records)),'mergedReferenceSections':sum(len(r['mergedSections']) for r in records),'teacherPreviewPages':sum(r['teacherPreviewRows']>0 for r in records),'newPublicAssets':sorted(PUBLIC-set(BASE['files'])),'checks':records,'errors':errors,'sourceBackup':'before.zip','day':DAY}
 (OUT/('implementation.json' if action=='apply' else 'transformation-verification.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
 assert not errors,errors[:3]
 print(json.dumps({k:v for k,v in report.items() if k not in ['checks','newPublicAssets']},ensure_ascii=False),flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['apply','verify']);execute(parser.parse_args().action)
