#!/usr/bin/env python3
"""Local preview without browser caching, so an edited engine or chapter is never hidden by a stale copy.

    python3 serve.py 8765 site        # then open http://localhost:8765/<book>/

python3 -m http.server sends no Cache-Control and has a backlog of 5, which drops connections when a page opens
many files at once; this server sends no-store and queues up to 128.
"""
import functools, http.server, sys

class NoStore(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(0 if sys.argv[1:] in (["-h"], ["--help"]) else 2)
    port, root = int(sys.argv[1]), sys.argv[2]
    print(f"serving {root} at http://localhost:{port}/ (no-store)", flush=True)
    Server(("", port), functools.partial(NoStore, directory=root)).serve_forever()
