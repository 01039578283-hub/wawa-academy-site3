"""Loopback-only preview using the current combined release allowlist."""
from http.server import ThreadingHTTPServer
from preview_learning_guides import Preview

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8864),Preview)
    print('Local teacher finder preview: http://127.0.0.1:8864/선생님찾기/',flush=True)
    server.serve_forever()
