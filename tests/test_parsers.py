import os
import unittest

import tests  # noqa: F401  (sys.path)
import ornekler
import scraper


class FiyatCevirmeTest(unittest.TestCase):
    def test_bicimler(self):
        ornekler_ = {"12.499": 12499.0, "15.239,50": 15239.5, "₺1.299": 1299.0, "1299.90": 1299.9,
                     "2.849,00 TL": 2849.0, "1,234.56": 1234.56, "TL 999": 999.0, "Sepette 11.499,00 TL": 11499.0,
                     "1.234.567": 1234567.0, 2499: 2499.0}
        for metin, beklenen in ornekler_.items():
            self.assertEqual(scraper.fiyati_sayiya_cevir(metin), beklenen, metin)
        for bos in ("", None, "abc", 0, "-"):
            self.assertIsNone(scraper.fiyati_sayiya_cevir(bos))


class SiteAyristiriciTest(unittest.TestCase):
    """[TR] Her ayrıştırıcı, beklediği yapıdaki örnek sayfadan tüm ürünleri doğru fiyatla çıkarmalı."""

    def setUp(self):
        self.urunler = ornekler.urun_listesi("ssd", 12)
        self.fiyatlar = {k: f for k, _, f in self.urunler}

    def _dogrula(self, sonuc, kod_cevir=lambda k: k):
        self.assertEqual(len(sonuc), len(self.urunler))
        for kod, fiyat in self.fiyatlar.items():
            veri = sonuc[kod_cevir(kod)]
            self.assertAlmostEqual(veri["fiyat"], fiyat, places=2)
            self.assertTrue(veri["isim"])
            self.assertTrue(veri["url"].startswith("http"))

    def test_vatan(self):
        self._dogrula(scraper.parse_vatan(ornekler.vatan_sayfasi(self.urunler)))

    def test_sinerji_oneri_blogunu_almaz(self):
        sonuc = scraper.parse_sinerji(ornekler.sinerji_sayfasi(self.urunler))
        self._dogrula(sonuc)
        self.assertFalse(any("Monitör" in v["isim"] for v in sonuc.values()))

    def test_incehesap(self):
        self._dogrula(scraper.parse_incehesap(ornekler.incehesap_sayfasi(self.urunler)), lambda k: str(int(k[1:])))

    def test_tebilon(self):
        self._dogrula(scraper.parse_tebilon(ornekler.tebilon_sayfasi(self.urunler)))

    def test_woocommerce_eski_fiyat_ve_stok(self):
        html = ornekler.woocommerce_sayfasi(self.urunler, stok_disi={"P1003"})
        sonuc = scraper.parse_woocommerce(html, "https://www.gaming.gen.tr/", r"/urun/(\d+)/")
        self._dogrula(sonuc, lambda k: k[1:])
        self.assertFalse(sonuc["1003"]["in_stock"])
        self.assertTrue(sonuc["1004"]["in_stock"])

    def test_amazon_ustu_cizili_fiyati_almaz(self):
        self._dogrula(scraper.parse_amazon(ornekler.amazon_sayfasi(self.urunler), "https://www.amazon.com.tr/s"),
                      lambda k: f"B0{k[1:]:0>8}")

    def test_trendyol_kartlari_ve_gomulu_json(self):
        desen = r"-p-(\d{5,})"
        self._dogrula(scraper.parse_trendyol(ornekler.trendyol_sayfasi(self.urunler), "https://www.trendyol.com/x", desen),
                      lambda k: f"{k[1:]}0000")
        sonuc = scraper.parse_trendyol(ornekler.gomulu_json_sayfasi(self.urunler), "https://www.trendyol.com/x", desen)
        self._dogrula(sonuc, lambda k: f"{k[1:]}0000")
        # [TR] Marka adı isme eklenir, görsel CDN'e taşınır. / [EN] Brand is prefixed, image moved to the CDN.
        ilk = sonuc["10000000"]
        self.assertTrue(ilk["image_url"].startswith("https://cdn.dsmcdn.com/"))

    def test_akakce(self):
        self._dogrula(scraper.parse_akakce(ornekler.akakce_sayfasi(self.urunler), "https://www.akakce.com/ssd.html",
                                           r"en-ucuz-[^,\"']+,(\d+)\.html"), lambda k: k[1:])

    def test_genel_kart_kupon_ve_eski_fiyati_almaz(self):
        sonuc = scraper.parse_genel(ornekler.genel_kart_sayfasi(self.urunler), "https://www.hepsiburada.com/x",
                                    r"-pm?-([A-Za-z0-9]{8,})(?:[/?#\"']|$)")
        self._dogrula(sonuc, lambda k: f"HBCV0000{k[1:]}XY")

    def test_genel_jsonld(self):
        sonuc = scraper.parse_genel(ornekler.jsonld_sayfasi(self.urunler), "https://www.teknosa.com/x",
                                    r"-p-(\d{6,})(?:[/?#]|$)")
        self._dogrula(sonuc, lambda k: f"{k[1:]}00000")

    def test_sayfa_ayristir_hata_firlatmaz(self):
        urunler, meta = scraper.sayfa_ayristir("olmayan-parser", "<html></html>", "https://x.test")
        self.assertEqual(urunler, {})
        self.assertIn("KeyError", meta["hata"])
        urunler, meta = scraper.sayfa_ayristir("genel", "<<<bozuk", "https://x.test", r"/p/(\d+)")
        self.assertEqual((urunler, meta["hata"]), ({}, None))


@unittest.skipUnless(os.path.exists(ornekler.ITOPYA_ORNEK), "itopya_temp.html yok")
class GercekItopyaSayfasiTest(unittest.TestCase):
    """[TR] Depodaki gerçek İtopya sayfasıyla (canlı siteden kaydedilmiş). / [EN] Real saved İtopya page."""

    @classmethod
    def setUpClass(cls):
        cls.html = ornekler.itopya_sayfasi()
        cls.sonuc, cls.meta = scraper.sayfa_ayristir("itopya", cls.html, "https://www.itopya.com/rambellek_k10")

    def test_tum_urunler_ve_sepette_fiyat(self):
        self.assertEqual(len(self.sonuc), 20)
        self.assertEqual(self.sonuc["33440"]["fiyat"], 11499.0)  # [TR] "Sepette 11.499,00" (liste: 15.359,40)
        self.assertTrue(all(v["isim"] and v["url"].startswith("https://www.itopya.com/") for v in self.sonuc.values()))

    def test_toplam_sayfa(self):
        self.assertEqual(self.meta["toplam_sayfa"], 6)  # urunSayisi = 110 -> ceil(110 / 20)

    def test_genel_ayristirici_ayni_sonucu_bulur(self):
        """[TR] Sadece ürün linki deseniyle, site yapısını bilmeden aynı fiyatlar. / [EN] Same prices from link pattern only."""
        genel = scraper.parse_genel(self.html, "https://www.itopya.com/", r"_u(\d+)")
        self.assertEqual(set(genel), set(self.sonuc))
        for kod, veri in self.sonuc.items():
            self.assertAlmostEqual(genel[kod]["fiyat"], veri["fiyat"], places=2)
            self.assertEqual(genel[kod]["image_url"], veri["image_url"])


if __name__ == "__main__":
    unittest.main()
