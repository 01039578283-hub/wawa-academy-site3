"""Read-only candidate for the next local improvement: unconfirmed grade links."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import json
from urllib.parse import urljoin
from lxml import html,etree
import improve_neighborhood_pages as impl
from audit_neighborhood_phase5 import OUT,filename

def main():
    candidates={}
    for r in impl.inventory():
        if r['role']!='enrollment':continue
        c=impl.CENTERS[tuple(r['centerKey'])]
        if not impl.grades_for(r,c,r['subject']):candidates[r['path']]={'stage':r.get('stage'),'subject':r['subject'],'center':c['routeName'],'neighborhood':r['neighborhood']}
    urls=etree.parse(str(impl.ROOT/'sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
    def read(url):
        path=impl.unquote(impl.urlsplit(url).path);doc=html.document_fromstring((impl.ROOT/filename(path)).read_bytes());found=[]
        for a in doc.xpath('//section[@id="related-intents"]//a[@href]'):
            target=impl.unquote(impl.urlsplit(urljoin(impl.DOMAIN+impl.U(path),a.get('href'))).path)
            if target in candidates:
                label=' '.join(a.itertext()).strip()
                if not any(v in label for v in ['확인 필요','확인필요','미확인']):found.append({'path':path,'target':target,'label':label,**candidates[target]})
        return found
    results=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for found in pool.map(read,urls):results.extend(found)
    result={'checkedPages':len(urls),'enrollmentTargetsWithUnconfirmedGrades':len(candidates),'linksWithoutConfirmationLabel':len(results),'sourcePages':len({v['path'] for v in results}),'targetPages':len({v['target'] for v in results}),'byStage':dict(Counter(v['stage'] or 'all' for v in results)),'meaning':'No grade in supplied authority; this is not evidence that a class is unavailable. Suggest clarify link labels while preserving routes.','examples':results[:30],'deployed':False}
    impl.dump(OUT/'next-link-audit.json',result);print(json.dumps({k:v for k,v in result.items() if k!='examples'},ensure_ascii=False))

if __name__=='__main__':main()
