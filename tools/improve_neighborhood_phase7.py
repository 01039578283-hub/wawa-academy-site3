"""Bounded hub finder, purposeful directory labels and aligned descriptions."""
import argparse,hashlib,json,re,zipfile
from urllib.parse import unquote,urlsplit
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase7 import OUT,BACKUP,ASSETS
from audit_neighborhood_phase6 import dump

SECTION=re.compile(r'<section\b(?=[^>]*\bid="choose-guide-purpose")[^>]*>.*?</section>',re.S)
TAGS=re.compile(r'<a\b[^>]*>.*?</a>',re.S)
META=re.compile(r'<meta\b[^>]*>',re.I)
SCRIPTS=re.compile(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',re.S)
CSS='''
/* Phase 7: purpose-based neighborhood finder on existing index pages. */
.nf-section{background:#fbf7ef;padding:32px 0;scroll-margin-top:110px}
.nf-section [hidden]{display:none!important}
.nf-section h2{font-size:28px;line-height:1.5;margin:0 0 14px;overflow-wrap:anywhere}
.nf-section p{line-height:1.8;margin:10px 0;overflow-wrap:anywhere}
.nf-purpose-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:22px 0}
.nf-purpose-grid article{min-width:0;padding:18px;border:1px solid #ddd0b9;border-radius:10px;background:white}
.nf-purpose-grid h3,.nf-result h3{font-size:18px;line-height:1.6;margin:0 0 8px;overflow-wrap:anywhere}
.nf-purpose-grid p{font-size:14px}
.nf-form{padding:22px;border:1px solid #d3c5b0;border-radius:12px;background:#fff}
.nf-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.nf-field{display:block;min-width:0;font-weight:700;font-size:15px;color:#493c30}
.nf-field input,.nf-field select{display:block;width:100%;min-width:0;max-width:100%;min-height:46px;margin-top:7px;padding:10px;border:1px solid #a69276;border-radius:6px;background:#fff;color:#292923;font:inherit;box-sizing:border-box}
.nf-field input:focus-visible,.nf-field select:focus-visible,.nf-link:focus-visible{outline:3px solid #9a4629;outline-offset:3px}
.nf-course-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;grid-column:1/-1}
.nf-message{font-size:14px;color:#5e5144;min-height:26px}
.nf-result{border-top:2px solid #c9ae89;margin-top:18px;padding-top:20px}
.nf-results,.nf-follow{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.nf-link{display:inline-flex;align-items:center;min-width:0;min-height:44px;max-width:100%;padding:10px 14px;border:1px solid #cbbfaa;border-radius:8px;box-sizing:border-box;color:#79381e;background:white;font-size:15px;font-weight:700;line-height:1.6;text-decoration:none;white-space:normal;overflow-wrap:anywhere}
.nf-link:hover{color:#79381e;background:#fff1e2}
.nf-note{font-size:14px}
.nf-follow .nf-link{font-size:14px;font-weight:500}
@media(max-width:760px){.nf-section{padding:24px 0;scroll-margin-top:210px}.nf-section h2{font-size:24px}.nf-purpose-grid{grid-template-columns:1fr;gap:10px}.nf-purpose-grid article{padding:14px}.nf-fields{grid-template-columns:1fr}.nf-course-fields{grid-column:auto}.nf-form{padding:16px}.nf-results,.nf-follow{display:grid;grid-template-columns:minmax(0,1fr)}}
'''

def configuration(page):
    category=page['category'];path=page['path']
    if category:
        topics={'전문학원':'학습관리학원','영수전문학원':'영어·수학학원','영어전문학원':'영어학원','수학전문학원':'수학학원','초등학생학원':'초등학생학원','중학생학원':'중학생학원','고등학생학원':'고등학생학원'}
        heading=topics[category]+' 비교 기준과 동네 안내 찾기'
        intro='수업을 비교할 때 '+impl.CATEGORIES[category][1]+'부터 살펴보세요. 동네별 선택 기준과 실제 지점의 수강 조건을 구분해 확인할 수 있습니다.'
        desc=topics[category]+' 선택 기준을 동네별로 찾고, 학생의 학년·과목에 맞는 수강 조건과 학습 점검 안내를 확인하세요.'
        purpose='comparison'
    else:
        heading={'/':'우리 동네 학원 안내, 목적에 맞게 찾기','/지점안내/':'동네별 수강 학년·위치 안내 찾기','/전국센터/':'동네별 학습 점검과 수강 안내 찾기','/과목별학원/':'과목·학년별 비교 기준과 동네 안내 찾기'}[path]
        intro={'/':'먼저 필요한 정보를 골라 보세요. 실제 수강 조건, 학생 답안의 점검 방법, 수업 선택 질문을 서로 다른 안내에서 확인할 수 있습니다.','/지점안내/':'동네를 고른 뒤 실제 지점의 안내 학년·주소·교습비를 확인하세요. 현재 모집 여부와 과목별 수업 장소는 해당 지점에 다시 확인합니다.','/전국센터/':'학생의 현재 학년과 과목을 기준으로 진도·오답 점검을 찾아보세요. 실제 수강 학년과 주소·교습비는 수강 안내에서 따로 확인합니다.','/과목별학원/':'영어·수학·학교급별로 비교할 질문을 찾아보세요. 동네의 선택 기준과 실제 지점의 수강 조건, 학습 점검을 나누어 확인할 수 있습니다.'}[path]
        desc={'/':'코칭학원의 동네·학년·과목별 수강 안내와 학습 점검, 비교 기준을 찾고 실제 지점의 주소·안내 학년·교습비를 확인하세요.','/지점안내/':'동네·학년·과목별 수강 안내에서 실제 지점의 주소·안내 학년·교습비 자료를 확인하고 상담을 준비하세요.','/전국센터/':'전국 371개 동네의 영어·수학 학습 점검을 학년별로 찾고, 실제 지점의 수강 조건과 비교 기준을 확인하세요.','/과목별학원/':'영어·수학·영수와 학교급별 학원 선택 기준을 동네별로 찾고, 수강 조건과 진도·오답 점검 안내를 확인하세요.'}[path]
        purpose='study' if path=='/전국센터/' else 'comparison' if path=='/과목별학원/' else 'enrollment'
    assert 0<len(desc)<=80
    return {'heading':heading,'intro':intro,'description':desc,'purpose':purpose,'category':category or '전문학원'}

def render(config):
    E=impl.E
    cards=[('수강·위치 안내','주소·안내 학년·교습비 원문과 운영 조건을 확인합니다.','/지점안내/'),('진도·오답 점검','초등·중등·고등 영어·수학의 학생 답안과 복습 기록을 살펴봅니다.','/전국센터/'),('비교·선택 기준','과목과 학교급에 맞춰 수업을 비교할 질문과 준비 자료를 정리합니다.','/과목별학원/')]
    def options(values,selected):return ''.join('<option value="'+E(value)+'"'+(' selected' if value==selected else '')+'>'+E(label)+'</option>' for value,label in values)
    contents='<section id="choose-guide-purpose" class="nf-section" data-neighborhood-finder="20261001-v7"><div class="wrap"><h2>'+E(config['heading'])+'</h2><p>'+E(config['intro'])+'</p>'
    cards_html='<div class="nf-purpose-grid">'
    for title,text,path in cards:cards_html+='<article><h3>'+title+'</h3><p>'+text+'</p><a class="nf-link" href="'+impl.U(path)+'">'+title+' 전체 목록</a></article>'
    cards_html+='</div>'
    contents+='<form class="nf-form" hidden aria-label="동네 안내 찾기"><div class="nf-fields">'
    contents+='<label class="nf-field" for="nf-search">동네·지역·지점 검색<input id="nf-search" data-nf-search type="search" placeholder="예: 명일동, 부천중동, 다산" autocomplete="off" aria-describedby="nf-message"></label>'
    contents+='<label class="nf-field" for="nf-area">동네 선택<select id="nf-area" data-nf-area><option value="">동네를 선택해 주세요</option></select></label>'
    contents+='<label class="nf-field" for="nf-purpose">안내 목적<select id="nf-purpose" data-nf-purpose>'+options([('enrollment','수강·위치 안내'),('study','진도·오답 점검'),('comparison','비교·선택 기준')],config['purpose'])+'</select></label>'
    contents+='<label class="nf-field" for="nf-category" data-nf-comparison-field>비교 주제<select id="nf-category" data-nf-category>'+options([(k,v[0]+'·선택 기준') for k,v in impl.CATEGORIES.items()],config['category'])+'</select></label>'
    contents+='<div class="nf-course-fields" data-nf-course-fields><label class="nf-field" for="nf-subject">과목<select id="nf-subject" data-nf-subject>'+options([('수학','수학'),('영어','영어')],'수학')+'</select></label><label class="nf-field" for="nf-stage">학교급<select id="nf-stage" data-nf-stage>'+options([(g,g) for g in ['전체','초등','중등','고등']],'전체')+'</select></label></div>'
    contents+='</div></form><p id="nf-message" class="nf-message" data-nf-message role="status" aria-live="polite">아래 지역·분류 목록에서도 동네 안내를 찾을 수 있습니다.</p><div class="nf-result" data-nf-result role="region" aria-label="선택한 동네 안내" aria-live="polite" hidden></div>'+cards_html+'</div></section>'
    def field(match):
        body=match[3];start=re.search(r'<(?:input|select)\b',body).start()
        return '<div class="nf-field"'+match[2]+'><label for="'+match[1]+'">'+body[:start]+'</label>'+body[start:]+'</div>'
    return re.sub(r'<label class="nf-field" for="([^"]+)"([^>]*)>(.*?)</label>',field,contents,flags=re.S)

def edit(page,old,config):
    section=render(config)
    if page['hasChooser']:new,count=SECTION.subn(lambda m:section,old);assert count==1
    else:
        main=re.search(r'<main\b[^>]*>',old);assert main
        first_end=old.index('</section>',main.end())+len('</section>');new=old[:first_end]+section+old[first_end:]
    links={a['href']:a for a in page['links']}
    def label(match):
        a=html.fromstring(match[0]);review=links.get(a.get('href'))
        if not review:return match[0]
        result,count=re.subn(r'<small>.*?</small>',lambda m:'<small>'+impl.E(review['afterSmall'])+'</small>',match[0],flags=re.S)
        assert count==1;return result
    new=TAGS.sub(label,new)
    def meta(match):
        node=html.fromstring(match[0]).xpath('//meta')[0];key=node.get('name') or node.get('property')
        if key not in ['description','og:description','twitter:description']:return match[0]
        result,count=re.subn(r'content="[^"]*"',lambda m:'content="'+impl.E(config['description'])+'"',match[0]);assert count==1;return result
    new=META.sub(meta,new)
    from validate_neighborhood_seo import nodes
    lookup={a['target']:a['after'] for a in page['links']}
    def schema(match):
        data=json.loads(match[2]);changed=False
        for node in nodes(data):
            if node.get('@type') in ['WebPage','CollectionPage','Article']:
                node['description']=config['description'];node['dateModified']='2026-10-01';changed=True
            elif node.get('@type')=='ListItem' and unquote(urlsplit(node.get('url','')).path) in lookup:
                node['name']=lookup[unquote(urlsplit(node['url']).path)];changed=True
        return match[1]+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+match[3] if changed else match[0]
    new=SCRIPTS.sub(schema,new)
    new=re.sub(r'<time datetime="\d{4}-\d{2}-\d{2}">\d{4}\.\d{2}\.\d{2}</time>','<time datetime="2026-10-01">2026.10.01</time>',new)
    if '/assets/neighborhood-seo/local.css' not in new:new=new.replace('</head>','<link rel="stylesheet" href="/assets/neighborhood-seo/local.css"></head>',1)
    new=new.replace('</head>','<script defer src="/assets/neighborhood-seo/find-guide.js?v=20261001-v7"></script></head>',1)
    return new

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    audit=impl.load(OUT/'hub-audit.json');pages=audit['pages']
    if args.sample:pages=[p for p in pages if p['path'] in ['/','/전국센터/','/과목별학원/수학전문학원/']]
    implementation=impl.load(OUT/'implementation.json') if (OUT/'implementation.json').exists() else {'pages':[]}
    reviewed=impl.load(OUT/'reviewed-pages.json') if (OUT/'reviewed-pages.json').exists() else {p['path']:configuration(p) for p in audit['pages']}
    dump(OUT/'reviewed-pages.json',reviewed)
    with zipfile.ZipFile(BACKUP) as snapshot:
        for p in pages:
            path=impl.ROOT/p['file'];base=snapshot.read(p['file']);assert hashlib.sha256(base).hexdigest()==p['sha256']
            new=edit(p,base.decode('utf-8'),reviewed[p['path']]).encode('utf-8')
            actual=path.read_bytes();previous=next((r for r in implementation['pages'] if r['path']==p['path']),None)
            assert actual in [base,new] or previous and hashlib.sha256(actual).hexdigest()==previous['sha256'],p['path']
            path.write_bytes(new)
            implementation['pages']=[r for r in implementation['pages'] if r['path']!=p['path']]+[{'path':p['path'],'file':p['file'],'links':len(p['links']),'sha256':hashlib.sha256(new).hexdigest()}]
        css=snapshot.read('assets/neighborhood-seo/local.css');addition=CSS.replace('\n','\r\n').encode('utf-8');path=impl.ROOT/'assets/neighborhood-seo/local.css'
        actual=path.read_bytes();assert actual.startswith(css) and actual[len(css):].count(b'/* Phase 7:')<=1;path.write_bytes(css+addition)
        sitemap_old=snapshot.read('sitemap.xml').decode('utf-8');sitemap=sitemap_old
        modified={r['path'] for r in implementation['pages']}
        def dates(match):
            block=match[0];loc=re.search(r'<loc>(.*?)</loc>',block);assert loc
            if unquote(urlsplit(loc[1]).path) not in modified:return block
            if '<lastmod>' in block:return re.sub(r'<lastmod>.*?</lastmod>','<lastmod>2026-10-01</lastmod>',block)
            return block.replace('</url>','<lastmod>2026-10-01</lastmod></url>')
        sitemap=re.sub(r'<url>.*?</url>',dates,sitemap,flags=re.S)
        (impl.ROOT/'sitemap.xml').write_bytes(sitemap.encode('utf-8'))
    public=impl.load(OUT/'reviewed-finder-data.json')
    (impl.ROOT/ASSETS[1]).write_text(json.dumps(public,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    implementation.update(changedHtmlPages=len(implementation['pages']),relabelledLinks=sum(r['links'] for r in implementation['pages']),deployed=False)
    dump(OUT/'implementation.json',implementation)
    print(json.dumps({k:v for k,v in implementation.items() if k!='pages'},ensure_ascii=False))

if __name__=='__main__':main()
