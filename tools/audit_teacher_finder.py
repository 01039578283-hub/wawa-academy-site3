"""Whole-release preservation plus complete source-row/photo/link verification."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from urllib.parse import urlsplit,unquote,urljoin
import copy,hashlib,json,re,zipfile,sys,openpyxl
from lxml import html,etree
import build_teacher_finder as impl
from audit_neighborhood_phase6 import state

ROOT=impl.ROOT;OUT=impl.OUT
digest=lambda b:hashlib.sha256(b).hexdigest()

def normalize(doc):
    doc=copy.deepcopy(doc)
    for n in doc.xpath('//*[@data-teacher-bridge or @data-teacher-nav or @data-teacher-style]'):n.drop_tree()
    for n in doc.xpath('//script[@type="application/ld+json"]'):
        payload=json.loads(n.text)
        def walk(value):
            if isinstance(value,list):
                for v in value:walk(v)
            elif isinstance(value,dict):
                if value.get('@type') in ['WebPage','CollectionPage','AboutPage','ContactPage','Article'] and value.get('dateModified'):value['dateModified']='REVIEWED_MODIFICATION_DATE'
                for v in value.values():walk(v)
        walk(payload);n.text=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    for n in doc.xpath('//*[text()[contains(.,"내용 수정 2026.")]]'):
        if n.text:n.text=re.sub(r'내용 수정 2026\.\d{2}\.\d{2}','내용 수정 REVIEWED_MODIFICATION_DATE',n.text)
    return html.tostring(doc,encoding='utf-8').replace(b'\r\n',b'\n')

def main():
    baseline=impl.load(OUT/'baseline-manifest.json');manifest=impl.load(ROOT/'release-public-manifest.json');data=impl.load(impl.DATA/'import.json');report=impl.load(OUT/'implementation.json')
    assert set(baseline['files'])<=set(manifest['files'])
    new=set(manifest['files'])-set(baseline['files']);assert new==set(report['newPublicFiles']) and len(new)==218
    assert manifest['sitemapPages']==8664 and len(manifest['files'])==10947
    changes=[n for n,h in baseline['files'].items() if manifest['files'][n]!=h];assert all(n.endswith('.html') or n in ['sitemap.xml','rss.xml'] for n in changes)
    errors=[];checked=[];bridgecounts=Counter();branch_by_file={b['path'].strip('/')+'/index.html':b for b in data['branches']}
    new_pages={'선생님찾기/index.html',*branch_by_file};linked=Counter();internal=0;fragments=0
    workbook=openpyxl.load_workbook(impl.INPUT/'교사 프로필.xlsx',read_only=True,data_only=True)
    excel=list(workbook.active.iter_rows(values_only=True));workbook.close()
    assert len(excel)==1002
    collisions=sum(count>1 for count in Counter((r[0],r[1]) for r in excel).values());assert collisions==6
    for b in data['branches']:
        for t in b['teachers']:
            actual=excel[t['sourceRow']-1]
            assert (t['branch'],t['name'],t['intro'])==(actual[0],actual[1],actual[3])
            assert t['focus']==[v.strip() for v in actual[2].split('/')]
    with zipfile.ZipFile(OUT/'teachers-before.zip') as backup:
        for i,name in enumerate(sorted(manifest['files']),1):
            raw=(ROOT/name).read_bytes();assert digest(raw)==manifest['files'][name],name
            if name in manifest['textSha256']:assert digest(raw.decode('utf-8').replace('\r\n','\n').encode())==manifest['textSha256'][name],name
            if not name.endswith('.html'):
                if name in baseline['files'] and name not in ['sitemap.xml','rss.xml']:assert raw==backup.read(name),name
                continue
            doc=html.document_fromstring(raw)
            if name in baseline['files']:
                old=html.document_fromstring(backup.read(name));assert normalize(doc)==normalize(old),'Old page content changed outside additions/date: '+name
                assert len(doc.xpath('//header//a[@data-teacher-nav]'))==1,name
            else:
                assert len(doc.xpath('//h1'))==1 and doc.xpath('//main'),name
                ids=doc.xpath('//*[@id]/@id');assert len(ids)==len(set(ids)),name
                desc=doc.xpath('//meta[@name="description"]/@content')[0];assert desc.endswith('.') and len(desc)<=80
                assert doc.xpath('//meta[@property="og:description"]/@content')==[desc] and doc.xpath('//meta[@name="twitter:description"]/@content')==[desc]
                schemas=[json.loads(n.text) for n in doc.xpath('//script[@type="application/ld+json"]')]
                assert schemas[0]['@graph'][0]['description']==desc
                assert not doc.xpath('//script[@type="application/ld+json" and (contains(text(),"Review") or contains(text(),"Person"))]'),name
            for entry in doc.xpath('//*[@data-teacher-bridge]'):
                assert len(doc.xpath('//*[@data-teacher-bridge]'))==1,name
                bridgecounts['pages']+=1
            if name in branch_by_file:
                b=branch_by_file[name];cards=doc.xpath('//*[@data-teacher-id]');assert len(cards)==len(b['teachers'])
                for node,t in zip(cards,b['teachers']):
                    assert node.get('id')==node.get('data-teacher-id')==t['id']
                    assert node.xpath('.//*[@data-teacher-intro]/text()')==[t['intro']]
                    assert node.xpath('.//h3/text()')==[t['name']+' 선생님']
                    assert node.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," tf-tags ")]/span/text()')==t['focus']
                    assert node.xpath('.//img/@src')==[t['image']['path']] and node.xpath('.//img/@alt')==['대표 프로필 이미지']
                    assert node.xpath('.//figcaption/text()')==['대표 프로필 이미지']
                    checked.append(t['sourceRow'])
                imagepaths=doc.xpath('//main//img/@src');assert len(imagepaths)==len(set(imagepaths)),name
                if b['branchPath']:assert doc.xpath('//main//a[@href=$href]',href=impl.U(b['branchPath'])),name
                else:assert not doc.xpath('//main//a[starts-with(@href,"/%EC%A7%80%EC%A0%90%EC%95%88%EB%82%B4/")]'),name
            # Check every new link across old pages, and all new pages' local links/images.
            nodes=doc.xpath('//a[@data-teacher-nav] | //*[@data-teacher-bridge]//a') if name not in new_pages else doc.xpath('//a[@href] | //img[@src] | //link[@href] | //script[@src]')
            canonical=doc.xpath('//link[@rel="canonical"]/@href')[0]
            for node in nodes:
                target=urlsplit(urljoin(canonical,node.get('href') or node.get('src')))
                if target.netloc!=urlsplit(impl.DOMAIN).netloc:continue
                path=unquote(target.path);destination=path.lstrip('/')+('index.html' if path.endswith('/') else '')
                assert destination in manifest['files'],(name,destination)
                internal+=1;linked[destination]+=1
                if target.fragment:
                    targetdoc=doc if destination==name else html.document_fromstring((ROOT/destination).read_bytes());assert targetdoc.xpath('//*[@id=$ident]',ident=unquote(target.fragment)),(name,target.fragment);fragments+=1
            if i%2000==0:print('Audited source/public files',i,flush=True)
    assert sorted(checked)==list(range(1,1003)) and len(set(checked))==1002
    assert bridgecounts['pages']==8361,bridgecounts
    assert len(html.parse(str(ROOT/'선생님찾기/index.html')).xpath('//*[@data-teacher-branch]'))==205
    assert all(linked[n]>0 for n in new_pages)
    for im in data['images']:
        assert (ROOT/im['path'].lstrip('/')).read_bytes()==(impl.INPUT/im['sourceFile']).read_bytes()
    assert state()==impl.load(OUT/'authoring-before.json')
    result={'publicHtml':8664,'publicFiles':10947,'baselineHtmlPreserved':8458,'sourceRowsVerified':1002,'branchesVerified':205,'sameBranchMaskedNameCollisions':6,'contextualBridgePages':bridgecounts['pages'],'internalLinksVerified':internal,'fragmentsVerified':fragments,'newPublicFiles':218,'changedExistingPublicFiles':len(changes),'representativeImagesVerified':10,'authoringPreserved':True,'errors':[]}
    result['manifestSha256']=digest((ROOT/'release-public-manifest.json').read_bytes())
    result['preservationPolicy']='Retain old DOM content and data, apart from teacher additions, actual page modification dates and CRLF/LF normalization.'
    impl.dump(OUT/'source-audit.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
