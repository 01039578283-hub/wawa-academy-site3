"""Loopback-only preview of the current reviewed public manifest."""
from http.server import ThreadingHTTPServer
from preview_learning_guides import Preview
if __name__=='__main__':
    print('Education preview: http://127.0.0.1:8865/교육정보/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8865),Preview).serve_forever()
