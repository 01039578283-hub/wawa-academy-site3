"""Loopback-only preview of the allowlisted release output."""
import json, mimetypes
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, unquote, quote

ROOT=Path(__file__).resolve().parents[1]
BUILT=ROOT/'.public-release'
PUBLIC=set(json.loads((ROOT/'release-public-manifest.json').read_text('utf-8-sig'))['files'])

class Preview(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_HEAD(self):self.respond(False)
    def do_GET(self):self.respond(True)
    def respond(self,with_body):
        parts=urlsplit(self.path);path=unquote(parts.path);query='?'+parts.query if parts.query else ''
        destination=None
        if path.endswith('/index.html'):destination=path.removesuffix('index.html')
        elif path!='/' and not path.endswith('/') and not Path(path).suffix:destination=path+'/'
        if destination:
            self.send_response(308);self.send_header('Location',quote(destination,safe='/')+query);self.end_headers();return
        name=path.lstrip('/')+('index.html' if path.endswith('/') else '')
        if name not in PUBLIC:
            self.send_response(404);self.end_headers();return
        mime=mimetypes.guess_type(name)[0] or 'application/octet-stream'
        if name.endswith('.js'):mime='text/javascript'
        if name.endswith(('.html','.txt','.css','.js','.xml','.json')):mime+='; charset=utf-8'
        data=(BUILT/name).read_bytes()
        self.send_response(200)
        for key,value in {'Content-Type':mime,'Content-Length':str(len(data)),'X-Content-Type-Options':'nosniff','X-Robots-Tag':'noindex, nofollow','Cache-Control':'no-store'}.items():self.send_header(key,value)
        self.end_headers()
        if with_body:self.wfile.write(data)

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8863),Preview)
    print('Local learning-guide preview: http://127.0.0.1:8863/학습가이드/',flush=True)
    server.serve_forever()
