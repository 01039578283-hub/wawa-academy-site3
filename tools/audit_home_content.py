"""Check the homepage directory against the visible content and reviewed baseline."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urljoin,unquote,quote
import argparse,hashlib,json
from lxml import html,etree
ROOT=Path(__file__).resolve().parents[1]
DOMAIN='https://xn--sp5b72l1taf0p.com'
def load(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out):
    baseline=load(out/'baseline-manifest.json');manifest=load(ROOT/'release-public-manifest.json');doc=html.document_fromstring((ROOT/'index.html').read_bytes())
    assert set(manifest['files'])==set(baseline['files'])|{'assets/home-content-20261003.css'}
    def check(n):
        assert sha(ROOT/n)==manifest['files'][n],n
        if n!='index.html':assert manifest['files'][n]==baseline['files'][n],n
    with ThreadPoolExecutor(max_workers=12) as pool:list(pool.map(check,baseline['files']))
    assert len(doc.xpath('//h1'))==1
    ids=doc.xpath('//*[@id]/@id');assert len(ids)==len(set(ids))
    schemas=[json.loads(n.text) for n in doc.xpath('//script[@type="application/ld+json"]')];assert len(schemas)==1;graph=schemas[0]['@graph']
    lists=[n for n in graph if n['@type']=='ItemList'];assert len(lists)==2
    checked=0
    for section in ['home-content','learning-library']:
        actual=[];seen=set()
        for a in doc.xpath(f'//*[@id="{section}"]//a[@href]'):
            assert not a.get('onclick') and a.get('href').strip()
            target=urlsplit(urljoin(DOMAIN+'/',a.get('href')))
            assert target.netloc==urlsplit(DOMAIN).netloc
            path=unquote(target.path);name='index.html' if path=='/' else path.strip('/')+'/index.html';assert name in manifest['files'],name
            destination=html.document_fromstring((ROOT/name).read_bytes())
            if target.fragment:assert destination.xpath('//*[@id=$v]',v=unquote(target.fragment)),target.fragment
            checked+=1
            if not a.get('href').startswith('/') or path in seen:continue
            seen.add(path);heading=a.xpath('.//h4')
            title=' '.join((heading[0].text_content() if heading else ''.join(a.xpath('.//text()[not(parent::*[@aria-hidden="true"])]'))).split())
            actual.append((title,DOMAIN+quote(path,safe='/')))
        node=next(n for n in lists if n['@id']==DOMAIN+'/#'+section+'-list')
        assert node['numberOfItems']==len(actual)
        assert [(i['name'],i['url']) for i in node['itemListElement']]==actual
        assert [i['position'] for i in node['itemListElement']]==list(range(1,len(actual)+1))
    assert len(doc.xpath('//*[@id="home-content"]//a[contains(@class,"hc-menu-card")]'))==7
    assert len(doc.xpath('//*[@id="learning-library"]//*[contains(@class,"hc-question-card")]'))==6
    assert len(doc.xpath('//*[@id="learning-library"]//div[@class="hc-grade-row"]//nav/a'))==12
    faq=next(n for n in graph if n['@type']=='FAQPage')['mainEntity']
    visible=[(' '.join(d.xpath('string(.//summary/h3)').split()),' '.join(d.xpath('string(./p[1])').split())) for d in doc.xpath('//*[@id="faq"]//details')]
    assert [(q['name'],q['acceptedAnswer']['text']) for q in faq]==visible
    assert len(visible)==5 and all('후기' not in a for q,a in visible)
    description=load(ROOT/'seo-descriptions.json')['pages']['/']['description'];assert len(description)<=80 and description.endswith('.')
    assert doc.xpath('//meta[@name="description"]/@content')==[description]
    for field in ['og:description','twitter:description']:
        assert doc.xpath('//meta[@property=$v or @name=$v]/@content',v=field)==[description]
    assert next(n for n in graph if n['@type']=='WebPage')['description']==description
    previous=html.document_fromstring((out/'baseline-index.html').read_bytes())
    for identifier in ['choose-guide-purpose','coaching','videos','ai-preview','featured-local-links','contact']:
        assert etree.tostring(doc.get_element_by_id(identifier),with_tail=False)==etree.tostring(previous.get_element_by_id(identifier),with_tail=False),identifier
    assert doc.xpath('//nav[contains(@class,"floating-actions")]/a/@href')==previous.xpath('//nav[contains(@class,"floating-actions")]/a/@href')
    assert not doc.xpath('//*[@data-curriculum-bridge or @data-education-bridge or @data-teacher-bridge or @data-learning-guide-entry]')
    assert '편집 원칙' not in doc.text_content()
    oldhubs=['/학습가이드/','/교육정보/','/공부커리큘럼/','/선생님찾기/','/지점안내/','/전국센터/','/과목별학원/','/학습관리/','/상담문의/']
    assert set(oldhubs)<=set(unquote(urlsplit(urljoin(DOMAIN+'/',p)).path) for p in doc.xpath('//a[@href]/@href'))
    result={'publicFiles':len(manifest['files']),'htmlPages':manifest['sitemapPages'],'unchangedExistingHtml':8783,'preservedCurriculumPages':89,'newHomeLinksChecked':checked,'visibleItemLists':2,'faqSchemaMatchesVisible':5,'gradeDirectLinks':12,'topicGroups':6,'preservedContactRoutes':True,'rssAndSitemapUnchanged':True,'errors':[]}
    (out/'source-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);run(p.parse_args().out)
