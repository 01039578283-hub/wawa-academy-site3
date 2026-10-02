"""Independently check all HTML, link eligibility and phase-5 preservation."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlsplit,unquote
import argparse,hashlib,json,re,zipfile
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import OUT,BACKUP,LABEL,dump

TAG=re.compile(r'<a\b[^>]*>.*?</a>',re.S|re.I)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    targets={r['path']:r for r in impl.inventory() if r['role']=='enrollment' and not impl.grades_for(r,impl.CENTERS[tuple(r['centerKey'])],r['subject'])}
    changes=impl.load(OUT/'implementation.json');changed={r['file'] for r in changes['pages']}
    with zipfile.ZipFile(BACKUP) as snapshot:
        manifest=json.loads(snapshot.read('release-public-manifest.json'))
        names=[n for n in manifest['files'] if n.endswith('.html')]
        if args.sample:names=sorted(changed)
        def check(name):
            old=snapshot.read(name);new=(impl.ROOT/name).read_bytes();assert hashlib.sha256(old).hexdigest()==manifest['files'][name],name
            path='/' if name=='index.html' else '/'+name.removesuffix('index.html')
            doc=html.document_fromstring(new);previous=html.document_fromstring(old)
            links=doc.xpath('//a');oldlinks=previous.xpath('//a')
            assert len(links)==len(oldlinks),name
            old_tags=list(TAG.finditer(old.decode('utf-8')));new_tags=list(TAG.finditer(new.decode('utf-8')))
            assert len(old_tags)==len(new_tags)==len(links),name
            selected=[];labels=0;exclusions=Counter();seen=set();faq_count=0
            for index,(before,after) in enumerate(zip(oldlinks,links)):
                href=before.get('href');u=urlsplit(urljoin(impl.DOMAIN+impl.U(path),href or ''))
                dest=unquote(u.path);local=u.netloc==urlsplit(impl.DOMAIN).netloc
                breadcrumb=bool(before.xpath('ancestor::nav[contains(concat(" ",normalize-space(@class)," ")," bc-breadcrumb ")]'))
                eligible=bool(href and local and dest in targets and dest!=path and not breadcrumb)
                if eligible:
                    assert after.get('data-grade-confirmation')=='source-empty',(name,href)
                    attrs=dict(after.attrib);assert attrs.pop('data-grade-confirmation')=='source-empty'
                    classes=attrs.get('class','').split();assert classes.count('ns-grade-confirm-link')==1
                    attrs['class']=' '.join(c for c in classes if c!='ns-grade-confirm-link')
                    if not before.get('class'):attrs.pop('class',None)
                    assert attrs==dict(before.attrib),(name,href,'attributes')
                    content=after.xpath('./span[@class="ns-grade-confirm-label"]');status=after.xpath('./span[@class="ns-grade-confirm-status"]')
                    assert len(content)==len(status)==1 and len(after)==2,(name,href)
                    assert ''.join(content[0].itertext())==''.join(before.itertext()),(name,href,'original label')
                    assert status[0].text==LABEL and not status[0].get('aria-hidden'),(name,href,'visible accessible state')
                    assert after.get('aria-label') is None,'No label should override visible confirmation status'
                    selected.append(index);labels+=1;seen.add(dest)
                else:
                    assert after.get('data-grade-confirmation') is None,(name,href,'false confirmation')
                    assert old_tags[index][0]==new_tags[index][0],(name,href,'unrelated link changed')
                    if href and local and dest in targets:exclusions['same-page section' if dest==path else 'location breadcrumb']+=1
            # Remove only the independently eligible anchor changes, then require
            # byte-exact old HTML: protects schema, dates, facts, media and contact.
            value=new.decode('utf-8')
            for index in reversed(selected):
                match=new_tags[index];value=value[:match.start()]+old_tags[index][0]+value[match.end():]
            assert value.encode('utf-8')==old,(name,'changes outside approved links')
            for section in doc.xpath('//section[@data-faq-role][@id="faq" or @id="faq-section"]'):
                pairs=[{'@type':'Question','name':' '.join(d.xpath('./summary//text()')).strip(),'acceptedAnswer':{'@type':'Answer','text':' '.join(d.xpath('./p//text()')).strip()}} for d in section.xpath('.//details[summary]')]
                schemas=[n for s in doc.xpath('//script[@type="application/ld+json"]') for n in json.loads(s.text).get('@graph',[]) if n.get('@type')=='FAQPage']
                if pairs:
                    assert len(schemas)==1 and schemas[0]['mainEntity']==pairs,(name,'FAQ content/schema mismatch')
                    if len(pairs)==5:faq_count=len(pairs)
            return {'file':name,'changed':old!=new,'labels':labels,'seen':list(seen),'excluded':dict(exclusions),'faq':faq_count,'sha256':hashlib.sha256(new).hexdigest()}
        results=[];errors=[]
        with ThreadPoolExecutor(max_workers=8) as pool:
            for start in range(0,len(names),128):
                for name,result in zip(names[start:start+128],pool.map(check,names[start:start+128])):results.append(result)
                if len(results)%1024==0:print('Verified HTML',len(results),flush=True)
        css_old=snapshot.read('assets/neighborhood-seo/local.css');css=(impl.ROOT/'assets/neighborhood-seo/local.css').read_bytes()
        assert css.startswith(css_old) and css[len(css_old):].count(b'/* Phase 6:')==1
        assert snapshot.read('sitemap.xml')==(impl.ROOT/'sitemap.xml').read_bytes()
        for name in snapshot.namelist():
            if name.startswith('tools/data/neighborhood-seo/'):
                assert snapshot.read(name)==(impl.ROOT/name).read_bytes(),name
    output={'sitemapPages':len(results),'changedHtmlPages':sum(r['changed'] for r in results),'unchangedHtmlPages':sum(not r['changed'] for r in results),'labeledLinks':sum(r['labels'] for r in results),'labeledTargets':len(set(p for r in results for p in r['seen'])),'authorityTargets':len(targets),'excluded':dict(sum((Counter(r['excluded']) for r in results),Counter())),'retainedFAQQuestions':sum(r['faq'] for r in results),'originalHtmlOutsideApprovedAnchorsByteExact':True,'hrefsAndAttributesPreserved':True,'centerInputsByteExact':True,'sitemapByteExact':True,'errors':errors,'deployed':False}
    if not args.sample:
        assert output['changedHtmlPages']==changes['changedPages']==281
        assert output['labeledLinks']==changes['changedLinks']==1152
        assert output['labeledTargets']==55 and output['retainedFAQQuestions']==41775
    dump(OUT/('sample-validation.json' if args.sample else 'validation.json'),output)
    print(json.dumps(output,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
