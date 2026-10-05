"""Incremental 30-article expansion from reviewed private inputs.

Do not rerun the original education generator against its historical baseline.
This step preserves current curriculum, homepage modules, routes and RSS IDs.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote,urlsplit
from email.utils import format_datetime
import json,re,datetime,hashlib,sys,zipfile
from lxml import html,etree
import build_education_info as legacy
from seo_feed_content import body,identity
from improve_neighborhood_pages import inventory
ROOT=legacy.ROOT
OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-education-expansion-20261006')
DATE='2026-10-06'
load=legacy.load;dump=legacy.dump;write=legacy.write;digest=legacy.digest;U=legacy.U;E=legacy.E;url=legacy.url

def related(path,context,rows):
    newer=rows[30:]
    if context and context.get('subject')=='영어':pool=[r for r in newer if r['number'] in [34,45,49,59]]
    elif context and context.get('subject')=='수학':pool=[r for r in newer if r['number'] in [31,35,44,51]]
    elif context and context.get('stage')=='초등':pool=[r for r in newer if r['number'] in [35,52,54,56]]
    else:pool=newer
    slot=int(hashlib.sha256(path.encode()).hexdigest()[:8],16)%len(pool)
    chosen=pool[slot]
    old=legacy.recommendation(path,context,rows[:30])[0]
    return old,chosen

def bridge(path,context,rows):
    selected=related(path,context,rows)
    label=context['neighborhood']+'에서 공부와 수업을 살펴볼 때' if context else '학생과 학부모가 함께 확인하는 교육정보'
    return '<section class="ei-bridge" data-education-bridge><div class="ei-bridge-wrap"><p class="ei-bridge-label">'+E(label)+'</p><h2>함께 읽는 교육정보</h2><p>현재 학년과 과목의 고민에 맞춰 공부 방법과 수업 점검 질문을 살펴보세요.</p><div class="ei-bridge-links">'+''.join('<a href="'+U(r['path'])+'">'+E(r['title'])+'<span aria-hidden="true">→</span></a>' for r in selected)+'</div><a class="ei-bridge-all" href="/교육정보/">교육정보 60개 전체 보기 →</a></div></section>'

def new_graph(text,callback):
    def change(m):
        data=json.loads(m.group(2));callback(data)
        return m.group(1)+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+m.group(3)
    return re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',change,text,flags=re.S)

def homepage(text,rows):
    featured=[rows[i-1] for i in [48,45,54]]
    section='<section class="ei-bridge" id="new-education" data-education-expansion-home><div class="ei-bridge-wrap"><p class="ei-bridge-label">새로 더한 교육정보 30편</p><h2>지금 필요한 공부 설명을 더 넓게 찾아보세요</h2><p>과학 탐구 정리, 영어 서술형, 부모의 학습 지원까지. 기존 30편과 함께 60편의 교육정보를 읽을 수 있습니다.</p><div class="ei-bridge-links">'+''.join('<a href="'+U(r['path'])+'">'+E(r['title'])+'<span aria-hidden="true">→</span></a>' for r in featured)+'</div><a class="ei-bridge-all" href="/교육정보/#articles">교육정보 60편 찾아보기 →</a></div></section>'
    text,count=re.subn(r'(<section\b[^>]*id="learning-library"[^>]*>)',lambda m:section+m.group(1),text,count=1);assert count==1
    for old in ['학생·학부모를 위한 30개 글','도움이 되는 30개 글']:assert old in text;text=text.replace(old,old.replace('30','60'))
    def update(data):
        graph=data['@graph'];page=next(g for g in graph if g.get('@id')==url('/')+'#webpage')
        page['dateModified']=DATE
        page['hasPart'].append({'@type':'WebPageElement','@id':url('/')+'#new-education','name':'새로 더한 교육정보','url':url('/')+'#new-education','mainEntity':{'@id':url('/')+'#new-education-list'}})
        graph.append({'@type':'ItemList','@id':url('/')+'#new-education-list','numberOfItems':3,'itemListElement':[{'@type':'ListItem','position':i,'name':r['title'],'url':url(r['path'])} for i,r in enumerate(featured,1)]})
    return new_graph(text,update)

def main():
    baseline=load(OUT/'baseline-manifest.json');data=load(OUT/'expanded-content.json');rows=data['articles'];assert len(rows)==60
    stamp=load(OUT/'publication.json')['publishedAt'];legacy.DATE=DATE
    # Keep legacy guide lookup tied to its original reviewed route inventory only.
    originals=load(OUT/'baseline-content.json')['articles'];assert rows[:30]==originals
    contexts={r['path']:r for r in inventory()};changed=[];new=set()
    # Every mutation is replayed against the complete current-release backup.
    with zipfile.ZipFile(OUT/'public-before.zip') as backup:
        def patch(name):
            old=backup.read(name).decode('utf-8-sig');text=old;path='/' if name=='index.html' else '/'+name[:-10]
            if name=='교육정보/index.html':return
            if name=='index.html':text=homepage(text,rows)
            elif 'data-education-bridge' in text:
                text,n=re.subn(r'<section\b[^>]*data-education-bridge\b[^>]*>.*?</section>',lambda m:bridge(path,contexts.get(path),rows),text,flags=re.S);assert n==1,name
            elif name.startswith('교육정보/'):
                r=next(o for o in originals if o['path']==path);pool=[o for o in rows[30:] if o['category']==r['category']] or rows[30:]
                slot=int(digest(path.encode())[:8],16)%len(pool);selected=pool[slot:slot+2] or pool[:2]
                extra='<section data-education-expansion-related><h2>이 주제의 새 교육정보</h2><div class="ei-related">'+''.join('<a href="'+U(o['path'])+'">'+E(o['title'])+'<span aria-hidden="true">→</span></a>' for o in selected)+'</div></section>'
                assert '<section class="ei-locator" id="local-info">' in text
                text=text.replace('<section class="ei-locator" id="local-info">',extra+'<section class="ei-locator" id="local-info">',1)
            else:
                assert text.count('</main>')==1,name
                text=text.replace('</main>',bridge(path,contexts.get(path),rows)+'</main>',1)
                if '/assets/education-info.css' not in text:text=text.replace('</head>',legacy.CSS+'</head>',1)
            if text!=old:
                text=legacy.patch_dates(text);write(ROOT/name,text);changed.append(name)
        names=[n for n in baseline['files'] if n.endswith('.html')]
        # Sequential reads from a ZIP prevent shared-file handle contention on Windows.
        for i,name in enumerate(names,1):
            patch(name)
            if i%2000==0:print('Updated contextual education access',i,flush=True)
    ordered=dict(data,articles=rows[30:]+rows[:30])
    path,summary,text=legacy.listing(ordered,stamp)
    for a,b in [('30개 글','60개 글'),('<strong>30</strong>','<strong>60</strong>'),('지금 필요한 글 한 편','새로 추가한 교육정보부터 살펴보세요')]:text=text.replace(a,b)
    def hub_schema(d):
        for g in d['@graph']:
            if g.get('@type')=='ItemList':g['numberOfItems']=60
            if g.get('@type')=='CollectionPage':g['datePublished']=load(OUT/'baseline-content.json')['articles'][0].get('publishedAt') or '2026-10-03'
    text=new_graph(text,hub_schema)
    # Preserve the actual hub publication date from its current production graph.
    with zipfile.ZipFile(OUT/'public-before.zip') as z:
        oldhub=html.fromstring(z.read('교육정보/index.html'));g=json.loads(oldhub.xpath('//script[@type="application/ld+json"]/text()')[0])['@graph']
        pub=next(v['datePublished'] for v in g if v.get('@type')=='CollectionPage')
    text=new_graph(text,lambda d:next(v for v in d['@graph'] if v.get('@type')=='CollectionPage').update(datePublished=pub))
    text=text.replace('30개 글에서','60개 글에서')
    # Build all 30 articles from the same reviewed content that supplies metadata/FAQ.
    pages=[(path,summary,text)]
    for r in rows[30:]:
        path,summary,text=legacy.article(r,data,r['publishedAt'])
        text=text.replace('<div class="ei-intro">','<p class="ei-small">사진은 학습 상황을 설명하기 위한 참고 이미지입니다.</p><div class="ei-intro">',1)
        pages.append((path,summary,text))
    descriptions=load(ROOT/'seo-descriptions.json')
    for path,summary,text in pages:
        text=text.replace('<a href="/선생님찾기/">선생님찾기</a>','<a href="/공부커리큘럼/">공부커리큘럼</a><a href="/선생님찾기/">선생님찾기</a>',1)
        text=text.replace('<a class="ei-text-link" href="/선생님찾기/">','<a class="ei-text-link" href="/공부커리큘럼/">학년·과목별 공부 범위 보기 →</a><a class="ei-text-link" href="/선생님찾기/">')
        name=path.strip('/')+'/index.html';write(ROOT/name,text)
        if name in baseline['files']:changed.append(name)
        else:new.add(name)
        descriptions['pages'][path.rstrip('/')]=dict(description=summary,sources=[summary])
    dump(ROOT/'seo-descriptions.json',descriptions)
    for r in rows[30:]:
        for im in r['images']:
            raw=(legacy.SOURCE/'1 이미지'/im['source']).read_bytes();assert digest(raw)==im['sha256']
            write(ROOT/im['path'].lstrip('/'),raw);new.add(im['path'].lstrip('/'))
    sitemap=(ROOT/'sitemap.xml').read_text('utf-8');tree=etree.fromstring(sitemap.encode())
    existing={unquote(urlsplit(n.text).path):n.getparent() for n in tree.xpath('//*[local-name()="loc"]')}
    for name in changed:
        path='/' if name=='index.html' else '/'+name[:-10]
        existing[path].find('{*}lastmod').text=DATE
    ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
    for r in rows[30:]:
        assert r['path'] not in existing
        n=etree.SubElement(tree,ns+'url');etree.SubElement(n,ns+'loc').text=url(r['path']);etree.SubElement(n,ns+'lastmod').text=DATE
    write(ROOT/'sitemap.xml',etree.tostring(tree,encoding='UTF-8',xml_declaration=True,pretty_print=True))
    feed=etree.fromstring((ROOT/'rss.xml').read_bytes(),etree.XMLParser(resolve_entities=False,no_network=True,remove_blank_text=True,strip_cdata=False));channel=feed.find('channel')
    identities=[identity(item) for item in channel.findall('item')];assert len(identities)==135
    for item in channel.findall('item'):
        canonical=item.findtext('link');path=unquote(urlsplit(canonical).path);name='index.html' if path=='/' else path.strip('/')+'/index.html'
        content,_=body(html.document_fromstring((ROOT/name).read_bytes()),canonical);item.find('description').text=etree.CDATA(content)
    for r in rows[30:]:
        canonical=url(r['path']);item=etree.SubElement(channel,'item')
        for key,value in [('title',r['title']),('link',canonical),('guid',canonical),('pubDate',format_datetime(datetime.datetime.fromisoformat(r['publishedAt'])))]:
            n=etree.SubElement(item,key);n.text=value
            if key=='guid':n.set('isPermaLink','true')
        content,_=body(html.document_fromstring((ROOT/r['path'].strip('/')/'index.html').read_bytes()),canonical);etree.SubElement(item,'description').text=etree.CDATA(content)
    channel.find('lastBuildDate').text=format_datetime(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(microsecond=0))
    assert [identity(item) for item in channel.findall('item')][:135]==identities
    write(ROOT/'rss.xml',etree.tostring(feed,encoding='UTF-8',xml_declaration=True,pretty_print=True))
    names=sorted(set(baseline['files'])|new);textnames=set(baseline['textSha256'])|{n for n in new if n.endswith('.html')}
    def hashes(n):
        b=(ROOT/n).read_bytes();return n,digest(b),digest(b.decode('utf-8').replace('\r\n','\n').encode()) if n in textnames else None
    with ThreadPoolExecutor(max_workers=12) as pool:values=list(pool.map(hashes,names))
    manifest=load(ROOT/'release-public-manifest.json');manifest['files']={n:h for n,h,_ in values};manifest['textSha256']={n:h for n,_,h in values if h};manifest['sitemapPages']=sum(n.endswith('.html') for n in names);manifest['createdAt']=stamp;dump(ROOT/'release-public-manifest.json',manifest)
    write(ROOT/'tools/data/education-info/content.json',json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    dump(OUT/'implementation.json',dict(newArticles=30,totalArticles=60,newPublicFiles=sorted(new),modifiedHtml=sorted(changed),publicFiles=len(names),htmlPages=manifest['sitemapPages'],photos=90,rssItems=165,oldRssIdentitiesPreserved=135))
    print(json.dumps({'publicFiles':len(names),'htmlPages':manifest['sitemapPages'],'oldPagesWithUpdatedAccess':len(changed),'newArticles':30,'photos':90,'rssItems':165},ensure_ascii=False))
if __name__=='__main__':main()
