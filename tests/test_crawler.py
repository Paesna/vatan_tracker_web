import asyncio
import time
import unittest
from unittest import mock

import tests  # noqa: F401  (sys.path)
import config
import crawler
import ornekler
from tests.yardimci import SahteMagaza

URUNLER = ornekler.urun_listesi("ssd", 40, baslangic_fiyat=1000.0, artis=1000.0)  # 1.000 ... 40.000 TL


def listeli_magaza(urunler=URUNLER, sayfa_boyutu=10, sayfayi_yok_say=False):
    def yanit(yol, sayfa):
        if sayfayi_yok_say:
            sayfa = 1
        dilim = urunler[(sayfa - 1) * sayfa_boyutu: sayfa * sayfa_boyutu]
        return 200, ornekler.vatan_sayfasi(dilim)
    return SahteMagaza(yanit)


def test_sitesi(taban, **ek):
    site = {"ad": "Test", "renk": "#000", "parser": "vatan", "dogrulandi": True, "kod_on_eki": "test-",
            "kategoriler": {"ssd": f"{taban}/ssd/?srt=UP"}, "sayfalama": {"tip": "query", "param": "page"},
            "fiyata_gore_sirali": True, "pazaryeri": False, "yeni_urun_bildirimi": True, "ram_ddr5_zorunlu": False,
            "max_sayfa": 15, "aralik": 120, "enabled": True, "istek_araligi": 0.01}
    site.update(ek)
    return site


def tara(site, **tarayici_ayar):
    async def calistir():
        ayar = {"parse_isci": 0, "tekrar": 1, "istek_araligi": 0.01}
        ayar.update(tarayici_ayar)
        async with crawler.Tarayici(**ayar) as t:
            hedef = crawler.Hedef("test", "ssd", site["kategoriler"]["ssd"])
            ilk = await t.hedef_tara(hedef)
            return ilk, t
    with mock.patch.dict(config.SITES, {"test": site}):
        return asyncio.run(calistir())


class SayfaUrlTest(unittest.TestCase):
    def test_query(self):
        taban = "https://www.vatanbilgisayar.com/pc-bilgisayar-bellek-ram/?opf=p26559%2F&srt=UP&stk=true"
        self.assertEqual(crawler.sayfa_url(taban, 1, {"tip": "query", "param": "page"}), taban)
        self.assertEqual(crawler.sayfa_url(taban, 3, {"tip": "query", "param": "page"}), taban + "&page=3")
        # [TR] Mevcut parametre değiştirilir, başlangıç 0 olabilir, ek parametreler eklenir.
        self.assertEqual(crawler.sayfa_url("https://t.test/x?page=1&a=b", 2, {"tip": "query", "param": "page", "baslangic": 0}),
                         "https://t.test/x?page=1&a=b")
        self.assertEqual(crawler.sayfa_url("https://www.itopya.com/ssd_k20?or=edf", 2,
                                           {"tip": "query", "param": "pg", "ek": {"isFR": "false"}}),
                         "https://www.itopya.com/ssd_k20?or=edf&pg=2&isFR=false")

    def test_yol_wordpress_akakce(self):
        self.assertEqual(crawler.sayfa_url("https://www.incehesap.com/ssd-harddisk-fiyatlari/sirala-ucuz/", 2,
                                           {"tip": "yol", "kalip": "sayfa-{n}/"}),
                         "https://www.incehesap.com/ssd-harddisk-fiyatlari/sirala-ucuz/sayfa-2/")
        self.assertEqual(crawler.sayfa_url("https://www.gaming.gen.tr/kategori/bilgisayar-bilesenleri/ssd/?orderby=price",
                                           4, {"tip": "wordpress"}),
                         "https://www.gaming.gen.tr/kategori/bilgisayar-bilesenleri/ssd/page/4/?orderby=price")
        self.assertEqual(crawler.sayfa_url("https://www.akakce.com/ram/ddr5.html", 5, {"tip": "akakce"}),
                         "https://www.akakce.com/ram/ddr5,5.html")


class HedefTest(unittest.TestCase):
    def test_hedef_listesi(self):
        hedefler = crawler.hedefleri_olustur(siteler=["vatan", "itopya"], kategoriler=["ssd", "anakart"])
        self.assertEqual({(h.site, h.kategori) for h in hedefler},
                         {("vatan", "ssd"), ("vatan", "anakart"), ("itopya", "ssd"), ("itopya", "anakart")})
        with mock.patch.dict(config.SITES["amazon"], {"enabled": False}):
            self.assertNotIn("amazon", {h.site for h in crawler.hedefleri_olustur()})
            self.assertIn("amazon", {h.site for h in crawler.hedefleri_olustur(hepsi=True)})


class TaramaTest(unittest.TestCase):
    def test_butce_siniri_durdurur(self):
        with listeli_magaza() as magaza, mock.patch.dict(config.KATEGORILER["ssd"], {"butce": 20000.0}):
            sonuc, _ = tara(test_sitesi(magaza.taban))
        # [TR] Limit 23.000 TL: 3. sayfanın en ucuzu (21.000) altında, 4. sayfanınki (31.000) üstünde.
        self.assertTrue(sonuc.basarili and sonuc.tam)
        self.assertEqual((sonuc.sayfa, sonuc.durma_nedeni), (4, "butce"))
        self.assertEqual(sonuc.kapsam, 31000.0)
        self.assertEqual(len(sonuc.urunler), 40)
        self.assertEqual(len(magaza.istekler), 4)

    def test_tekrar_eden_sayfa_ve_bos_sayfa(self):
        # [TR] Sayfa parametresi yok sayılıyor: sırasız listede eksik, sıralıda görülen en yüksek fiyata kadar tam.
        # [EN] Page parameter ignored: partial on unsorted lists, complete up to the highest seen price on sorted ones.
        with listeli_magaza(sayfayi_yok_say=True) as magaza:
            sonuc, _ = tara(test_sitesi(magaza.taban, fiyata_gore_sirali=False))
        self.assertEqual((sonuc.sayfa, sonuc.durma_nedeni, sonuc.tam, len(sonuc.urunler)), (2, "tekrar-eden-sayfa", False, 10))
        with listeli_magaza(sayfayi_yok_say=True) as magaza:
            sonuc, _ = tara(test_sitesi(magaza.taban))
        self.assertEqual((sonuc.durma_nedeni, sonuc.tam, sonuc.kapsam), ("tekrar-eden-sayfa", True, 10000.0))
        with listeli_magaza(urunler=URUNLER[:15]) as magaza:
            sonuc, _ = tara(test_sitesi(magaza.taban, fiyata_gore_sirali=False))
        self.assertEqual((sonuc.sayfa, sonuc.durma_nedeni, sonuc.tam, sonuc.kapsam), (3, "bos-sayfa", True, None))

    def test_max_sayfa_siralanmamis_listede_eksik_sayilir(self):
        with listeli_magaza() as magaza:
            sonuc, _ = tara(test_sitesi(magaza.taban, fiyata_gore_sirali=False, max_sayfa=2))
        self.assertTrue(sonuc.basarili)
        self.assertFalse(sonuc.tam)
        self.assertEqual((sonuc.sayfa, sonuc.durma_nedeni), (2, "max-sayfa"))

    def test_kategori_filtresi(self):
        urunler = URUNLER[:5] + [("PX1", "ASUS ROG STRIX ARION M.2 NVMe USB 3.2 SSD KUTUSU", 900.0)]
        with listeli_magaza(urunler=urunler) as magaza:
            sonuc, _ = tara(test_sitesi(magaza.taban))
        self.assertEqual((len(sonuc.urunler), sonuc.elenen), (5, 1))
        hepsi_cop = [("PX1", "ASUS ROG STRIX ARION M.2 NVMe USB 3.2 SSD KUTUSU", 900.0)]
        with listeli_magaza(urunler=hepsi_cop) as magaza:
            sonuc, _ = tara(test_sitesi(magaza.taban))
        self.assertFalse(sonuc.basarili)
        self.assertIn("kategori filtresi", sonuc.hata)

    def test_403_engel_ve_dinlenme(self):
        with SahteMagaza(lambda yol, sayfa: (403, "Forbidden")) as magaza:
            async def calistir():
                async with crawler.Tarayici(parse_isci=0, tekrar=2, istek_araligi=0.01) as t:
                    hedef = crawler.Hedef("test", "ssd", f"{magaza.taban}/ssd/")
                    ilk = await t.hedef_tara(hedef)
                    ikinci = await t.hedef_tara(hedef)
                    return ilk, ikinci, t.engel_kalan(hedef.host)
            with mock.patch.dict(config.SITES, {"test": test_sitesi(magaza.taban)}):
                ilk, ikinci, kalan = asyncio.run(calistir())
            self.assertEqual(len(magaza.istekler), 1)  # [TR] 403'te tekrar denenmez / [EN] no retry on 403
        self.assertTrue(ilk.engellendi and not ilk.basarili)
        self.assertTrue(ikinci.engellendi)
        self.assertEqual(ikinci.istek, 0)  # [TR] dinlenirken hiç istek atılmaz / [EN] no request while cooling down
        self.assertGreater(kalan, config.ENGEL_BEKLEME_SANIYE - 5)

    def test_captcha_sayfasi_engel_sayilir(self):
        with SahteMagaza(lambda yol, sayfa: (200, "<html><body>Lütfen robot olmadığınızı doğrulayın (captcha)</body></html>")) as magaza:
            sonuc, _ = tara(test_sitesi(magaza.taban))
        self.assertTrue(sonuc.engellendi)
        self.assertFalse(sonuc.basarili)

    def test_5xx_tekrar_denenir(self):
        sayac = {"n": 0}

        def yanit(yol, sayfa):
            sayac["n"] += 1
            if sayac["n"] == 1:
                return 502, "bad gateway"
            return 200, ornekler.vatan_sayfasi(URUNLER[:5] if sayfa == 1 else [])
        with SahteMagaza(yanit) as magaza:
            sonuc, _ = tara(test_sitesi(magaza.taban))
        self.assertTrue(sonuc.basarili)
        self.assertEqual(len(sonuc.urunler), 5)

    def test_site_basina_nezaket_araligi(self):
        with listeli_magaza() as magaza, mock.patch.dict(config.KATEGORILER["ssd"], {"butce": 50000.0}):
            tara(test_sitesi(magaza.taban, istek_araligi=0.2), site_basina=2)
        zamanlar = [z for z, _, _ in magaza.istekler]
        araliklar = [b - a for a, b in zip(zamanlar, zamanlar[1:])]
        self.assertTrue(araliklar)
        self.assertGreaterEqual(min(araliklar), 0.2 * 0.7 - 0.02)

    def test_eszamanli_hedefler_ve_surec_havuzu(self):
        """[TR] Birden çok hedef aynı anda taranır; ayrıştırma ayrı süreçte yapılır. / [EN] Concurrency + process pool."""
        with listeli_magaza() as magaza:
            site = test_sitesi(magaza.taban, istek_araligi=0.0)
            site["kategoriler"] = {"ssd": f"{magaza.taban}/ssd/?srt=UP", "ram": f"{magaza.taban}/ram/?srt=UP"}

            async def calistir():
                async with crawler.Tarayici(parse_isci=1, tekrar=0, istek_araligi=0.0) as t:
                    hedefler = [crawler.Hedef("test", "ssd", site["kategoriler"]["ssd"]),
                                crawler.Hedef("test", "ssd", site["kategoriler"]["ram"])]
                    t0 = time.monotonic()
                    sonuclar = await t.hepsini_tara(hedefler)
                    return sonuclar, crawler.ozet_istatistik(sonuclar, time.monotonic() - t0)
            with mock.patch.dict(config.SITES, {"test": site}):
                sonuclar, ozet = asyncio.run(calistir())
        self.assertTrue(all(s.basarili for s in sonuclar))
        self.assertEqual(ozet["basarili"], 2)
        self.assertGreater(ozet["sayfa_sn"], 0)


if __name__ == "__main__":
    unittest.main()
