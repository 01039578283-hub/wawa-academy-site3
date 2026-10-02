"""Keep unconfirmed pages without asserting an available course in schema."""
import json
from lxml import html
import improve_neighborhood_pages as impl

def main():
 changed=0;unconfirmed=0
 for r in impl.inventory():
  if r['role']!='enrollment' or not r.get('subject'):continue
  c=impl.CENTERS[tuple(r['centerKey'])]
  if impl.grades_for(r,c,r['subject']):continue
  unconfirmed+=1;path=impl.ROOT/r['path'].strip('/')/'index.html';before=path.read_text('utf-8');doc=html.document_fromstring(before);guard=impl.protect(doc)
  for script in doc.xpath('//script[@type="application/ld+json"]'):
   data=json.loads(script.text);graph=data.get('@graph',[])
   graph[:]=[n for n in graph if n.get('@type')!='Service']
   script.text=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
  assert impl.protect(doc)==guard
  after=html.tostring(doc,encoding='unicode',method='html',doctype='<!DOCTYPE html>')+'\n'
  if after!=before:impl.write_page(path,after);changed+=1
 impl.dump(impl.REPORT/'unconfirmed-course-schema.json',{'unconfirmedEnrollmentPages':unconfirmed,'changedPages':changed,'urlsRetained':unconfirmed,'deployed':False})
 print(json.dumps({'unconfirmedEnrollmentPages':unconfirmed,'changedPages':changed,'urlsRetained':unconfirmed},ensure_ascii=False))
if __name__=='__main__':main()
