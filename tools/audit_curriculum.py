"""Check every current public file and every new curriculum link and source row."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from urllib.parse import urljoin,urlsplit,unquote,parse_qs
import json,re,copy,zipfile,openpyxl
from lxml import html,etree
import build_curriculum as impl
from audit_neighborhood_phase6 import state

SOURCE=impl.Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\센터정보\초중고_학년과목별_공부커리큘럼_기초표준심화.xlsx')

def normalized(doc):
    doc=copy.deepcopy(doc)
    for n in doc.xpath('//*[@data-curriculum-nav or @data-curriculum-style or @data-curriculum-bridge]'):n.drop_tree()
    for n in doc.xpath('//script[@type="application/ld+json"]'):
        data=json.loads(n.text)
        def walk(v):
            if isinstance(v,list):
                for t in v:walk(t)
            elif isinstance(v,dict):
                if 'dateModified' in v:v['dateModified']='MODIFICATION_DATE'
                for t in v.values():walk(t)
        walk(data);n.text=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    for n in doc.xpath('//*[text()[contains(.,"내용 수정 2026.")]]'):
        if n.text:n.text=re.sub(r'내용 수정 2026\.\d{2}\.\d{2}','내용 수정 MODIFICATION_DATE',n.text)
    return html.tostring(doc,encoding='utf-8').replace(b'\r\n',b'\n')

def audit():
    root,out=impl.ROOT,impl.OUT;base=impl.load(out/'baseline-manifest.json');manifest=impl.load(root/'release-public-manifest.json');report=impl.load(out/'implementation.json');data=impl.load(impl.DATA)
    assert impl.digest(SOURCE.read_bytes())==data['sha256']
    workbook=openpyxl.load_workbook(SOURCE,read_only=True,data_only=True)
    workbook_values={sheet.title:list(sheet.values) for sheet in workbook}
    for title,s in data['sheets'].items():
        for row in s['rows']:
            actual=[v.isoformat() if hasattr(v,'isoformat') else v for v in workbook_values[title][row['row']-1]];assert actual==row['values'],(title,row['row'])
    new=set(manifest['files'])-set(base['files']);assert new==set(report['newPublicFiles']) and len(new)==91
    assert len(manifest['files'])==11162 and manifest['sitemapPages']==8784
    subjects={impl.subject_path(r[0],r[1]).strip('/')+'/index.html':r for sheet in ['초등과목','중등과목','고등과목'] for r in impl.rows(sheet)}
    choices=impl.rows('고등선택과목');counts=Counter();incoming=Counter();links=0;fragments=0;level_coverage=set();titles=[];descriptions=[]
    docs={}
    with zipfile.ZipFile(out/'curriculum-before.zip') as backup:
        assert len(backup.namelist())==len(base['files'])
        def read(name):
            raw=(root/name).read_bytes();assert impl.digest(raw)==manifest['files'][name],name
            if name in manifest['textSha256']:assert impl.digest(raw.decode('utf-8').replace('\r\n','\n').encode())==manifest['textSha256'][name],name
            if not name.endswith('.html'):
                if name in base['files'] and name not in ['rss.xml','sitemap.xml']:assert manifest['files'][name]==base['files'][name],name
                return name,None
            return name,html.document_fromstring(raw)
        with ThreadPoolExecutor(max_workers=12) as pool:
            for i,(name,doc) in enumerate(pool.map(read,manifest['files']),1):
                if doc is not None:docs[name]=doc
                if i%2500==0:print('Checked curriculum publication hashes',i,flush=True)
        for name,doc in docs.items():
            canonical=doc.xpath('//link[@rel="canonical"]/@href')[0]
            if name in base['files']:
                old=html.document_fromstring(backup.read(name));assert normalized(doc)==normalized(old),name
                assert len(doc.xpath('//header//a[@data-curriculum-nav]'))==1,name
                bridge_count=len(doc.xpath('//*[@data-curriculum-bridge]'));assert bridge_count==int(name in report['bridgeHtml']),name
                counts['legacyNav']+=1;counts['legacyBridge']+=bridge_count
                nodes=doc.xpath('//a[@data-curriculum-nav] | //*[@data-curriculum-bridge]//a | //link[@data-curriculum-style]')
            else:
                assert len(doc.xpath('//h1'))==1 and len(doc.xpath('//main'))==1,name
                title=doc.xpath('string(//h1)');titles.append(title)
                description=doc.xpath('//meta[@name="description"]/@content')[0];descriptions.append(description)
                assert description.endswith('.') and len(description)<=80,name
                assert doc.xpath('//meta[@property="og:description"]/@content')==doc.xpath('//meta[@name="twitter:description"]/@content')==[description]
                graph=json.loads(doc.xpath('//script[@type="application/ld+json"]')[0].text)['@graph'];assert graph[0]['description']==description
                assert canonical==impl.url('/'+name.removesuffix('index.html')),name
                ids=doc.xpath('//*[@id]/@id');assert len(ids)==len(set(ids)),name
                nodes=doc.xpath('//a[@href] | //link[@href] | //script[@src] | //img[@src]')
                text=' '.join(doc.xpath('//main')[0].itertext());assert '편집 원칙' not in text
                if name in subjects:
                    r=subjects[name];g,s=r[:2];assert title==impl.title_for(r)
                    for index in [2,3,4,6,7,8]:assert r[index] in text,(name,index)
                    for step in r[5].split('→'):assert step.strip() in text,(name,step)
                    low=g in ['초1','초2'] and s in ['영어','사회','과학']
                    if low:
                        assert not doc.xpath('//*[@class="cc-level"]'),name
                        assert '정규 교과' in text or '통합교과' in text
                    else:
                        levels=doc.xpath('//*[@class="cc-level"]');assert len(levels)==3,name
                        source_levels=[v for v in data['sheets']['반별운영']['rows'] if v['values'][0]=={'초':'초등학생','중':'중학생','고':'고등학생'}[g[0]] and v['values'][1]==('사회' if s=='역사' else s)]
                        for node,row in zip(levels,source_levels):
                            v=row['values'];content=' '.join(node.itertext())
                            for index in [3,5,6,7]:assert v[index] in content,(name,index)
                            for step in v[4].split('→'):assert step.strip() in content
                            level_coverage.add(row['row'])
                        assert '실제 개설 반을 뜻하지 않습니다' in text
                    counts['subjects']+=1
                if name.startswith('공부커리큘럼/고등과목/'):
                    path='/'+name.removesuffix('index.html');s=path.strip('/').split('/')[2] if len(path.strip('/').split('/'))>2 else None
                    selected=[r for r in choices if not s or r[0]==s]
                    nodes_choices=doc.xpath('//*[@class="cc-choice"]');assert len(nodes_choices)==len(selected),name
                    for node,row in zip(nodes_choices,selected):
                        content=' '.join(node.itertext())
                        for v in row[:7]:assert v in content,(name,v)
                    counts['courseEntries']+=len(nodes_choices)
            for node in nodes:
                target=urlsplit(urljoin(canonical,node.get('href') or node.get('src')))
                if target.netloc!=urlsplit(impl.DOMAIN).netloc:continue
                path=unquote(target.path);dest=path.lstrip('/')+('index.html' if path.endswith('/') else '')
                assert dest in manifest['files'],(name,dest);incoming[dest]+=1;links+=1
                if target.fragment:
                    dest_doc=docs[dest];assert dest_doc.xpath('//*[@id=$id]',id=unquote(target.fragment)),(name,target.fragment);fragments+=1
                if target.query and path.startswith(impl.BASE):
                    assert parse_qs(target.query).get('subject',[None])[0] in impl.SUBJECTS,(name,target.query)
                    assert docs[dest].xpath('//*[@data-curriculum-filter]'),(name,dest)
        original=etree.fromstring(backup.read('rss.xml'));feed=etree.fromstring((root/'rss.xml').read_bytes())
        assert [impl.identity(it) for it in original.findall('channel/item')]==[impl.identity(it) for it in feed.findall('channel/item')][:129]
        assert len(feed.findall('channel/item'))==135
        old_locs=etree.fromstring(backup.read('sitemap.xml')).xpath('//*[local-name()="loc"]/text()');locs=etree.fromstring((root/'sitemap.xml').read_bytes()).xpath('//*[local-name()="loc"]/text()')
        assert locs[:len(old_locs)]==old_locs and len(locs)==len(set(locs))==8784
    assert len(set(titles))==89 and len(set(descriptions))==89
    assert counts['subjects']==66 and len(level_coverage)==45 and counts['courseEntries']==58
    assert counts['legacyNav']==8695 and counts['legacyBridge']==8375
    assert all(incoming[n]>0 for n in new if n.endswith('.html'))
    assert state()==impl.load(out/'authoring-before.json')
    result={'publicFiles':11162,'sitemapPages':8784,'newHtmlPages':89,'oldHtmlPreserved':8695,'gradeSubjectRowsVerified':66,'learningLevelRowsCovered':45,'highCourseRowsVerified':29,'menuLinksVerified':counts['legacyNav'],'contextualBridgePages':counts['legacyBridge'],'internalLinksVerified':links,'fragmentLinksVerified':fragments,'rssItems':135,'oldRssIdentitiesPreserved':129,'originalWorkbookUnchanged':True,'authoringPreserved':True,'errors':[]}
    impl.dump(out/'source-audit.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':audit()
