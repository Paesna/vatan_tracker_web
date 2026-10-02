import os
from dotenv import load_dotenv

# [TR] .env dosyasını oku (eğer varsa) / [EN] Load .env file (if exists)
load_dotenv()

"""
[TR] Bulut (Cloud) Odaklı Ayarlar Modülü / [EN] Cloud-Focused Configuration Module
[TR] Render, Heroku gibi bulut sistemleri için "Environment Variables" (Çevre Değişkenleri) destekler. / [EN] Supports Environment Variables for cloud systems like Render, Heroku etc.
"""


def _env_float(isim, varsayilan):
    deger = os.getenv(isim, "").strip()
    try:
        return float(deger) if deger else float(varsayilan)
    except ValueError:
        return float(varsayilan)


def _env_int(isim, varsayilan):
    return int(_env_float(isim, varsayilan))


def _env_bool(isim, varsayilan=False):
    deger = os.getenv(isim, "").strip().lower()
    if not deger:
        return varsayilan
    return deger in ("1", "true", "evet", "yes", "on")


def _env_liste(isim):
    return [p.strip().lower() for p in os.getenv(isim, "").split(",") if p.strip()]


# --- BÜTÇE VE BİLDİRİM AYARLARI / BUDGET & ALERT SETTINGS ---
# [TR] HEDEF_FIYAT eski isimdir; BUTCE verilmezse onun değeri kullanılır.
# [EN] HEDEF_FIYAT is the legacy name; it is used when BUTCE is not set.
HEDEF_FIYAT = _env_float("HEDEF_FIYAT", 20000.0)
# [TR] Ürün başına üst fiyat (TL). Bunun üstündeki ürünler için bildirim gönderilmez, yeni ürün olarak eklenmez.
# [EN] Per-product price ceiling (TL). No alerts above it and such products are not added as new.
BUTCE = _env_float("BUTCE", HEDEF_FIYAT)
# [TR] Fiyata göre sıralı sitelerde taramanın bütçenin yüzde kaç üstüne kadar devam edeceği. Bütçenin hemen
#      üstüne çıkan ürünlerin fiyatını da görebilmek (ve yanlışlıkla "stok yok" dememek) için pay bırakılır.
# [EN] On price-sorted sites, how far (percent) above the budget the crawl continues, so products that just
#      crossed the budget keep being tracked instead of being reported as out of stock.
BUTCE_PAYI_YUZDE = _env_float("BUTCE_PAYI_YUZDE", 15.0)
INDIRIM_YUZDESI = _env_float("INDIRIM_YUZDESI", 15.0)
KONTROL_SIKLIGI_SANIYE = _env_int("KONTROL_SIKLIGI_SANIYE", 120)
# [TR] Pazar yerleri (Amazon, Hepsiburada, Trendyol, n11) ve Akakçe daha seyrek taranır (engel riski).
# [EN] Marketplaces (Amazon, Hepsiburada, Trendyol, n11) and Akakçe are scanned less often (ban risk).
PAZARYERI_SIKLIGI_SANIYE = _env_int("PAZARYERI_SIKLIGI_SANIYE", 600)
# [TR] Stokta olmayan bir ürün en az bu kadar dakika sonra tekrar stoğa girerse "STOĞA GİRDİ" bildirimi atılır (0 = kapalı).
# [EN] Send a "BACK IN STOCK" alert when a product returns after at least this many minutes (0 = disabled).
STOK_BILDIRIM_DAKIKA = _env_int("STOK_BILDIRIM_DAKIKA", 60)
NOTEBOOK_RAM_HARIC = _env_bool("NOTEBOOK_RAM_HARIC", False)

# --- KATEGORİLER / CATEGORIES ---
KATEGORILER = {
    "ram": {"ad": "RAM (DDR5)", "emoji": "🧠", "butce": _env_float("BUTCE_RAM", BUTCE)},
    "ssd": {"ad": "SSD", "emoji": "💾", "butce": _env_float("BUTCE_SSD", BUTCE)},
    "anakart": {"ad": "Anakart", "emoji": "🧩", "butce": _env_float("BUTCE_ANAKART", BUTCE)},
}
AKTIF_KATEGORILER = [k for k in (_env_liste("AKTIF_KATEGORILER") or list(KATEGORILER)) if k in KATEGORILER]


def kategori_butcesi(kategori):
    """[TR] Kategorinin bütçesi (TL). / [EN] Budget (TL) of the category."""
    return KATEGORILER.get(kategori, {}).get("butce", BUTCE)


def tarama_limiti(kategori):
    """[TR] Taramanın devam edeceği en yüksek fiyat (bütçe + pay). / [EN] Highest price the crawl covers."""
    return kategori_butcesi(kategori) * (1 + BUTCE_PAYI_YUZDE / 100.0)


# --- TELEGRAM AYARLARI / TELEGRAM SETTINGS ---
# [TR] Bulut sistemine yüklerken GitHub'da şifrenin görünmemesi için bunları sitenin (Render vb.) "Environment Variables" bölümüne yazacaksın.
# [TR] Eğer bulutta değilsen veya test ediyorsan, kendi token'ını doğrudan da yazabilirsin (ama GitHub'a yüklerken silmeyi unutma!).
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- DISCORD AYARLARI / DISCORD SETTINGS ---
# [TR] Discord sunucunda oluşturduğun Webhook URL'sini buraya gir. / [EN] Enter your Discord Webhook URL here.
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# --- VERİTABANI AYARLARI / DATABASE SETTINGS ---
DB_URL = os.getenv("DB_URL", "")

# [TR] DB_URL boş veya placeholder ("your_...") ise proje klasöründe yerel SQLite dosyasına düş.
# [EN] Fall back to a local SQLite file in the project folder if DB_URL is empty or a placeholder.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not DB_URL or DB_URL.startswith("your_"):
    DB_URL = "sqlite:///" + os.path.join(_BASE_DIR, "ram_tracker.db").replace("\\", "/")
elif DB_URL.startswith("postgres://"):
    # [TR] SQLAlchemy 2.0 "postgres://" şemasını kabul etmez; Supabase/Render bazen bu formatta verir.
    # [EN] SQLAlchemy 2.0 rejects the "postgres://" scheme; Supabase/Render sometimes provide it.
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

# --- PERFORMANS / PERFORMANCE ---
# [TR] Aynı anda yapılabilecek toplam HTTP isteği. 0 = otomatik (CPU çekirdeği x 4, 8..32 arası).
# [EN] Total concurrent HTTP requests. 0 = automatic (CPU cores x 4, clamped to 8..32).
MAX_ESZAMANLI_ISTEK = _env_int("MAX_ESZAMANLI_ISTEK", 0)
# [TR] Tek bir siteye aynı anda en fazla kaç istek atılacağı (siteleri yormamak ve ban yememek için düşük tutun).
# [EN] Max concurrent requests per site (keep it low to stay polite and avoid bans).
SITE_BASINA_ESZAMANLI = max(1, _env_int("SITE_BASINA_ESZAMANLI", 2))
# [TR] Aynı siteye art arda iki istek arasındaki en kısa süre (saniye, ±%30 rastgele sapma eklenir).
# [EN] Minimum gap between two requests to the same site (seconds, ±30% jitter is added).
SITE_ISTEK_ARALIGI_SANIYE = _env_float("SITE_ISTEK_ARALIGI_SANIYE", 0.75)
ISTEK_ZAMAN_ASIMI = _env_float("ISTEK_ZAMAN_ASIMI", 20)
ISTEK_TEKRAR = _env_int("ISTEK_TEKRAR", 2)
# [TR] HTML ayrıştırma için süreç (process) sayısı. -1 = otomatik (çekirdek - 1, en fazla 4), 0 = ana süreçte ayrıştır.
# [EN] Worker processes for HTML parsing. -1 = automatic (cores - 1, max 4), 0 = parse in the main process.
PARSE_ISCI_SAYISI = _env_int("PARSE_ISCI_SAYISI", -1)
# [TR] curl_cffi tarayıcı taklidi (TLS parmak izi). "chrome" = desteklenen en yeni Chrome.
# [EN] curl_cffi browser impersonation (TLS fingerprint). "chrome" = newest supported Chrome.
IMPERSONATE = os.getenv("IMPERSONATE", "chrome").strip() or "chrome"
MAX_SAYFA = _env_int("MAX_SAYFA", 15)
PAZARYERI_MAX_SAYFA = _env_int("PAZARYERI_MAX_SAYFA", 3)
# [TR] 403/429 (engel) alan site bu kadar saniye dinlendirilir; üst üste engelde süre ikiye katlanır (en fazla 2 saat).
# [EN] A site answering 403/429 (blocked) is paused this many seconds; doubles on repeated blocks (max 2 hours).
ENGEL_BEKLEME_SANIYE = _env_int("ENGEL_BEKLEME_SANIYE", 600)
# [TR] Ürünün "son görülme" zamanı en fazla bu sıklıkla DB'ye yazılır (gereksiz yazmayı önler).
# [EN] A product's "last seen" time is written to the DB at most this often (avoids needless writes).
SON_GORULME_GUNCELLEME_DAKIKA = _env_int("SON_GORULME_GUNCELLEME_DAKIKA", 30)
# [TR] Sadece ilk sayfaları taranan (pazar yeri) sitelerde, bu kadar saattir görünmeyen ürün stok dışı sayılır.
# [EN] On sites where only the first pages are scanned (marketplaces), products unseen this long count as out of stock.
ESKIME_SAAT = _env_float("ESKIME_SAAT", 6)

# --- WEB SCRAPING AYARLARI / WEB SCRAPING SETTINGS ---
URL_ALL = "https://www.vatanbilgisayar.com/pc-bilgisayar-bellek-ram/?opf=p26559%2F&srt=UP"
URL_STOCK = "https://www.vatanbilgisayar.com/pc-bilgisayar-bellek-ram/?opf=p26559%2F&srt=UP&stk=true"

TEBILON_COOKIE = os.getenv("TEBILON_COOKIE", "")
TEBILON_USER_AGENT = os.getenv("TEBILON_USER_AGENT", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# [TR] SİTE TANIMLARI / [EN] SITE DEFINITIONS
#   parser            : scraper.py içindeki ayrıştırıcı / parser name in scraper.py
#   kategoriler       : kategori -> liste URL'si (mümkünse fiyata göre artan sıralı) / category -> listing URL
#   sayfalama         : sayfa URL'si nasıl kurulur / how page URLs are built (bkz. crawler.sayfa_url)
#   fiyata_gore_sirali: True ise bütçe aşılınca sonraki sayfalara geçilmez / stop paging once over budget
#   pazaryeri         : seyrek tarama, sadece ilk sayfalar, yeni ürün bildirimi kapalı / marketplace mode
#   dogrulandi        : ayrıştırıcı canlı sitede test edildi mi / parser verified against the live site
#   urun_link_deseni  : genel ayrıştırıcı için ürün linki deseni (grup 1 = ürün kodu) / product link regex
#   ram_ddr5_zorunlu  : URL'de DDR5 filtresi yoksa isimde DDR5 aranır / require DDR5 when URL has no filter
SITES = {
    "vatan": {
        "ad": "Vatan Bilgisayar", "renk": "#27AE60", "parser": "vatan", "dogrulandi": True,
        # [TR] Eski kayıtlarla uyum için Vatan ürün kodlarına önek eklenmez. / [EN] No prefix (legacy codes).
        "kod_on_eki": "",
        # [TR] stk=true: sadece stoktakiler listelenir; listeden düşen ürün stok dışı sayılır (istek sayısı yarıya iner).
        # [EN] stk=true lists in-stock items only; items dropping off the list count as out of stock (half the requests).
        "kategoriler": {
            "ram": "https://www.vatanbilgisayar.com/pc-bilgisayar-bellek-ram/?opf=p26559%2F&srt=UP&stk=true",
            "ssd": "https://www.vatanbilgisayar.com/solid-state-disk/?srt=UP&stk=true",
            "anakart": "https://www.vatanbilgisayar.com/anakart/?srt=UP&stk=true",
        },
        "sayfalama": {"tip": "query", "param": "page"},
        "fiyata_gore_sirali": True,
    },
    "sinerji": {
        "ad": "Sinerji", "renk": "#2E86C1", "parser": "sinerji", "dogrulandi": True,
        "kategoriler": {
            "ram": "https://www.sinerji.gen.tr/bellek-ram-c-2010?fx=bellek-turu:6238&sx=PriceAsc",
            "ssd": "https://www.sinerji.gen.tr/ssd-disk-c-2147?sx=PriceAsc",
            "anakart": "https://www.sinerji.gen.tr/anakart-c-2009?sx=PriceAsc",
        },
        "sayfalama": {"tip": "query", "param": "px"},
        "fiyata_gore_sirali": True,
    },
    "incehesap": {
        "ad": "İncehesap", "renk": "#E67E22", "parser": "incehesap", "dogrulandi": True,
        "kategoriler": {
            "ram": "https://www.incehesap.com/ram-fiyatlari/ozellik-4918,6917/sirala-ucuz/",
            "ssd": "https://www.incehesap.com/ssd-harddisk-fiyatlari/sirala-ucuz/",
            "anakart": "https://www.incehesap.com/anakart-fiyatlari/sirala-ucuz/",
        },
        "sayfalama": {"tip": "yol", "kalip": "sayfa-{n}/"},
        "fiyata_gore_sirali": True,
    },
    "tebilon": {
        "ad": "Tebilon", "renk": "#9B59B6", "parser": "tebilon", "dogrulandi": True,
        "kategoriler": {
            "ram": "https://www.tebilon.com/bilgisayar-parcalari/ram/ddr5-ram/?o=far",
            "ssd": "https://www.tebilon.com/bilgisayar-parcalari/ssd/?o=far",
            "anakart": "https://www.tebilon.com/bilgisayar-parcalari/anakart/?o=far",
        },
        "sayfalama": {"tip": "query", "param": "page"},
        "fiyata_gore_sirali": True,
    },
    "itopya": {
        "ad": "İtopya", "renk": "#C0392B", "parser": "itopya", "dogrulandi": True,
        "kategoriler": {
            "ram": "https://www.itopya.com/rambellek_k10?or=edf&ramtipi=ddr5-q5795",
            "ssd": "https://www.itopya.com/ssd_k20?or=edf",
            "anakart": "https://www.itopya.com/anakart_k9?or=edf",
        },
        # [TR] Sitenin "Daha Fazla Ürün Göster" butonunun kullandığı AJAX parçası (isFR=false&pg=N).
        # [EN] The AJAX fragment used by the site's "load more" button (isFR=false&pg=N).
        "sayfalama": {"tip": "query", "param": "pg", "ek": {"isFR": "false"}},
        "fiyata_gore_sirali": True,
    },
    "gaming": {
        "ad": "Gaming.gen.tr", "renk": "#E74C3C", "parser": "woocommerce", "dogrulandi": False,
        "kategoriler": {
            "ram": "https://www.gaming.gen.tr/kategori/bilgisayar-bilesenleri/ram-bellek/?orderby=price",
            "ssd": "https://www.gaming.gen.tr/kategori/bilgisayar-bilesenleri/ssd/?orderby=price",
            "anakart": "https://www.gaming.gen.tr/kategori/bilgisayar-bilesenleri/anakart/?orderby=price",
        },
        "sayfalama": {"tip": "wordpress"},
        "fiyata_gore_sirali": True,
        "urun_link_deseni": r"/urun/(\d+)/",
        "ram_ddr5_zorunlu": True,
    },
    "gamegaraj": {
        "ad": "GameGaraj", "renk": "#F39C12", "parser": "genel", "dogrulandi": False,
        "kategoriler": {
            "ram": "https://www.gamegaraj.com/bilgisayar-parcalari/ram-bellek/?sort=price_asc",
            "ssd": "https://www.gamegaraj.com/bilgisayar-parcalari/ssd/?sort=price_asc",
            "anakart": "https://www.gamegaraj.com/bilgisayar-parcalari/anakart/?sort=price_asc",
        },
        "sayfalama": {"tip": "query", "param": "page"},
        "fiyata_gore_sirali": True,
        # [TR] Ürün linkleri kategoriyle aynı klasörde; uzun slug ile ayırt edilir. / [EN] Long slug = product.
        "urun_link_deseni": r"/bilgisayar-parcalari/([a-z0-9][a-z0-9-]{24,})/?(?:[?#]|$)",
        "ram_ddr5_zorunlu": True,
    },
    "teknosa": {
        "ad": "Teknosa", "renk": "#0F4C9A", "parser": "genel", "dogrulandi": False,
        "kategoriler": {
            "ssd": "https://www.teknosa.com/ssd-c-116001008",
            "anakart": "https://www.teknosa.com/anakart-c-116001002",
        },
        # [TR] SAP Hybris altyapısı: sayfa numarası 0'dan başlar. / [EN] SAP Hybris: page index starts at 0.
        "sayfalama": {"tip": "query", "param": "page", "baslangic": 0},
        "fiyata_gore_sirali": False,
        "max_sayfa": 5,
        "urun_link_deseni": r"-p-(\d{6,})(?:[/?#]|$)",
    },
    "mediamarkt": {
        "ad": "MediaMarkt", "renk": "#DF0000", "parser": "genel", "dogrulandi": False,
        "kategoriler": {
            "ssd": "https://www.mediamarkt.com.tr/tr/category/solid-state-disk-drive-ssd-798099.html",
            "anakart": "https://www.mediamarkt.com.tr/tr/category/anakart-798063.html",
        },
        "sayfalama": {"tip": "query", "param": "page"},
        "fiyata_gore_sirali": False,
        "max_sayfa": 5,
        "urun_link_deseni": r"/product/[^\"'?#]*?-(\d{5,})\.html",
    },
    "amazon": {
        "ad": "Amazon.com.tr", "renk": "#FF9900", "parser": "amazon", "dogrulandi": False, "pazaryeri": True,
        "kategoriler": {
            "ram": "https://www.amazon.com.tr/s?k=ddr5&rh=n%3A12601944031",
            "ssd": "https://www.amazon.com.tr/s?rh=n%3A12601984031",
            "anakart": "https://www.amazon.com.tr/s?rh=n%3A12601941031",
        },
        "sayfalama": {"tip": "query", "param": "page"},
        "fiyata_gore_sirali": False,
        "urun_link_deseni": r"/dp/([A-Z0-9]{10})",
        "ram_ddr5_zorunlu": True,
        "istek_araligi": 2.5,
    },
    "hepsiburada": {
        "ad": "Hepsiburada", "renk": "#FF6000", "parser": "genel", "dogrulandi": False, "pazaryeri": True,
        "kategoriler": {
            "ram": "https://www.hepsiburada.com/bellek-ramler-c-47?filtreler=kullanimtipi%3ADDR5",
            "ssd": "https://www.hepsiburada.com/ssd-solid-state-drive-c-114814",
            "anakart": "https://www.hepsiburada.com/anakartlar-c-152",
        },
        "sayfalama": {"tip": "query", "param": "sayfa"},
        "fiyata_gore_sirali": False,
        "urun_link_deseni": r"-pm?-([A-Za-z0-9]{8,})(?:[/?#\"']|$)",
        "ram_ddr5_zorunlu": True,
        "istek_araligi": 2.0,
    },
    "trendyol": {
        "ad": "Trendyol", "renk": "#F27A1A", "parser": "trendyol", "dogrulandi": False, "pazaryeri": True,
        "kategoriler": {
            "ram": "https://www.trendyol.com/ddr5-ram-x-c108545-a306-v3094",
            "ssd": "https://www.trendyol.com/ssd-harddisk-x-c103784",
            "anakart": "https://www.trendyol.com/anakart-x-c108540",
        },
        "sayfalama": {"tip": "query", "param": "pi"},
        "fiyata_gore_sirali": False,
        "urun_link_deseni": r"-p-(\d{5,})",
        "ram_ddr5_zorunlu": True,
        "istek_araligi": 2.0,
    },
    "n11": {
        "ad": "n11", "renk": "#7B2D8E", "parser": "genel", "dogrulandi": False, "pazaryeri": True,
        "kategoriler": {
            "ssd": "https://www.n11.com/bilgisayar/bilgisayar-bilesenleri/hard-disk?q=ssd",
            "anakart": "https://www.n11.com/bilgisayar/bilgisayar-bilesenleri/anakart",
        },
        "sayfalama": {"tip": "query", "param": "pg"},
        "fiyata_gore_sirali": False,
        "urun_link_deseni": r"/urun/[^\"'?#]*?-(\d{5,})(?:[/?#\"']|$)",
        "istek_araligi": 2.0,
    },
    "akakce": {
        "ad": "Akakçe (en ucuz satıcı)", "renk": "#1E8449", "parser": "akakce", "dogrulandi": False, "pazaryeri": True,
        "kategoriler": {
            "ram": "https://www.akakce.com/ram/ddr5.html",
            "ssd": "https://www.akakce.com/ssd.html",
            "anakart": "https://www.akakce.com/anakart.html",
        },
        "sayfalama": {"tip": "akakce"},
        "fiyata_gore_sirali": False,
        "urun_link_deseni": r"en-ucuz-[^,\"']+,(\d+)\.html",
        "istek_araligi": 3.0,
    },
}

# [TR] .env üzerinden site seçimi: SADECE_SITELER=vatan,itopya veya DEVRE_DISI_SITELER=amazon,akakce
# [EN] Site selection via .env: SADECE_SITELER=vatan,itopya or DEVRE_DISI_SITELER=amazon,akakce
_SADECE = set(_env_liste("SADECE_SITELER"))
_KAPALI = set(_env_liste("DEVRE_DISI_SITELER"))
for _ad, _site in SITES.items():
    _site.setdefault("kod_on_eki", f"{_ad}-")
    _site.setdefault("pazaryeri", False)
    _site.setdefault("yeni_urun_bildirimi", not _site["pazaryeri"])
    _site.setdefault("ram_ddr5_zorunlu", False)
    _site.setdefault("max_sayfa", PAZARYERI_MAX_SAYFA if _site["pazaryeri"] else MAX_SAYFA)
    _site.setdefault("aralik", PAZARYERI_SIKLIGI_SANIYE if _site["pazaryeri"] else KONTROL_SIKLIGI_SANIYE)
    _site["enabled"] = (not _SADECE or _ad in _SADECE) and _ad not in _KAPALI


def site_adi(site):
    """[TR] Sitenin görünen adı. / [EN] Display name of a site."""
    return SITES.get(site, {}).get("ad", site.capitalize() if site else "?")


def site_bul(kod, url=""):
    """
    [TR] Ürün kodunun önekinden, yoksa URL'nin alan adından site anahtarını bulur (önek yoksa Vatan).
    [EN] Finds the site key from the product code prefix, else from the URL domain (no prefix = Vatan).
    """
    kod = str(kod or "")
    for ad, site in SITES.items():
        on_ek = site["kod_on_eki"]
        if on_ek and kod.startswith(on_ek):
            return ad
    for ad, site in SITES.items():
        for liste_url in site["kategoriler"].values():
            alan = liste_url.split("/")[2].replace("www.", "")
            if url and alan in url:
                return ad
    return "vatan"


# [TR] Eski betiklerle uyumluluk için (main.py artık SITES kullanır). / [EN] Legacy compatibility (main.py uses SITES).
SOURCES = {
    ad: {
        "enabled": site["enabled"] and "ram" in site["kategoriler"],
        "all_url": URL_ALL if ad == "vatan" else site["kategoriler"].get("ram"),
        "stock_url": URL_STOCK if ad == "vatan" else None,
    }
    for ad, site in SITES.items() if "ram" in site["kategoriler"]
}
