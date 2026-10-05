"""Complete current-release preservation, article facts and link validation."""
from collections import Counter,deque
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urljoin,unquote
import copy,json,re,zipfile,sys,hashlib
from lxml import html,etree
import build_education_expansion as impl
from audit_neighborhood_phase6 import state
ROOT,OUT=impl.ROOT,impl.OUT
def normalize(raw,name,base=False):
    doc=html.document_fromstring(raw)
    for n in doc.xpath('//*[@data-education-bridge or @data-education-expansion-related or @data-education-expansion-home]'):n.drop_tree()
    # Curriculum pages gained the same stylesheet used by existing article bridges.
    if name.startswith('공부커리큘럼/'):
        for n in doc.xpath('//link[@data-education-style]'):n.drop_tree()
    for n in doc.xpath('//script[@type="application/ld+json"]'):
        data=json.loads(n.text)
        def visit(v):
            if isinstance(v,list):
                for t in v:visit(t)
            elif isinstance(v,dict):
                if 'dateModified' in v:v['dateModified']='DATE'
                for t in v.values():visit(t)
        visit(data)
        if name=='index.html':
            graph=data['@graph'];graph[:]=[g for g in graph if g.get('@id')!=impl.url('/')+'#new-education-list']
            page=next(g for g in graph if g.get('@id')==impl.url('/')+'#webpage')
            page['hasPart']=[g for g in page['hasPart'] if g.get('@id')!=impl.url('/')+'#new-education']
        n.text=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    for n in doc.iter():
        if n.text:
            n.text=re.sub(r'내용 수정 2026\.\d{2}\.\d{2}','내용 수정 DATE',n.text)
            if name=='index.html':
                for phrase in ['학생·학부모를 위한 60개 글','도움이 되는 60개 글']:n.text=n.text.replace(phrase,phrase.replace('60','30'))
    return html.tostring(doc,encoding='utf-8').replace(b'\r\n',b'\n')
def main():
    base=impl.load(OUT/'baseline-manifest.json');m=impl.load(ROOT/'release-public-manifest.json');data=impl.load(OUT/'expanded-content.json');newrows=data['articles'][30:];rows={r['path'].strip('/')+'/index.html':r for r in newrows};report=impl.load(OUT/'implementation.json')
    assert set(m['files'])-set(base['files'])==set(report['newPublicFiles'])
    assert m['sitemapPages']==8814 and len(m['files'])==11286
    assert data['articles'][:30]==impl.load(OUT/'baseline-content.json')['articles']
    backup=zipfile.ZipFile(OUT/'public-before.zip');assert backup.testzip() is None
    local=set(m['files']);incoming=Counter();links=0;fragments=0;images=0;oldchecked=0;pagegraph={};idcache={}
    for i,(name,h) in enumerate(m['files'].items(),1):
        raw=(ROOT/name).read_bytes();assert impl.digest(raw)==h,name
        if name in m['textSha256']:assert impl.digest(raw.decode('utf-8').replace('\r\n','\n').encode())==m['textSha256'][name],name
        if not name.endswith('.html'):
            if name in base['files'] and name not in ['rss.xml','sitemap.xml']:assert h==base['files'][name],name
            continue
        doc=html.document_fromstring(raw);ids=doc.xpath('//*[@id]/@id');assert len(ids)==len(set(ids)),name;idcache[name]=set(ids)
        assert len(doc.xpath('//h1'))==1 and len(doc.xpath('//main'))==1,name
        canonical=doc.xpath('//link[@rel="canonical"]/@href');assert len(canonical)==1 and unquote(canonical[0])==unquote(impl.url('/' if name=='index.html' else '/'+name[:-10])),name
        if name in base['files'] and name!='교육정보/index.html':
            assert normalize(raw,name)==normalize(backup.read(name),name,True),name;oldchecked+=1
            if name.startswith('교육정보/'):assert doc.xpath('//*[@data-education-expansion-related]'),name
            elif name!='index.html':assert len(doc.xpath('//*[@data-education-bridge]'))==1,name
        if name in rows:
            r=rows[name];article=doc.xpath('//*[@data-education-article]')[0];text=' '.join(article.itertext())
            for paragraph in r['intro']+[p for s in r['sections'] for p in s['paragraphs']]+r['checks']+[v for pair in r['faq'] for v in pair]+[v for row in r['table']['rows'] for v in row]:assert paragraph in text,(name,paragraph)
            assert doc.xpath('string(//h1)')==r['title'];desc=doc.xpath('//meta[@name="description"]/@content')[0]
            assert desc==r['summary'] and len(desc)<=80 and desc.endswith('.')
            assert doc.xpath('//meta[@property="og:description"]/@content')==doc.xpath('//meta[@name="twitter:description"]/@content')==[desc]
            graph=json.loads(doc.xpath('//script[@type="application/ld+json"]/text()')[0])['@graph']
            faq=next(g for g in graph if g['@type']=='FAQPage')['mainEntity'];assert [(q['name'],q['acceptedAnswer']['text']) for q in faq]==[tuple(q) for q in r['faq']]
            schema=next(g for g in graph if g['@type']=='Article');assert schema['headline']==r['title'] and schema['datePublished']==r['publishedAt'] and schema['dateModified']==impl.DATE
            assert schema['citation']==[data['sources'][s]['url'] for s in r['sources']]
            photos=article.xpath('.//figure/img');assert len(photos)==3 and len({p.get('src') for p in photos})==3
            for j,(node,im) in enumerate(zip(photos,r['images'])):
                assert node.get('src')==im['path'] and node.get('alt')==im['alt'] and node.get('width')==str(im['width']) and node.get('height')==str(im['height'])
                assert node.get('loading')=='lazy' and node.getparent().getprevious().get('id')=='section-'+str([1,3,5][j])
                assert (ROOT/im['path'].lstrip('/')).read_bytes()==(impl.legacy.SOURCE/'1 이미지'/im['source']).read_bytes();images+=1
            manuscript=impl.legacy.SOURCE/r['originalFolder']/'원고.txt';assert impl.digest(manuscript.read_bytes())==r['originalSha256']
            assert doc.xpath('//a[@href="/전국센터/"]') and doc.xpath('//a[@href="/지점안내/"]') and doc.xpath('//a[@href="/공부커리큘럼/"]')
        edges=set()
        for n in doc.xpath('//a[@href] | //img[@src] | //link[@href] | //script[@src]'):
            value=n.get('href') or n.get('src');target=urlsplit(urljoin(canonical[0],value))
            if target.netloc!=urlsplit(impl.legacy.DOMAIN).netloc:continue
            path=unquote(target.path);dest=path.lstrip('/')+('index.html' if path.endswith('/') else '')
            assert dest in local,(name,dest);links+=1
            if n.tag=='a':incoming[dest]+=1;edges.add(dest)
            if target.fragment:
                if dest not in idcache:idcache[dest]=set(html.fromstring((ROOT/dest).read_bytes()).xpath('//*[@id]/@id'))
                assert unquote(target.fragment) in idcache[dest],(name,value);fragments+=1
        pagegraph[name]=edges
        if i%2000==0:print('Verified all page content and links',i,flush=True)
    hub=html.fromstring((ROOT/'교육정보/index.html').read_bytes());cards=hub.xpath('//*[@data-education-list]//*[@data-education-card]')
    assert len(cards)==60 and len({c.xpath('.//h3/a/@href')[0] for c in cards})==60
    assert {unquote(c.xpath('.//h3/a/@href')[0]) for c in cards}=={r['path'] for r in data['articles']}
    g=json.loads(hub.xpath('//script[@type="application/ld+json"]/text()')[0])['@graph'];listing=next(v for v in g if v['@type']=='ItemList');assert listing['numberOfItems']==len(listing['itemListElement'])==60
    oldfeed=etree.fromstring(backup.read('rss.xml'));feed=etree.fromstring((ROOT/'rss.xml').read_bytes());assert len(feed.findall('channel/item'))==165
    assert [impl.identity(i) for i in oldfeed.findall('channel/item')]==[impl.identity(i) for i in feed.findall('channel/item')][:135]
    oldlocs=set(etree.fromstring(backup.read('sitemap.xml')).xpath('//*[local-name()="loc"]/text()'));locs=etree.fromstring((ROOT/'sitemap.xml').read_bytes()).xpath('//*[local-name()="loc"]/text()');assert len(locs)==len(set(locs))==8814 and oldlocs<=set(locs)
    depths={'index.html':0};pending=deque(['index.html'])
    while pending:
        name=pending.popleft()
        for dest in pagegraph[name]:
            if dest.endswith('.html') and dest not in depths:depths[dest]=depths[name]+1;pending.append(dest)
    assert all(depths[n]<=2 and incoming[n]>0 for n in rows)
    assert state()==impl.load(OUT/'authoring-before.json')
    result=dict(publicFiles=len(local),htmlPages=8814,newArticles=30,totalEducationArticles=60,oldPagesPreservedOutsideScopedLinks=oldchecked,photosVerified=images,internalResourcesAndLinksVerified=links,fragmentLinksVerified=fragments,maxNewArticleClicksFromHome=max(depths[n] for n in rows),oldRssIdentitiesPreserved=135,rssItems=165,authoringPreserved=True,errors=[])
    impl.dump(OUT/'source-audit.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
