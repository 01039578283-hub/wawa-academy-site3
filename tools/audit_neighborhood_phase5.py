"""Preserve the reviewed phase-4 pages and inventory visible FAQ/schema scope."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path
import hashlib,json,zipfile
from lxml import html
import improve_neighborhood_pages as impl

OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase5-20261001')
PRIOR=OUT.parent/'site3-neighborhood-phase4-20261001'
BACKUP=OUT/'phase4-before-phase5.zip'

def entries():
    result=impl.inventory()
    result.extend({'path':impl.center_path(c),'role':'center-hub','neighborhood':c['routeName'],'centerKey':[c['region'],c['routeName']],'branchPath':impl.center_path(c),'enrollmentPath':impl.center_path(c)} for c in impl.FACTS['centers'])
    assert len(result)==8355 and len({r['path'] for r in result})==8355
    return result

def filename(path):return path.strip('/')+'/index.html' if path!='/' else 'index.html'

def audit(row):
    raw=(impl.ROOT/filename(row['path'])).read_bytes();doc=html.document_fromstring(raw)
    sections=doc.xpath('//main//section[@id="faq" or @id="faq-section"]')
    assert len(sections)==1 and not sections[0].xpath('.//section'),row['path']
    pairs=[(' '.join(d.xpath('./summary//text()')).strip(),' '.join(d.xpath('./p//text()')).strip()) for d in sections[0].xpath('.//details[summary]')]
    schema=[n for s in doc.xpath('//script[@type="application/ld+json"]') for n in json.loads(s.text).get('@graph',[]) if n.get('@type')=='FAQPage']
    assert len(schema)==1,row['path']
    matches=[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in pairs]
    assert schema[0]['mainEntity']==matches,row['path']
    assert len(doc.xpath('//main/section[@id="page-images"]'))==1,row['path']
    return {'path':row['path'],'role':row['role'],'faqId':sections[0].get('id'),'questions':len(pairs),'feeAnswer':pairs[-1][1],'sha256':hashlib.sha256(raw).hexdigest()}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    prior=impl.load(PRIOR/'validation.json');assert prior['errors']==[] and prior['changedHtmlPages']==8355
    manifest=impl.load(impl.ROOT/'release-public-manifest.json')
    assert hashlib.sha256((impl.ROOT/'release-public-manifest.json').read_bytes()).hexdigest()=='92e13d1c3e21130cada25749c707ca35c5e48f51d2b743f15cd2feaacf238613'
    rows=entries()
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(audit,rows))
    for r in results:assert manifest['files'][filename(r['path'])]==r['sha256'],r['path']
    if not BACKUP.exists():
        names=[n for n in manifest['files'] if n.endswith('.html')]+['sitemap.xml','assets/neighborhood-seo/local.css','release-public-manifest.json']
        names+=['tools/data/neighborhood-seo/'+p.name for p in impl.DATA.glob('*.json')]
        names+=['tools/'+p.name for p in (impl.ROOT/'tools').glob('*phase4.py')]
        with zipfile.ZipFile(BACKUP,'x',zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
            with ThreadPoolExecutor(max_workers=8) as pool:
                for name,raw in pool.map(lambda n:(n,(impl.ROOT/n).read_bytes()),names):
                    if name in manifest['files']:assert hashlib.sha256(raw).hexdigest()==manifest['files'][name],name
                    archive.writestr(name,raw)
    with zipfile.ZipFile(BACKUP) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read('release-public-manifest.json'))==manifest
        assert len([n for n in archive.namelist() if n.endswith('/index.html') or n=='index.html'])==8403
    audit_result={'pages':len(results),'roles':dict(Counter(r['role'] for r in results)),'questions':sum(r['questions'] for r in results),'schemaMatchesVisibleFAQ':True,'commonFeeAnswers':Counter(r['feeAnswer'] for r in results).most_common(),'backupSha256':hashlib.sha256(BACKUP.read_bytes()).hexdigest(),'pagesReviewed':results,'deployed':False}
    impl.dump(OUT/'before-faq-audit.json',audit_result)
    print(json.dumps({k:v for k,v in audit_result.items() if k!='pagesReviewed'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
