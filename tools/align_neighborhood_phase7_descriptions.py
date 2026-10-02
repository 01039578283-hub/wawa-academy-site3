"""Update only eleven reviewed summaries in the existing editorial build input."""
import copy,hashlib,json
import improve_neighborhood_pages as impl
from audit_neighborhood_phase7 import OUT
from audit_neighborhood_phase6 import dump

def main():
    path=impl.ROOT/'seo-descriptions.json';snapshot=OUT/'seo-descriptions-before-phase7.json'
    raw=path.read_bytes()
    if not snapshot.exists():snapshot.write_bytes(raw)
    before=json.loads(snapshot.read_bytes().decode('utf-8-sig'));expected=copy.deepcopy(before)
    reviewed=impl.load(OUT/'reviewed-pages.json');audit=impl.load(OUT/'hub-audit.json');changes=[]
    for page in audit['pages']:
        key=page['path'].rstrip('/') or '/';entry=expected['pages'][key]
        description=reviewed[page['path']]['description'];assert len(description)<=80 and description.endswith('.')
        assert entry['description']==page['oldDescription']
        entry['sources']=list(dict.fromkeys(entry.get('sources',[])+[page['oldDescription'],description]));entry['description']=description
        changes.append({'path':page['path'],'before':page['oldDescription'],'after':description})
    assert json.loads(raw.decode('utf-8-sig')) in [before,expected]
    dump(path,expected)
    result={'reviewedPages':len(changes),'changes':changes,'oldConfigSha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'newConfigSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'otherEntriesUnchanged':True,'deployed':False}
    dump(OUT/'description-input-alignment.json',result)
    print('Aligned reviewed descriptions',len(changes),'other editorial entries unchanged',flush=True)

if __name__=='__main__':main()
