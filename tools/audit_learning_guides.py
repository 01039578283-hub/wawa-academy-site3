"""Whole-release preservation and every learning-guide page/link verification."""
import copy, hashlib, json, re, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote, quote
from lxml import html, etree
from build_learning_guides import ROOT, OUT, DATE, DOMAIN, TOPS, CATEGORIES, articles, digest, dump
from review_seo_feeds import TRACKER, nodes
from seo_feed_content import body, identity, spaced

def audit():
    built=ROOT/'.public-release'
    manifest=json.loads((ROOT/'release-public-manifest.json').read_text('utf-8-sig'))
    baseline=json.loads((OUT/'baseline-manifest.json').read_text('utf-8-sig'))
    expected=set(manifest['files']);actual={p.relative_to(built).as_posix() for p in built.rglob('*') if p.is_file()}
    assert actual==expected,(sorted(actual-expected),sorted(expected-actual))
    assert set(baseline['files'])<=expected
    assert len(expected)==10729 and sum(n.endswith('.html') for n in expected)==8458
    changed=[];pages=[];assets=[]
    def compare(name):
        raw=(ROOT/name).read_bytes();result=(built/name).read_bytes();h=digest(raw)
        assert h==manifest['files'][name],name
        if name.endswith('.html'):
            text=raw.decode('utf-8');count=text.count('data-site="wawa-04"');assert count in [0,1]
            target=text if count else re.sub(r'</head\s*>',lambda m:TRACKER+m.group(),text,count=1,flags=re.I)
            assert result.decode('utf-8').replace('\r\n','\n')==target.replace('\r\n','\n'),name
            doc=html.document_fromstring(result)
            canonical=doc.xpath('//link[@rel="canonical"]/@href')[0]
            route='/' if name=='index.html' else '/'+name.removesuffix('index.html')
            record={'file':name,'path':quote(route,safe='/'),'canonical':canonical,'h1':spaced(' '.join(doc.xpath('//h1')[0].itertext())),'builtSha256':digest(result),'builtTextSha256':digest(result.decode('utf-8').replace('\r\n','\n').encode('utf-8')),'sourceSha256':h,'errors':[]}
            kind='pages'
        else:
            assert result==raw,name
            record={'file':name,'path':quote('/'+name,safe='/'),'builtSha256':digest(result)}
            if name in manifest.get('textSha256',{}):record['builtTextSha256']=digest(result.decode('utf-8').replace('\r\n','\n').encode('utf-8'))
            kind='assets'
        return name,h,kind,record
    with ThreadPoolExecutor(max_workers=16) as pool:
        for name,h,kind,record in pool.map(compare,sorted(expected)):
            if name in baseline['files'] and baseline['files'][name]!=h:changed.append(name)
            (pages if kind=='pages' else assets).append(record)
    assert set(changed)==set(TOPS)|{'sitemap.xml','rss.xml'},changed
    print('All public files and original content preserved:',len(expected),flush=True)
    new=[r for r in pages if r['file'].startswith('학습가이드/')]; assert len(new)==55
    rows=articles();by_slug={r['slug']:r for r in rows};docs={};links=0;fragments=0;visible_chars=[]
    def document(name):
        if name not in docs:docs[name]=html.document_fromstring((built/name).read_bytes())
        return docs[name]
    descriptions=json.loads((ROOT/'seo-descriptions.json').read_text('utf-8-sig'))['pages']
    forbidden=['편집 원칙','편집원칙','편집 기준','편집 정책','editorial-policy','AggregateRating','Review','성적 보장']
    for record in new:
        name=record['file'];doc=document(name);main=doc.xpath('//main');assert len(main)==1
        assert len(doc.xpath('//h1'))==1
        ids=doc.xpath('//*[@id]/@id');assert len(ids)==len(set(ids)),name
        description=doc.xpath('//meta[@name="description"]/@content');assert len(description)==1 and len(description[0])<=80 and description[0].endswith('.')
        assert doc.xpath('//meta[@property="og:description"]/@content')==description==doc.xpath('//meta[@name="twitter:description"]/@content')
        key=unquote(urlsplit(record['canonical']).path).rstrip('/')
        assert descriptions[key]['description']==description[0]
        schemas=[n for s in doc.xpath('//script[@type="application/ld+json"]') for n in nodes(json.loads(s.text))]
        assert all(n['dateModified']==DATE for n in schemas if n.get('@type') in ['WebPage','CollectionPage','Article'])
        assert all(n['description']==description[0] for n in schemas if n.get('@type') in ['WebPage','CollectionPage','Article'])
        raw=(built/name).read_text('utf-8');assert all(term not in raw for term in forbidden),name
        for value in doc.xpath('//a/@href | //link[@rel="stylesheet"]/@href | //script[@src]/@src | //img/@src'):
            parsed=urlsplit(urljoin(record['canonical'],value))
            if parsed.netloc!=urlsplit(DOMAIN).netloc:continue
            path=unquote(parsed.path);target=path.lstrip('/')+('index.html' if path.endswith('/') else '')
            assert target in expected,(name,value)
            links+=1
            if parsed.fragment:
                assert unquote(parsed.fragment) in document(target).xpath('//*[@id]/@id'),(name,value)
                fragments+=1
        if name=='학습가이드/index.html':assert len(doc.xpath('//*[@data-guide-card]'))==48
        elif name.split('/')[1] in {c[0] for c in CATEGORIES.values()}:assert len(doc.xpath('//*[@data-guide-card]'))==8
        else:
            slug=name.split('/')[1];row=by_slug[slug]
            assert doc.xpath('//h1/text()')==[row['title']]
            assert len(doc.xpath('//table'))==1 and len(doc.xpath('//*[@data-guide-faq]'))==2
            assert len(doc.xpath('//*[@data-record-field]'))==4
            faq=next(n for n in schemas if n.get('@type')=='FAQPage')
            assert [(x['name'],x['acceptedAnswer']['text']) for x in faq['mainEntity']]==[tuple(x) for x in row['faq']]
            fields=doc.xpath('//*[@data-record-field]/@data-label');assert fields==[x[0] for x in row['worksheet']]
            outline=doc.xpath('//*[@class="lg-worksheet-outline"]//dt/text()');assert outline==fields
            text=spaced(' '.join(main[0].itertext()));visible_chars.append(len(text))
            assert len(text)>1900,(slug,len(text))
            assert len(doc.xpath('//*[@id="sources"]//li/a'))==len(row['sources'])
            blank=(built/'assets/learning-guide-worksheets'/f'{slug}.txt').read_text('utf-8-sig')
            assert all(label in blank for label in fields) and '실천 기록' in blank
            assert '実' not in blank and '記録' not in blank
            exported,_=body(doc,record['canonical']);feed_doc=html.fromstring(exported)
            assert not feed_doc.xpath('.//form | .//textarea | .//input | .//button')
            assert feed_doc.xpath('.//h1/text()')==[row['title']]
            assert len(feed_doc.xpath('.//table'))==1
            for q,a in row['faq']:assert q in exported and a in exported
    assert len({tuple(tuple(w) for w in r['worksheet']) for r in rows})==48
    assert len({r['example']['text'][0] for r in rows})==48
    with zipfile.ZipFile(OUT/'guides-before.zip') as backup:
        assert backup.testzip() is None
        old_sitemap=etree.fromstring(backup.read('sitemap.xml'));old_feed=etree.fromstring(backup.read('rss.xml'))
        for name in TOPS:
            before=html.document_fromstring(backup.read(name));after=document(name)
            old=before.xpath('//main')[0];fresh=copy.deepcopy(after.xpath('//main')[0])
            for element in fresh.xpath('.//*[@data-learning-guide-entry]'):element.drop_tree()
            assert spaced(' '.join(old.itertext()))==spaced(' '.join(fresh.itertext())),name
            assert before.xpath('//h1//text()')==after.xpath('//h1//text()')
        old_entries={unquote(urlsplit(e.findtext('{*}loc')).path):e.findtext('{*}lastmod') for e in old_sitemap}
    sitemap=etree.parse(str(built/'sitemap.xml'));current_entries={unquote(urlsplit(e.findtext('{*}loc')).path):e.findtext('{*}lastmod') for e in sitemap.getroot()}
    top_paths={'/' if n=='index.html' else '/'+n.removesuffix('index.html') for n in TOPS}
    assert all(current_entries[p]==v for p,v in old_entries.items() if p not in top_paths)
    feed=etree.parse(str(built/'rss.xml'));items=feed.xpath('//channel/item')
    assert [identity(i) for i in items[:50]]==[identity(i) for i in old_feed.xpath('//channel/item')]
    assert len(items)==98
    for item in items:
        path=unquote(urlsplit(item.findtext('link')).path);doc=document(path.lstrip('/')+'index.html')
        assert item.findtext('description')==body(doc,item.findtext('link'))[0]
    assert not re.search(r'fetch\s*\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage', (built/'assets/learning-guides.js').read_text('utf-8'))
    inputs={'manifestSha256':digest((ROOT/'release-public-manifest.json').read_bytes()),'configSha256':digest((ROOT/'vercel.json').read_bytes()),'builtRoot':str(built),'canonicalOrigin':DOMAIN,'pages':pages,'assets':assets}
    dump(OUT/'http-inputs.json',inputs)
    dump(OUT/'validation.json',{'articles':48,'categoryHubs':6,'guidePages':55,'allPublicFiles':len(expected),'allPublicHtml':8458,'existingPublicFilesPreserved':len(baseline['files'])-len(changed),'changedExistingPublicFiles':changed,'oldUrlsPreserved':8403,'oldRssIdentitiesPreserved':50,'rssItems':98,'internalLinksChecked':links,'fragmentsChecked':fragments,'distinctWorksheets':48,'distinctExamples':48,'articleVisibleCharacters':{'min':min(visible_chars),'max':max(visible_chars)},'unrelatedDatesPreserved':True,'forbiddenPublicMentions':0,'exactBuildCompared':True,'errors':[],'deployed':False})
    print(json.dumps({'guidePages':55,'links':links,'fragments':fragments,'errors':0,'deployed':False},ensure_ascii=False),flush=True)

if __name__=='__main__':audit()
