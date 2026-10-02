"""[TR] Test yardımcıları: geçici DB ve sahte mağaza HTTP sunucusu. / [EN] Test helpers: temp DB and fake shop server."""
import os
import shutil
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs

import database


class GeciciDB:
    """[TR] Her test için boş bir SQLite veritabanı. / [EN] A fresh SQLite database per test."""

    def __enter__(self):
        self.klasor = tempfile.mkdtemp(prefix="tracker_test_")
        self.url = "sqlite:///" + os.path.join(self.klasor, "test.db").replace("\\", "/")
        database.configure_engine(self.url)
        return self

    def __exit__(self, *exc):
        database.engine.dispose()
        shutil.rmtree(self.klasor, ignore_errors=True)


class SahteMagaza:
    """
    [TR] Sayfalı ürün listesi sunan yerel HTTP sunucusu. `yanit(yol, sayfa)` -> (durum, html) ile davranış değişir.
    [EN] Local HTTP server serving a paged product listing. Behaviour is set via `yanit(path, page)` -> (status, html).
    """

    def __init__(self, yanit):
        self.yanit = yanit
        self.istekler = []
        magaza = self

        class Isleyici(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                parca = urlsplit(self.path)
                q = parse_qs(parca.query)
                sayfa = int((q.get("page") or q.get("pg") or ["1"])[0])
                magaza.istekler.append((time.monotonic(), self.path, dict(self.headers)))
                durum, govde = magaza.yanit(parca.path, sayfa)
                veri = govde.encode("utf-8")
                self.send_response(durum)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(veri)))
                self.end_headers()
                self.wfile.write(veri)

        self.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
        self.taban = f"http://127.0.0.1:{self.sunucu.server_address[1]}"

    def __enter__(self):
        threading.Thread(target=self.sunucu.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.sunucu.shutdown()
        self.sunucu.server_close()
