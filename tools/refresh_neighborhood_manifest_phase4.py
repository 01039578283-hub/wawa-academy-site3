"""Read each existing public file once, then refresh its reviewed hashes."""
from concurrent.futures import ThreadPoolExecutor
import hashlib,re,datetime
import improve_neighborhood_pages as impl
from audit_neighborhood_fees_phase4 import OUT

def read(name):
    raw=(impl.ROOT/name).read_bytes();binary=hashlib.sha256(raw).hexdigest();text=None
    if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$',name,re.I):
        lf=raw.decode('utf-8').replace('\r\n','\n').replace('\r','\n')
        text=hashlib.sha256(lf.encode('utf-8')).hexdigest()
    return name,binary,text

def main():
    check=impl.load(OUT/'validation.json');site=impl.load(impl.REPORT/'validation.json');diff=impl.load(OUT/'diff-check.json')
    assert check['errors']==site['errors']==[] and check['changedHtmlPages']==8355 and diff['exitCode']==0
    manifest=impl.load(impl.ROOT/'release-public-manifest.json');names=sorted(manifest['files']);files={};text_hashes={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index,(name,binary,text) in enumerate(pool.map(read,names),1):
            files[name]=binary
            if text:text_hashes[name]=text
            if index%2500==0:print('Refreshed public hashes',index,flush=True)
    assert len(files)==10622
    manifest.update(files=files,textSha256=text_hashes,createdAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat())
    impl.dump(impl.ROOT/'release-public-manifest.json',manifest)
    print('Reviewed manifest',len(files),'private fee PDF files excluded',flush=True)

if __name__=='__main__':main()
