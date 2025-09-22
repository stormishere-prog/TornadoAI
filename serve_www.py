import os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.getcwd(), "www")
PORT = int(os.environ.get("PORT", "8787"))

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Always serve from ROOT
        import posixpath, urllib.parse
        path = path.split('?',1)[0].split('#',1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = [w for w in path.split('/') if w]
        full = ROOT
        for w in words:
            full = os.path.join(full, w)
        return full

    def log_message(self, fmt, *args):
        pass  # quiet

if __name__ == "__main__":
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Serving {ROOT} on http://127.0.0.1:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
