from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
root = Path.cwd()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=str(root / "dist"), **kw)
    def translate_path(self, path):
        clean = path.split("?")[0]
        if clean in ("/js/journal.js", "/js/journal-notes.js", "/css/journal.css"):
            return str(root / "site" / clean.lstrip("/"))
        return super().translate_path(path)
ThreadingHTTPServer(("127.0.0.1", 8748), Handler).serve_forever()
