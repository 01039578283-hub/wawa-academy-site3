"""Add factual grade-confirmation labels to reviewed enrollment links only."""
from concurrent.futures import ThreadPoolExecutor
import argparse,hashlib,json,re
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import OUT,BACKUP,LABEL,ANCHORS,dump

BADGE='<span class="ns-grade-confirm-status">'+LABEL+'</span>'
CSS='''
/* Phase 6: confirmation status on links to enrollment pages with empty grade data. */
.ns-grade-confirm-link{display:inline-flex!important;flex-direction:column;align-items:flex-start!important;justify-content:center;gap:4px;min-width:0;min-height:44px;max-width:100%;box-sizing:border-box;white-space:normal;overflow-wrap:anywhere;color:#79381e!important;background:#fff!important;text-align:left}
.ns-grade-confirm-link:hover,.ns-grade-confirm-link:focus-visible{color:#79381e!important;background:#fff1e2!important}
.ns-grade-confirm-link:focus-visible{outline:3px solid #9a4629;outline-offset:3px}
.ns-grade-confirm-label{max-width:100%;color:inherit;white-space:normal;overflow-wrap:anywhere}
.ns-grade-confirm-status{display:block;max-width:100%;padding:2px 7px;border:1px solid #c5a967;border-radius:5px;background:#fff4d6;color:#593b00;font-size:12px;font-weight:600;line-height:1.6;white-space:normal;overflow-wrap:anywhere;box-sizing:border-box}
'''

def add_label(raw):
    opening,inner=raw.split('>',1);inner=inner.rsplit('</a',1)[0]
    assert '<' not in inner.strip(),raw
    if 'class="' in opening:
        opening=re.sub(r'class="([^"]*)"',lambda m:'class="'+m[1]+' ns-grade-confirm-link"',opening,count=1)
    else:opening+=' class="ns-grade-confirm-link"'
    return opening+' data-grade-confirmation="source-empty"><span class="ns-grade-confirm-label">'+inner+'</span>'+BADGE+'</a>'

def apply_page(page):
    path=impl.ROOT/page['file'];raw=path.read_bytes();old=raw.decode('utf-8')
    selected={a['anchorIndex'] for a in page['links'] if a['eligible']}
    if not selected:return None
    assert hashlib.sha256(raw).hexdigest()==page['sha256'],page['path']
    index=-1;changes=0
    def replace(match):
        nonlocal index,changes
        node=html.fromstring(match[0])
        if node.get('href') is None:return match[0]
        index+=1
        if index not in selected:return match[0]
        changes+=1;return add_label(match[0])
    new=ANCHORS.sub(replace,old);assert changes==len(selected)
    path.write_bytes(new.encode('utf-8'));assert path.read_bytes()==new.encode('utf-8')
    return {'path':page['path'],'file':page['file'],'links':changes,'beforeSha256':page['sha256'],'afterSha256':hashlib.sha256(new.encode('utf-8')).hexdigest()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    assert BACKUP.exists()
    audit=impl.load(OUT/'incoming-link-audit.json')
    pages=[p for p in audit['pages'] if any(a['eligible'] for a in p['links'])]
    if args.sample:
        samples=[]
        for role in ['comparison-guide','overview','study-guide','center-hub','enrollment']:
            samples.append(next(p for p in pages if p['role']==role))
        pages=samples
    done=impl.load(OUT/'implementation.json') if (OUT/'implementation.json').exists() else {'pages':[]}
    previous={p['file'] for p in done['pages']}
    for p in pages:
        if p['file'] in previous:
            prior=next(x for x in done['pages'] if x['file']==p['file'])
            current=hashlib.sha256((impl.ROOT/p['file']).read_bytes()).hexdigest()
            if current==prior['beforeSha256']:
                previous.remove(p['file']);done['pages'].remove(prior)
            else:assert current==prior['afterSha256'],p['file']
    pending=[p for p in pages if p['file'] not in previous]
    with ThreadPoolExecutor(max_workers=4) as pool:done['pages']+=list(pool.map(apply_page,pending))
    css_path=impl.ROOT/'assets/neighborhood-seo/local.css';raw=css_path.read_bytes()
    if CSS.strip() not in raw.decode('utf-8').replace('\r\n','\n'):css_path.write_bytes(raw+CSS.replace('\n','\r\n').encode('utf-8'))
    done.update(changedPages=len(done['pages']),changedLinks=sum(p['links'] for p in done['pages']),deployed=False)
    dump(OUT/'implementation.json',done)
    print(json.dumps({k:v for k,v in done.items() if k!='pages'},ensure_ascii=False))

if __name__=='__main__':main()
