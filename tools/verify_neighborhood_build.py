"""Verify reviewed content survives the existing public release pipeline.

The published pipeline adds one existing wawa-04 tracker to pages without it.
Accept exactly that head insertion, then require every other byte to match.
"""
import hashlib,json,re,os
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import improve_neighborhood_pages as impl

def read_pairs(names,out):
 def read_pair(name):return name,(impl.ROOT/name).read_bytes(),(out/name).read_bytes()
 with ThreadPoolExecutor(max_workers=8) as pool:
  for start in range(0,len(names),32):
   yield from pool.map(read_pair,names[start:start+32])

def output_files(root):
 # DirEntry exposes the Windows directory enumeration's file type, so this
 # full inventory does not issue a separate Path.stat for every public file.
 # Preserve the exact file-set check and explicitly reject links.
 result=set();pending=[root]
 while pending:
  folder=pending.pop()
  with os.scandir(folder) as entries:
   for entry in entries:
    if entry.is_symlink():raise ValueError('Unexpected output symlink: '+entry.path)
    if entry.is_dir(follow_symlinks=False):pending.append(Path(entry.path))
    elif entry.is_file(follow_symlinks=False):result.add(Path(entry.path).relative_to(root).as_posix())
 return result

def main():
 out=impl.ROOT/'.public-release';manifest_bytes=(impl.ROOT/'release-public-manifest.json').read_bytes();manifest=json.loads(manifest_bytes)
 expected=set(manifest['files']);actual=output_files(out)
 errors=[];inserted=0;present=0
 tracker=b'<script defer src="https://wawa-visit-collector.clean-peach-8202.chatgpt.site/tracker.js" data-site="wawa-04" crossorigin="anonymous" referrerpolicy="no-referrer"></script>'
 tracker_pattern=rb'<script\b[^>]*wawa-visit-collector[^>]*>[\s\S]*?</script>'
 if actual!=expected:errors.append({'fileSet':{'missing':sorted(expected-actual),'unexpected':sorted(actual-expected)}})
 for i,(name,src,dest) in enumerate(read_pairs(sorted(expected & actual),out),1):
  if hashlib.sha256(src).hexdigest()!=manifest['files'][name]:errors.append({'file':name,'message':'Reviewed source changed after manifest creation'})
  reviewed=src
  if name.endswith('.html'):
   tags=re.findall(tracker_pattern,src,re.I)
   if not tags:
    assert re.search(rb'</head\s*>',src,re.I),name
    reviewed=re.sub(rb'</head\s*>',lambda m:tracker+m[0],src,count=1,flags=re.I);inserted+=1
   elif tags==[tracker]:present+=1
   else:errors.append({'file':name,'message':'Unexpected source analytics tracker'})
   if re.findall(tracker_pattern,dest,re.I)!=[tracker]:errors.append({'file':name,'message':'Output must contain exactly one existing wawa-04 tracker'})
  if dest!=reviewed:errors.append({'file':name,'message':'Build differs from reviewed source and exact existing tracker insertion'})
  if name.startswith(('tools/','reports/','.env','.git')) or name.lower().endswith(('.xlsx','.xls','.csv','.zip')):errors.append({'file':name,'message':'Private source in public output'})
  if i%2500==0:print('Verified build files',i,flush=True)
 result={'publicFiles':len(actual),'htmlPages':sum(p.endswith('/index.html') or p=='index.html' for p in expected),'fullReleasePipeline':True,'reviewedContentPreserved':not errors,'reviewedManifestSha256':hashlib.sha256(manifest_bytes).hexdigest(),'expectedPostprocessing':'Exactly one existing wawa-04 tracker head insertion on pages that lack it; all other bytes unchanged','analyticsTrackerInsertedPages':inserted,'analyticsAlreadyPresentPages':present,'privateSourceFiles':0,'errors':errors,'deployed':False}
 impl.dump(impl.REPORT/'build-verification.json',result);print(json.dumps(result,ensure_ascii=False));raise SystemExit(bool(errors))
if __name__=='__main__':main()
