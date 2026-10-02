"""
[TR] Performans Ölçümü ve Site Sağlık Kontrolü / [EN] Performance Benchmark and Site Health Check
[TR] Bu Linux makinenin saniyede kaç sayfa/ürün ayrıştırabildiğini, veritabanı hızını ve (isteğe bağlı) canlı
     sitelerin cevap süresini ölçer; sonuçlara göre .env ayarları önerir.
[EN] Measures how many pages/products per second this machine can parse, the database speed and (optionally)
     live site latency, then recommends .env settings.

Kullanım / Usage:
    python benchmark.py                      # [TR] çevrimdışı: CPU + DB (internet gerekmez) / [EN] offline
    python benchmark.py --canli              # [TR] + her hedefin 1. sayfası (site sağlığı) / [EN] + page 1 of every target
    python benchmark.py --canli --tam        # [TR] + tam tarama turu (DB'ye yazmaz) / [EN] + full crawl (no DB writes)
    python benchmark.py --canli --site vatan,itopya --kategori ssd
"""

import argparse
import asyncio
import multiprocessing
import os
import platform
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

import config
import crawler
import ornekler
import scraper

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


def _bellek_gb():
    try:
        with open("/proc/meminfo") as f:
            for satir in f:
                if satir.startswith("MemTotal:"):
                    return int(satir.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return None


def sistem_bilgisi():
    print("=== SİSTEM / SYSTEM ===")
    bellek = _bellek_gb()
    try:
        import curl_cffi
        curl_surum = curl_cffi.__version__
    except Exception:
        curl_surum = "yok / missing"
    print(f"  OS: {platform.platform()} | Python {platform.python_version()} | CPU çekirdeği: {os.cpu_count()}"
          + (f" | RAM: {bellek:.1f} GB" if bellek else ""))
    print(f"  HTML parser: {scraper.HTML_PARSER}" + ("" if scraper.HTML_PARSER == "lxml" else
          "  ⚠️ lxml kurulu değil! 'pip install -r requirements.txt' ile kurun (~2 kat hızlı ayrıştırma)."))
    print(f"  curl_cffi: {curl_surum} | impersonate: {config.IMPERSONATE}")


def _ayristir_toplu(isler):
    """[TR] Süreç havuzu işçisi: bir paket sayfayı ayrıştırır. / [EN] Pool worker: parses a batch of pages."""
    toplam = 0
    for parser, desen, html, url in isler:
        urunler, _ = scraper.sayfa_ayristir(parser, html, url, desen)
        toplam += len(urunler)
    return toplam


def cpu_olcumu(sure=1.5):
    """[TR] Ayrıştırıcı başına ve çok çekirdekli toplam ayrıştırma hızı. / [EN] Per-parser and multi-core speed."""
    print("\n=== HTML AYRIŞTIRMA HIZI (tek çekirdek) / PARSE SPEED (single core) ===")
    ornek = ornekler.benchmark_ornekleri()
    toplam_sayfa_sn = []
    for parser, desen, html, url in ornek:
        urunler, meta = scraper.sayfa_ayristir(parser, html, url, desen)
        n, t0 = 0, time.perf_counter()
        while time.perf_counter() - t0 < sure / len(ornek) * 3 or n < 3:
            scraper.sayfa_ayristir(parser, html, url, desen)
            n += 1
        gecen = time.perf_counter() - t0
        sayfa_sn = n / gecen
        toplam_sayfa_sn.append(sayfa_sn)
        print(f"  {parser:<12} {len(html) / 1024:7.0f} KB | {len(urunler):3d} ürün | {1000 * gecen / n:6.1f} ms/sayfa | "
              f"{sayfa_sn:6.1f} sayfa/sn | {sayfa_sn * len(urunler):7.0f} ürün/sn" + (f" | HATA: {meta['hata']}" if meta["hata"] else ""))

    if scraper.HTML_PARSER == "lxml":
        from bs4 import BeautifulSoup
        html = ornek[0][2]
        t0 = time.perf_counter()
        for _ in range(3):
            BeautifulSoup(html, "html.parser")
        yavas = (time.perf_counter() - t0) / 3
        t0 = time.perf_counter()
        for _ in range(3):
            BeautifulSoup(html, "lxml")
        hizli = (time.perf_counter() - t0) / 3
        print(f"  -> lxml, yerleşik html.parser'dan {yavas / hizli:.1f} kat hızlı ({ornek[0][0]} sayfası: "
              f"{1000 * yavas:.0f} ms -> {1000 * hizli:.0f} ms)")

    ort_tek = sum(toplam_sayfa_sn) / len(toplam_sayfa_sn)
    print("\n=== ÇOK ÇEKİRDEKLİ AYRIŞTIRMA / MULTI-CORE PARSING (ProcessPool) ===")
    is_paketi = [ornek[i % len(ornek)] for i in range(len(ornek) * 4)]
    cekirdek = os.cpu_count() or 1
    denenecek = sorted({1, 2, 4, max(1, cekirdek - 1), cekirdek})
    en_iyi = (0, ort_tek)
    olcumler = {}
    for isci in [w for w in denenecek if w <= max(cekirdek, 1)]:
        with ProcessPoolExecutor(max_workers=isci, mp_context=multiprocessing.get_context("spawn")) as havuz:
            list(havuz.map(_ayristir_toplu, [[x] for x in ornek[:isci]]))  # [TR] ısınma / [EN] warm-up
            t0 = time.perf_counter()
            paketler = [is_paketi[i::isci * 2] for i in range(isci * 2)]
            urun = sum(havuz.map(_ayristir_toplu, paketler))
            gecen = time.perf_counter() - t0
        sayfa_sn = len(is_paketi) / gecen
        print(f"  {isci} süreç: {sayfa_sn:6.1f} sayfa/sn | {urun / gecen:7.0f} ürün/sn")
        olcumler[isci] = sayfa_sn
        if sayfa_sn > en_iyi[1] * 1.15:
            en_iyi = (isci, sayfa_sn)
    return olcumler.get(1, ort_tek), en_iyi


def db_olcumu(adet=3000):
    """[TR] Eski (satır satır) ve yeni (toplu) yazma hızını geçici SQLite'ta karşılaştırır. / [EN] Old vs bulk writes."""
    print("\n=== VERİTABANI / DATABASE (geçici SQLite) ===")
    import database
    from main import sonuclari_isle
    klasor = tempfile.mkdtemp(prefix="tracker_bench_")
    try:
        database.configure_engine("sqlite:///" + os.path.join(klasor, "bench.db").replace("\\", "/"))
        database.init_db()
        simdi = database.get_tr_time()

        n_eski = 150
        t0 = time.perf_counter()
        for i in range(n_eski):
            database.add_product(f"eski-{i}", f"Ürün {i}", "https://x.test", 1000.0 + i, None, "vatan", "ssd")
            database.add_price_history(f"eski-{i}", 1000.0 + i, 1)
            database.get_product_base(f"eski-{i}")
            database.get_last_history(f"eski-{i}")
        eski_sn = n_eski / (time.perf_counter() - t0)

        sonuc = crawler.HedefSonucu("vatan", "ssd", "https://x.test", basarili=True, tam=True)
        sonuc.urunler = {f"Y{i}": {"isim": f"Samsung 990 EVO {i} 1TB NVMe M.2 SSD", "fiyat": 1000.0 + i,
                                   "url": f"https://x.test/{i}", "image_url": "", "in_stock": True}
                         for i in range(adet)}
        t0 = time.perf_counter()
        durum = database.durum_yukle()
        islem = sonuclari_isle([sonuc], durum, simdi)
        database.toplu_yaz(islem["yeni_urunler"], islem["guncellemeler"], islem["gecmis"], islem["hedef_durumlari"])
        toplu_sn = adet / (time.perf_counter() - t0)

        t0 = time.perf_counter()
        durum = database.durum_yukle()
        yukle = time.perf_counter() - t0
        print(f"  Eski yöntem (ürün başına ayrı sorgular): {eski_sn:8.0f} ürün/sn")
        print(f"  Yeni yöntem (tek sorgu + toplu yazma)  : {toplu_sn:8.0f} ürün/sn  -> {toplu_sn / eski_sn:.0f} kat hızlı")
        print(f"  {len(durum)} ürün durumunu yükleme: {1000 * yukle:.0f} ms")
        print("  Not: Supabase gibi uzak PostgreSQL'de her sorgu ~20-80 ms ağ gecikmesi ekler; fark orada çok daha büyüktür.")
        return toplu_sn
    finally:
        database.configure_engine(config.DB_URL)
        shutil.rmtree(klasor, ignore_errors=True)


def oneriler(tek_surec, en_iyi, canli=None):
    print("\n=== ÖNERİLER / RECOMMENDATIONS ===")
    hedefler = crawler.hedefleri_olustur()
    hostlar = {}
    for h in hedefler:
        hostlar.setdefault(h.host, []).append(h)
    gecikme = (canli or {}).get("ort_gecikme") or 0.8
    # [TR] Kabaca: uzman sitelerde hedef başına ~6, pazar yerlerinde ~3 sayfa. / [EN] Rough page estimates.
    tahmini_sure = 0.0
    toplam_sayfa = 0
    for host, liste in hostlar.items():
        ayar = liste[0].ayar
        sayfa = sum(min(ayar["max_sayfa"], 3 if ayar["pazaryeri"] else 6) for _ in liste)
        toplam_sayfa += sayfa
        aralik = ayar.get("istek_araligi", config.SITE_ISTEK_ARALIGI_SANIYE)
        host_sure = sayfa * max(aralik, gecikme / config.SITE_BASINA_ESZAMANLI)
        tahmini_sure = max(tahmini_sure, host_sure)
    ayristirma_kapasitesi = en_iyi[1]
    ag_kapasitesi = sum(1.0 / max(liste[0].ayar.get("istek_araligi", config.SITE_ISTEK_ARALIGI_SANIYE),
                                  gecikme / config.SITE_BASINA_ESZAMANLI) for liste in hostlar.values())
    # [TR] Ağın getirebileceğinin 2 katını ayrıştıracak kadar süreç yeter; fazlası boşuna RAM harcar.
    # [EN] Enough workers to parse 2x what the network can deliver; more just wastes RAM.
    gereken = int(-(-(ag_kapasitesi * 2) // max(tek_surec, 1e-6)))
    isci = max(1, min(en_iyi[0] or 1, gereken)) if (os.cpu_count() or 1) > 1 else 0
    print(f"  Etkin hedef: {len(hedefler)} ({len(hostlar)} site) | tahmini sayfa/tur: ~{toplam_sayfa}")
    print(f"  Ağ tarafı (nazik limitlerle) en fazla ~{ag_kapasitesi:.1f} sayfa/sn; "
          f"CPU tarafı ~{ayristirma_kapasitesi:.0f} sayfa/sn ayrıştırabilir.")
    darbogaz = "AĞ / site nezaket limitleri" if ag_kapasitesi < ayristirma_kapasitesi else "CPU (ayrıştırma)"
    print(f"  -> Darboğaz / bottleneck: {darbogaz}. Bir tam tur tahminen ~{tahmini_sure:.0f} sn sürer.")
    min_aralik = max(60, int(tahmini_sure * 3))
    print("\n  .env için önerilen ayarlar / suggested .env settings:")
    print(f"    PARSE_ISCI_SAYISI={isci}")
    print(f"    MAX_ESZAMANLI_ISTEK={crawler.otomatik_eszamanlilik()}")
    print(f"    SITE_BASINA_ESZAMANLI={config.SITE_BASINA_ESZAMANLI}   # 3+ ban riskini artırır / raises ban risk")
    print(f"    KONTROL_SIKLIGI_SANIYE={max(min_aralik, 120)}   # en az / at least {min_aralik}")
    if darbogaz.startswith("CPU"):
        print("  İpucu: CPU darboğaz ise PARSE_ISCI_SAYISI'nı çekirdek sayısına yaklaştırın.")
    else:
        print("  İpucu: Ağ darboğazında hızlandırmak için SITE_ISTEK_ARALIGI_SANIYE'yi düşürmek mümkün ama"
              " sitelerin sizi engelleme (403) riskini artırır; önce 0.5'i deneyin.")


async def canli_olcum(siteler=None, kategoriler=None, tam=False):
    """[TR] Canlı siteler: 1. sayfa sağlık kontrolü veya tam tarama. / [EN] Live: page-1 health or full crawl."""
    hedefler = crawler.hedefleri_olustur(siteler, kategoriler, hepsi=bool(siteler))
    print(f"\n=== CANLI ÖLÇÜM / LIVE ({'tam tarama' if tam else '1. sayfa'}) - {len(hedefler)} hedef ===")
    if not tam:
        for site in {h.site for h in hedefler}:
            config.SITES[site]["max_sayfa"] = 1
    t0 = time.monotonic()
    async with crawler.Tarayici() as tarayici:
        sonuclar = await tarayici.hepsini_tara(hedefler)
    ozet = crawler.ozet_istatistik(sonuclar, time.monotonic() - t0)
    for s in sorted(sonuclar, key=lambda x: (x.site, x.kategori)):
        dogrulandi = "" if config.SITES[s.site]["dogrulandi"] else " (beta)"
        if s.basarili:
            gecikme = s.ag_suresi / max(1, s.istek)
            print(f"  ✅ {s.site + dogrulandi:<18} {s.kategori:<8} | {s.sayfa} sayfa | {len(s.urunler):4d} ürün "
                  f"({s.elenen} elendi) | gecikme {gecikme:.2f} sn | ayrıştırma {1000 * s.ayristirma_suresi / max(1, s.sayfa):.0f} ms/sayfa"
                  + (f" | {s.durma_nedeni}" if tam else ""))
        else:
            print(f"  {'⛔' if s.engellendi else '❌'} {s.site + dogrulandi:<18} {s.kategori:<8} | {s.hata}")
    print(f"\n  Toplam: {ozet['sayfa']} sayfa, {ozet['urun']} ürün, {ozet['bayt'] / 1e6:.1f} MB, {ozet['sure']:.1f} sn -> "
          f"{ozet['sayfa_sn']:.1f} sayfa/sn, {ozet['urun_sn']:.0f} ürün/sn | ort. gecikme {ozet['ort_gecikme']:.2f} sn | "
          f"{ozet['basarili']}/{ozet['hedef']} hedef başarılı, {ozet['engel']} engelli")
    return ozet


def _liste(deger):
    return [p.strip().lower() for p in deger.split(",") if p.strip()] if deger else None


def ana():
    ap = argparse.ArgumentParser(description="Tarayıcı performans ölçümü / crawler benchmark")
    ap.add_argument("--canli", action="store_true", help="Canlı sitelere istek at / hit live sites")
    ap.add_argument("--tam", action="store_true", help="Canlı modda tam tarama / full crawl in live mode")
    ap.add_argument("--site", help="Sadece bu siteler / only these sites")
    ap.add_argument("--kategori", help="Sadece bu kategoriler / only these categories")
    ap.add_argument("--sure", type=float, default=1.5, help="CPU ölçüm süresi (sn) / CPU test seconds")
    args = ap.parse_args()

    sistem_bilgisi()
    ort_tek, en_iyi = cpu_olcumu(args.sure)
    db_olcumu()
    canli = None
    if args.canli:
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        canli = asyncio.run(canli_olcum(_liste(args.site), _liste(args.kategori), args.tam))
    oneriler(ort_tek, en_iyi, canli)


if __name__ == "__main__":
    ana()
