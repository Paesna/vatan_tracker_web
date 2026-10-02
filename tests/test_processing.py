import asyncio
import datetime
import unittest
from unittest import mock

from sqlalchemy import inspect, text

import tests  # noqa: F401  (sys.path)
import config
import crawler
import database
import main
import ornekler
from tests.yardimci import GeciciDB, SahteMagaza

T0 = datetime.datetime(2026, 10, 1, 12, 0, 0)


def sonuc(site="vatan", kategori="ssd", urunler=None, basarili=True, tam=True, kapsam=None):
    s = crawler.HedefSonucu(site, kategori, "https://x.test", basarili=basarili, tam=tam, kapsam=kapsam)
    s.urunler = urunler or {}
    return s


def urun(isim, fiyat, stok=True):
    return {"isim": isim, "fiyat": fiyat, "url": f"https://x.test/{abs(hash(isim))}", "image_url": "", "in_stock": stok}


SSD1 = "Samsung 990 EVO Plus 1TB NVMe M.2 SSD"
SSD2 = "Kingston NV3 2TB PCIe 4.0 NVMe M.2 SSD"
SSD3 = "WD Black SN850X 4TB Soğutuculu NVMe M.2 SSD"


class IslemeTest(unittest.TestCase):
    def setUp(self):
        self.db = GeciciDB().__enter__()
        database.init_db()
        self.patchler = [mock.patch.dict(config.KATEGORILER["ssd"], {"butce": 20000.0}),
                         mock.patch.object(config, "BUTCE_PAYI_YUZDE", 15.0),
                         mock.patch.object(config, "INDIRIM_YUZDESI", 15.0),
                         mock.patch.object(config, "STOK_BILDIRIM_DAKIKA", 60),
                         mock.patch.object(config, "ESKIME_SAAT", 6.0),
                         mock.patch.object(config, "SON_GORULME_GUNCELLEME_DAKIKA", 30)]
        for p in self.patchler:
            p.start()

    def tearDown(self):
        for p in self.patchler:
            p.stop()
        self.db.__exit__()

    def tur(self, sonuclar, zaman):
        durum = database.durum_yukle()
        islem = main.sonuclari_isle(sonuclar, durum, zaman)
        database.toplu_yaz(islem["yeni_urunler"], islem["guncellemeler"], islem["gecmis"], islem["hedef_durumlari"],
                           son_tarama=zaman)
        return islem

    def test_ilk_tarama_bildirimsiz_sonra_yeni_urun(self):
        islem = self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0), "B": urun(SSD2, 5000.0)})], T0)
        self.assertEqual(islem["sayac"]["yeni"], 2)
        self.assertEqual(islem["bildirimler"], [])  # [TR] baseline
        islem = self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0), "B": urun(SSD2, 5000.0),
                                         "C": urun(SSD3, 19000.0), "D": urun("Crucial T705 4TB NVMe M.2 SSD", 22000.0),
                                         "E": urun("Samsung 9100 PRO 8TB NVMe M.2 SSD", 30000.0)})],
                         T0 + datetime.timedelta(minutes=2))
        self.assertEqual([b["tur"] for b in islem["bildirimler"]], ["yeni"])  # [TR] C: bütçe içinde
        kodlar = set(database.durum_yukle())
        self.assertIn("D", kodlar)       # [TR] bütçe + pay içinde: takip edilir ama bildirim yok
        self.assertNotIn("E", kodlar)    # [TR] tarama limitinin (23.000) üstü: eklenmez
        self.assertEqual(islem["sayac"]["butce_disi"], 1)

    def test_buyuk_ve_kucuk_dusus_artis(self):
        self.tur([sonuc(urunler={"A": urun(SSD1, 4000.0)})], T0)
        islem = self.tur([sonuc(urunler={"A": urun(SSD1, 3800.0)})], T0 + datetime.timedelta(minutes=2))
        self.assertEqual(islem["bildirimler"], [])  # [TR] %5 düşüş
        islem = self.tur([sonuc(urunler={"A": urun(SSD1, 3300.0)})], T0 + datetime.timedelta(minutes=4))
        self.assertEqual([b["tur"] for b in islem["bildirimler"]], ["indirim"])  # [TR] 4000'e göre %17.5
        self.assertAlmostEqual(islem["bildirimler"][0]["oran"], 17.5)
        st = database.durum_yukle()["A"]
        self.assertEqual((st["base_price"], st["last_price"]), (3300.0, 3300.0))
        self.tur([sonuc(urunler={"A": urun(SSD1, 3600.0)})], T0 + datetime.timedelta(minutes=6))
        self.assertEqual(database.durum_yukle()["A"]["base_price"], 3600.0)  # [TR] artışta base yükselir
        self.assertEqual(len(database.fiyat_gecmisi("A")), 4)

    def test_listeden_dusen_stok_disi_ve_kapsam(self):
        self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0), "B": urun(SSD2, 9000.0)})], T0)
        # [TR] Kapsam 8000: B (9000) kapsam dışı -> dokunulmaz; A görünmüyor -> stok dışı.
        islem = self.tur([sonuc(urunler={}, kapsam=8000.0)], T0 + datetime.timedelta(minutes=2))
        durum = database.durum_yukle()
        self.assertEqual((durum["A"]["in_stock"], durum["B"]["in_stock"]), (0, 1))
        self.assertEqual(islem["sayac"]["stok_disi"], 1)
        # [TR] Başarısız hedefte hiçbir şey stok dışı sayılmaz. / [EN] Failed targets never mark products.
        self.tur([sonuc(urunler={}, basarili=False)], T0 + datetime.timedelta(minutes=4))
        self.assertEqual(database.durum_yukle()["B"]["in_stock"], 1)

    def test_eksik_tarama_eskime_kurali(self):
        self.tur([sonuc(site="amazon", urunler={"A": urun(SSD1, 3000.0)}, tam=False)], T0)
        self.tur([sonuc(site="amazon", urunler={}, tam=False)], T0 + datetime.timedelta(hours=1))
        self.assertEqual(database.durum_yukle()["amazon-A"]["in_stock"], 1)  # [TR] henüz eskimedi
        self.tur([sonuc(site="amazon", urunler={}, tam=False)], T0 + datetime.timedelta(hours=7))
        self.assertEqual(database.durum_yukle()["amazon-A"]["in_stock"], 0)

    def test_stoga_girdi_bildirimi(self):
        self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0), "B": urun(SSD2, 5000.0)})], T0)
        self.tur([sonuc(urunler={})], T0 + datetime.timedelta(minutes=2))
        islem = self.tur([sonuc(urunler={"B": urun(SSD2, 5000.0)})], T0 + datetime.timedelta(minutes=10))
        self.assertEqual(islem["bildirimler"], [])  # [TR] 8 dk: çok kısa
        islem = self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0), "B": urun(SSD2, 5000.0)})], T0 + datetime.timedelta(hours=2))
        self.assertEqual([(b["tur"], b["kod"]) for b in islem["bildirimler"]], [("stok", "A")])

    def test_dusus_ve_stok_tek_bildirim(self):
        self.tur([sonuc(urunler={"A": urun(SSD1, 4000.0)})], T0)
        self.tur([sonuc(urunler={})], T0 + datetime.timedelta(minutes=2))
        islem = self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0)})], T0 + datetime.timedelta(hours=3))
        self.assertEqual([b["tur"] for b in islem["bildirimler"]], ["indirim"])

    def test_pazaryeri_yeni_urun_bildirmez(self):
        self.tur([sonuc(site="trendyol", urunler={"A": urun(SSD1, 3000.0)}, tam=False)], T0)
        islem = self.tur([sonuc(site="trendyol", urunler={"A": urun(SSD1, 3000.0), "B": urun(SSD2, 4000.0)}, tam=False)],
                         T0 + datetime.timedelta(minutes=10))
        self.assertEqual(islem["sayac"]["yeni"], 1)
        self.assertEqual(islem["bildirimler"], [])

    def test_son_gorulme_seyreltilir(self):
        self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0)})], T0)
        islem = self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0)})], T0 + datetime.timedelta(minutes=5))
        self.assertEqual(islem["guncellemeler"], {})  # [TR] değişiklik yok, 30 dk dolmadı -> yazma yok
        islem = self.tur([sonuc(urunler={"A": urun(SSD1, 3000.0)})], T0 + datetime.timedelta(minutes=40))
        self.assertEqual(set(islem["guncellemeler"]["A"]), {"last_seen"})

    def test_hedef_durumu_ve_istatistik_yazilir(self):
        s = sonuc(urunler={"A": urun(SSD1, 3000.0)})
        s.sayfa, s.istek = 2, 2
        self.tur([s], T0)
        self.tur([s], T0 + datetime.timedelta(minutes=2))  # [TR] güncelleme yolu / [EN] update path
        database.toplu_yaz(istatistik={"timestamp": T0, "duration": 3.2, "targets": 1, "ok_targets": 1, "blocked": 0,
                                       "requests": 2, "pages": 2, "products": 1, "bytes": 1000, "pages_per_sec": 0.6,
                                       "products_per_sec": 0.3, "avg_latency": 0.2, "parse_seconds": 0.1,
                                       "db_seconds": 0.01, "changes": 1, "alerts": 0})
        hedefler = database.hedef_durumlari()
        self.assertEqual(len(hedefler), 1)
        self.assertEqual((hedefler[0]["key"], hedefler[0]["ok"], hedefler[0]["pages"]), ("vatan:ssd", 1, 2))
        # [TR] Başarısız tur son başarı zamanını silmez. / [EN] A failed round keeps the last success time.
        hata = sonuc(basarili=False)
        hata.hata, hata.istek = "HTTP 500", 1
        self.tur([hata], T0 + datetime.timedelta(minutes=4))
        hedef = database.hedef_durumlari()[0]
        self.assertEqual((hedef["ok"], hedef["error"], hedef["last_ok"]), (0, "HTTP 500", T0 + datetime.timedelta(minutes=2)))
        self.assertEqual(len(database.tarama_istatistikleri()), 1)
        self.assertEqual(database.get_last_scan(), T0 + datetime.timedelta(minutes=4))


class GecisTest(unittest.TestCase):
    """[TR] Eski (v1) şemalı veritabanı otomatik taşınmalı, veri kaybolmamalı. / [EN] v1 DB migrates losslessly."""

    def test_eski_semadan_gecis(self):
        with GeciciDB():
            with database.engine.begin() as conn:
                conn.execute(text("CREATE TABLE products (code VARCHAR PRIMARY KEY, name VARCHAR, url VARCHAR, "
                                  "base_price FLOAT, first_seen DATETIME)"))
                conn.execute(text("CREATE TABLE price_history (id INTEGER PRIMARY KEY AUTOINCREMENT, code VARCHAR, "
                                  "price FLOAT, in_stock INTEGER, timestamp DATETIME)"))
                conn.execute(text("CREATE TABLE system_status (id INTEGER PRIMARY KEY, last_scan DATETIME)"))
                conn.execute(text("INSERT INTO products VALUES ('BL-1', 'KINGSTON 16GB FURY BEAST DDR5 6000MHz RAM', "
                                  "'https://www.vatanbilgisayar.com/k.html', 7000, '2026-07-01 10:00:00'), "
                                  "('itopya-33440', 'Lexar 16GB THOR DDR5 6000MHz Ram', 'https://www.itopya.com/x_u33440', "
                                  "11000, '2026-07-01 10:00:00')"))
                conn.execute(text("INSERT INTO price_history (code, price, in_stock, timestamp) VALUES "
                                  "('BL-1', 7000, 1, '2026-07-01 10:00:00'), ('BL-1', 6500, 0, '2026-07-02 10:00:00'), "
                                  "('itopya-33440', 11000, 1, '2026-07-01 10:00:00')"))
            database.init_db()
            database.init_db()  # [TR] iki kez çalıştırmak güvenli olmalı / [EN] must be idempotent
            durum = database.durum_yukle()
            self.assertEqual((durum["BL-1"]["site"], durum["BL-1"]["category"]), ("vatan", "ram"))
            self.assertEqual((durum["BL-1"]["last_price"], durum["BL-1"]["in_stock"]), (6500.0, 0))
            self.assertEqual((durum["itopya-33440"]["site"], durum["itopya-33440"]["last_price"]), ("itopya", 11000.0))
            indeksler = {i["name"] for i in inspect(database.engine).get_indexes("price_history")}
            self.assertIn("ix_price_history_code_timestamp", indeksler)
            self.assertEqual(len(database.fiyat_gecmisi("BL-1")), 2)


class BildirimMetniTest(unittest.TestCase):
    def test_html_kacis_ve_tl_bicimi(self):
        b = {"tur": "indirim", "kod": "A", "isim": "Samsung <990> EVO & Plus 1TB NVMe M.2 SSD", "site": "vatan",
             "kategori": "ssd", "url": "https://x.test", "resim": "", "fiyat": 2849.0, "stok": 1,
             "eski_fiyat": 3499.0, "oran": 18.6,
             "ozellikler": {"kapasite_gb": 1000, "arayuz": "NVMe", "form": "M.2"}}
        baslik, mesaj, renk, kaynak, kat_ad, ozet, stok = main._bildirim_metinleri(b)
        self.assertIn("Samsung &lt;990&gt; EVO &amp; Plus", mesaj)
        self.assertIn("2.849,00 TL", mesaj)
        self.assertIn("<s>3.499,00 TL</s>", mesaj)
        self.assertIn("TL/TB", mesaj)
        self.assertEqual((kaynak, stok), ("Vatan Bilgisayar", "Var"))

    def test_bildirim_seli_ozetlenir(self):
        bildirimler = [{"tur": "yeni", "kod": str(i), "isim": f"Ürün {i} 1TB NVMe M.2 SSD", "site": "itopya",
                        "kategori": "ssd", "url": "https://x.test", "resim": "", "fiyat": 1000.0 + i, "stok": 1,
                        "ozellikler": {}} for i in range(main.MAX_BILDIRIM_TUR + 7)]
        with mock.patch.object(main, "telegram_mesaj_gonder") as tg, mock.patch.object(main, "discord_mesaj_gonder") as dc:
            main.bildirimleri_gonder(bildirimler)
        self.assertEqual(dc.call_count, main.MAX_BILDIRIM_TUR)
        self.assertEqual(tg.call_count, main.MAX_BILDIRIM_TUR + 1)
        self.assertIn("+7", tg.call_args_list[-1].args[0])


class UctanUcaTest(unittest.TestCase):
    """[TR] Sahte mağaza -> crawler -> işleme -> DB, gerçek döngüyle (tek tur). / [EN] Full loop, single round."""

    def test_tek_tur(self):
        urunler = ornekler.urun_listesi("ssd", 25, baslangic_fiyat=1000.0, artis=1000.0)

        def yanit(yol, sayfa):
            return 200, ornekler.vatan_sayfasi(urunler[(sayfa - 1) * 10: sayfa * 10])

        with GeciciDB(), SahteMagaza(yanit) as magaza:
            database.init_db()
            site = dict(config.SITES["vatan"])
            site.update(kategoriler={"ssd": f"{magaza.taban}/solid-state-disk/?srt=UP&stk=true"}, istek_araligi=0.01)
            with mock.patch.dict(config.SITES, {"vatan": site}), \
                    mock.patch.dict(config.KATEGORILER["ssd"], {"butce": 20000.0}), \
                    mock.patch.object(config, "PARSE_ISCI_SAYISI", 0):
                asyncio.run(main.dongu(tek_sefer=True, siteler=["vatan"], kategoriler=["ssd"], bildirim_gonder=False))
                durum = database.durum_yukle()
            self.assertEqual(len(durum), 23)  # [TR] 1.000 ... 23.000 TL (limit = 20.000 x 1,15)
            self.assertTrue(all(st["site"] == "vatan" and st["category"] == "ssd" for st in durum.values()))
            # [TR] 3. sayfanın en ucuzu (21.000) limitin altında -> 4. sayfa istenir, boş gelir.
            self.assertEqual(database.hedef_durumlari()[0]["stop_reason"], "bos-sayfa")
            self.assertEqual(len(database.tarama_istatistikleri()), 1)
            self.assertEqual(len(magaza.istekler), 4)


if __name__ == "__main__":
    unittest.main()
