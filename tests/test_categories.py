import unittest

import tests  # noqa: F401  (sys.path)
import categories as c


class KategoriKurallariTest(unittest.TestCase):
    def test_ram_kabul_ve_ret(self):
        kabul = ["KINGSTON 16GB FURY BEAST DDR5 6000MHz CL36 PC RAM",
                 "Lexar 16GB THOR RGB 6000MHz CL36 XMP/ EXPO DDR5 Single Kit Ram",
                 "Corsair 32GB (2x16GB) Vengeance RGB 6000MHz CL30 DDR5 Ram",
                 "Lexar 16GB Thor 2nd 6000MHz CL36 XMP/ EXPO DDR5 Soğutuculu Single Kit Ram"]
        ret = ["RAM Soğutucu Fanı", "Lenovo IdeaPad 16GB RAM 512GB SSD Laptop",
               "MSI RTX 4060 8GB GDDR6 2460MHz", "SanDisk 64GB USB Bellek", "Samsung Odyssey G5 27\" Monitör"]
        for isim in kabul:
            self.assertTrue(c.kategoriye_uygun_mu("ram", isim), isim)
        for isim in ret:
            self.assertFalse(c.kategoriye_uygun_mu("ram", isim), isim)

    def test_ram_ddr5_zorunlu(self):
        self.assertTrue(c.kategoriye_uygun_mu("ram", "Kingston Fury Beast 32GB (2x16) 6000MHz CL36", ddr5_zorunlu=True))
        self.assertFalse(c.kategoriye_uygun_mu("ram", "G.Skill 32GB DDR4 3600MHz Ram", ddr5_zorunlu=True))
        self.assertFalse(c.kategoriye_uygun_mu("ram", "Kingston 8GB 3200MHz Ram", ddr5_zorunlu=True))
        # [TR] Eski siteler (URL'de DDR5 filtresi var) için DDR5 şartı yok. / [EN] No DDR5 requirement by default.
        self.assertTrue(c.kategoriye_uygun_mu("ram", "Kingston 8GB 3200MHz Ram"))

    def test_notebook_ram_haric(self):
        isim = "Crucial 16GB DDR5 4800MHz SODIMM Notebook Ram"
        self.assertTrue(c.kategoriye_uygun_mu("ram", isim))
        self.assertFalse(c.kategoriye_uygun_mu("ram", isim, notebook_ram_haric=True))

    def test_ssd_kabul_ve_ret(self):
        kabul = ["Samsung 990 EVO Plus 1TB NVMe M.2 SSD (Okuma 7150MB / Yazma 6300MB)",
                 "Samsung 990 PRO 2TB NVMe M.2 SSD Soğutucu ile",
                 "WD 1TB Black NVMe M.2 Soğutuculu SSD (3470MB Okuma / 3000MB Yazma)",
                 "KINGSTON 240GB A400 SATA 3.0 SSD", "Samsung 870 EVO 1TB 2.5\" SATA",
                 "MSI SPATIUM M560 2TB PCIe 5.0 NVMe M.2"]
        ret = ["ASUS ROG STRIX ARION WHITE M.2 NVMe USB 3.2 SSD KUTUSU", "Samsung T7 Shield 2TB Taşınabilir SSD",
               "M.2 SSD Soğutucu Heatsink", "Seagate Barracuda 2TB 7200RPM SATA HDD",
               "HP Victus 16GB RAM 1TB SSD RTX 4060 Laptop", "SSD 2.5 inç Kızak Aparatı",
               "Kingston 240GB SSD (Arızalı)"]
        for isim in kabul:
            self.assertTrue(c.kategoriye_uygun_mu("ssd", isim), isim)
        for isim in ret:
            self.assertFalse(c.kategoriye_uygun_mu("ssd", isim), isim)

    def test_anakart_kabul_ve_ret(self):
        kabul = ["MSI PRO H610M-E DDR5 INTEL H610", "ASROCK B450M-HDV R4.0 AMD B450", "GIGABYTE B650 AORUS ELITE AX",
                 "ASUS ROG STRIX B860-F GAMING WIFI Intel B860 LGA 1851 ATX Anakart", "MSI PRO B760M-A D4 WIFI",
                 "ASUS TUF GAMING B650-PLUS WIFI AM5 ATX (M.2 Soğutucu)"]
        ret = ["Redmi 8 Anakart Sim Sd Kart Okuyucu", "Noctua NH-U12S AM5 Soğutucu",
               "AMD Ryzen 5 7600 + B650 Anakart Paket", "Astec Anakart Hm55 Ddr3 Vga-Ses-Lan-Sata 988P",
               "Anakart Pili CR2032", "Lenovo ThinkPad T480 Laptop Anakart"]
        for isim in kabul:
            self.assertTrue(c.kategoriye_uygun_mu("anakart", isim), isim)
        for isim in ret:
            self.assertFalse(c.kategoriye_uygun_mu("anakart", isim), isim)

    def test_turkce_normalize(self):
        self.assertEqual(c.normalize("İŞLEMCİ Soğutuculu TAŞINABİLİR"), "islemci sogutuculu tasinabilir")
        self.assertEqual(c.normalize(None), "")


class OzellikCikarmaTest(unittest.TestCase):
    def test_ssd(self):
        oz = c.ssd_ozellikleri("Samsung 990 EVO Plus 1TB NVMe M.2 SSD (Okuma 7150MB / Yazma 6300MB)")
        self.assertEqual(oz["kapasite_gb"], 1000)
        self.assertEqual(oz["arayuz"], "NVMe")
        self.assertEqual(oz["form"], "M.2")
        self.assertEqual(oz["okuma_mbs"], 7150)
        oz = c.ssd_ozellikleri("Kingston 1000GB SNV2S/1000G Serisi NVMe M.2 SSD")
        self.assertEqual(oz["kapasite_gb"], 1000)
        oz = c.ssd_ozellikleri("MSI SPATIUM M560 2TB PCIe 5.0 NVMe M.2")
        self.assertEqual((oz["kapasite_gb"], oz["pcie_gen"]), (2000, "Gen5"))
        oz = c.ssd_ozellikleri("Samsung 870 EVO 500GB 2.5\" SATA 3.0 SSD (1GB LPDDR4 Cache)")
        self.assertEqual((oz["kapasite_gb"], oz["arayuz"], oz["form"]), (500, "SATA", '2.5"'))

    def test_anakart(self):
        oz = c.anakart_ozellikleri("ASUS PRIME B650M-R AMD B650M")
        self.assertEqual((oz["chipset"], oz["platform"], oz["soket"], oz["bellek"], oz["form"]),
                         ("B650", "AMD", "AM5", "DDR5", "mATX"))
        oz = c.anakart_ozellikleri("MSI PRO B760M-A D4 WIFI")
        self.assertEqual((oz["platform"], oz["soket"], oz["bellek"], oz["wifi"]), ("Intel", "LGA1700", "DDR4", True))
        oz = c.anakart_ozellikleri("ASUS ROG STRIX B650E-I GAMING WIFI")
        self.assertEqual((oz["chipset"], oz["form"]), ("B650E", "Mini-ITX"))
        oz = c.anakart_ozellikleri("ASUS TUF GAMING X870E-PLUS WIFI7 AMD X870")
        self.assertEqual(oz["chipset"], "X870E")
        oz = c.anakart_ozellikleri("ASUS ROG STRIX B860-F GAMING WIFI Intel B860 LGA 1851 ATX Anakart")
        self.assertEqual((oz["soket"], oz["bellek"], oz["form"]), ("LGA1851", "DDR5", "ATX"))
        self.assertFalse(c.anakart_ozellikleri("MSI MAG B850 TOMAHAWK MAX")["wifi"])

    def test_ram(self):
        oz = c.ram_ozellikleri("Corsair 32GB (2x16GB) Vengeance RGB 6000MHz CL30 DDR5 Ram")
        self.assertEqual((oz["kapasite_gb"], oz["kit"], oz["hiz_mhz"], oz["cl"], oz["tip"], oz["form"]),
                         (32, "2x16GB", 6000, 30, "DDR5", "DIMM"))
        self.assertEqual(c.ram_ozellikleri("Crucial 16GB DDR5 4800MHz SODIMM")["form"], "SODIMM")

    def test_birim_fiyat_ve_ozet(self):
        oz = c.ssd_ozellikleri("Samsung 990 EVO Plus 2TB NVMe M.2 SSD")
        birim, ad = c.birim_fiyat("ssd", 7000.0, oz)
        self.assertEqual((birim, ad), (3500.0, "TL/TB"))
        self.assertEqual(c.birim_fiyat("anakart", 7000.0, {}), (None, None))
        self.assertIn("2 TB", c.ozet_metni("ssd", oz))
        self.assertEqual(c.kategori_tahmin_et("MSI PRO B650M-P DDR5 AM5 mATX Anakart"), "anakart")
        self.assertEqual(c.kategori_tahmin_et("Kingston NV3 1TB NVMe M.2 SSD"), "ssd")


if __name__ == "__main__":
    unittest.main()
