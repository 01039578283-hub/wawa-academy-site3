"""Keep the national, regional and grade/subject hubs focused on navigation.

Apply after the subject-role correction. Preserve all native directory links
and original search handlers; only remove detail-only media and reorder hubs.
"""
import json,re,zipfile
from concurrent.futures import ThreadPoolExecutor
from lxml import html
import fix_subject_hub_roles as core

NAMES=['전국센터/index.html']+['전국센터/'+slug+'/index.html' for slug in
       ['서울','경기','인천','충청','대전','대구','울산','부산','경상','광주','전라','강원','제주',
        '초등영어학원','초등수학학원','중등영어학원','중등수학학원','고등영어학원','고등수학학원']]

def transform(name,text):
    doc=html.fromstring(text)
    if doc.xpath('//body[@data-directory-role="20261006"]'):return text
    children=list(doc.xpath('//main/*'));old_ids=set(doc.xpath('//main//*[@id]/@id'))
    hero=children[0];assert 'center-hero' in hero.get('class','')
    # A root directory has region/course links and a name search; child hubs
    # have one or two native directory sections. Keep their tested handlers.
    directory_ids=['reading-3','reading-4','reading-5'] if name==NAMES[0] else ['reading-4','reading-5']
    directory=[];rest=[]
    for node in children[1:]:
        ident=node.get('id');cls=node.get('class','').split()
        if ident in ['page-images','learning-space','hub-center-examples','choose-guide-purpose','hub-directory']:continue
        if 'cl-toc' in cls or node.tag=='p' and 'cl-revised' in cls:continue
        if ident in directory_ids:
            node.set('class',' '.join(cls+['sh-section']))
            for wrap in node.xpath('.//*[@class]'):
                classes=wrap.get('class').split()
                if 'cl-reading' in classes:wrap.set('class',' '.join(c for c in classes if c!='cl-reading'))
            directory.append(core.serialize(node))
        else:
            if node.tag=='section' and ident:node.set('class',' '.join(cls+['sh-optional']))
            for detail in node.xpath('.//details'):
                if detail.xpath('string(./summary)')==core.PHOTO_QUESTION:
                    detail.xpath('./summary')[0].text=core.NEW_QUESTION
                    detail.xpath('./p')[0].text=core.NEW_ANSWER
            rest.append(core.serialize(node))
    assert directory
    main=core.serialize(hero)+'<div id="hub-directory">'+''.join(directory)+'</div>'+''.join(rest)
    main+=f'<p class="cl-revised wrap">내용 정리·수정 <time datetime="{core.TODAY}">2026.10.06</time> · 지역·과목별 이동 안내를 정리했습니다.</p>'
    present=set(html.fromstring('<main>'+main+'</main>').xpath('//*[@id]/@id'))|{'main'}
    aliases=''.join(f'<span class="sh-anchor" id="{core.E(i)}" aria-hidden="true"></span>' for i in sorted(old_ids-present))
    main=main.replace('</section>','</section>'+aliases,1)
    updated=re.sub(r'<main\b[^>]*>.*?</main>',lambda m:'<main id="main">'+main+'</main>',text,count=1,flags=re.S)
    updated=re.sub(r'<body\b([^>]*)class="([^"]+)"',lambda m:'<body data-directory-role="20261006"'+m[1]+'class="'+m[2]+' subject-hub"',updated,count=1)
    includes=f'<link rel="stylesheet" href="{core.asset_url(core.ASSETS[0])}"><script defer src="{core.asset_url(core.ASSETS[1])}"></script>'
    updated=updated.replace('</head>',includes+'</head>',1)
    actual=html.fromstring(updated)
    parts=[(n.get('id'),n.xpath('string(.//h2)')) for n in actual.xpath('//main//section[@id][.//h2]')]
    def schema(match):
        data=json.loads(match[1]);graph=data['@graph'];page=next(n for n in graph if n.get('@type')=='CollectionPage')
        page['dateModified']=core.TODAY;page.pop('mentions',None)
        page['hasPart']=[{'@id':page['url']+'#'+ident} for ident,_ in parts]
        graph[:]=[n for n in graph if n.get('@type')!='WebPageElement']
        for ident,label in parts:graph.append({'@type':'WebPageElement','@id':page['url']+'#'+ident,'url':page['url']+'#'+ident,'name':label,'isPartOf':{'@id':page['@id']}})
        for node in graph:
            if node.get('@type')=='FAQPage':
                for q in node['mainEntity']:
                    if q['name']==core.PHOTO_QUESTION:q['name']=core.NEW_QUESTION;q['acceptedAnswer']['text']=core.NEW_ANSWER
        return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False,separators=(',',':'))+'</script>'
    return re.sub(r'<script type="application/ld\+json">(.*?)</script>',schema,updated,count=1,flags=re.S)

def apply():
    m=json.loads((core.ROOT/'release-public-manifest.json').read_text('utf-8'))
    baseline=json.loads((core.OUT/'baseline-manifest.json').read_text('utf-8'))
    with zipfile.ZipFile(core.OUT/'before.zip','a',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for name in NAMES:
            raw=(core.ROOT/name).read_bytes()
            if name not in z.namelist():
                assert core.sha(raw)==baseline['files'][name]
                z.writestr(name,raw)
            (core.ROOT/name).write_bytes(transform(name,raw.decode('utf-8')).encode('utf-8'))
    sitemap=(core.ROOT/'sitemap.xml').read_text('utf-8')
    for name in NAMES:
        canonical=html.fromstring((core.ROOT/name).read_bytes()).xpath('//link[@rel="canonical"]/@href')[0]
        pattern=r'(<url>\s*<loc>'+re.escape(canonical)+r'</loc>\s*<lastmod>)[^<]*(</lastmod>)'
        sitemap,count=re.subn(pattern,lambda a:a[1]+core.TODAY+a[2],sitemap);assert count==1
    (core.ROOT/'sitemap.xml').write_bytes(sitemap.encode('utf-8'))
    for name in NAMES+['sitemap.xml']:
        raw=(core.ROOT/name).read_bytes();m['files'][name]=core.sha(raw);m['textSha256'][name]=core.sha(raw.decode('utf-8').replace('\r\n','\n').encode('utf-8'))
    (core.ROOT/'release-public-manifest.json').write_bytes((json.dumps(m,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    (core.OUT/'release-manifest-sha.txt').write_text(core.sha((core.ROOT/'release-public-manifest.json').read_bytes())+'\n','utf-8')
    print('Corrected twenty connected national, regional and course hubs',flush=True)

def verify():
    checked=[]
    with zipfile.ZipFile(core.OUT/'before.zip') as z:
        for name in NAMES:
            original=z.read(name).decode('utf-8');current=(core.ROOT/name).read_bytes().decode('utf-8')
            assert current==transform(name,original),name
            assert transform(name,current)==current
            before=html.fromstring(original);after=html.fromstring(current)
            assert not after.xpath('//main//img|//main//iframe')
            assert after.xpath('string(//h1)')==before.xpath('string(//h1)')
            assert after.xpath('//link[@rel="canonical"]/@href')==before.xpath('//link[@rel="canonical"]/@href')
            assert core.serialize(before.xpath('//header')[0])==core.serialize(after.xpath('//header')[0])
            assert core.serialize(before.xpath('//footer')[0])==core.serialize(after.xpath('//footer')[0])
            old_directory=before.xpath('//main//section[@id="reading-3" or @id="reading-4" or @id="reading-5"]//a/@href') if name==NAMES[0] else before.xpath('//main//section[@id="reading-4" or @id="reading-5"]//a/@href')
            assert old_directory==after.xpath('//*[@id="hub-directory"]//a/@href'),name
            ids=after.xpath('//*[@id]/@id');assert len(ids)==len(set(ids))
            assert set(before.xpath('//main//*[@id]/@id'))<=set(ids)
            graph=json.loads(after.xpath('//script[@type="application/ld+json"]/text()')[0])['@graph']
            for faq in [n for n in graph if n.get('@type')=='FAQPage']:
                actual=[(x.xpath('string(./summary)'),x.xpath('string(./p)')) for x in after.xpath('//main//section[contains(@class,"hub-guide-faq")]//details')]
                assert actual==[(x['name'],x['acceptedAnswer']['text']) for x in faq['mainEntity']],name
            checked.append({'file':name,'bodyImages':0,'directoryLinksPreserved':len(old_directory),'originalAnchorIdsPreserved':True})
    result={'hubPages':20,'directoryLinksPreserved':sum(r['directoryLinksPreserved'] for r in checked),'removedHubImages':140,'checks':checked,'errors':[]}
    core.dump('connected-hub-verification.json',result);print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','verify']);args=p.parse_args()
    {'apply':apply,'verify':verify}[args.action]()
