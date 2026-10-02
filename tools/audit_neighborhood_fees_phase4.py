"""Read the 193 previously supplied branch PDF links; never infer current prices."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import json, re, hashlib, urllib.request, time
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path
import improve_neighborhood_pages as impl

OUT=Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase4-20261001')
POPPLER=r'C:\Users\1992k\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin'

def fetch(item):
    target=OUT/'source-pdfs'/(item['id']+'.pdf')
    try:
        if not target.exists():
            url='https://drive.google.com/uc?export=download&id='+item['id']
            for attempt in range(3):
                try:
                    raw=urllib.request.urlopen(url,timeout=45).read()
                    assert raw.startswith(b'%PDF'), 'Provider returned non-PDF'
                    target.write_bytes(raw);break
                except Exception:
                    if attempt==2:raise
                    time.sleep(1)
        raw=target.read_bytes();reader=PdfReader(target)
        pages=[page.extract_text() for page in reader.pages]
        # Extract exact printed dates; multiple dates are kept page-specific.
        dates=[sorted(set('-'.join([a,b.zfill(2),c.zfill(2)]) for a,b,c in re.findall(r'(20\d{2})\s*년\s*(\d+)\s*월\s*(\d+)\s*일',text))) for text in pages]
        return {**item,'pdfSha256':hashlib.sha256(raw).hexdigest(),'pdfBytes':len(raw),'pdfPages':len(pages),'pageTexts':pages,'pageDates':dates,'rawDownloadStatus':'verified PDF','error':None}
    except Exception as e:
        return {**item,'rawDownloadStatus':'unavailable','error':type(e).__name__}

def main():
    (OUT/'source-pdfs').mkdir(exist_ok=True)
    source=impl.load(OUT/'fee-source-extracts.json')
    results=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for index,result in enumerate(pool.map(fetch,source['files']),1):
            results.append(result)
            if index%25==0:print('Verified PDF originals',index,flush=True)
    result={'retrievedAt':'2026-10-01','source':'Existing supplied feeLink URLs; connector metadata and text followed by provider raw PDF download','files':results,'errors':[[r['center'],r['error']] for r in results if r.get('error')]}
    impl.dump(OUT/'fee-pdf-audit.json',result)
    print(json.dumps({'sources':len(results),'errors':result['errors'],'pages':sum(r.get('pdfPages',0) for r in results),'dates':dict(Counter(d for r in results for page in r.get('pageDates',[]) for d in page))},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
