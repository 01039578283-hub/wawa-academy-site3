"""Keep editorial build input aligned with the 35 reviewed hub summaries."""
import copy, hashlib, json
import improve_neighborhood_pages as impl
from audit_neighborhood_phase8 import OUT
from audit_neighborhood_phase6 import dump

def main():
    path = impl.ROOT / 'seo-descriptions.json'; snapshot = OUT / 'seo-descriptions-before-phase8.json'
    before = json.loads(snapshot.read_text('utf-8-sig')); expected = copy.deepcopy(before)
    configs = impl.load(OUT / 'reviewed-configs.json'); changes = []
    for page in impl.load(OUT / 'reviewed-pages.json'):
        key = page['path'].rstrip('/'); entry = expected['pages'][key]
        assert entry['description'] == page['oldDescription']
        description = configs[page['path']]['description']
        assert len(description) <= 80 and description.endswith('.')
        entry['sources'] = list(dict.fromkeys(entry.get('sources', []) + [page['oldDescription'], description]))
        entry['description'] = description
        changes.append({'path': page['path'], 'before': page['oldDescription'], 'after': description})
    current = path.read_bytes()
    previous = impl.load(OUT / 'description-input-alignment.json') if (OUT / 'description-input-alignment.json').exists() else None
    assert json.loads(current.decode('utf-8-sig')) in [before, expected] or previous and hashlib.sha256(current).hexdigest() == previous['newConfigSha256']
    dump(path, expected)
    dump(OUT / 'description-input-alignment.json', {'reviewedPages': len(changes), 'changes': changes, 'oldConfigSha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(), 'newConfigSha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'otherEntriesUnchanged': True, 'deployed': False})
    print('Aligned reviewed editorial descriptions:', len(changes), flush=True)

if __name__ == '__main__':
    main()
