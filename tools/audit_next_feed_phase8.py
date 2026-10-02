"""Read-only comparison of existing RSS items with their current destinations."""
from email.utils import parsedate_to_datetime
from urllib.parse import unquote, urlsplit
import hashlib, json
from lxml import etree, html
import improve_neighborhood_pages as impl
from audit_neighborhood_phase8 import OUT
from audit_neighborhood_phase5 import filename
from audit_neighborhood_phase6 import dump
from validate_neighborhood_seo import nodes

def main():
    raw = (impl.ROOT / 'rss.xml').read_bytes(); feed = etree.fromstring(raw); records = []
    for item in feed.xpath('//item'):
        path = unquote(urlsplit(item.findtext('link')).path)
        doc = html.document_fromstring((impl.ROOT / filename(path)).read_bytes())
        headline = ' '.join(doc.xpath('//h1')[0].itertext()).strip()
        modified = []
        for script in doc.xpath('//script[@type="application/ld+json"]'):
            for node in nodes(json.loads(script.text)):
                if node.get('@type') in ['WebPage', 'CollectionPage', 'Article'] and node.get('dateModified'):
                    modified.append(node['dateModified'][:10])
        description = item.findtext('description') or ''
        records.append({'path': path, 'rssTitle': item.findtext('title'), 'currentH1': headline, 'titlesEqual': item.findtext('title') == headline, 'rssPubDate': item.findtext('pubDate'), 'currentModifiedDates': modified, 'summaryCharacters': len(description), 'embeddedBody': description.lstrip().startswith('<section')})
    output = {'rssItems': len(records), 'rssLastBuildDate': feed.xpath('//channel/lastBuildDate/text()'), 'differentTitles': sum(not r['titlesEqual'] for r in records), 'embeddedBodyItems': sum(r['embeddedBody'] for r in records), 'itemsPublishedBeforeCurrentModifiedDate': sum(bool(r['currentModifiedDates']) and parsedate_to_datetime(r['rssPubDate']).date().isoformat() < max(r['currentModifiedDates']) for r in records), 'pages': records, 'rssSha256': hashlib.sha256(raw).hexdigest(), 'interpretation': 'A shorter feed title or older publication date is not alone a feed error. Review current page purpose, summaries and actual modification dates together before changing the feed.', 'readOnly': True, 'deployed': False}
    dump(OUT / 'next-feed-audit.json', output)
    print(json.dumps({k: v for k, v in output.items() if k != 'pages'}, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
