"""Normalize only reviewed phase-3 HTML after Windows text serialization.

Keep semantic protection checks and the documented single-file replacement
exception. Original phase-2 bytes remain in the immutable input ZIP.
"""
import re, time
from concurrent.futures import ThreadPoolExecutor
from lxml import html
import improve_neighborhood_pages as impl
from improve_neighborhood_phase3 import VERSION
from audit_neighborhood_phase3 import OUT

def normalize_one(name):
    path=impl.ROOT/name
    original=path.read_bytes()
    if ('data-neighborhood-phase3="'+VERSION+'"').encode() not in original:return None
    payload=re.sub(rb'\r+\n',b'\n',original)
    payload=payload.replace('내용 수정·센터 자료 대조 2026.09.30'.encode(),
        '내용 수정 2026.10.01 · 센터 자료 대조 2026.09.30'.encode())
    assert b'\r' not in payload, path
    if payload==original:return (0,None)
    guard=impl.protect(html.document_fromstring(original))
    assert impl.protect(html.document_fromstring(payload))==guard, path
    assert path.resolve().is_relative_to(impl.ROOT.resolve())
    pending=path.with_name('index.html.neighborhood-tmp');fallback=None
    try:
        for attempt in range(3):
            try:
                pending.write_bytes(payload);pending.replace(path);break
            except OSError as error:
                if error.errno not in [13,22] or attempt==2:raise
                time.sleep(.2)
    except PermissionError:
        assert path.relative_to(impl.ROOT).as_posix()=='전국센터/이곡동/초등영어학원/index.html'
        with path.open('r+b') as stream:
            stream.seek(0);stream.write(payload);stream.truncate();stream.flush()
        if pending.exists():pending.unlink()
        fallback=path.relative_to(impl.ROOT).as_posix()
    assert path.read_bytes()==payload
    return (1,fallback)

def main():
    reviewed=changed=0;fallbacks=[]
    manifest=impl.load(impl.ROOT/'release-public-manifest.json')
    names=[name for name in manifest['files'] if name.endswith('.html')]
    assert len(names)==len(set(names))==8403
    # Each worker owns a distinct manifest path and its own DOM. Aggregate
    # results only after those protected, atomic writes have finished.
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index,result in enumerate(pool.map(normalize_one,names),1):
            if result is not None:
                reviewed+=1;changed+=result[0]
                if result[1]:fallbacks.append(result[1])
            if index%2000==0:print('Reviewed HTML',index,'normalized',changed,flush=True)
    assert reviewed==8259, reviewed
    impl.dump(OUT/'newline-verification.json',{'reviewedHtml':reviewed,'normalizedHtml':changed,'remainingCarriageReturns':0,'protectedFieldsPreserved':True,'handleWritePaths':fallbacks})
    print('Reviewed',reviewed,'normalized',changed,'protected fields preserved',flush=True)

if __name__=='__main__':main()
