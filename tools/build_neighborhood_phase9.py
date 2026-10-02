"""Allow only the reviewed RSS change, then verify the complete local release."""
import argparse, datetime, hashlib, json, shutil, subprocess, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
import improve_neighborhood_pages as impl
from improve_neighborhood_phase9 import OUT, BACKUP, BASE_SHA, validate
from audit_neighborhood_phase6 import dump
from build_neighborhood_phase5 import read, streamed_dump

def freeze():
    validation = impl.load(OUT / 'validation.json'); site = impl.load(impl.REPORT / 'validation.json')
    assert validation['errors'] == site['errors'] == [] and validation['items'] == 50
    assert site['sitemapPages'] == 8403
    current = (impl.ROOT / 'release-public-manifest.json').read_bytes()
    previous = impl.load(OUT / 'reviewed-release-state.json') if (OUT / 'reviewed-release-state.json').exists() else None
    assert hashlib.sha256(current).hexdigest() == BASE_SHA or previous and hashlib.sha256(current).hexdigest() == previous['manifestSha256'], 'Unexpected manifest drift'
    with zipfile.ZipFile(BACKUP) as archive:
        baseline = archive.read('release-public-manifest.json')
    assert hashlib.sha256(baseline).hexdigest() == BASE_SHA
    manifest = json.loads(baseline); names = sorted(manifest['files'])
    assert len(names) == 10624
    files = {}; texts = {}; changed = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for start in range(0, len(names), 64):
            for name, binary, text in pool.map(read, names[start:start + 64]):
                files[name] = binary
                if text:
                    texts[name] = text
                if binary != manifest['files'][name]:
                    changed.append(name); assert name == 'rss.xml', name
            if len(files) % 2560 == 0:
                print('Compared public source files', len(files), flush=True)
    assert changed == ['rss.xml'] and sum(n.endswith('.html') for n in files) == 8403
    with (OUT / 'diff-check-output.txt').open('wb') as stream:
        result = subprocess.run(['git', '-c', 'core.safecrlf=false', 'diff', '--check'], cwd=impl.ROOT, stdout=stream, stderr=subprocess.STDOUT)
    dump(OUT / 'diff-check.json', {'exitCode': result.returncode, 'scope': 'Entire existing worktree', 'outputBytes': (OUT / 'diff-check-output.txt').stat().st_size})
    assert result.returncode == 0
    manifest.update(files=files, textSha256=texts, createdAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat())
    streamed_dump(impl.ROOT / 'release-public-manifest.json', manifest)
    shutil.copyfile(impl.ROOT / 'release-public-manifest.json', OUT / 'release-public-manifest.json')
    shutil.copyfile(impl.REPORT / 'validation.json', OUT / 'all-site-validation.json')
    dump(OUT / 'public-html-files.json', [n for n in files if n.endswith('.html')])
    dump(OUT / 'reviewed-release-state.json', {'manifestSha256': hashlib.sha256((impl.ROOT / 'release-public-manifest.json').read_bytes()).hexdigest(), 'publicFiles': 10624, 'htmlPages': 8403, 'changedPublicFiles': 1, 'changedFiles': changed, 'unchangedHtmlPages': 8403, 'unchangedOtherPublicFiles': 10623, 'deployed': False})
    print('RSS-only manifest frozen; every HTML and other public file unchanged', flush=True)

def build():
    state = impl.load(OUT / 'reviewed-release-state.json')
    assert hashlib.sha256((impl.ROOT / 'release-public-manifest.json').read_bytes()).hexdigest() == state['manifestSha256']
    validate()
    steps = [['node', 'release-public-build.mjs'], ['node', 'wawa-analytics-build.mjs', 'wawa-04', '.public-release'], ['node', 'seo-descriptions.mjs', '--root=.public-release', '--files-file=' + str(OUT / 'public-html-files.json')], [sys.executable, '-X', 'utf8', 'tools/verify_neighborhood_build.py']]
    results = []
    for index, command in enumerate(steps, 1):
        print('Local release step', index, command[1], flush=True); start = time.monotonic()
        with (OUT / ('build-step-' + str(index) + '.log')).open('wb') as stream:
            result = subprocess.run(command, cwd=impl.ROOT, stdout=stream, stderr=subprocess.STDOUT)
        results.append({'step': index, 'command': command, 'exitCode': result.returncode, 'seconds': round(time.monotonic() - start, 2)})
        dump(OUT / 'build-pipeline.json', results)
        assert result.returncode == 0
        print('Completed local release step', index, flush=True)
    shutil.copyfile(impl.REPORT / 'build-verification.json', OUT / 'build-verification.json')
    assert impl.load(OUT / 'build-verification.json')['errors'] == []
    validate(True)
    print('Full public output and RSS verified; no deployment', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['freeze', 'build']); action = parser.parse_args().action
    globals()[action]()
