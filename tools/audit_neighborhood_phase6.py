"""Audit all incoming links to enrollment pages without source grade rows."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin,urlsplit,unquote
import hashlib,json,re,subprocess,zipfile
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase5 import filename

OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase6-20261001')
PRIOR=OUT.parent/'site3-neighborhood-phase5-20261001'
BACKUP=OUT/'phase5-before-phase6.zip'
BASE_SHA='bc4a40d4362767d097c28d48e5dbe2164ee984090858119cfb3e26857fc299d6'
LABEL='자료상 학년 확인 필요'
ANCHORS=re.compile(r'<a\b[^>]*>.*?</a>',re.S|re.I)

def dump(path,data):
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',encoding='utf-8') as handle:
        for part in json.JSONEncoder(ensure_ascii=False,indent=2).iterencode(data):handle.write(part)
        handle.write('\n')
    temp.replace(path)

def targets():
    return {r['path']:r for r in impl.inventory() if r['role']=='enrollment' and not impl.grades_for(r,impl.CENTERS[tuple(r['centerKey'])],r['subject'])}

def destination(path,href):
    parsed=urlsplit(urljoin(impl.DOMAIN+impl.U(path),href))
    if parsed.netloc!=urlsplit(impl.DOMAIN).netloc:return None
    return unquote(parsed.path)

def state():
    source=Path(r'C:\Users\1992k\Desktop\홈페이지 작업 폴더\홈페이지 정리\새 홈페이지3')
    def git(*args):return subprocess.run(['git',*args],cwd=source,check=True,capture_output=True).stdout.decode('utf-8').splitlines()
    return {'head':git('rev-parse','HEAD')[0],'statusEntries':len(git('status','--porcelain')),'stagedEntries':len(git('diff','--cached','--name-only')),'expandedUntrackedStatusEntries':len(git('status','--porcelain','--untracked-files=all'))}

def audit():
    OUT.mkdir(parents=True,exist_ok=True)
    raw_manifest=(impl.ROOT/'release-public-manifest.json').read_bytes()
    assert hashlib.sha256(raw_manifest).hexdigest()==BASE_SHA
    manifest=json.loads(raw_manifest); candidates=targets(); assert len(candidates)==55
    rows={r['path']:r for r in impl.inventory()}
    for c in impl.FACTS['centers']:rows[impl.center_path(c)]={'role':'center-hub','centerKey':[c['region'],c['routeName']]}
    names=[n for n in manifest['files'] if n.endswith('.html')]
    def scan(name):
        path='/' if name=='index.html' else '/'+name.removesuffix('index.html')
        raw=(impl.ROOT/name).read_bytes(); assert hashlib.sha256(raw).hexdigest()==manifest['files'][name],name
        doc=html.document_fromstring(raw);matches=[]
        for i,a in enumerate(doc.xpath('//a[@href]')):
            target=destination(path,a.get('href'))
            if target not in candidates:continue
            ancestors=a.xpath('ancestor::*[@id]'); section=ancestors[-1].get('id') if ancestors else ''
            breadcrumb=bool(a.xpath('ancestor::nav[contains(concat(" ",normalize-space(@class)," ")," bc-breadcrumb ")]'))
            same_page=target==path
            matches.append({'anchorIndex':i,'href':a.get('href'),'target':target,'label':impl.norm(' '.join(a.itertext())),'section':section,'eligible':not same_page and not breadcrumb,'exclusion':'same-page section' if same_page else 'location breadcrumb' if breadcrumb else None,'innerHtml':html.tostring(a,encoding='unicode')})
        if not matches:return None
        # Raw matching has the same anchor order as the parser on reviewed HTML.
        parsed=[html.fromstring(m[0]) for m in ANCHORS.finditer(raw.decode('utf-8'))]
        assert [a.get('href') for a in parsed if a.get('href') is not None]==doc.xpath('//a[@href]/@href'),name
        return {'file':name,'path':path,'role':rows.get(path,{}).get('role','other'),'sha256':manifest['files'][name],'links':matches}
    with ThreadPoolExecutor(max_workers=8) as pool:pages=[p for p in pool.map(scan,names) if p]
    counts=Counter(a['section'] for p in pages for a in p['links'])
    data={'sitemapPages':len(names),'targetPages':len(candidates),'sourcePages':len(pages),'incomingLinks':sum(len(p['links']) for p in pages),'eligibleLinks':sum(a['eligible'] for p in pages for a in p['links']),'eligibleSourcePages':sum(any(a['eligible'] for a in p['links']) for p in pages),'excluded':dict(Counter(a['exclusion'] for p in pages for a in p['links'] if not a['eligible'])),'bySection':dict(counts),'byRole':dict(Counter(p['role'] for p in pages)),'targets':[dict(r,grades=impl.grades_for(r,impl.CENTERS[tuple(r['centerKey'])],r['subject'])) for r in candidates.values()],'pages':pages,'meaning':'Missing grades in the supplied authority do not mean classes are unavailable. Preserve routes and label confirmation status.','deployed':False}
    dump(OUT/'incoming-link-audit.json',data); dump(OUT/'original-source-state.json',state())
    print(json.dumps({k:v for k,v in data.items() if k not in ['pages','targets']},ensure_ascii=False),flush=True)
    print(json.dumps(pages[:2],ensure_ascii=False),flush=True)

def backup():
    raw=(impl.ROOT/'release-public-manifest.json').read_bytes(); assert hashlib.sha256(raw).hexdigest()==BASE_SHA
    manifest=json.loads(raw)
    names=[n for n in manifest['files'] if n.endswith('.html')]+['sitemap.xml','assets/neighborhood-seo/local.css','release-public-manifest.json']
    names+=['tools/data/neighborhood-seo/'+p.name for p in impl.DATA.glob('*.json')]
    names+=['tools/'+p.name for p in (impl.ROOT/'tools').glob('*phase5.py')]
    if not BACKUP.exists():
        with zipfile.ZipFile(BACKUP,'x',zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
            with ThreadPoolExecutor(max_workers=8) as pool:
                for name,content in pool.map(lambda n:(n,(impl.ROOT/n).read_bytes()),names):
                    if name in manifest['files']:assert hashlib.sha256(content).hexdigest()==manifest['files'][name],name
                    archive.writestr(name,content)
            archive.write(PRIOR/'reviewed-faq.json','phase5/reviewed-faq.json')
    with zipfile.ZipFile(BACKUP) as archive:
        assert archive.testzip() is None
        assert archive.read('release-public-manifest.json')==raw
        assert len([n for n in archive.namelist() if n.endswith('.html')])==8403
    result={'name':BACKUP.name,'sha256':hashlib.sha256(BACKUP.read_bytes()).hexdigest(),'bytes':BACKUP.stat().st_size,'htmlPages':8403,'deployed':False}
    dump(OUT/'backup-verification.json',result); print(json.dumps(result),flush=True)

if __name__=='__main__':
    import sys
    if '--backup' in sys.argv:backup()
    else:audit()
