/** Explicit post-release notification. Dry run by default; never called by builds. */
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=new Set(process.argv.slice(2));
const base=[...args].find(a=>a.startsWith('--base='))?.slice(7);
if(!base||!/^[a-f0-9]{40}$/.test(base))throw Error('Provide the reviewed --base=<full commit SHA>');
const submit=args.has('--submit'),working=args.has('--working-tree');
if(submit&&working)throw Error('A working tree cannot be submitted');
for(const a of args)if(!['--submit','--working-tree'].includes(a)&&!a.startsWith('--base='))throw Error('Unknown argument');
const git=(...a)=>execFileSync('git',a,{cwd:root,encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();
const head=git('rev-parse','HEAD');
if(submit&&git('status','--porcelain','--untracked-files=no'))throw Error('Submit only an unchanged reviewed commit');
const config=JSON.parse(fs.readFileSync(path.join(root,'indexnow-config.json'),'utf8'));
if(config.host!=='xn--sp5b72l1taf0p.com'||config.endpoint!=='https://searchadvisor.naver.com/indexnow')throw Error('Unexpected notification destination');
if(!/^[a-f0-9]{32}\.txt$/.test(config.keyFile))throw Error('Invalid ownership filename');
const key=fs.readFileSync(path.join(root,config.keyFile),'utf8');
if(config.keyFile!==key+'.txt')throw Error('Ownership file content mismatch');
const files=git('diff','--name-only','-z',base,...(working?[]:[head])).split('\0').filter(n=>n.endsWith('.html'));
const manifest=JSON.parse(fs.readFileSync(path.join(root,'release-public-manifest.json'),'utf8'));
const urls=files.map(name=>{
 if(!manifest.files[name])throw Error('Changed HTML is not in the reviewed public manifest');
 const bytes=fs.readFileSync(path.join(root,name));
 if(createHash('sha256').update(bytes).digest('hex')!==manifest.files[name])throw Error('Changed source differs from the reviewed manifest');
 const html=bytes.toString('utf8');
 const matches=[...html.matchAll(/<link\b[^>]*rel="canonical"[^>]*href="([^"]+)"/g)];
 if(matches.length!==1)throw Error('Canonical must occur exactly once');
 const url=new URL(matches[0][1]);
 if(url.origin!==`https://${config.host}`||url.search||url.hash||!url.pathname.endsWith('/'))throw Error('Unsafe canonical');
 const expected=decodeURIComponent(url.pathname)==='/'?'index.html':decodeURIComponent(url.pathname).slice(1)+'index.html';
 if(expected!==name)throw Error('Canonical does not match the changed file');
 return url.href;
}).sort();
if(!urls.length||urls.length>10000||new Set(urls).size!==urls.length)throw Error('Invalid changed URL scope');
const result={commit:head,base,urls:urls.length,mode:submit?'submit':'dry-run',endpoint:config.endpoint,indexingGuaranteed:false};
if(submit){
 const ownership=await fetch(`https://${config.host}/${config.keyFile}`,{redirect:'error',signal:AbortSignal.timeout(20000)});
 if(ownership.status!==200||(await ownership.text())!==key)throw Error('Live ownership file is not the reviewed file');
 const response=await fetch(config.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:config.host,key,keyLocation:`https://${config.host}/${config.keyFile}`,urlList:urls}),redirect:'error',signal:AbortSignal.timeout(30000)});
 result.status=response.status;result.accepted=[200,202].includes(response.status);
 if(!result.accepted){result.error=(await response.text()).slice(0,200);console.log(JSON.stringify(result));process.exit(1);}
}
console.log(JSON.stringify(result));
