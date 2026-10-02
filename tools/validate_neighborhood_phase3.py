"""Independent phase-3 checks against the immutable reviewed phase-2 ZIP."""
import argparse, hashlib, json, zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from lxml import html, etree
import improve_neighborhood_pages as impl
import improve_neighborhood_phase3 as phase3
from audit_neighborhood_phase3 import OUT, audit

def picture_layout(doc):
    return [(image.get('src'),image.get('data-role'),image.get('width'),image.get('height'),image.get('loading')) for image in doc.xpath('//main//img')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    rows=impl.inventory();by_path={row['path']:row for row in rows};errors=[];counts=Counter();names_count=0;caption_count=0;changed=[]
    photos=phase3.photo_data()
    def fail(path,message):errors.append([path,message])
    urls=etree.parse(str(impl.ROOT/'sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
    def read_current(url):
        path=impl.unquote(impl.urlsplit(url).path)
        name=path.strip('/')+'/index.html' if path!='/' else 'index.html'
        return path,(impl.ROOT/name).read_bytes()
    with ThreadPoolExecutor(max_workers=8) as pool:
        current_html=dict(pool.map(read_current,urls))
    with zipfile.ZipFile(OUT/'phase2-before-phase3.zip') as archive:
        old_urls=etree.fromstring(archive.read('sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
        if urls!=old_urls:fail('sitemap','URL set/order changed')
        for index,url in enumerate(urls,1):
            path=impl.unquote(impl.urlsplit(url).path);name=path.strip('/')+'/index.html' if path!='/' else 'index.html'
            before=archive.read(name);raw=current_html[path];old=html.document_fromstring(before);doc=html.document_fromstring(raw)
            marker=doc.xpath('//body/@data-neighborhood-phase3')==[phase3.VERSION]
            if raw!=before:changed.append(path)
            if impl.protect(old)!=impl.protect(doc):fail(path,'URL/H1/index/media/contact protection')
            if picture_layout(old)!=picture_layout(doc):fail(path,'Original image order/dimensions/loading changed')
            for query in ['string(//title)','//meta[@name="description"]/@content','//meta[@property="og:description"]/@content','//meta[@name="twitter:description"]/@content']:
                if old.xpath(query)!=doc.xpath(query):fail(path,'Previously reviewed metadata changed')
            if not marker and raw!=before:fail(path,'Unmarked page changed')
            if path in by_path:
                row=by_path[path];center=impl.CENTERS[tuple(row['centerKey'])]
                if not marker:
                    if not args.sample:fail(path,'Missing phase-3 marker')
                    continue
                counts[row['role']]+=1
                school=impl.byid(doc,'schools') if impl.byid(doc,'schools') is not None else impl.byid(doc,'center-schools')
                main=doc.xpath('//main')[0];image=impl.byid(doc,'page-images')
                if school is None or main.index(school)>=main.index(image):fail(path,'School facts not before body image');continue
                # Resolve the exact local school area independently; never use
                # the combined center-wide list or a different nearby town.
                area=next(item for item in center['schoolAreas'] if impl.norm(item['neighborhood'])==impl.norm(row['neighborhood']))
                kinds=[phase3.KINDS[row['stage']]] if row.get('stage') else list(phase3.KINDS.values())
                blocks=school.xpath('.//article[@data-school-kind]')
                if [block.get('data-school-kind') for block in blocks]!=kinds:fail(path,'School stage filtering')
                for kind,block in zip(kinds,blocks):
                    names=list(dict.fromkeys(area['schools'].get(kind,[])))
                    if block.xpath('.//ul[@class="ns-school-names"]/li/text()')!=names:fail(path,'School list not exact/complete for this local area')
                    names_count+=len(names)
                    prefix=next(stage[0] for stage,value in phase3.KINDS.items() if value==kind)
                    subjects=impl.subjects_for(row)
                    facts=block.xpath('.//*[@data-school-subject]')
                    if [item.get('data-school-subject') for item in facts]!=subjects:fail(path,'School course filtering')
                    for subject,item in zip(subjects,facts):
                        grades=[grade for grade in center['subjects'][subject] if grade.startswith(prefix)]
                        if item.xpath('./dd/text()')!=[impl.pretty(grades)]:fail(path,'School card grade differs from confirmed center data')
                if row['role']=='study-guide':
                    scenarios=impl.byid(doc,'student-fit')
                    if main.index(scenarios)>=main.index(image):fail(path,'Student scenarios buried after image')
                    guide=impl.byid(doc,'intent-guide');target='/학습관리/#'+phase3.profile_anchor(row['stage'],row['subject'])
                    if guide.xpath('.//a/@href').count(impl.U(target))!=1:fail(path,'Wrong shared guide target')
                    if len(scenarios.xpath('.//article'))!=3:fail(path,'Diagnostic scenarios lost')
            elif marker and path.startswith('/지점안내/'):
                _,region,center_name=path.strip('/').split('/');center=impl.CENTERS[region,center_name];counts['center-hub']+=1
            elif path=='/학습관리/':
                if not marker:fail(path,'Shared guide missing')
                counts['shared-guide']+=1;center=None
                for stage in phase3.KINDS:
                    for subject in ['영어','수학']:
                        detail=impl.byid(doc,phase3.profile_anchor(stage,subject));checks=impl.GUIDE_CHECKS[stage+'-'+subject][1]
                        if detail is None:fail(path,'Missing shared topic');continue
                        articles=detail.xpath('.//article')
                        if [(item.xpath('string(./h3)'),item.xpath('string(./p)')) for item in articles]!=checks:fail(path,'Shared question explanations changed/lost')
            else:center=None
            if marker and center:
                block=impl.byid(doc,'learning-space')
                if center['photoMode']=='center':
                    mapping=photos[center['region'],center['routeName']]
                    if block.xpath('string(.//h2)')!=center['routeName']+' 제공 사진':fail(path,'All branch photos incorrectly described as facilities')
                    for image in block.xpath('.//img[@data-role="space-image"]'):
                        caption=mapping[image.get('src')]['caption']
                        if image.get('alt')!=caption.replace(' — ',' ') or image.getparent().xpath('./figcaption/text()')!=[caption]:fail(path,'Missing reviewed picture caption')
                        caption_count+=1
                elif '브랜드 공통 학습 공간 예시' not in block.text_content():fail(path,'Common provenance lost')
            if index%2000==0:print('Validated phase-3 pages',index,flush=True)
    # All reviewed raw source pictures and existing public assets are unchanged.
    picture_sources=impl.load(OUT/'photo-audit.json')
    for entry in picture_sources['entries']:
        for photo in entry['photos']:
            from audit_neighborhood_photos_phase3 import SOURCE
            if hashlib.sha256((SOURCE/photo['original']).read_bytes()).hexdigest()!=photo['originalSha256']:fail(entry['center'],'Supplied photo changed')
            if hashlib.sha256((impl.ROOT/photo['src'].lstrip('/')).read_bytes()).hexdigest()!=photo['publicSha256']:fail(entry['center'],'Existing public picture changed')
    result={'sitemapPages':len(urls),'phase3NeighborhoodPages':sum(counts[role] for role in ['enrollment','study-guide','comparison-guide','overview']),'roles':dict(counts),'centerHubs':counts['center-hub'],'fullSchoolNameOccurrences':names_count,'reviewedCaptionOccurrences':caption_count,'changedHtmlPages':len(changed),'changedPaths':changed,'errors':errors,'deployed':False}
    if not args.sample:
        if result['phase3NeighborhoodPages']!=8162 or counts['center-hub']!=96 or counts['shared-guide']!=1:fail('coverage','Incomplete phase-3 scope')
        overlap=audit(rows,lambda row:current_html[row['path']]);impl.dump(OUT/'after.json',overlap)
    impl.dump(OUT/('sample-validation.json' if args.sample else 'validation.json'),result)
    print(json.dumps({key:value for key,value in result.items() if key!='changedPaths'},ensure_ascii=False));raise SystemExit(bool(errors))
if __name__=='__main__':main()
