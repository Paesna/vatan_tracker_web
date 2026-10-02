"""
[TR] Asenkron Tarayıcı (Crawler) Modülü / [EN] Async Crawler Module
[TR] Tüm site x kategori hedeflerini aynı anda tarar:
     - curl_cffi AsyncSession: tek oturum, kalıcı (keep-alive) bağlantılar, Chrome TLS parmak izi
     - Site başına eşzamanlılık limiti + istekler arası rastgele aralık (ban yememek için nazik tarama)
     - 403/429/captcha alan siteyi artan sürelerle dinlendirme (cooldown)
     - Sayfalama: fiyata göre sıralı sitelerde bütçe aşılınca durur, tekrar eden/boş sayfada durur
     - HTML ayrıştırma ayrı süreçlerde (ProcessPool) -> çok çekirdekli Linux makinede paralel
[EN] Crawls every site x category target concurrently:
     - curl_cffi AsyncSession: one session, keep-alive connections, Chrome TLS fingerprint
     - Per-site concurrency limit + jittered gap between requests (polite crawling, avoids bans)
     - Sites answering 403/429/captcha are paused with growing cooldowns
     - Pagination: stops when over budget on price-sorted sites, on repeated or empty pages
     - HTML parsing runs in worker processes (ProcessPool) -> parallel on multi-core Linux machines
"""

import asyncio
import multiprocessing
import os
import random
import re
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

import categories
import config
import scraper

# [TR] Bot korumasının döndürdüğü sayfalarda geçen ifadeler. / [EN] Phrases found on bot-protection pages.
_ENGEL_ISARETLERI = re.compile(
    r"captcha|robot olmadiginizi|robot degilim|are you a robot|access denied|attention required|"
    r"just a moment|cf-chl|unusual traffic|automated access|validatecaptcha|px-captcha|"
    r"request unsuccessful|bot detection|guvenlik dogrulamasi", re.IGNORECASE)


def otomatik_eszamanlilik():
    """[TR] CPU çekirdeğine göre toplam eşzamanlı istek sayısı. / [EN] Total concurrency from CPU cores."""
    if config.MAX_ESZAMANLI_ISTEK > 0:
        return config.MAX_ESZAMANLI_ISTEK
    return max(8, min(32, (os.cpu_count() or 2) * 4))


def otomatik_isci_sayisi():
    """[TR] HTML ayrıştırma süreç sayısı. / [EN] Number of HTML parsing worker processes."""
    if config.PARSE_ISCI_SAYISI >= 0:
        return config.PARSE_ISCI_SAYISI
    cekirdek = os.cpu_count() or 1
    return 0 if cekirdek <= 1 else min(4, cekirdek - 1)


@dataclass(frozen=True)
class Hedef:
    """[TR] Taranacak tek bir site x kategori listesi. / [EN] A single site x category listing to crawl."""
    site: str
    kategori: str
    url: str

    @property
    def anahtar(self):
        return f"{self.site}:{self.kategori}"

    @property
    def ayar(self):
        return config.SITES[self.site]

    @property
    def host(self):
        return urlsplit(self.url).netloc


def hedefleri_olustur(siteler=None, kategoriler=None, hepsi=False):
    """
    [TR] Etkin site ve kategorilerden hedef listesi üretir. / [EN] Builds targets from enabled sites/categories.
    Args:
        siteler / kategoriler: [TR] Sadece bunlar (opsiyonel). / [EN] Only these (optional).
        hepsi: [TR] Devre dışı siteleri de dahil et (test/benchmark). / [EN] Include disabled sites too.
    """
    hedefler = []
    for site, ayar in config.SITES.items():
        if siteler and site not in siteler:
            continue
        if not hepsi and not ayar["enabled"]:
            continue
        for kategori, url in ayar["kategoriler"].items():
            if kategoriler and kategori not in kategoriler:
                continue
            if not kategoriler and kategori not in config.AKTIF_KATEGORILER:
                continue
            hedefler.append(Hedef(site, kategori, url))
    return hedefler


def _sorgu_ayarla(url, param, deger):
    """[TR] Sorgu parametresini mevcut kodlamayı bozmadan ekler/değiştirir. / [EN] Sets a query param in place."""
    parca = urlsplit(url)
    sorgu = parca.query
    desen = re.compile(rf"(^|&){re.escape(param)}=[^&]*")
    if desen.search(sorgu):
        sorgu = desen.sub(lambda m: f"{m.group(1)}{param}={deger}", sorgu)
    else:
        sorgu = f"{sorgu}&{param}={deger}" if sorgu else f"{param}={deger}"
    return urlunsplit(parca._replace(query=sorgu))


def sayfa_url(taban, n, sayfalama):
    """
    [TR] n. sayfanın URL'si (1. sayfa her zaman taban URL'dir). / [EN] URL of page n (page 1 is the base URL).
    Tipler / types:
        query     : ?page=n  (param, baslangic=0 ise ?page=n-1, ek: n>=2 için ek parametreler)
        yol       : /kategori/sirala-ucuz/ + "sayfa-{n}/"
        wordpress : /kategori/ssd/ + "page/{n}/" (sorgu korunur)
        akakce    : /ssd.html -> /ssd,{n}.html
    """
    if n <= 1:
        return taban
    tip = sayfalama.get("tip", "query")
    parca = urlsplit(taban)
    if tip == "query":
        deger = n - 1 + sayfalama.get("baslangic", 1)
        url = _sorgu_ayarla(taban, sayfalama.get("param", "page"), deger)
        for anahtar, ek_deger in sayfalama.get("ek", {}).items():
            url = _sorgu_ayarla(url, anahtar, ek_deger)
        return url
    if tip in ("yol", "wordpress"):
        kalip = sayfalama.get("kalip", "page/{n}/") if tip == "yol" else "page/{n}/"
        yol = parca.path if parca.path.endswith("/") else parca.path + "/"
        return urlunsplit(parca._replace(path=yol + kalip.format(n=n)))
    if tip == "akakce":
        yol = re.sub(r"(,\d+)?\.html$", f",{n}.html", parca.path)
        return urlunsplit(parca._replace(path=yol))
    raise ValueError(f"Bilinmeyen sayfalama tipi / unknown pagination type: {tip}")


@dataclass
class HedefSonucu:
    """[TR] Bir hedefin tarama sonucu. / [EN] Crawl result of a single target."""
    site: str
    kategori: str
    url: str
    urunler: dict = field(default_factory=dict)
    # [TR] En az bir sayfa ayrıştırıldı ve kategoriye uyan ürün bulundu. / [EN] Parsed and found products.
    basarili: bool = False
    # [TR] Liste sonuna (veya bütçe sınırına) kadar eksiksiz tarandı. / [EN] Crawled to the end (or budget).
    tam: bool = False
    # [TR] tam=True iken bu fiyatın altındaki her ürün görüldü (None = hepsi). / [EN] Coverage price limit.
    kapsam: float = None
    sayfa: int = 0
    istek: int = 0
    bayt: int = 0
    ham: int = 0
    elenen: int = 0
    sure: float = 0.0
    ag_suresi: float = 0.0
    ayristirma_suresi: float = 0.0
    hata: str = None
    engellendi: bool = False
    durma_nedeni: str = ""

    @property
    def anahtar(self):
        return f"{self.site}:{self.kategori}"


@dataclass
class _Cevap:
    durum: int = 0
    metin: str = ""
    bayt: int = 0
    sure: float = 0.0
    hata: str = None
    engellendi: bool = False
    tekrar_sonra: float = 0.0


class Tarayici:
    """
    [TR] Kullanım: async with Tarayici() as t: sonuclar = await t.hepsini_tara(hedefler)
    [EN] Usage:    async with Tarayici() as t: results = await t.hepsini_tara(targets)
    """

    def __init__(self, max_eszamanli=None, site_basina=None, istek_araligi=None, parse_isci=None,
                 impersonate=None, zaman_asimi=None, tekrar=None, oturum=None):
        self.max_eszamanli = max_eszamanli or otomatik_eszamanlilik()
        self.site_basina = site_basina or config.SITE_BASINA_ESZAMANLI
        self.istek_araligi = config.SITE_ISTEK_ARALIGI_SANIYE if istek_araligi is None else istek_araligi
        self.parse_isci = otomatik_isci_sayisi() if parse_isci is None else parse_isci
        self.impersonate = impersonate or config.IMPERSONATE
        self.zaman_asimi = zaman_asimi or config.ISTEK_ZAMAN_ASIMI
        self.tekrar = config.ISTEK_TEKRAR if tekrar is None else tekrar
        self._oturum = oturum
        self._kendi_oturumu = oturum is None
        self._havuz = None
        self._genel_sem = None
        self._host_sem = {}
        self._host_kilit = {}
        self._host_son = {}
        # [TR] host -> (bitiş zamanı (monotonic), ardışık engel sayısı) / [EN] host -> (until, strike count)
        self._engel = {}

    async def __aenter__(self):
        self._genel_sem = asyncio.Semaphore(self.max_eszamanli)
        if self._oturum is None:
            from curl_cffi.requests import AsyncSession
            self._oturum = AsyncSession(impersonate=self.impersonate, timeout=self.zaman_asimi,
                                        max_clients=self.max_eszamanli)
        if self.parse_isci > 0:
            try:
                # [TR] "spawn": asyncio/curl iş parçacıklarıyla güvenli, Windows'ta da çalışır.
                # [EN] "spawn": safe alongside asyncio/curl threads and works on Windows too.
                self._havuz = ProcessPoolExecutor(max_workers=self.parse_isci,
                                                  mp_context=multiprocessing.get_context("spawn"))
            except (OSError, ValueError) as e:
                print(f"⚠️ Ayrıştırma süreç havuzu açılamadı, tek süreçte devam / parse pool unavailable: {e}")
                self._havuz = None
        return self

    async def __aexit__(self, *exc):
        if self._oturum is not None and self._kendi_oturumu:
            try:
                await self._oturum.close()
            except Exception:
                pass
        if self._havuz is not None:
            self._havuz.shutdown(wait=False, cancel_futures=True)

    # --- ENGEL / COOLDOWN ---
    def engel_kalan(self, host):
        """[TR] Host dinlendiriliyorsa kalan saniye, değilse 0. / [EN] Seconds left in a host's cooldown."""
        bitis, _ = self._engel.get(host, (0, 0))
        return max(0.0, bitis - time.monotonic())

    def _engelle(self, host, tekrar_sonra=0.0):
        _, sayac = self._engel.get(host, (0, 0))
        sayac += 1
        sure = min(7200, config.ENGEL_BEKLEME_SANIYE * (2 ** (sayac - 1)))
        sure = max(sure, tekrar_sonra or 0)
        self._engel[host] = (time.monotonic() + sure, sayac)
        return sure

    def _engel_sifirla(self, host):
        # [TR] Aynı sitenin başka bir hedefi az önce engel aldıysa, süren dinlenmeyi silme.
        # [EN] Don't clear an active cooldown that another target of the same site just triggered.
        bitis, sayac = self._engel.get(host, (0, 0))
        if sayac and bitis <= time.monotonic():
            self._engel[host] = (0, 0)

    # --- HTTP ---
    async def _sira_bekle(self, host, aralik):
        """[TR] Aynı siteye istekler arasında rastgele (±%30) boşluk bırakır. / [EN] Jittered per-host gap."""
        kilit = self._host_kilit.setdefault(host, asyncio.Lock())
        async with kilit:
            bekle = self._host_son.get(host, 0) + aralik * random.uniform(0.7, 1.3) - time.monotonic()
            if bekle > 0:
                await asyncio.sleep(bekle)
            self._host_son[host] = time.monotonic()

    def _basliklar(self, site, n):
        basliklar = {"Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"}
        if site == "tebilon" and (config.TEBILON_COOKIE or config.TEBILON_USER_AGENT):
            # [TR] Tarayıcıdan kopyalanan çerez, o tarayıcının User-Agent'ı ile birlikte gönderilmeli.
            # [EN] A cookie copied from a browser must be sent with that browser's User-Agent.
            basliklar["User-Agent"] = config.TEBILON_USER_AGENT or config.HEADERS["User-Agent"]
            if config.TEBILON_COOKIE:
                basliklar["Cookie"] = config.TEBILON_COOKIE
        if site == "itopya" and n > 1:
            basliklar["X-Requested-With"] = "XMLHttpRequest"
        return basliklar

    async def getir(self, url, site, n=1):
        """[TR] Bir sayfayı nazik limitler, tekrar deneme ve engel tespitiyle indirir. / [EN] Polite fetch."""
        host = urlsplit(url).netloc
        ayar = config.SITES.get(site, {})
        aralik = ayar.get("istek_araligi", self.istek_araligi)
        sem = self._host_sem.setdefault(host, asyncio.Semaphore(self.site_basina))
        cevap = _Cevap()
        for deneme in range(self.tekrar + 1):
            async with sem:
                await self._sira_bekle(host, aralik)
                async with self._genel_sem:
                    t0 = time.monotonic()
                    try:
                        r = await self._oturum.get(url, headers=self._basliklar(site, n), timeout=self.zaman_asimi)
                        cevap = _Cevap(durum=r.status_code, metin=r.text or "", bayt=len(r.content or b""),
                                       sure=time.monotonic() - t0)
                        try:
                            cevap.tekrar_sonra = float(r.headers.get("Retry-After") or 0)
                        except (TypeError, ValueError):
                            cevap.tekrar_sonra = 0.0
                    except Exception as e:
                        cevap = _Cevap(hata=f"{type(e).__name__}: {str(e)[:160]}", sure=time.monotonic() - t0)
            if cevap.hata is None:
                if cevap.durum in (403, 429) or (cevap.durum == 503 and _ENGEL_ISARETLERI.search(cevap.metin[:20000])):
                    cevap.engellendi = True
                    cevap.hata = f"HTTP {cevap.durum} (engel / blocked)"
                    return cevap
                if cevap.durum >= 500:
                    cevap.hata = f"HTTP {cevap.durum}"
                elif cevap.durum >= 400:
                    cevap.hata = f"HTTP {cevap.durum}"
                    return cevap
                else:
                    return cevap
            if deneme < self.tekrar:
                await asyncio.sleep((1.5 ** deneme) + random.uniform(0, 0.5))
        return cevap

    async def ayristir(self, parser_adi, html, url, desen):
        """[TR] HTML'i süreç havuzunda (yoksa iş parçacığında) ayrıştırır. / [EN] Parses in pool or thread."""
        if self._havuz is not None:
            try:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(self._havuz, scraper.sayfa_ayristir, parser_adi, html, url, desen)
            except Exception as e:  # BrokenProcessPool vb. / etc.
                print(f"⚠️ Süreç havuzu hatası, iş parçacığına geçiliyor / pool failed, using threads: {e}")
                self._havuz = None
        return await asyncio.to_thread(scraper.sayfa_ayristir, parser_adi, html, url, desen)

    # --- HEDEF TARAMA / TARGET CRAWL ---
    async def hedef_tara(self, hedef):
        ayar = hedef.ayar
        sonuc = HedefSonucu(hedef.site, hedef.kategori, hedef.url)
        t0 = time.monotonic()
        kalan = self.engel_kalan(hedef.host)
        if kalan > 0:
            sonuc.engellendi = True
            sonuc.hata = f"dinlendiriliyor / cooling down ({int(kalan)} sn)"
            return sonuc

        limit = config.tarama_limiti(hedef.kategori)
        sirali = ayar.get("fiyata_gore_sirali", False)
        max_sayfa = max(1, int(ayar.get("max_sayfa", config.MAX_SAYFA)))
        gorulen = set()
        toplam_sayfa = None
        n = 1
        while True:
            if n > 1 and self.engel_kalan(hedef.host) > 0:
                # [TR] Aynı sitenin başka bir hedefi engel aldı; bu taramayı da yarıda bırak.
                # [EN] Another target of this site got blocked; stop this crawl too.
                sonuc.engellendi = True
                sonuc.hata = "site engel aldı, tarama yarıda kesildi / site blocked, crawl stopped"
                break
            url = sayfa_url(hedef.url, n, ayar.get("sayfalama", {}))
            cevap = await self.getir(url, hedef.site, n)
            sonuc.istek += 1
            sonuc.ag_suresi += cevap.sure
            sonuc.bayt += cevap.bayt
            if cevap.engellendi:
                sonuc.engellendi = True
                sure = self._engelle(hedef.host, cevap.tekrar_sonra)
                sonuc.hata = f"{cevap.hata}; {int(sure)} sn dinlendirilecek / cooling down"
                break
            if cevap.hata:
                sonuc.hata = f"sayfa {n}: {cevap.hata}"
                break

            t_ayristir = time.monotonic()
            urunler, meta = await self.ayristir(ayar["parser"], cevap.metin, url, ayar.get("urun_link_deseni"))
            sonuc.ayristirma_suresi += time.monotonic() - t_ayristir
            sonuc.sayfa += 1
            if meta.get("hata"):
                sonuc.hata = f"sayfa {n} ayrıştırma / parse: {meta['hata']}"
                break
            if n == 1:
                toplam_sayfa = meta.get("toplam_sayfa")

            if not urunler:
                if n == 1:
                    if _ENGEL_ISARETLERI.search(cevap.metin[:50000]):
                        sonuc.engellendi = True
                        sure = self._engelle(hedef.host)
                        sonuc.hata = f"bot koruması / captcha; {int(sure)} sn dinlendirilecek"
                    else:
                        sonuc.hata = "0 ürün: site yapısı değişmiş olabilir / 0 products: markup may have changed"
                else:
                    sonuc.tam, sonuc.durma_nedeni = True, "bos-sayfa"
                break

            yeni = {k: v for k, v in urunler.items() if k not in gorulen}
            if not yeni:
                # [TR] Ya liste bitti ya da site sayfa parametresini yok sayıyor; ikisini ayırt edemeyiz.
                #      Sıralı listede görülen en yüksek fiyata kadar kapsam kesindir; sırasız listede eksik sayılır.
                # [EN] Either the list ended or the site ignores the page parameter; we can't tell which.
                #      On a sorted list coverage up to the highest seen price is certain; unsorted counts as partial.
                fiyatlar = [v["fiyat"] for v in sonuc.urunler.values()]
                if sirali and fiyatlar:
                    sonuc.tam, sonuc.kapsam = True, max(fiyatlar)
                sonuc.durma_nedeni = "tekrar-eden-sayfa"
                break
            gorulen.update(yeni)
            sonuc.ham += len(yeni)

            sayfa_fiyatlari = []
            for kod, veri in yeni.items():
                if categories.kategoriye_uygun_mu(hedef.kategori, veri.get("isim"),
                                                  ddr5_zorunlu=ayar.get("ram_ddr5_zorunlu", False),
                                                  notebook_ram_haric=config.NOTEBOOK_RAM_HARIC):
                    sonuc.urunler[kod] = veri
                    sayfa_fiyatlari.append(veri["fiyat"])
                else:
                    sonuc.elenen += 1

            if toplam_sayfa and n >= toplam_sayfa:
                sonuc.tam, sonuc.durma_nedeni = True, "son-sayfa"
                break
            if sirali and sayfa_fiyatlari and min(sayfa_fiyatlari) > limit:
                # [TR] Fiyata göre artan sıralı listede bu sayfanın en ucuzu bile bütçe sınırının üstünde.
                # [EN] Ascending price list: even this page's cheapest item is above the budget limit.
                sonuc.tam, sonuc.kapsam, sonuc.durma_nedeni = True, min(sayfa_fiyatlari), "butce"
                break
            if n >= max_sayfa:
                if sirali and sayfa_fiyatlari:
                    sonuc.tam, sonuc.kapsam = True, min(sayfa_fiyatlari)
                sonuc.durma_nedeni = "max-sayfa"
                break
            n += 1

        if sonuc.sayfa and not sonuc.engellendi:
            self._engel_sifirla(hedef.host)
        if sonuc.urunler:
            sonuc.basarili = True
        elif sonuc.ham and not sonuc.hata:
            sonuc.hata = (f"kategori filtresi {sonuc.ham} ürünün hepsini eledi / category filter "
                          f"dropped all {sonuc.ham} products")
        if not sonuc.basarili:
            sonuc.tam = False
        sonuc.sure = time.monotonic() - t0
        return sonuc

    async def hepsini_tara(self, hedefler):
        """[TR] Tüm hedefleri eşzamanlı tarar; hata fırlatmaz. / [EN] Crawls all targets concurrently."""
        async def guvenli(hedef):
            try:
                return await self.hedef_tara(hedef)
            except Exception as e:
                s = HedefSonucu(hedef.site, hedef.kategori, hedef.url)
                s.hata = f"beklenmeyen hata / unexpected: {type(e).__name__}: {e}"
                return s
        return await asyncio.gather(*(guvenli(h) for h in hedefler))


def ozet_istatistik(sonuclar, sure):
    """[TR] Tarama özeti (sayfa/sn, ürün/sn...). / [EN] Scan summary (pages/s, products/s...)."""
    sayfa = sum(s.sayfa for s in sonuclar)
    urun = sum(len(s.urunler) for s in sonuclar)
    istek = sum(s.istek for s in sonuclar)
    ag = sum(s.ag_suresi for s in sonuclar)
    return {
        "sure": sure,
        "hedef": len(sonuclar),
        "basarili": sum(1 for s in sonuclar if s.basarili),
        "engel": sum(1 for s in sonuclar if s.engellendi),
        "hata": sum(1 for s in sonuclar if s.hata and not s.basarili),
        "istek": istek,
        "sayfa": sayfa,
        "urun": urun,
        "bayt": sum(s.bayt for s in sonuclar),
        "sayfa_sn": sayfa / sure if sure > 0 else 0.0,
        "urun_sn": urun / sure if sure > 0 else 0.0,
        "ort_gecikme": ag / istek if istek else 0.0,
        "ayristirma": sum(s.ayristirma_suresi for s in sonuclar),
    }
