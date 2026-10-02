"""Independent route coverage, privacy and complete previous-HTML preservation."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote,urlsplit
import argparse,copy,hashlib,json,re,zipfile
from lxml import html,etree
import improve_neighborhood_pages as impl
from audit_neighborhood_phase7 import OUT,BACKUP,ASSETS,HUBS
from audit_neighborhood_phase6 import dump
from validate_neighborhood_seo import nodes

SECTION=re.compile(r'<section\b(?=[^>]*\bid="choose-guide-purpose")[^>]*>.*?</section>',re.S)
ANCHORS=re.compile(r'<a\b[^>]*>.*?</a>',re.S)
META=re.compile(r'<meta\b[^>]*>',re.I)
SCHEMA=re.compile(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',re.S)
JS_TAG='<script defer src="/assets/neighborhood-seo/find-guide.js?v=20261001-v7"></script>'
CSS_TAG='<link rel="stylesheet" href="/assets/neighborhood-seo/local.css">'

def data_check():
    raw=(impl.ROOT/ASSETS[1]).read_bytes();data=json.loads(raw)
    assert data==impl.load(OUT/'reviewed-finder-data.json')
    rows=impl.inventory();lookup={r['path']:r for r in rows};covered=set();unknown=set();seen=set()
    allowed={'id','name','region','district','center','branch','overview','enrollment','study','comparison'}
    for area in data['areas']:
        assert set(area)==allowed and area['id']==impl.norm(area['name']) and area['id'] not in seen
        seen.add(area['id'])
        r=lookup[area['overview']];assert r['role']=='overview' and r['neighborhood']==area['name']
        center=impl.CENTERS[tuple(r['centerKey'])]
        assert [area[k] for k in ['region','district','center','branch']]==[center['region'],center['district'],center['routeName'],impl.center_path(center)]
        covered.add(area['overview'])
        for role,group in [('enrollment',area['enrollment']),('study-guide',area['study'])]:
            assert set(group)=={'영어','수학'}
            for subject,grades in group.items():
                assert set(grades)==({'전체','초등','중등','고등'} if role=='enrollment' else {'초등','중등','고등'})
                for stage,item in grades.items():
                    assert set(item)==({'href','label','unconfirmed'} if role=='enrollment' else {'href','label'})
                    row=lookup[item['href']];assert row['role']==role and row['subject']==subject and row.get('stage','전체')==stage and row['neighborhood']==area['name']
                    if role=='enrollment':
                        assert item['unconfirmed']==(not bool(impl.grades_for(row,center,subject)))
                        if item['unconfirmed']:unknown.add(item['href'])
                    covered.add(item['href'])
        assert set(area['comparison'])==set(impl.CATEGORIES)
        for category,item in area['comparison'].items():
            assert set(item)=={'href','label'};row=lookup[item['href']]
            assert row['role']=='comparison-guide' and row['category']==category and row['neighborhood']==area['name'];covered.add(item['href'])
    assert len(seen)==371 and covered==set(lookup) and len(unknown)==55
    return {'areas':len(seen),'reviewedRoutes':len(covered),'confirmationTargets':len(unknown),'publicDatasetBytes':len(raw),'whitelistOnly':True}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    audit=impl.load(OUT/'hub-audit.json');pages={p['file']:p for p in audit['pages']};configs=impl.load(OUT/'reviewed-pages.json')
    current=impl.load(OUT/'implementation.json');implemented={p['file'] for p in current['pages']}
    with zipfile.ZipFile(BACKUP) as snapshot:
        manifest=json.loads(snapshot.read('release-public-manifest.json'))
        names=[n for n in manifest['files'] if n.endswith('.html')]
        if args.sample:names=sorted(implemented)
        def check(name):
            old=snapshot.read(name);new=(impl.ROOT/name).read_bytes();assert hashlib.sha256(old).hexdigest()==manifest['files'][name]
            if name not in implemented:
                assert new==old,(name,'unapproved HTML changed');return {'changed':False,'labels':0,'schemaLabels':0}
            page=pages[name];config=configs[page['path']];before=old.decode('utf-8');after=new.decode('utf-8')
            doc=html.document_fromstring(new);previous=html.document_fromstring(old)
            chooser=doc.xpath('//section[@id="choose-guide-purpose"]');assert len(chooser)==1
            assert chooser[0].get('data-neighborhood-finder')=='20261001-v7'
            assert not chooser[0].xpath('.//section')
            main=doc.xpath('//main')[0];assert main.index(chooser[0])==1,(name,'finder must follow the existing hero')
            original_section=SECTION.search(before)
            restored,count=SECTION.subn(lambda m:original_section[0] if original_section else '',after);assert count==1
            assert restored.count(JS_TAG)==1;restored=restored.replace(JS_TAG,'',1)
            if '/assets/neighborhood-seo/local.css' not in before:
                assert restored.count(CSS_TAG)==1;restored=restored.replace(CSS_TAG,'',1)
            # Explicit directory-caption changes only; strong label/href and
            # every unrelated anchor attribute and byte remain unchanged.
            oldanchors=list(ANCHORS.finditer(before));newanchors=list(ANCHORS.finditer(restored));assert len(oldanchors)==len(newanchors)
            lookup={a['href']:a for a in page['links']};labels=0
            for olda,newa in reversed(list(zip(oldanchors,newanchors))):
                a=html.fromstring(olda[0]);b=html.fromstring(newa[0]);review=lookup.get(a.get('href'))
                if review:
                    assert dict(a.attrib)==dict(b.attrib) and html.tostring(a[0])==html.tostring(b[0])
                    assert b[1].tag=='small' and b[1].text==review['afterSmall'] and len(b)==2
                    labels+=1
                    restored=restored[:newa.start()]+olda[0]+restored[newa.end():]
                else:assert olda[0]==newa[0],(name,'unrelated link')
            assert labels==len(page['links'])
            oldmetas=list(META.finditer(before));newmetas=list(META.finditer(restored));assert len(oldmetas)==len(newmetas)
            count=0
            for oldm,newm in reversed(list(zip(oldmetas,newmetas))):
                a=html.fromstring(oldm[0]).xpath('//meta')[0];b=html.fromstring(newm[0]).xpath('//meta')[0];kind=a.get('name') or a.get('property')
                if kind in ['description','og:description','twitter:description']:
                    attrs=dict(b.attrib);assert attrs.pop('content')==config['description'] and len(config['description'])<=80
                    attrs['content']=a.get('content');assert attrs==dict(a.attrib)
                    restored=restored[:newm.start()]+oldm[0]+restored[newm.end():];count+=1
                else:assert oldm[0]==newm[0]
            assert count==3
            oldscripts=list(SCHEMA.finditer(before));newscripts=list(SCHEMA.finditer(restored));assert len(oldscripts)==len(newscripts)
            link_names={a['target']:a['after'] for a in page['links']};schema_labels=0
            for olds,news in reversed(list(zip(oldscripts,newscripts))):
                expected=json.loads(olds[2])
                for node in nodes(expected):
                    if node.get('@type') in ['WebPage','CollectionPage','Article']:
                        node.update(description=config['description'],dateModified='2026-10-01')
                    if node.get('@type')=='ListItem' and unquote(urlsplit(node.get('url','')).path) in link_names:
                        node['name']=link_names[unquote(urlsplit(node['url']).path)];schema_labels+=1
                assert json.loads(news[2])==expected,(name,'unauthorized schema change')
                restored=restored[:news.start()]+olds[0]+restored[news.end():]
            if page['category']:assert schema_labels==371
            times=re.compile(r'<time datetime="\d{4}-\d{2}-\d{2}">\d{4}\.\d{2}\.\d{2}</time>')
            oldtimes=list(times.finditer(before));newtimes=list(times.finditer(restored));assert len(oldtimes)==len(newtimes)
            for a,b in reversed(list(zip(oldtimes,newtimes))):
                assert b[0]=='<time datetime="2026-10-01">2026.10.01</time>'
                restored=restored[:b.start()]+a[0]+restored[b.end():]
            assert restored.encode('utf-8')==old,(name,'body changed outside approved scope')
            assert previous.xpath('//link[@rel="canonical"]/@href')==doc.xpath('//link[@rel="canonical"]/@href')
            return {'changed':True,'labels':labels,'schemaLabels':schema_labels}
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(check,names))
        css=snapshot.read('assets/neighborhood-seo/local.css');current_css=(impl.ROOT/'assets/neighborhood-seo/local.css').read_bytes()
        assert current_css.startswith(css) and current_css[len(css):].count(b'/* Phase 7:')==1
        old_map=etree.fromstring(snapshot.read('sitemap.xml'));new_map=etree.fromstring((impl.ROOT/'sitemap.xml').read_bytes())
        old_urls=old_map.xpath('//*[local-name()="url"]');new_urls=new_map.xpath('//*[local-name()="url"]');assert len(old_urls)==len(new_urls)==8403
        for a,b in zip(old_urls,new_urls):
            loc=a.find('{*}loc').text;assert b.find('{*}loc').text==loc
            if unquote(urlsplit(loc).path) in {p['path'] for p in current['pages']}:
                assert b.find('{*}lastmod').text=='2026-10-01'
                if a.find('{*}lastmod') is not None:a.find('{*}lastmod').text='2026-10-01'
                else:etree.SubElement(a,'{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod').text='2026-10-01'
            assert etree.tostring(a)==etree.tostring(b),'sitemap changed outside modified URLs'
        for name in snapshot.namelist():
            if name.startswith('tools/data/neighborhood-seo/'):assert snapshot.read(name)==(impl.ROOT/name).read_bytes(),name
    output={'sitemapPages':len(results),'changedHtmlPages':sum(r['changed'] for r in results),'unchangedHtmlPages':sum(not r['changed'] for r in results),'directoryLabels':sum(r['labels'] for r in results),'matchingItemListLabels':sum(r['schemaLabels'] for r in results),'originalHTMLOutsideApprovedFieldsByteExact':True,'existingURLsAndOrderPreserved':True,'centerInputsByteExact':True,**data_check(),'errors':[],'deployed':False}
    if not args.sample:assert output['changedHtmlPages']==11 and output['directoryLabels']==output['matchingItemListLabels']==2597
    dump(OUT/('sample-validation.json' if args.sample else 'validation.json'),output);print(json.dumps(output,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
