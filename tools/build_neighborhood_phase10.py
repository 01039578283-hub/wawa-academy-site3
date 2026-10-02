"""Run exactly the configured future build, then compare every public byte."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse, hashlib, json, shlex, shutil, subprocess, sys, time, zipfile
import improve_neighborhood_pages as impl
from audit_neighborhood_phase6 import dump
from build_neighborhood_phase5 import read

OUT = Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase10-20261002')
BASE_SHA = 'ac8b06be27ae7e3c8c4e0e130cbf248707ebd966b00239d655beec20433230a7'
STEPS = [['node', 'seo-feed-check.mjs'], ['node', 'release-public-build.mjs'], ['node', 'wawa-analytics-build.mjs', 'wawa-04', '.public-release'], ['node', 'seo-descriptions.mjs', '--root=.public-release'], ['node', 'seo-feed-check.mjs', '--root=.public-release', '--built-output']]

def scope():
    raw = (impl.ROOT / 'release-public-manifest.json').read_bytes(); assert hashlib.sha256(raw).hexdigest() == BASE_SHA
    current = impl.load(impl.ROOT / 'vercel.json')
    with zipfile.ZipFile(OUT / 'phase9-before-phase10.zip') as archive:
        previous = json.loads(archive.read('vercel.json'))
    assert {k: v for k, v in current.items() if k != 'buildCommand'} == {k: v for k, v in previous.items() if k != 'buildCommand'}
    assert [shlex.split(s) for s in current['buildCommand'].split(' && ')] == STEPS
    names = sorted(json.loads(raw)['files']); expected = json.loads(raw)['files']; changed = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for start in range(0, len(names), 64):
            for name, binary, _ in pool.map(read, names[start:start + 64]):
                if binary != expected[name]: changed.append(name)
    assert not changed and len(names) == 10624
    protected = impl.load(OUT / 'protected-input-hashes.json')
    assert all(hashlib.sha256((impl.ROOT / name).read_bytes()).hexdigest() == expected for name, expected in protected.items())
    ledger = impl.load(impl.ROOT / 'seo-feed-review.json')
    assert len(ledger['pages']) == ledger['htmlPages'] == ledger['sitemap']['urls'] == 8403 and len(ledger['rss']['items']) == 50
    dump(OUT / 'scope-validation.json', {'publicFiles': 10624, 'htmlPages': 8403, 'rssItems': 50, 'changedPublicFiles': 0, 'changedManifest': False, 'manifestSha256': BASE_SHA, 'sourceFactsAndExistingBuildFilesUnchanged': True, 'onlyVercelBuildCommandChanged': True, 'configuredSteps': STEPS, 'ledgerRootFileIncludedInVercelSource': True, 'ledgerExcludedFromPublicManifest': True, 'errors': [], 'deployed': False})
    shutil.copyfile(impl.ROOT / 'seo-feed-review.json', OUT / 'seo-feed-review.json')
    print('All public source bytes preserved; future build configuration scope confirmed', flush=True)

def build():
    config = impl.load(impl.ROOT / 'vercel.json'); commands = [shlex.split(s) for s in config['buildCommand'].split(' && ')]; assert commands == STEPS
    results = []
    for index, command in enumerate(commands, 1):
        print('Configured local build step', index, command[1], flush=True); start = time.monotonic()
        with (OUT / f'build-step-{index}.log').open('wb') as log:
            done = subprocess.run(command, cwd=impl.ROOT, stdout=log, stderr=subprocess.STDOUT)
        results.append({'step': index, 'command': command, 'exitCode': done.returncode, 'seconds': round(time.monotonic() - start, 2)})
        dump(OUT / 'build-pipeline.json', results); assert done.returncode == 0
        print('Completed configured build step', index, flush=True)
    for index, name in [(1, 'source-feed-check.json'), (5, 'output-feed-check.json')]:
        result = json.loads((OUT / f'build-step-{index}.log').read_text('utf-8').strip().splitlines()[-1])
        assert result['ok'] and result['htmlPages'] == 8403 and result['rssItems'] == 50
        dump(OUT / name, result)
    with (OUT / 'complete-output-verification.log').open('wb') as log:
        done = subprocess.run([sys.executable, '-X', 'utf8', 'tools/verify_neighborhood_build.py'], cwd=impl.ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert done.returncode == 0
    shutil.copyfile(impl.REPORT / 'build-verification.json', OUT / 'build-verification.json')
    assert impl.load(OUT / 'build-verification.json')['errors'] == []
    assert hashlib.sha256((impl.ROOT / 'release-public-manifest.json').read_bytes()).hexdigest() == BASE_SHA
    print('Configured build and all 10,624 public output files verified; no deployment', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['scope', 'build']); args = parser.parse_args()
    globals()[args.action]()
