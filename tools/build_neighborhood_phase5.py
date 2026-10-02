"""Freeze the validated local phase-5 source, then run existing release checks."""
from concurrent.futures import ThreadPoolExecutor
import argparse,datetime,hashlib,json,re,shutil,subprocess,time
import improve_neighborhood_pages as impl
from audit_neighborhood_phase5 import OUT

def read(name):
    raw=(impl.ROOT/name).read_bytes();binary=hashlib.sha256(raw).hexdigest();text=None
    if re.search(r'\.(html|css|js|json|xml|txt|svg|webmanifest)$',name,re.I):text=hashlib.sha256(raw.decode('utf-8').replace('\r\n','\n').replace('\r','\n').encode('utf-8')).hexdigest()
    return name,binary,text

def streamed_dump(path,data):
    pending=path.with_name(path.name+'.phase5-tmp')
    with pending.open('w',encoding='utf-8',newline='\n') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2);stream.write('\n')
    pending.replace(path)

def freeze(reuse_diff=False):
    check=impl.load(OUT/'validation.json');site=impl.load(impl.REPORT/'validation.json')
    assert check['errors']==site['errors']==[] and check['changedHtmlPages']==8355 and check['questions']==41775
    if reuse_diff:
        assert impl.load(OUT/'diff-check.json')['exitCode']==0
        print('Reusing completed full diff check; no public edits since that check',flush=True)
    else:
        diff=subprocess.run(['git','diff','--check'],cwd=impl.ROOT,capture_output=True)
        impl.dump(OUT/'diff-check.json',{'exitCode':diff.returncode,'outputBytes':len(diff.stdout)+len(diff.stderr)})
        (OUT/'diff-check-output.txt').write_bytes(diff.stdout+diff.stderr);assert diff.returncode==0
    manifest=impl.load(impl.ROOT/'release-public-manifest.json');files={};text_hashes={}
    names=sorted(manifest['files']);index=0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for start in range(0,len(names),64):
            for name,binary,text in pool.map(read,names[start:start+64]):
                files[name]=binary;index+=1
                if text:text_hashes[name]=text
                if index%2500==0:print('Reviewed public files',index,flush=True)
    assert len(files)==10622
    manifest.update(files=files,textSha256=text_hashes,createdAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat())
    streamed_dump(impl.ROOT/'release-public-manifest.json',manifest)
    impl.dump(OUT/'public-html-files.json',[n for n in files if n.endswith('.html')]);assert len([n for n in files if n.endswith('.html')])==8403
    shutil.copyfile(impl.REPORT/'validation.json',OUT/'all-site-validation.json')
    shutil.copyfile(impl.ROOT/'release-public-manifest.json',OUT/'release-public-manifest.json')
    impl.dump(OUT/'reviewed-release-state.json',{'manifestSha256':hashlib.sha256((impl.ROOT/'release-public-manifest.json').read_bytes()).hexdigest(),'publicFiles':len(files),'htmlPages':8403,'deployed':False})
    print('Validated local source manifest frozen; no deployment',flush=True)

def build():
    import sys
    steps=[['node','release-public-build.mjs'],['node','wawa-analytics-build.mjs','wawa-04','.public-release'],['node','seo-descriptions.mjs','--root=.public-release','--files-file='+str(OUT/'public-html-files.json')],[sys.executable,'-X','utf8','tools/verify_neighborhood_build.py']]
    results=[]
    for index,command in enumerate(steps,1):
        print('Local release verification step',index,command[1],flush=True);start=time.monotonic()
        with (OUT/('build-step-'+str(index)+'.log')).open('wb') as stream:result=subprocess.run(command,cwd=impl.ROOT,stdout=stream,stderr=subprocess.STDOUT)
        results.append({'step':index,'command':command,'exitCode':result.returncode,'seconds':round(time.monotonic()-start,2)})
        impl.dump(OUT/'build-pipeline.json',results)
        print('Completed local step',index,'exit',result.returncode,flush=True);assert result.returncode==0
    report=impl.load(impl.REPORT/'build-verification.json');assert report['errors']==[]
    shutil.copyfile(impl.REPORT/'build-verification.json',OUT/'build-verification.json')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');parser.add_argument('--build',action='store_true');parser.add_argument('--reuse-diff',action='store_true');args=parser.parse_args();assert args.freeze or args.build
    if args.freeze:freeze(args.reuse_diff)
    if args.build:build()
