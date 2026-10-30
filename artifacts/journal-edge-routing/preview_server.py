from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]


class Preview(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        relative = urlsplit(path).path.lstrip('/') or 'index.html'
        base = ROOT / ('site' if relative == 'index.html' or relative.startswith(('js/', 'css/')) else 'dist')
        target = (base / relative).resolve()
        return str(target if target.is_relative_to(base.resolve()) else base / '__missing__')

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(('127.0.0.1', 0), Preview)
print(f'http://127.0.0.1:{server.server_port}/#/journal?view=atlas', flush=True)
server.serve_forever()
