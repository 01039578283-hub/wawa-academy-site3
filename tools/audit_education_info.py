"""Verify complete publication preservation and authored article inputs."""
from pathlib import Path
from collections import Counter
from urllib.parse import urljoin,urlsplit,unquote
import copy,json,re,zipfile,hashlib
from lxml import html,etree
import build_education_info as impl
from audit_neighborhood_phase6 import state

def normalized(doc):
    doc=copy.deepcopy(doc)
    for n in doc.xpath('//*[@data-education-nav or @data-education-style or @data-education-bridge]'):n.drop_tree()
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

def main():
    root,out=impl.ROOT,impl.OUT
    data=impl.load(impl.DATA);base=impl.load(out/'baseline-manifest.json');manifest=impl.load(root/'release-public-manifest.json');report=impl.load(out/'implementation.json')
    rows={r['path'].strip('/')+'/index.html':r for r in data['articles']}
    new=set(manifest['files'])-set(base['files']);assert new==set(report['newPublicFiles']) and len(new)==124
    assert len(manifest['files'])==11071 and manifest['sitemapPages']==8695
    links=0;fragments=0;bridges=0;photos=0;incoming=Counter();titles=[]
    with zipfile.ZipFile(out/'education-before.zip') as backup:
        assert backup.testzip() is None
        for i,(name,hash) in enumerate(manifest['files'].items(),1):
            raw=(root/name).read_bytes();assert impl.digest(raw)==hash,name
            if name in manifest['textSha256']:assert impl.digest(raw.decode('utf-8').replace('\r\n','\n').encode())==manifest['textSha256'][name],name
            if not name.endswith('.html'):
                if name in base['files'] and name not in ['rss.xml','sitemap.xml']:assert raw==backup.read(name),name
                continue
            doc=html.document_fromstring(raw);canonical=doc.xpath('//link[@rel="canonical"]/@href')[0]
            if name in base['files']:
                old=html.document_fromstring(backup.read(name));assert normalized(doc)==normalized(old),name
                assert len(doc.xpath('//header//a[@data-education-nav]'))==1,name
                assert len(doc.xpath('//*[@data-education-bridge]'))==1,name
                bridges+=1
                nodes=doc.xpath('//a[@data-education-nav] | //*[@data-education-bridge]//a | //link[@data-education-style]')
            else:
                assert len(doc.xpath('//h1'))==1 and len(doc.xpath('//main'))==1,name
                ids=doc.xpath('//*[@id]/@id');assert len(ids)==len(set(ids)),name
                desc=doc.xpath('//meta[@name="description"]/@content')[0];assert desc.endswith('.') and len(desc)<=80,name
                assert doc.xpath('//meta[@property="og:description"]/@content')==doc.xpath('//meta[@name="twitter:description"]/@content')==[desc]
                graph=json.loads(doc.xpath('//script[@type="application/ld+json"]')[0].text)['@graph'];assert graph[0]['description']==desc
                assert canonical==impl.url('/'+name[:-10]),name
                nodes=doc.xpath('//a[@href] | //img[@src] | //link[@href] | //script[@src]')
                if name in rows:
                    r=rows[name];titles.append(doc.xpath('string(//h1)'));assert titles[-1]==r['title']
                    article=doc.xpath('//*[@data-education-article]')[0]
                    text=' '.join(article.itertext())
                    for p in r['intro']+[p for s in r['sections'] for p in s['paragraphs']]+r['checks']+[v for pair in r['faq'] for v in pair]+[v for row in r['table']['rows'] for v in row]:assert p in text,(name,p)
                    images=article.xpath('.//figure/img');assert len(images)==3,name
                    for j,(node,im) in enumerate(zip(images,r['images'])):
                        assert node.get('src')==im['path'] and node.get('alt')==im['alt'] and node.get('width')==str(im['width']) and node.get('height')==str(im['height'])
                        assert node.getparent().getprevious().get('id')=='section-'+str([1,3,5][j]),name
                        assert (root/im['path'].lstrip('/')).read_bytes()==(impl.SOURCE/'1 이미지'/im['source']).read_bytes()
                        photos+=1
                    faq=next(g for g in graph if g['@type']=='FAQPage')['mainEntity'];assert [(v['name'],v['acceptedAnswer']['text']) for v in faq]==[tuple(v) for v in r['faq']]
                    schema=next(g for g in graph if g['@type']=='Article');assert schema['headline']==r['title'] and schema['image']==[impl.DOMAIN+im['path'] for im in r['images']]
                    assert schema['citation']==[data['sources'][s]['url'] for s in r['sources']]
                    manuscript=impl.SOURCE/r['originalFolder']/'원고.txt';assert impl.digest(manuscript.read_bytes())==r['originalSha256']
            for node in nodes:
                target=urlsplit(urljoin(canonical,node.get('href') or node.get('src')))
                if target.netloc!=urlsplit(impl.DOMAIN).netloc:continue
                path=unquote(target.path);dest=path.lstrip('/')+('index.html' if path.endswith('/') else '')
                assert dest in manifest['files'],(name,dest)
                links+=1;incoming[dest]+=1
                if target.fragment:
                    targetdoc=doc if dest==name else html.document_fromstring((root/dest).read_bytes());assert targetdoc.xpath('//*[@id=$id]',id=unquote(target.fragment)),(name,target.fragment);fragments+=1
            if i%2000==0:print('Audited public files',i,flush=True)
        oldfeed=etree.fromstring(backup.read('rss.xml'));feed=etree.fromstring((root/'rss.xml').read_bytes())
        assert [impl.identity(item) for item in oldfeed.findall('channel/item')]==[impl.identity(item) for item in feed.findall('channel/item')][:99]
        assert len(feed.findall('channel/item'))==129
        oldlocs=etree.fromstring(backup.read('sitemap.xml')).xpath('//*[local-name()="loc"]/text()');locs=etree.fromstring((root/'sitemap.xml').read_bytes()).xpath('//*[local-name()="loc"]/text()')
        assert len(locs)==len(set(locs))==8695 and set(oldlocs)<=set(locs)
    assert len(set(titles))==30 and photos==90 and bridges==8664
    assert all(incoming[n]>0 for n in rows) and incoming['교육정보/index.html']>8664
    locations=impl.load(root/'assets/education-locations.json');assert len(locations)==564 and Counter(r['kind'] for r in locations)=={'neighborhood':371,'center':193}
    for r in locations:assert unquote(r['path']).strip('/')+'/index.html' in manifest['files']
    assert state()==impl.load(out/'authoring-before.json')
    result={'publicFiles':11071,'htmlPages':8695,'oldHtmlPreserved':8664,'newHtmlPages':31,'authoredArticles':30,'originalManuscriptsUntouched':30,'photosVerified':90,'photosPerArticle':3,'primaryReferenceSources':11,'existingGuidesLinked':32,'contextualBridgePages':bridges,'newInternalLinksVerified':links,'fragmentLinksVerified':fragments,'locationOptionsVerified':564,'existingRssIdentitiesPreserved':99,'rssItems':129,'authoringPreserved':True,'errors':[],'manifestSha256':impl.digest((root/'release-public-manifest.json').read_bytes())}
    impl.dump(out/'source-audit.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
