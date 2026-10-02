"""Select final UI coverage and audit the next hub-navigation opportunity."""
from collections import Counter
from urllib.parse import unquote,urlsplit
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import OUT,dump

def main():
    audit=impl.load(OUT/'incoming-link-audit.json');pages=[p for p in audit['pages'] if any(a['eligible'] for a in p['links'])]
    inventory={r['path']:r for r in impl.inventory()}
    for c in impl.FACTS['centers']:inventory[impl.center_path(c)]={'centerKey':[c['region'],c['routeName']]}
    chosen=[]
    def add(page):
        if page['path'] not in [p['path'] for p in chosen]:chosen.append(page)
    for role in ['comparison-guide','overview','study-guide','center-hub','enrollment']:add(next(p for p in pages if p['role']==role))
    for center in sorted({tuple(r['centerKey']) for r in audit['targets']}):
        if center not in {tuple(inventory[p['path']]['centerKey']) for p in chosen}:add(next(p for p in pages if tuple(inventory[p['path']]['centerKey'])==center))
    # Include the grade-level button group as well as subject-level siblings.
    add(next(p for p in pages if p['role']=='enrollment' and inventory[p['path']].get('stage')))
    cases=[]
    for p in chosen:
        doc=html.document_fromstring((impl.ROOT/p['file']).read_bytes());link=next(a for a in p['links'] if a['eligible'])
        case={'index':len(cases),'path':p['path'],'role':p['role'],'centerKey':inventory[p['path']]['centerKey'],'section':link['section'],'target':link['target'],'href':link['href'],'linkLabel':link['label'],'questions':[' '.join(x.xpath('./summary//text()')).strip() for x in doc.xpath('//section[@id="faq" or @id="faq-section"]//details[summary]')]}
        cases.append(case)
    dump(OUT/'responsive-cases.json',cases)
    print('UI cases',len(cases),'conditions',len(cases)*4,flush=True)
    # All topical index hubs: distinguish a factual branch route from a general
    # learning/comparison route before proposing the next phase.
    names=['index.html','지점안내/index.html','전국센터/index.html','과목별학원/index.html']
    names+=['전국센터/'+s+'/index.html' for s in ['영어','수학']]
    names+=['전국센터/'+s+'/'+g+'/index.html' for s in ['영어','수학'] for g in ['초등','중등','고등']]
    names+=['과목별학원/'+c+'/index.html' for c in impl.CATEGORIES]
    audited=[]
    for name in names:
        path=impl.ROOT/name
        if not path.exists():continue
        doc=html.document_fromstring(path.read_bytes())
        links=[{'label':' '.join(a.itertext()).strip(),'href':a.get('href')} for a in doc.xpath('//main//a[@href]')]
        role_links=Counter('수강' if '수강' in a['label'] else '학습 점검' if '점검' in a['label'] else '비교' if '비교' in a['label'] else 'other' for a in links)
        audited.append({'file':name,'h1':doc.xpath('//h1/text()'),'mainLinks':len(links),'roleLabels':dict(role_links),'sampleLinks':links[:6],'mainTextCharacters':len(''.join(doc.xpath('//main//text()'))),'roleChoiceSections':len(doc.xpath('//section[@id="related-intents" or @data-faq-role or @id="local-summary"]'))})
    dump(OUT/'next-hub-audit.json',{'scope':'existing root, subject, grade and category index hubs','pages':audited,'hubCount':len(audited),'deployed':False,'readOnly':True})
    print('Next-step hubs audited',len(audited),flush=True)

if __name__=='__main__':main()
