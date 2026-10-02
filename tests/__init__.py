"""
[TR] Çevrimdışı testler (internet gerekmez). Çalıştırma: python -m unittest discover -s tests -t . -v
[EN] Offline tests (no internet needed). Run: python -m unittest discover -s tests -t . -v
"""
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)
# [TR] Testlerdeki yerel HTTP sunucusuna giden istekler sistem proxy'sine takılmasın.
# [EN] Requests to the tests' local HTTP server must bypass any system proxy.
for _ad in ("NO_PROXY", "no_proxy"):
    _mevcut = os.environ.get(_ad, "")
    if "127.0.0.1" not in _mevcut:
        os.environ[_ad] = ",".join(x for x in (_mevcut, "127.0.0.1", "localhost") if x)
