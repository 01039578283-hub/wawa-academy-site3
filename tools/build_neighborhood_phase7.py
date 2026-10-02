"""Freeze approved hub fields and two public finder assets; local pipeline only."""
from concurrent.futures import ThreadPoolExecutor
import argparse,datetime,hashlib,json,shutil,subprocess,time
import improve_neighborhood_pages as impl
from audit_neighborhood_phase7 import OUT,BASE_SHA,ASSETS
from audit_neighborhood_phase6 import dump
from build_neighborhood_phase5 import read,streamed_dump

def freeze():
    check=impl.load(OUT/'validation.json');site=impl.load(impl.REPORT/'validation.json')
    assert check['errors']==site['errors']==[] and check['directoryLabels']==2597 and check['reviewedRoutes']==8162
    raw=(impl.ROOT/'release-public-manifest.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==BASE_SHA
    manifest=json.loads(raw);approved={p['file'] for p in impl.load(OUT/'implementation.json')['pages']}|{'sitemap.xml','assets/neighborhood-seo/local.css'}|set(ASSETS)
    print('Checking full local diff',flush=True)
    with (OUT/'diff-check-output.txt').open('wb') as stream:diff=subprocess.run(['git','-c','core.safecrlf=false','diff','--check'],cwd=impl.ROOT,stdout=stream,stderr=subprocess.STDOUT)
    dump(OUT/'diff-check.json',{'exitCode':diff.returncode,'outputBytes':(OUT/'diff-check-output.txt').stat().st_size,'scope':'entire existing worktree'});assert diff.returncode==0
    names=sorted(set(manifest['files'])|set(ASSETS));files={};texts={};changed=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for start in range(0,len(names),64):
            for name,binary,text in pool.map(read,names[start:start+64]):
                if binary!=manifest['files'].get(name):changed.append(name);assert name in approved,name
                files[name]=binary
                if text:texts[name]=text
            if len(files)%2560==0:print('Reviewed public files',len(files),flush=True)
    assert set(changed)==approved and len(files)==10624
    manifest.update(files=files,textSha256=texts,createdAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat())
    streamed_dump(impl.ROOT/'release-public-manifest.json',manifest)
    dump(OUT/'public-html-files.json',[n for n in files if n.endswith('.html')])
    shutil.copyfile(impl.REPORT/'validation.json',OUT/'all-site-validation.json');shutil.copyfile(impl.ROOT/'release-public-manifest.json',OUT/'release-public-manifest.json')
    dump(OUT/'reviewed-release-state.json',{'manifestSha256':hashlib.sha256((impl.ROOT/'release-public-manifest.json').read_bytes()).hexdigest(),'publicFiles':len(files),'htmlPages':8403,'changedPublicFiles':len(changed),'changedFiles':changed,'deployed':False})
    print('Final local manifest frozen; no deployment',flush=True)

def build(resume_from=1):
    import sys
    steps=[['node','release-public-build.mjs'],['node','wawa-analytics-build.mjs','wawa-04','.public-release'],['node','seo-descriptions.mjs','--root=.public-release','--files-file='+str(OUT/'public-html-files.json')],[sys.executable,'-X','utf8','tools/verify_neighborhood_build.py']]
    results=[]
    if resume_from>1:
        initial=impl.load(OUT/'build-pipeline.json');assert initial[resume_from-1]['exitCode']!=0
        assert hashlib.sha256((impl.ROOT/'release-public-manifest.json').read_bytes()).hexdigest()==impl.load(OUT/'reviewed-release-state.json')['manifestSha256']
        dump(OUT/'build-pipeline-initial.json',initial)
        shutil.copyfile(OUT/('build-step-'+str(resume_from)+'.log'),OUT/('build-step-'+str(resume_from)+'-initial.log'))
        results=initial[:resume_from-1];assert all(r['exitCode']==0 for r in results)
    for index,command in enumerate(steps,1):
        if index<resume_from:continue
        print('Local pipeline step',index,command[1],flush=True);start=time.monotonic()
        with (OUT/('build-step-'+str(index)+'.log')).open('wb') as stream:result=subprocess.run(command,cwd=impl.ROOT,stdout=stream,stderr=subprocess.STDOUT)
        results.append({'step':index,'command':command,'exitCode':result.returncode,'seconds':round(time.monotonic()-start,2)})
        dump(OUT/'build-pipeline.json',results);assert result.returncode==0;print('Completed local step',index,flush=True)
    shutil.copyfile(impl.REPORT/'build-verification.json',OUT/'build-verification.json');assert impl.load(OUT/'build-verification.json')['errors']==[]
    print('All public output bytes verified',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');parser.add_argument('--build',action='store_true');parser.add_argument('--resume-from',type=int,default=1);args=parser.parse_args();assert args.freeze or args.build
    if args.freeze:freeze()
    if args.build:build(args.resume_from)
