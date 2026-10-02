"""Loopback-only, public-route allowlist preview. Never serves tools or secrets."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlsplit
import argparse

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_DIRS={'assets','전국센터','과목별학원','학습관리','상담문의','지점안내'}
PUBLIC_FILES={'index.html','robots.txt','sitemap.xml','rss.xml','llms.txt'}
class Handler(SimpleHTTPRequestHandler):
    finder_data_unavailable=False
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.webp':'image/webp','.avif':'image/avif'}
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
    def do_GET(self):
        path=unquote(urlsplit(self.path).path).lstrip('/')
        if self.finder_data_unavailable and path=='assets/neighborhood-seo/find-guide.json':
            self.send_error(503);return
        parts=Path(path).parts
        allowed=(not parts or path in PUBLIC_FILES or parts[0] in PUBLIC_DIRS)
        if not allowed or '..' in parts or '\\' in path or any(p.startswith('.') for p in parts):
            self.send_error(404);return
        resolved=(ROOT/path).resolve()
        if not resolved.is_relative_to(ROOT):self.send_error(404);return
        if resolved.is_dir() and not (resolved/'index.html').is_file():self.send_error(404);return
        return super().do_GET()
    do_HEAD=do_GET
    def end_headers(self):
        self.send_header('X-Robots-Tag','noindex, nofollow')
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def log_message(self,*args):pass

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8852);parser.add_argument('--finder-data-unavailable',action='store_true');args=parser.parse_args()
    Handler.finder_data_unavailable=args.finder_data_unavailable
    print('Public-only preview: http://127.0.0.1:'+str(args.port)+'/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
