"""Freeze scoped hub changes and run the existing complete local release pipeline."""
from concurrent.futures import ThreadPoolExecutor
import argparse, datetime, hashlib, json, shutil, subprocess, sys, time, zipfile
import improve_neighborhood_pages as impl
from audit_neighborhood_phase8 import OUT, BACKUP, BASE_SHA, JS
from audit_neighborhood_phase6 import dump
from build_neighborhood_phase5 import read, streamed_dump

def freeze():
    check = impl.load(OUT / 'validation.json'); site = impl.load(impl.REPORT / 'validation.json')
    assert check['errors'] == site['errors'] == [] and check['changedHtmlPages'] == 35 and check['scopedMemberships'] == 2968
    raw = (impl.ROOT / 'release-public-manifest.json').read_bytes()
    previous = impl.load(OUT / 'reviewed-release-state.json') if (OUT / 'reviewed-release-state.json').exists() else None
    assert hashlib.sha256(raw).hexdigest() == BASE_SHA or previous and hashlib.sha256(raw).hexdigest() == previous['manifestSha256']
    with zipfile.ZipFile(BACKUP) as archive:
        baseline = archive.read('release-public-manifest.json')
    assert hashlib.sha256(baseline).hexdigest() == BASE_SHA
    manifest = json.loads(baseline)
    mandatory = {p['file'] for p in impl.load(OUT / 'implementation.json')['pages']} | {JS}
    allowed = mandatory | {'sitemap.xml'}
    with (OUT / 'diff-check-output.txt').open('wb') as stream:
        result = subprocess.run(['git', '-c', 'core.safecrlf=false', 'diff', '--check'], cwd=impl.ROOT, stdout=stream, stderr=subprocess.STDOUT)
    dump(OUT / 'diff-check.json', {'exitCode': result.returncode, 'outputBytes': (OUT / 'diff-check-output.txt').stat().st_size, 'scope': 'entire existing worktree'})
    assert result.returncode == 0
    files = {}; texts = {}; changed = []; names = sorted(manifest['files'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        for start in range(0, len(names), 64):
            for name, binary, text in pool.map(read, names[start:start + 64]):
                if binary != manifest['files'][name]:
                    changed.append(name); assert name in allowed, name
                files[name] = binary
                if text:
                    texts[name] = text
            if len(files) % 2560 == 0:
                print('Reviewed public files', len(files), flush=True)
    assert mandatory <= set(changed) <= allowed and len(files) == 10624
    manifest.update(files=files, textSha256=texts, createdAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat())
    streamed_dump(impl.ROOT / 'release-public-manifest.json', manifest)
    dump(OUT / 'public-html-files.json', [n for n in files if n.endswith('.html')])
    shutil.copyfile(impl.REPORT / 'validation.json', OUT / 'all-site-validation.json')
    shutil.copyfile(impl.ROOT / 'release-public-manifest.json', OUT / 'release-public-manifest.json')
    dump(OUT / 'reviewed-release-state.json', {'manifestSha256': hashlib.sha256((impl.ROOT / 'release-public-manifest.json').read_bytes()).hexdigest(), 'publicFiles': len(files), 'htmlPages': 8403, 'changedPublicFiles': len(changed), 'changedFiles': changed, 'deployed': False})
    print('Final local manifest frozen; no deployment', flush=True)

def build():
    steps = [['node', 'release-public-build.mjs'], ['node', 'wawa-analytics-build.mjs', 'wawa-04', '.public-release'], ['node', 'seo-descriptions.mjs', '--root=.public-release', '--files-file=' + str(OUT / 'public-html-files.json')], [sys.executable, '-X', 'utf8', 'tools/verify_neighborhood_build.py']]
    results = []
    for index, command in enumerate(steps, 1):
        print('Local pipeline step', index, command[1], flush=True); start = time.monotonic()
        with (OUT / ('build-step-' + str(index) + '.log')).open('wb') as stream:
            result = subprocess.run(command, cwd=impl.ROOT, stdout=stream, stderr=subprocess.STDOUT)
        results.append({'step': index, 'command': command, 'exitCode': result.returncode, 'seconds': round(time.monotonic() - start, 2)})
        dump(OUT / 'build-pipeline.json', results); assert result.returncode == 0
        print('Completed local step', index, flush=True)
    shutil.copyfile(impl.REPORT / 'build-verification.json', OUT / 'build-verification.json')
    assert impl.load(OUT / 'build-verification.json')['errors'] == []
    print('All public output bytes verified', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--freeze', action='store_true'); parser.add_argument('--build', action='store_true'); args = parser.parse_args()
    assert args.freeze or args.build
    if args.freeze:
        freeze()
    if args.build:
        build()
