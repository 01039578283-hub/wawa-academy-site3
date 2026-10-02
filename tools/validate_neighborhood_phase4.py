"""Full-page preservation and independent literal source-row checks."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import argparse,json,re,zipfile,hashlib
from lxml import html,etree
import improve_neighborhood_pages as impl
from audit_neighborhood_fees_phase4 import OUT

FEES=re.compile(r'<section\b(?=[^>]*\bid="fees")[^>]*>.*?</section>',re.S)
def protected_remainder(raw):
    value=FEES.sub('<section id="fees">REVIEWED FEES</section>',raw.decode('utf-8'))
    value=value.replace(' data-neighborhood-phase4="20261001-v4"','')
    value=value.replace('공통 참고표의 금액을 지점 확정 교습비로 판단하지 말고 교습비 자료와 상담 답변을 비교합니다.','원문 게시일을 확인하고 자료의 과정명·기간·교습시간과 상담에서 받은 최종 금액을 비교합니다.')
    value=re.sub(r'(<p\b[^>]*class="[^"]*(?:cl-revised|bc-updated)[^"]*"[^>]*>).*?(</p>)',r'\g<1>REVISION NOTE\g<2>',value,flags=re.S)
    def schema(match):
        data=json.loads(match[2])
        for node in data.get('@graph',[]):
            if node.get('@type') in ['WebPage','CollectionPage','Article']:node.pop('dateModified',None)
        return match[1]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+match[3]
    return re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',schema,value,flags=re.S)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    sources=impl.load(OUT/'fee-grid-verified.json');fees={(s['region'],s['center']):s for s in sources['centers']}
    rows=impl.inventory();by_path={r['path']:r for r in rows}
    by_path.update({impl.center_path(c):{'path':impl.center_path(c),'role':'center-hub','centerKey':[c['region'],c['routeName']]} for c in impl.FACTS['centers']})
    urls=etree.parse(str(impl.ROOT/'sitemap.xml')).xpath('//*[local-name()="loc"]/text()');errors=[];counts=Counter();changed=[];table_centers=set();literal_rows=0
    def read(url):
        path=impl.unquote(impl.urlsplit(url).path);name=path.strip('/')+'/index.html' if path!='/' else 'index.html'
        return path,name,(impl.ROOT/name).read_bytes()
    with ThreadPoolExecutor(max_workers=8) as pool:current=list(pool.map(read,urls))
    with zipfile.ZipFile(OUT/'phase3-before-phase4.zip') as archive:
        oldurls=etree.fromstring(archive.read('sitemap.xml')).xpath('//*[local-name()="loc"]/text()')
        if urls!=oldurls:errors.append(['sitemap','URLs or order changed'])
        for index,(path,name,raw) in enumerate(current,1):
            before=archive.read(name);marker=b'data-neighborhood-phase4="20261001-v4"' in raw
            if raw!=before:changed.append(path)
            if not marker:
                if raw!=before:errors.append([path,'Unmarked page byte change'])
                if path in by_path and not args.sample:errors.append([path,'Required fee guidance not applied'])
                continue
            if path not in by_path:errors.append([path,'Unexpected phase-4 path']);continue
            row=by_path[path];counts[row['role']]+=1;center=impl.CENTERS[tuple(row['centerKey'])];source=fees[tuple(row['centerKey'])]
            doc=html.document_fromstring(raw);old=html.document_fromstring(before);block=impl.byid(doc,'fees')
            if protected_remainder(raw)!=protected_remainder(before):errors.append([path,'Bytes outside bounded fee/revision fields changed'])
            if impl.protect(doc)!=impl.protect(old):errors.append([path,'URL/H1/index/media/contact changed'])
            if block.xpath('.//*[@data-fee-file]/@data-fee-file')!=[source['fileId']]:errors.append([path,'Wrong source association'])
            if source['feeLink'] not in block.xpath('.//a/@href'):errors.append([path,'Original source link missing'])
            if not all(link in block.xpath('.//a/@href') for link in impl.byid(old,'fees').xpath('.//a/@href')):errors.append([path,'Existing fee links lost'])
            if '현재 적용 금액과 모집 여부는 지점 상담에서 확인' not in block.text_content():errors.append([path,'Historical source distinction missing'])
            if not all(date in block.text_content() for date in source['sourceDates']):errors.append([path,'Source dates missing'])
            if block.xpath('.//table[contains(@class,"bc-fees-common")]'):errors.append([path,'Generic regional amounts retained as fee table'])
            displayed=block.xpath('.//tr[@data-fee-course]')
            if displayed:table_centers.add(tuple(row['centerKey']))
            if row['role'] in ['overview','study-guide','comparison-guide'] and displayed:errors.append([path,'Guide role contains enrollment price table'])
            for tr in displayed:
                literal_rows+=1;course=tr.get('data-fee-course');page=int(tr.get('data-fee-page'));name_text=tr.xpath('string(./th)');cells=tr.xpath('./td');amount=cells[-1].text or '';time_text=cells[0].text_content()
                candidates=[record for record in source['rows'] if record['courseKey']==course and record['page']==page and record['course']==name_text and amount==format(record['totalFee'],',')+'원' and record['printedDate'] in cells[-1].text_content() and record['period']==cells[0].text and '총 교습시간 '+record['totalTime'] in time_text]
                if not candidates:errors.append([path,'Rendered row differs from exact PDF grid cells: '+course]);continue
                record=candidates[0]
                if row.get('stage') and row['stage']!=record['stage']:errors.append([path,'Different school stage fee shown'])
                if row.get('subject') and row['subject'] not in record['subjects']:errors.append([path,'Different subject fee shown'])
                subjects=[row['subject']] if row.get('subject') else record['subjects']
                if not any(any(grade.startswith(record['stage'][0]) for grade in center['subjects'].get(subject,[])) for subject in subjects):errors.append([path,'Fee implies unsupported grade stage'])
                if center['routeName']=='수지점' and '수학' in record['subjects']:errors.append([path,'Parent branch price assigned to separate W+ venue'])
                if '원문 표의 시간 단위 미기재' not in time_text:errors.append([path,'Missing ambiguous time unit notice'])
            if displayed and '주당 횟수를 판단하지 마세요' not in block.text_content():errors.append([path,'Numeric course-code distinction missing'])
            # No new commercial Offer/price schema or service broadening.
            for query in ['//meta[@name="description"]/@content','//meta[@property="og:description"]/@content','//meta[@name="twitter:description"]/@content','string(//title)']:
                if doc.xpath(query)!=old.xpath(query):errors.append([path,'Reviewed metadata changed'])
            if index%2000==0:print('Validated phase-4 pages',index,flush=True)
    for source in sources['centers']:
        if hashlib.sha256((OUT/'source-pdfs'/(source['fileId']+'.pdf')).read_bytes()).hexdigest()!=source['sourceSha256']:errors.append([source['center'],'PDF bytes changed'])
    result={'sitemapPages':len(urls),'neighborhoodPages':sum(counts[r] for r in ['enrollment','overview','study-guide','comparison-guide']),'centerHubs':counts['center-hub'],'roles':dict(counts),'changedHtmlPages':len(changed),'unchangedHtmlPages':len(urls)-len(changed),'literalFeeRowOccurrences':literal_rows,'centersWithDisplayedRows':len(table_centers),'originalPDFsVerified':len(fees),'sourceGridRows':sources['gridValidation']['verifiedRows'],'sourceCentersWithBaseRows':sources['gridValidation']['withRows'],'sourceOnlyCenters':len(fees)-sources['gridValidation']['withRows'],'changedPaths':changed,'errors':errors,'deployed':False}
    impl.dump(OUT/('sample-validation.json' if args.sample else 'validation.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='changedPaths'},ensure_ascii=False),flush=True)
    assert not errors

if __name__=='__main__':main()
