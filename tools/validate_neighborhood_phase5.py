"""Independently check all pages, bounded preservation, facts and visible FAQ."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import argparse,hashlib,json,re,zipfile
from lxml import html,etree
import improve_neighborhood_pages as impl
from audit_neighborhood_phase5 import OUT,PRIOR,BACKUP,entries,filename

FAQ=re.compile(r'<section\b(?=[^>]*\bid="(?:faq|faq-section)")[^>]*>.*?</section>',re.S)
SCRIPT=re.compile(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',re.S)
def remainder(raw):
    value=FAQ.sub('',raw.decode('utf-8')).replace(' data-neighborhood-phase5="20261001-v5"','')
    def normalize(m):
        data=json.loads(m[2])
        for n in data.get('@graph',[]):
            if n.get('@type')=='FAQPage':n.pop('mainEntity',None)
        return m[1]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+m[3]
    return SCRIPT.sub(normalize,value)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    facts=impl.load(PRIOR/'fee-grid-verified.json');sources={(s['region'],s['center']):s for s in facts['centers']}
    reviewed=impl.load(OUT/'reviewed-faq.json');assert reviewed['centerFactsSha256']==hashlib.sha256((impl.DATA/'centers.json').read_bytes()).hexdigest()
    assert reviewed['sourceInputSha256']==hashlib.sha256((PRIOR/'fee-grid-verified.json').read_bytes()).hexdigest()
    records={p['path']:p for p in reviewed['pages']};by_path={r['path']:r for r in entries()}
    urls=etree.parse(str(impl.ROOT/'sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
    def read(url):
        path=impl.unquote(impl.urlsplit(url).path);return path,filename(path),(impl.ROOT/filename(path)).read_bytes()
    with ThreadPoolExecutor(max_workers=8) as pool:pages=list(pool.map(read,urls))
    errors=[];changed=[];counts=Counter();question_count=0;fee_answers=Counter();schemas=0;positions=0
    with zipfile.ZipFile(BACKUP) as archive:
        if archive.read('sitemap.xml')!=(impl.ROOT/'sitemap.xml').read_bytes():errors.append(['sitemap','Bytes changed although all changed pages already have current lastmod'])
        for index,(path,name,raw) in enumerate(pages,1):
            before=archive.read(name);marked=b'data-neighborhood-phase5="20261001-v5"' in raw
            if raw!=before:changed.append(path)
            if not marked:
                if raw!=before:errors.append([path,'Unmarked page changed'])
                if path in by_path and not args.sample:errors.append([path,'Missing phase 5'])
                continue
            if path not in by_path:errors.append([path,'Unexpected phase 5 page']);continue
            if remainder(raw)!=remainder(before):errors.append([path,'Original bytes outside FAQ/FAQPage changed'])
            row=by_path[path];c=impl.CENTERS[tuple(row['centerKey'])];s=sources[tuple(row['centerKey'])];record=records[path];counts[row['role']]+=1
            doc=html.document_fromstring(raw);old=html.document_fromstring(before)
            if impl.protect(doc)!=impl.protect(old):errors.append([path,'Canonical/H1/index/media/contact changed'])
            sections=doc.xpath('//main/section[@id="faq" or @id="faq-section"]')
            if len(sections)!=1:errors.append([path,'FAQ section count']);continue
            block=sections[0];main=doc.xpath('//main')[0];image=impl.byid(doc,'page-images')
            if main.index(block)>=main.index(image):errors.append([path,'FAQ below long images'])
            else:positions+=1
            if block.get('data-faq-role')!=row['role']:errors.append([path,'Wrong role'])
            details=block.xpath('.//details[summary]');question_count+=len(details)
            if len(details)!=5:errors.append([path,'Expected five useful questions'])
            visible=[{'@type':'Question','name':' '.join(d.xpath('./summary//text()')).strip(),'acceptedAnswer':{'@type':'Answer','text':' '.join(d.xpath('./p//text()')).strip()}} for d in details]
            schema=[n for script in doc.xpath('//script[@type="application/ld+json"]') for n in json.loads(script.text).get('@graph',[]) if n.get('@type')=='FAQPage']
            if len(schema)!=1 or schema[0]['mainEntity']!=visible:errors.append([path,'Visible FAQ and schema mismatch'])
            else:schemas+=1
            if [v['name'] for v in visible]!=[p['question'] for p in record['pairs']] or [v['acceptedAnswer']['text'] for v in visible]!=[p['answer'] for p in record['pairs']]:errors.append([path,'Reviewed content changed'])
            text=block.text_content();fee=block.xpath('.//details[@data-faq-kind="fees"]')
            if len(fee)!=1:errors.append([path,'Fee question count']);continue
            answer=' '.join(fee[0].xpath('./p//text()')).strip();fee_answers[answer]+=1
            if not all(d in answer for d in s['sourceDates']):errors.append([path,'Source date missing from answer'])
            if '게시 당시 안내' not in answer or '현재 적용 금액은 지점에 확인' not in answer:errors.append([path,'Historical fees presented as current'])
            if s['feeLink'] not in fee[0].xpath('.//a/@href'):errors.append([path,'Wrong original fee source'])
            if c['address'] not in text:errors.append([path,'Actual address missing'])
            subjects=[row['subject']] if row.get('subject') else (['영어','수학'] if row.get('stage') or row.get('category')=='영수전문학원' else ['국어','영어','수학','과학','사회'])
            for subject in subjects:
                grades=[g for g in c['subjects'].get(subject,[]) if not row.get('stage') or g.startswith(row['stage'][0])]
                if subject+' '+impl.pretty(grades) not in text:errors.append([path,'Subject/stage/grade fact missing: '+subject])
            authority='센터 데이터 엑셀' if c.get('gradeAuthority')=='workbook' else '센터 안내 CSV'
            if authority not in text:errors.append([path,'Wrong grade authority'])
            if c.get('gradeAuthority')!='workbook' and '세부 학년은 지점에 다시 확인' not in text:errors.append([path,'Missing unmatched workbook confirmation'])
            if c['routeName']=='수지점' and ('수지점(W+)' not in text or '실제 수업 장소를 따로 확인' not in text):errors.append([path,'Separate venue condition lost'])
            if c['routeName']=='침산점' and '고3 수업 마감' not in text:errors.append([path,'Grade closure source note lost'])
            if row['role'] in ['enrollment','center-hub']:
                for v in [c.get('openingReference'),c.get('weekend')]:
                    if v and v not in text:errors.append([path,'Operating reference differs from data'])
                if '수업 시작 시각과 다를 수' not in text:errors.append([path,'Opening/class distinction lost'])
                old_fee=impl.byid(old,'fees')
                if not old_fee.xpath('.//tr[@data-fee-course]') and '일반 과정 항목은 확인이 필요' not in answer:errors.append([path,'Missing unconfirmed general fee condition'])
            if row['role']=='study-guide' and '학생 답안을 점검하는 방법' not in text:errors.append([path,'Learning advice attributed to center'])
            for a in block.xpath('.//a[@target="_blank"]'):
                if 'noopener' not in (a.get('rel') or '').split():errors.append([path,'External link relation missing'])
            for href in block.xpath('.//a[starts-with(@href,"#")]/@href'):
                if not doc.xpath('//*[@id=$id]',id=impl.unquote(href[1:])):errors.append([path,'Missing local FAQ link target: '+href])
            if index%1500==0:print('Checked FAQ preservation and facts',index,flush=True)
    for s in sources.values():
        if hashlib.sha256((PRIOR/'source-pdfs'/ (s['fileId']+'.pdf')).read_bytes()).hexdigest()!=s['sourceSha256']:errors.append([s['center'],'Original PDF hash changed'])
    result={'sitemapPages':len(pages),'changedHtmlPages':len(changed),'unchangedHtmlPages':len(pages)-len(changed),'neighborhoodPages':sum(n for role,n in counts.items() if role!='center-hub'),'centerHubs':counts['center-hub'],'roles':dict(counts),'questions':question_count,'faqSchemasMatchingVisibleContent':schemas,'faqBeforeOriginalImages':positions,'feeAnswersWithSourceDateContext':sum(fee_answers.values()),'distinctFeeAnswers':len(fee_answers),'originalPdfsVerified':len(sources),'errors':errors,'deployed':False}
    if not args.sample:
        if len(changed)!=8355:errors.append(['scope','Expected 8355 changed HTML pages'])
        if question_count!=41775:errors.append(['scope','Expected 41775 FAQ questions'])
    impl.dump(OUT/('sample-validation.json' if args.sample else 'validation.json'),result)
    print(json.dumps({**result,'errors':errors[:15],'errorCount':len(errors)},ensure_ascii=False));raise SystemExit(bool(errors))

if __name__=='__main__':main()
