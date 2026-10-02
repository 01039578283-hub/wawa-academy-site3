"""Review all routes for a factual neighborhood finder and eleven hub pages."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote,urlsplit,urljoin
import hashlib,json,zipfile
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import dump,state
from audit_neighborhood_phase5 import filename

OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase7-20261001')
PRIOR=OUT.parent/'site3-neighborhood-phase6-20261001'
BACKUP=OUT/'phase6-before-phase7.zip'
BASE_SHA='02330914792325d2e063a62bf5872c2200d2ec4e438d2ac88fb0b8c8fc634c39'
ASSETS=['assets/neighborhood-seo/find-guide.js','assets/neighborhood-seo/find-guide.json']
HUBS=['/','/지점안내/','/전국센터/','/과목별학원/']+['/과목별학원/'+c+'/' for c in impl.CATEGORIES]

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest_raw=(impl.ROOT/'release-public-manifest.json').read_bytes();assert hashlib.sha256(manifest_raw).hexdigest()==BASE_SHA
    manifest=json.loads(manifest_raw);rows=impl.inventory();by_path={r['path']:r for r in rows}
    assert len(by_path)==8162 and all(filename(p) in manifest['files'] for p in HUBS)
    def title(row):
        raw=(impl.ROOT/filename(row['path'])).read_bytes();assert hashlib.sha256(raw).hexdigest()==manifest['files'][filename(row['path'])]
        headings=html.document_fromstring(raw).xpath('//h1');assert len(headings)==1
        return row['path'],' '.join(headings[0].itertext()).strip()
    with ThreadPoolExecutor(max_workers=8) as pool:titles=dict(pool.map(title,[r for r in rows if r['role']=='comparison-guide']))
    areas={}
    for row in rows:
        key=impl.norm(row['neighborhood']);center=impl.CENTERS[tuple(row['centerKey'])]
        if key not in areas:areas[key]={'id':key,'name':row['neighborhood'],'region':center['region'],'district':center['district'],'center':center['routeName'],'branch':impl.center_path(center),'enrollment':{},'study':{},'comparison':{}}
        area=areas[key];assert area['center']==center['routeName']
        stage=row.get('stage','전체');subject=row.get('subject')
        if row['role']=='overview':area['overview']=row['path']
        elif row['role']=='enrollment':
            area['enrollment'].setdefault(subject,{})[stage]={'href':row['path'],'label':(stage+' ' if stage!='전체' else '')+subject+' 수강·위치 안내','unconfirmed':not bool(impl.grades_for(row,center,subject))}
        elif row['role']=='study-guide':area['study'].setdefault(subject,{})[stage]={'href':row['path'],'label':stage+' '+subject+' 진도·오답 점검'}
        elif row['role']=='comparison-guide':area['comparison'][row['category']]={'href':row['path'],'label':titles[row['path']]}
    assert len(areas)==371
    for area in areas.values():
        assert len(area['comparison'])==7 and all(len(v)==4 for v in area['enrollment'].values()) and all(len(v)==3 for v in area['study'].values())
    dataset={'version':'20261001-v7','areas':sorted(areas.values(),key=lambda a:(a['region'],a['district'],a['name']))}
    dump(OUT/'reviewed-finder-data.json',dataset)
    pages=[];labels=0
    for path in HUBS:
        name=filename(path);raw=(impl.ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==manifest['files'][name]
        doc=html.document_fromstring(raw);category=path.strip('/').split('/')[-1] if path.startswith('/과목별학원/') and path!='/과목별학원/' else None
        links=[]
        for index,a in enumerate(doc.xpath('//a[@href]')):
            target=unquote(urlsplit(urljoin(impl.DOMAIN+impl.U(path),a.get('href'))).path)
            if category and target in titles and by_path[target].get('category')==category:
                assert len(a)==2 and a[0].tag=='strong' and a[1].tag=='small',name
                neighborhood=by_path[target]['neighborhood'];assert titles[target].startswith(neighborhood+' '),target
                caption=titles[target][len(neighborhood)+1:]
                links.append({'anchorIndex':index,'href':a.get('href'),'target':target,'before':' '.join(a.itertext()).strip(),'after':' '.join(a[0].itertext()).strip()+' '+caption,'beforeSmall':a[1].text,'afterSmall':caption})
        if category:assert len(links)==371,name
        labels+=len(links)
        pages.append({'path':path,'file':name,'category':category,'sha256':manifest['files'][name],'oldDescription':doc.xpath('//meta[@name="description"]/@content')[0],'hasChooser':bool(doc.xpath('//section[@id="choose-guide-purpose"]')),'links':links})
    assert labels==2597
    audit={'pages':pages,'hubPages':11,'neighborhoods':371,'existingNeighborhoodRoutes':8162,'relabelledDirectoryLinks':labels,'roles':dict(Counter(r['role'] for r in rows)),'privacy':'Public dataset is a whitelist of existing neighborhood names, public center names and reviewed routes; no raw center objects or workbook sales notes.','deployed':False}
    dump(OUT/'hub-audit.json',audit);dump(OUT/'original-source-state.json',state())
    names=[n for n in manifest['files'] if n.endswith('.html')]+['sitemap.xml','assets/neighborhood-seo/local.css','release-public-manifest.json']
    names+=['tools/data/neighborhood-seo/'+p.name for p in impl.DATA.glob('*.json')]
    names+=['tools/'+p.name for p in (impl.ROOT/'tools').glob('*phase6*.py')]
    assert all(not (impl.ROOT/name).exists() for name in ASSETS)
    if not BACKUP.exists():
        with zipfile.ZipFile(BACKUP,'x',zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
            with ThreadPoolExecutor(max_workers=8) as pool:
                for name,raw in pool.map(lambda n:(n,(impl.ROOT/n).read_bytes()),names):
                    if name in manifest['files']:assert hashlib.sha256(raw).hexdigest()==manifest['files'][name],name
                    archive.writestr(name,raw)
    with zipfile.ZipFile(BACKUP) as archive:
        assert archive.testzip() is None and archive.read('release-public-manifest.json')==manifest_raw
        assert len([n for n in archive.namelist() if n.endswith('.html')])==8403
    dump(OUT/'backup-verification.json',{'name':BACKUP.name,'sha256':hashlib.sha256(BACKUP.read_bytes()).hexdigest(),'bytes':BACKUP.stat().st_size,'htmlPages':8403})
    print(json.dumps({k:v for k,v in audit.items() if k!='pages'},ensure_ascii=False),flush=True)

if __name__=='__main__':prepare()
