"""Read-only audit of remaining regional index navigation and example facts."""
from urllib.parse import unquote,urlsplit,urljoin
from collections import Counter
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase7 import OUT,HUBS
from audit_neighborhood_phase6 import dump

def main():
    manifest=impl.load(impl.ROOT/'release-public-manifest.json');paths={r['path'] for r in impl.inventory()}
    region_pages=[]
    for name in manifest['files']:
        parts=name.split('/')
        if len(parts)!=3 or parts[-1]!='index.html' or parts[0] not in ['전국센터','지점안내']:continue
        path='/'+name.removesuffix('index.html')
        if path not in paths:region_pages.append((name,path))
    center_by_path={impl.center_path(c):c for c in impl.FACTS['centers']}
    results=[];conflicts=[];example_counts=0
    for name,path in region_pages+[(p.strip('/')+'/index.html' if p!='/' else 'index.html',p) for p in HUBS]:
        doc=html.document_fromstring((impl.ROOT/name).read_bytes());checked=[]
        for article in doc.xpath('//section[@id="hub-center-examples"]//article'):
            anchors=article.xpath('.//a[@href]');paragraphs=article.xpath('./p')
            if not anchors or len(paragraphs)<2:continue
            target=unquote(urlsplit(urljoin(impl.DOMAIN+impl.U(path),anchors[0].get('href'))).path)
            center=center_by_path.get(target)
            if not center:continue
            # Example summaries specify their displayed subjects and school level.
            displayed=''.join(paragraphs[1].itertext());subjects=[s for s in ['국어','영어','수학','과학','사회'] if s in displayed]
            stage='초등' if '초등' in path else '중등' if '중등' in path or '중학생학원' in path else '고등' if '고등' in path else None
            expected=' / '.join(s+' '+impl.pretty([g for g in center['subjects'][s] if not stage or g.startswith(stage[0])]) for s in subjects)
            record={'center':center['routeName'],'displayed':displayed,'confirmed':expected,'gradeAuthority':center.get('gradeAuthority'),'same':impl.norm(displayed)==impl.norm(expected)}
            checked.append(record);example_counts+=1
            if not record['same']:conflicts.append({'page':path,**record})
        if (name,path) in region_pages:
            results.append({'path':path,'file':name,'h1':doc.xpath('//h1/text()'),'finderPresent':bool(doc.xpath('//*[@data-neighborhood-finder]')),'localLinks':len(doc.xpath('//main//a[@href]')),'exampleGradeChecks':checked,'sections':doc.xpath('//main//section/@id')})
    grade_hubs=[r for r in results if any(g in r['path'] for g in ['초등','중등','고등'])]
    output={'remainingIndexHubs':len(results),'regionalHubs':len(results)-len(grade_hubs),'gradeSubjectHubs':len(grade_hubs),'byType':dict(Counter(r['path'].strip('/').split('/')[0] for r in results)),'pages':results,'exampleCardsChecked':example_counts,'exampleGradeConflicts':conflicts,'currentPhaseHubConflicts':sum(c['page'] in HUBS for c in conflicts),'readOnly':True,'deployed':False}
    dump(OUT/'next-regional-audit.json',output)
    print('Regional hubs',len(results),'example grade conflicts',len(conflicts),'phase-7 hub conflicts',output['currentPhaseHubConflicts'],flush=True)

if __name__=='__main__':main()
