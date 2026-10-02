"""Back up the reviewed second release and audit same-purpose paragraphs.

Counts are descriptive, not search-engine scores. Common factual data and
reusable teaching advice can legitimately recur across local service areas.
"""
from pathlib import Path
from collections import defaultdict, Counter
import json, hashlib, zipfile
from lxml import html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase2 import paragraphs

OUT = Path(r'C:\Users\1992k\Desktop\CodexData\outputs\site3-neighborhood-phase3-20261001')

def audit(rows, read):
    groups = defaultdict(list)
    signatures = defaultdict(list)
    for index, row in enumerate(rows, 1):
        doc = html.document_fromstring(read(row))
        values = paragraphs(doc, row)
        for value in values:
            groups[(row['role'], value)].append(row['path'])
        signatures[(row['role'], tuple(sorted(values)))].append(row['path'])
        if index % 2000 == 0:
            print('Audited same-purpose pages', index, flush=True)
    repeated = [(key, paths) for key, paths in groups.items() if len(paths) > 1]
    identical = [(key, paths) for key, paths in signatures.items() if key[1] and len(paths) > 1]
    return {
        'pages': len(rows), 'roles': dict(Counter(row['role'] for row in rows)),
        'scope': 'phase2 designated editorial paragraphs >=70 characters; area/branch/address normalized; factual school paragraphs and shared disclosure text excluded',
        'interpretation': 'Remaining repeated guidance is not automatically a defect. This is not site-wide similarity or a Naver quality score.',
        'sameRoleParagraphGroups': len(repeated),
        'sameRoleParagraphOccurrences': sum(len(paths) for _, paths in repeated),
        'sameRoleEditorialSignatures': len(identical),
        'sameRoleEditorialSignaturePages': sum(len(paths) for _, paths in identical),
        'examples': [{'role': key[0], 'text': key[1], 'occurrences': len(paths), 'paths': paths[:5]} for key, paths in sorted(repeated, key=lambda item: -len(item[1]))[:24]],
    }

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / 'phase2-before-phase3.zip'
    assert not backup.exists(), 'Never replace the reviewed phase-2 backup'
    manifest = impl.load(impl.ROOT / 'release-public-manifest.json')
    with zipfile.ZipFile(backup, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for index, name in enumerate(manifest['files'], 1):
            if name.endswith('.html') or name in ['assets/neighborhood-seo/local.css', 'sitemap.xml', 'seo-descriptions.json']:
                raw = (impl.ROOT / name).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == manifest['files'][name], name
                archive.writestr(name, raw)
            if index % 3000 == 0:
                print('Backed up reviewed files', index, flush=True)
        archive.write(impl.ROOT / 'release-public-manifest.json', 'release-public-manifest.json')
        archive.write(impl.ROOT / 'seo-descriptions.json', 'seo-descriptions.json')
        for folder in [impl.DATA, impl.REPORT]:
            for path in folder.glob('*.json'):
                archive.write(path, path.relative_to(impl.ROOT).as_posix())
    with zipfile.ZipFile(backup) as archive:
        assert archive.testzip() is None
    rows = impl.inventory()
    result = audit(rows, lambda row: (impl.ROOT / row['path'].strip('/') / 'index.html').read_bytes())
    result['backup'] = str(backup)
    impl.dump(OUT / 'before.json', result)
    print(json.dumps({key: value for key, value in result.items() if key != 'examples'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
