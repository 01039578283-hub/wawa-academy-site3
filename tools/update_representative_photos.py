"""Apply a reviewed, fixed lower-gallery representative-photo assignment.

Never regenerates a page or moves a gallery. Requires the immutable before.zip
and full source/role/photo audit supplied via --evidence-dir. Public builds use
the static HTML and do not run this maintenance tool or randomize assignments.
"""
from pathlib import Path
from collections import Counter
import argparse, copy, csv, hashlib, html as escaping, json, re, zipfile
from urllib.parse import unquote, urlsplit
from html.parser import HTMLParser
from lxml import etree, html
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
DOMAIN='https://xn--sp5b72l1taf0p.com'
DATE='2026-10-10'
PAGE_TYPES={'WebPage','Article','AboutPage','BlogPosting'}
IMAGE_KEYS={'og:image','og:image:secure_url','og:image:type','og:image:width','og:image:height','og:image:alt','twitter:image','twitter:image:alt'}
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def nodes(v):
    if isinstance(v,list):
        for x in v:yield from nodes(x)
    elif isinstance(v,dict):
        yield v
        for x in v.values():yield from nodes(x)
def tag_attr(tag,key,value):
    value=escaping.escape(str(value),quote=True)
    pattern=r'(?<![\w:-])'+re.escape(key)+r'\s*=\s*(?:"[^"]*"|\x27[^\x27]*\x27|[^\s>]+)'
    if re.search(pattern,tag,re.I):return re.sub(pattern,lambda m:key+'="'+value+'"',tag,count=1,flags=re.I)
    return re.sub(r'\s*/?>$',lambda m:' '+key+'="'+value+'"'+m[0],tag,count=1)
def attrs(tag):
    class SingleTag(HTMLParser):
        def handle_starttag(self,name,items):self.values=dict(items)
        def handle_startendtag(self,name,items):self.values=dict(items)
    p=SingleTag();p.feed(tag);return p.values
def transform(text,p,b):
    photo=b['selected'];url=DOMAIN+photo['src'];is_common=b['mode']=='common'
    label=(p['actualBranch']+' 안내에 참고하는 브랜드 공통 학습 공간 사진') if is_common else photo['alt']
    head_end=text.index('</head>');head=text[:head_end];tail=text[head_end:]
    values={'og:image':url,'og:image:secure_url':url,'og:image:type':'image/webp','og:image:width':str(photo['width']),'og:image:height':str(photo['height']),'og:image:alt':label,'twitter:image':url,'twitter:image:alt':label}
    seen=set()
    def meta(m):
        tag=m[0];a=attrs(tag);key=a.get('property') or a.get('name')
        if key in IMAGE_KEYS:
            if key in seen:return ''
            seen.add(key);return tag_attr(tag,'content',values[key])
        if key=='article:modified_time':return tag_attr(tag,'content',DATE)
        return tag
    head=re.sub(r'<meta\b[^>]*>',meta,head,flags=re.I)
    for key,value in values.items():
        if key not in seen:head+='\n<meta '+('name' if key.startswith('twitter:') else 'property')+'="'+key+'" content="'+escaping.escape(value,quote=True)+'">'
    text=head+tail
    removed=0;marked=0
    def image(m):
        nonlocal removed,marked
        tag=m[0];a=attrs(tag)
        if a.get('data-role')=='representative-image':
            assert 'hidden' in a and a.get('aria-hidden')=='true' and 'display:none' in a.get('style','')
            removed+=1;return ''
        if a.get('data-role')=='space-image' and a.get('src')==photo['src']:
            marked+=1;tag=tag_attr(tag,'data-representative-photo','true')
            tag=tag_attr(tag,'width',photo['width']);tag=tag_attr(tag,'height',photo['height'])
            if is_common:tag=tag_attr(tag,'alt',label)
        return tag
    text=re.sub(r'<img\b[^>]*>',image,text,flags=re.I)
    assert removed==p['hiddenCount'] and marked==1,(p['file'],removed,marked)
    if is_common:
        pattern=r'(<figure>\s*<img\b[^>]*data-representative-photo="true"[^>]*>\s*)(</figure>)'
        caption='<figcaption data-photo-caption="common-reference">브랜드 공통 참고 사진 · '+escaping.escape(p['actualBranch'])+'의 실제 사진은 아닙니다.</figcaption>'
        text,n=re.subn(pattern,lambda m:m[1]+caption+m[2],text,count=1)
        assert n==1,p['file']
    def ld(m):
        prefix,body,suffix=m[1],m[2],m[3];data=json.loads(body)
        for node in nodes(data):
            typ=node.get('@type',[]);types={typ} if isinstance(typ,str) else set(typ)
            if types & PAGE_TYPES:
                if 'image' in node:node['image']=url
                if 'dateModified' in node:node['dateModified']=DATE
                if 'primaryImageOfPage' in node:
                    v=node['primaryImageOfPage'];assert isinstance(v,dict)
                    if 'url' in v:v.update(url=url,width=photo['width'],height=photo['height'])
                    if 'contentUrl' in v:v['contentUrl']=url
            if 'ImageObject' in types and str(node.get('@id','')).endswith('#primaryimage'):
                node.update(url=url,width=photo['width'],height=photo['height'])
                if 'contentUrl' in node:node['contentUrl']=url
        return prefix+json.dumps(data,ensure_ascii=False,separators=(',',':'))+suffix
    text=re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)([\s\S]*?)(</script>)',ld,text,flags=re.I)
    # Keep the current visible modification date consistent with the page/feed date.
    text=re.sub(r'(내용 수정\s*)(?:2026\.10\.07|2026-10-07)',lambda m:m[1]+'2026.10.10',text)
    return text
def preserve(before,after,p,b):
    old=html.document_fromstring(before);new=html.document_fromstring(after)
    assert new.xpath('//head/meta[@property="og:image"]/@content')==[DOMAIN+b['selected']['src']]
    assert new.xpath('//head/meta[@name="twitter:image"]/@content')==[DOMAIN+b['selected']['src']]
    assert not new.xpath('//img[@data-role="representative-image"]')
    rep=new.xpath('//main//img[@data-representative-photo="true"]');assert len(rep)==1
    assert rep[0].get('src')==b['selected']['src'] and rep[0].xpath('ancestor::section[@id="learning-space"]')
    assert not rep[0].xpath('ancestor::*[@hidden or @aria-hidden="true" or contains(@style,"display:none")]')
    assert len(new.xpath('//main//img[@src="'+b['selected']['src']+'"]'))==1
    assert [x.get('src') for x in old.xpath('//section[@id="learning-space"]//img')]==[x.get('src') for x in new.xpath('//section[@id="learning-space"]//img')]
    assert [x.get('src') for x in old.xpath('//section[@id="learning-space"]//img')]==[x['src'] for x in b['photos']],p['file']
    assert old.xpath('//a/@href')==new.xpath('//a/@href')
    for n in old.xpath('//img[@data-role="representative-image"]'):n.drop_tree()
    for xp in ['//title','//h1','//header','//footer','//section[@id="page-images"]']:
        assert [etree.tostring(n,with_tail=False) for n in old.xpath(xp)]==[etree.tostring(n,with_tail=False) for n in new.xpath(xp)],(p['file'],xp)
    assert old.xpath('//link[@rel="canonical"]/@href')==new.xpath('//link[@rel="canonical"]/@href')
    for key in ['description','og:description','twitter:description','og:title','twitter:title']:
        xp='//meta[@name="'+key+'" or @property="'+key+'"]'
        assert [dict(n.attrib) for n in old.xpath(xp)]==[dict(n.attrib) for n in new.xpath(xp)]
    # Compare the complete body DOM after reverting exactly the authorized edits.
    for n in old.xpath('//img[@data-role="representative-image"]'):n.getparent().remove(n)
    for n in new.xpath('//img[@data-representative-photo="true"]'):
        del n.attrib['data-representative-photo']
        original=next(x for x in old.xpath('//img[@data-role="space-image"]') if x.get('src')==n.get('src'))
        n.attrib.clear();n.attrib.update(original.attrib)
    for n in new.xpath('//figcaption[@data-photo-caption="common-reference"]'):n.getparent().remove(n)
    for n in new.xpath('//body//*[not(*)]'):
        if n.text and '내용 수정' in n.text:n.text=n.text.replace('내용 수정 2026.10.10','내용 수정 2026.10.07')
    # Structured data sometimes resides in body. Revert from the old script node
    # only after separately validating the semantic transform byte-for-byte.
    old_ld=old.xpath('//script[@type="application/ld+json"]');new_ld=new.xpath('//script[@type="application/ld+json"]')
    assert len(old_ld)==len(new_ld)
    for x,y in zip(old_ld,new_ld):y.text=x.text
    compact=lambda d:re.sub(r'>\s+<','><',etree.tostring(d.xpath('//body')[0],encoding='unicode',with_tail=False))
    assert compact(old)==compact(new),('Body content/order changed',p['file'])
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence-dir',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args();out=args.evidence_dir
    a=json.loads((out/'audit-before.json').read_text('utf8'));branches=json.loads((out/'proposed-selection.json').read_text('utf8'))
    chosen={(b['region'],b['branch']):b for b in branches};base=json.loads((out/'baseline-manifest.json').read_text('utf8'))
    backup=zipfile.ZipFile(out/'before.zip');changed=[];assignments=[]
    for i,p in enumerate(a['pages'],1):
        b=chosen[(p['region'],p['actualBranch'])];before=backup.read(p['file']);after=transform(before.decode('utf8'),p,b).encode('utf8')
        preserve(before,after,p,b)
        target=ROOT/p['file']
        if args.verify:assert target.read_bytes()==after,p['file']
        else:
            assert target.read_bytes() in [before,after],('Unexpected concurrent page edit',p['file'])
            if target.read_bytes()!=after:target.write_bytes(after)
        changed.append(p['file'])
        selected=b['selected'];assignments.append({'file':p['file'],'url':p['url'],'type':p['classification'],'actualBranch':p['actualBranch'],'region':p['region'],'mode':b['mode'],'imageUrl':DOMAIN+selected['src'],'source':selected['sourceMatch'],'sourceName':b['sourceName'],'width':selected['width'],'height':selected['height'],'bytes':selected['bytes'],'imageSha256':selected['sha256'],'reason':b['selectionReason']})
        if i%2000==0:print('Transformed and preserved',i,flush=True)
    if args.verify:
        actual=json.loads((ROOT/'representative-photo-assignment.json').read_text('utf8'));assert actual['pages']==assignments
    else:
        dump(ROOT/'representative-photo-assignment.json',{'schemaVersion':1,'reviewedAt':DATE,'sourceGuidance':'https://searchadvisor.naver.com/guide/markup-content','policy':'Fixed existing lower-gallery selection; common reference photos are labeled and are not actual branch photographs. No photo relocation, no original file deletion, no runtime randomization.','pages':assignments})
    for n in a['excludedPages']:assert (ROOT/n['file']).read_bytes()==backup.read(n['file']),('Excluded changed',n['file'])
    for name,digest in base['files'].items():
        if name.endswith('.html') or name in ['sitemap.xml','rss.xml']:continue
        assert sha((ROOT/name).read_bytes())==digest or sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==base.get('textSha256',{}).get(name),('Existing asset changed',name)
    result={'targetPages':len(assignments),'byType':dict(Counter(x['type'] for x in assignments)),'realPhotoPages':sum(x['mode']=='center' for x in assignments),'commonReferencePages':sum(x['mode']=='common' for x in assignments),'reusedLowerPhotos':len(assignments),'newPhotoPages':0,'removedHiddenPages':sum(bool(p['hiddenCount']) for p in a['pages']),'heldPages':0,'excludedHtmlUntouched':len(a['excludedPages']),'originalAssetsPreserved':True,'allBodyTextImagesMapsLinksAndOrderPreserved':True,'uniqueSelectedPhotos':len({x['imageUrl'] for x in assignments}),'errors':[]}
    dump(out/'source-verification.json',result)
    with (out/'page-photo-mapping.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(assignments[0]));w.writeheader();w.writerows(sorted(assignments,key=lambda x:(unquote(urlsplit(x['url']).path).count('/'),x['url'])))
    usage=Counter(x['imageUrl'] for x in assignments)
    dump(out/'photo-reuse.json',[{'imageUrl':url,'pages':count,'branches':sorted({x['actualBranch'] for x in assignments if x['imageUrl']==url}),'mode':next(x['mode'] for x in assignments if x['imageUrl']==url)} for url,count in usage.most_common()])
    dump(out/'changed-pages.json',changed)
    print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
