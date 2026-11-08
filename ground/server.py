"""Ground station web server (stdlib only): GET / -> 4-map page, GET /api/view -> GroundView.view() JSON."""
import json, os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

WEB = os.path.join(os.path.dirname(__file__), "web")


def make_server(view, port=8000, host="127.0.0.1"):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=WEB, **kw)

        def do_GET(self):
            if self.path.startswith("/api/view"):
                body = json.dumps(view.view()).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer((host, port), Handler)


def serve(view, port=8000):
    srv = make_server(view, port)
    print(f"Ground station: http://localhost:{srv.server_address[1]}")
    srv.serve_forever()
