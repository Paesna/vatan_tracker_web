"""
[TR] Kategori Kuralları ve Teknik Özellik Çıkarıcı / [EN] Category Rules and Spec Extractor
[TR] Ürün isminin hangi kategoriye (RAM / SSD / Anakart) ait olduğunu doğrular ve isimden kapasite,
     arayüz, soket, chipset, bellek tipi gibi özellikleri çıkarır. Siteler kategori sayfalarında vitrin,
     aksesuar ve pazar yeri çöpü (SSD kutusu, RAM soğutucu, laptop vb.) gösterdiğinden bu filtre şarttır.
[EN] Validates which category (RAM / SSD / Motherboard) a product name belongs to and extracts specs
     such as capacity, interface, socket, chipset and memory type from the name. Sites show promo blocks,
     accessories and marketplace junk (SSD enclosures, RAM coolers, laptops...) on category pages.

[TR] Tüm desenler normalize() edilmiş (küçük harf, Türkçe karakterleri ASCII'ye çevrilmiş) metin üzerinde çalışır.
[EN] All patterns run on normalize()d text (lower case, Turkish characters folded to ASCII).
"""

import re

KATEGORI_ADLARI = {"ram": "RAM", "ssd": "SSD", "anakart": "Anakart"}
KATEGORI_EMOJI = {"ram": "🧠", "ssd": "💾", "anakart": "🧩"}

_CEVIRI = str.maketrans({"ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "ı": "i",
                         "â": "a", "î": "i", "û": "u", "×": "x"})


def normalize(metin):
    """[TR] Karşılaştırma için metni sadeleştirir (İ/I/ı -> i, ş -> s ...). / [EN] Folds text for matching."""
    if not metin:
        return ""
    return str(metin).replace("İ", "i").replace("I", "i").lower().translate(_CEVIRI)


# --- ORTAK DIŞLAMALAR / COMMON EXCLUSIONS ---
# [TR] İkinci el / arızalı ürünler ve kategori sayfalarına sızan aksesuarlar.
# [EN] Used / broken items and accessories that leak into category listings.
_KULLANILMIS = re.compile(r"\b(arizali|hurda|ikinci el|2\.? ?el|yenilenmis|refurbished|parca icin)\b")
_AKSESUAR = re.compile(r"\b(kutusu|kutu|enclosure|adaptor|adapter|adaptoru|donusturucu|converter|kablo|kablosu|"
                       r"aparat|aparati|braket|bracket|kizak|kizagi|caddy|vida|vidasi|docking|dock)\b")
# [TR] Hazır sistem / laptop ilanları (isimde hem RAM hem SSD ya da işlemci modeli geçer).
# [EN] Pre-built PC / laptop listings (name mentions both RAM and SSD, or a CPU model).
_ISLEMCI = re.compile(r"\b(core ?i[3579]|i[3579][- ]\d{4,5}|ryzen ?[3579]|core ultra|celeron|pentium|athlon)\b")
_HAZIR_SISTEM = re.compile(r"\b(laptop|notebook bilgisayar|dizustu bilgisayar|masaustu bilgisayar|oyun bilgisayari|"
                           r"all in one|hazir sistem|mini pc|tablet|telefon)\b")

# --- RAM ---
# [TR] Eski filtrenin (ddr/ram) "bellek/memory/dimm" ile genişletilmiş hali. / [EN] Old ddr/ram rule, widened.
_RAM_DAHIL = re.compile(r"\b(ddr\d*|ram|bellek|memory|dimm|udimm|so-?dimm)\b")
# [TR] İsminde "RAM/DDR" geçmeyen kitler için: kapasite + hız birlikteyse RAM say (örn. "32GB (2x16) 6000MHz").
# [EN] For kits without "RAM/DDR" in the name: capacity + speed together means RAM (e.g. "32GB (2x16) 6000MHz").
_RAM_KAPASITE_HIZ = re.compile(r"\d+\s?gb\b.*\b\d{4,5}\s?(mhz|mt/s|mts)\b")
_RAM_HARIC = re.compile(r"\b(sogutucu|sogutucusu|ram fan|yuvasi|test karti|ekran karti|rtx|gtx|radeon|gddr\d|"
                        r"usb|flash|hafiza karti|sd kart|micro ?sd)\b|\brx ?\d{3,4}\b")
_RAM_NOTEBOOK = re.compile(r"\b(so-?dimm|notebook|laptop|dizustu)\b")

# --- SSD ---
_SSD_DAHIL = re.compile(r"\b(ssd|nvme)\b|solid state|kati hal|\bm\.?2\b")
# [TR] İsminde "SSD" yazmayan ama "SATA + kapasite" içeren SSD'ler için (HDD'ler hariç).
# [EN] For SSDs whose name lacks "SSD" but has "SATA + capacity" (HDDs excluded).
_SSD_SATA = re.compile(r"\bsata\b")
_HDD = re.compile(r"\bhdd\b|\brpm\b|\d{4} ?rpm")
# [TR] "Soğutucu" burada yok: SSD soğutucu aksesuarlarının isminde kapasite olmaz, kapasite şartı onları eler;
#      "990 PRO 2TB Soğutucu ile" gibi gerçek SSD'ler de kaybolmaz.
# [EN] No "cooler" here: SSD heatsink accessories carry no capacity and the capacity rule drops them,
#      while real SSDs named "990 PRO 2TB with heatsink" are kept.
_SSD_HARIC = re.compile(r"\b(harici|tasinabilir|portable|external|usb|sshd|thermal pad|termal ped)\b")
_KAPASITE = re.compile(r"(\d+(?:[.,]\d+)?)\s?(tb|gb)\b")

# --- ANAKART / MOTHERBOARD ---
_CHIPSET = re.compile(r"\b([abhqwxz])(\d{3})([es])?-?([mi])?\b")
_ANAKART_KELIME = re.compile(r"anakart|motherboard|mainboard")
_ANAKART_SOKET = re.compile(r"\b(am4|am5|lga ?1[0-9]{3})\b")
_ANAKART_FORM = re.compile(r"\b(e-?atx|atx|m-?atx|matx|micro[- ]?atx|mini[- ]?itx|itx)\b")
_ANAKART_HARIC = re.compile(r"\b(notebook|laptop|dizustu|paket|bundle|combo|io shield|i/o shield|arka panel|"
                            r"soket koruyucu)\b|islemci ?\+|\+ ?islemci|\bcpu ?\+")
# [TR] Soğutucu, pil, Wi-Fi kartı gibi aksesuarlar soket adı içerebilir ("AM5 Soğutucu") ama chipset içermez;
#      chipset'li gerçek anakart isminde de "M.2 Soğutucu", "Wi-Fi anten" gibi özellikler geçebilir.
#      Bu yüzden bu kelimeler sadece chipset yoksa eler.
# [EN] Accessories (coolers, batteries, Wi-Fi cards) may mention sockets ("AM5 cooler") but no chipset, while real
#      chipset-bearing board names may list features like "M.2 heatsink"; so these only exclude without a chipset.
_ANAKART_SOGUTUCU = re.compile(r"\b(sogutucu|sogutucusu|cooler|fan|montaj|pil|pili|batarya|test karti|post karti|"
                               r"anten|wifi karti)\b")

AMD_CHIPSETLER = {"a320", "b350", "x370", "b450", "x470", "a520", "b550", "x570",
                  "a620", "b650", "x670", "b840", "b850", "x870"}
INTEL_CHIPSETLER = {"h310", "b360", "b365", "h370", "z370", "z390", "q370",
                    "h410", "b460", "h470", "z490", "q470", "h510", "b560", "h570", "z590",
                    "h610", "b660", "h670", "z690", "q670", "w680", "b760", "h770", "z790", "w790",
                    "h810", "b860", "z890"}
_CHIPSET_SOKET = {
    **{c: "AM4" for c in ("a320", "b350", "x370", "b450", "x470", "a520", "b550", "x570")},
    **{c: "AM5" for c in ("a620", "b650", "x670", "b840", "b850", "x870")},
    **{c: "LGA1151" for c in ("h310", "b360", "b365", "h370", "z370", "z390", "q370")},
    **{c: "LGA1200" for c in ("h410", "b460", "h470", "z490", "q470", "h510", "b560", "h570", "z590")},
    **{c: "LGA1700" for c in ("h610", "b660", "h670", "z690", "q670", "w680", "b760", "h770", "z790")},
    **{c: "LGA1851" for c in ("h810", "b860", "z890")},
    "w790": "LGA4677",
}
_SOKET_DDR = {"AM5": "DDR5", "LGA1851": "DDR5", "AM4": "DDR4", "LGA1200": "DDR4", "LGA1151": "DDR4"}


def _chipset_bul(n):
    """[TR] İsimdeki ilk bilinen chipset'i döndürür: ('b650', 'm'). / [EN] First known chipset in name."""
    for m in _CHIPSET.finditer(n):
        cekirdek = m.group(1) + m.group(2)
        if cekirdek in AMD_CHIPSETLER or cekirdek in INTEL_CHIPSETLER:
            return cekirdek + (m.group(3) or ""), m.group(4) or ""
    return None, ""


def _kapasite_gb(n):
    """[TR] İsimdeki en büyük depolama kapasitesi (GB). 1 TB = 1000 GB. / [EN] Largest capacity in GB."""
    en_buyuk = None
    for deger, birim in _KAPASITE.findall(n):
        try:
            gb = float(deger.replace(",", "."))
        except ValueError:
            continue
        if birim == "tb":
            gb *= 1000
        if en_buyuk is None or gb > en_buyuk:
            en_buyuk = gb
    return int(en_buyuk) if en_buyuk else None


def _hazir_sistem_mi(n):
    """[TR] İsim laptop / hazır PC ilanına mı ait? / [EN] Does the name belong to a laptop / pre-built PC?"""
    if _HAZIR_SISTEM.search(n) or _ISLEMCI.search(n):
        return True
    # [TR] Hem RAM hem SSD kapasitesi geçiyorsa (örn. "16GB RAM 512GB SSD") bu bir bilgisayardır.
    # [EN] Both RAM and SSD capacities mentioned (e.g. "16GB RAM 512GB SSD") means a computer.
    return bool(re.search(r"\bram\b", n) and re.search(r"\bssd\b", n))


def kategoriye_uygun_mu(kategori, isim, ddr5_zorunlu=False, notebook_ram_haric=False):
    """
    [TR] Ürün ismi verilen kategorinin kurallarına uyuyor mu? / [EN] Does the product name fit the category?

    Args:
        kategori (str): "ram" | "ssd" | "anakart"
        isim (str): [TR] Ürün adı. / [EN] Product name.
        ddr5_zorunlu (bool): [TR] RAM için isimde DDR5 (ya da >= 4800 MHz) şartı. Site URL'si DDR5 filtresi
            içermeyen yeni siteler için kullanılır. / [EN] Require DDR5 for RAM (sites without a DDR5 URL filter).
        notebook_ram_haric (bool): [TR] SODIMM/notebook RAM'leri ele. / [EN] Drop SODIMM/notebook RAM.
    """
    n = normalize(isim)
    if not n or _KULLANILMIS.search(n):
        return False

    if kategori == "ram":
        if not (_RAM_DAHIL.search(n) or _RAM_KAPASITE_HIZ.search(n)):
            return False
        if _RAM_HARIC.search(n) or _AKSESUAR.search(n):
            return False
        if re.search(r"\bssd\b", n) or _ISLEMCI.search(n):
            return False
        # [TR] "DDR5" geçen anakart isimleri RAM sayılmasın. / [EN] Motherboard names mentioning "DDR5" are not RAM.
        if _ANAKART_KELIME.search(n) or _chipset_bul(n)[0]:
            return False
        if notebook_ram_haric and _RAM_NOTEBOOK.search(n):
            return False
        if ddr5_zorunlu:
            if "ddr4" in n or "ddr3" in n:
                return False
            if "ddr5" not in n:
                hiz = ram_ozellikleri(isim).get("hiz_mhz")
                return bool(hiz and hiz >= 4800)
        return True

    if kategori == "ssd":
        if _SSD_HARIC.search(n) or _AKSESUAR.search(n) or _HDD.search(n):
            return False
        if not (_SSD_DAHIL.search(n) or _SSD_SATA.search(n)):
            return False
        if _hazir_sistem_mi(n):
            return False
        # [TR] Gerçek SSD'lerin isminde kapasite olur; soğutucu/kızak gibi aksesuarlarda olmaz.
        # [EN] Real SSDs carry a capacity in their name; accessories don't.
        return _kapasite_gb(n) is not None

    if kategori == "anakart":
        if _ANAKART_HARIC.search(n) or _AKSESUAR.search(n) or _HAZIR_SISTEM.search(n) or _ISLEMCI.search(n):
            return False
        # [TR] Telefon/laptop anakartlarını elemek için masaüstü chipset'i, soket ya da form faktörü şart.
        # [EN] Require a desktop chipset, socket or form factor to drop phone/laptop boards.
        if _chipset_bul(n)[0]:
            return True
        if _ANAKART_SOGUTUCU.search(n):
            return False
        if _ANAKART_SOKET.search(n):
            return True
        return bool(_ANAKART_KELIME.search(n) and _ANAKART_FORM.search(n))

    return False


def ram_ozellikleri(isim):
    """[TR] RAM: toplam kapasite, hız, CL, tip, form. / [EN] RAM: total capacity, speed, CL, type, form."""
    n = normalize(isim)
    oz = {}
    kit = re.search(r"\b(\d)\s?x\s?(\d{1,3})\s?(gb)?\b", n)
    tekil = [int(x) for x in re.findall(r"\b(\d{1,3})\s?gb\b", n)]
    if kit and int(kit.group(1)) in (1, 2, 4, 8):
        oz["kapasite_gb"] = int(kit.group(1)) * int(kit.group(2))
        oz["kit"] = f"{kit.group(1)}x{kit.group(2)}GB"
    elif tekil:
        oz["kapasite_gb"] = max(tekil)
    hiz = re.search(r"\b(\d{4,5})\s?(mhz|mt/s|mts)\b", n) or re.search(r"\bddr[45][- ](\d{4,5})\b", n)
    if hiz:
        oz["hiz_mhz"] = int(hiz.group(1))
    cl = re.search(r"\bcl\s?(\d{2})\b", n)
    if cl:
        oz["cl"] = int(cl.group(1))
    tip = re.search(r"\bddr([345])\b", n)
    if tip:
        oz["tip"] = f"DDR{tip.group(1)}"
    oz["form"] = "SODIMM" if _RAM_NOTEBOOK.search(n) else "DIMM"
    return oz


def ssd_ozellikleri(isim):
    """[TR] SSD: kapasite, arayüz, PCIe nesli, form faktörü, okuma hızı. / [EN] SSD specs."""
    n = normalize(isim)
    oz = {}
    kapasite = _kapasite_gb(n)
    if kapasite:
        oz["kapasite_gb"] = kapasite
    if re.search(r"\bnvme\b|pcie|pci-e|pci express|\bgen ?[345]\b", n):
        oz["arayuz"] = "NVMe"
    elif re.search(r"\bsata\b|sata ?(iii|3)", n):
        oz["arayuz"] = "SATA"
    gen = re.search(r"(?:pcie|pci-e|pci express|\bgen)\s?([345])(?:\.0)?\b", n)
    if gen:
        oz["pcie_gen"] = f"Gen{gen.group(1)}"
    if re.search(r"\bm\.?2\b|\b22(80|42|30)\b", n):
        oz["form"] = "M.2"
    elif re.search(r"2[.,]5\s?(\"|''|inch|inc|in\b|”)", n):
        oz["form"] = '2.5"'
    okuma = (re.search(r"(?:okuma|read)(?: hizi)?\s*:?\s*(\d{3,5})\s?mb", n)
             or re.search(r"(\d{3,5})\s?mb(?:/s|ps)?\s*(?:okuma|read)", n)
             or re.search(r"\b(\d{3,5})\s?[-/]\s?\d{3,5}\s?mb", n))
    if okuma:
        oz["okuma_mbs"] = int(okuma.group(1))
    return oz


def anakart_ozellikleri(isim):
    """[TR] Anakart: platform, soket, chipset, bellek tipi, form faktörü, Wi-Fi. / [EN] Motherboard specs."""
    n = normalize(isim)
    oz = {}
    chipset, ek = _chipset_bul(n)
    if chipset:
        oz["chipset"] = chipset.upper()
        cekirdek = chipset[:4]
        oz["platform"] = "AMD" if cekirdek in AMD_CHIPSETLER else "Intel"
    soket = re.search(r"\bam([45])\b", n)
    if soket:
        oz["soket"] = f"AM{soket.group(1)}"
    else:
        lga = re.search(r"(?:lga|soket|socket)\s?-?(1851|1700|1200|1151|4677)\b", n) or \
              re.search(r"\b(1851|1700|1200|1151)\b(?!\s?(mhz|w\b|mt))", n)
        if lga:
            oz["soket"] = f"LGA{lga.group(1)}"
        elif chipset:
            oz["soket"] = _CHIPSET_SOKET.get(chipset[:4])
    if not oz.get("soket"):
        oz.pop("soket", None)
    if "platform" not in oz and oz.get("soket"):
        oz["platform"] = "AMD" if oz["soket"].startswith("AM") else "Intel"
    if re.search(r"ddr5|\bd5\b", n):
        oz["bellek"] = "DDR5"
    elif re.search(r"ddr4|\bd4\b", n):
        oz["bellek"] = "DDR4"
    elif oz.get("soket") in _SOKET_DDR:
        oz["bellek"] = _SOKET_DDR[oz["soket"]]
    if re.search(r"\be-?atx\b", n):
        oz["form"] = "E-ATX"
    elif re.search(r"mini[- ]?itx|\bitx\b", n) or ek == "i":
        oz["form"] = "Mini-ITX"
    elif re.search(r"\bm-?atx\b|micro[- ]?atx|\bmatx\b", n) or ek == "m":
        oz["form"] = "mATX"
    elif re.search(r"\batx\b", n):
        oz["form"] = "ATX"
    oz["wifi"] = bool(re.search(r"wi-?fi|\bwlan\b|\bax\b", n))
    return oz


def ozellikleri_cikar(kategori, isim):
    """[TR] Kategoriye göre özellik sözlüğü döndürür. / [EN] Returns the spec dict for the category."""
    if kategori == "ram":
        return ram_ozellikleri(isim)
    if kategori == "ssd":
        return ssd_ozellikleri(isim)
    if kategori == "anakart":
        return anakart_ozellikleri(isim)
    return {}


def birim_fiyat(kategori, fiyat, ozellikler):
    """
    [TR] Karşılaştırma için birim fiyat: SSD -> TL/TB, RAM -> TL/GB. Anakartta yoktur.
    [EN] Unit price for comparison: SSD -> TL/TB, RAM -> TL/GB. None for motherboards.
    """
    if not fiyat or not ozellikler:
        return None, None
    kapasite = ozellikler.get("kapasite_gb")
    if not kapasite:
        return None, None
    if kategori == "ssd":
        return fiyat / (kapasite / 1000.0), "TL/TB"
    if kategori == "ram":
        return fiyat / kapasite, "TL/GB"
    return None, None


def ozet_metni(kategori, ozellikler):
    """[TR] Bildirim ve kartlar için kısa özellik metni. / [EN] Short spec summary for alerts and cards."""
    if not ozellikler:
        return ""
    o = ozellikler
    parcalar = []
    if kategori == "ssd":
        if o.get("kapasite_gb"):
            gb = o["kapasite_gb"]
            parcalar.append(f"{gb / 1000:g} TB" if gb >= 1000 else f"{gb} GB")
        parcalar += [o.get("arayuz"), o.get("pcie_gen"), o.get("form")]
        if o.get("okuma_mbs"):
            parcalar.append(f"{o['okuma_mbs']} MB/s")
    elif kategori == "anakart":
        parcalar += [o.get("platform"), o.get("soket"), o.get("chipset"), o.get("bellek"), o.get("form")]
        if o.get("wifi"):
            parcalar.append("Wi-Fi")
    elif kategori == "ram":
        if o.get("kapasite_gb"):
            parcalar.append(f"{o['kapasite_gb']} GB" + (f" ({o['kit']})" if o.get("kit") else ""))
        parcalar += [o.get("tip")]
        if o.get("hiz_mhz"):
            parcalar.append(f"{o['hiz_mhz']} MHz")
        if o.get("cl"):
            parcalar.append(f"CL{o['cl']}")
        if o.get("form") == "SODIMM":
            parcalar.append("SODIMM")
    return " • ".join(p for p in parcalar if p)


def kategori_tahmin_et(isim):
    """
    [TR] Kategorisi bilinmeyen eski kayıtlar için isimden kategori tahmini (geçiş/migration için).
    [EN] Guesses a category from the name for legacy rows without one (used by the migration).
    """
    for kategori in ("ram", "ssd", "anakart"):
        if kategoriye_uygun_mu(kategori, isim):
            return kategori
    return "ram"
