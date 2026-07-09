import os
from dotenv import load_dotenv

# [TR] .env dosyasını oku (eğer varsa) / [EN] Load .env file (if exists)
load_dotenv()

"""
[TR] Bulut (Cloud) Odaklı Ayarlar Modülü / [EN] Cloud-Focused Configuration Module
[TR] Render, Heroku gibi bulut sistemleri için "Environment Variables" (Çevre Değişkenleri) destekler. / [EN] Supports Environment Variables for cloud systems like Render, Heroku etc.
"""

# --- AYARLAR / SETTINGS ---
HEDEF_FIYAT = float(os.getenv("HEDEF_FIYAT", 20000.0))
INDIRIM_YUZDESI = float(os.getenv("INDIRIM_YUZDESI", 15.0))
KONTROL_SIKLIGI_SANIYE = int(os.getenv("KONTROL_SIKLIGI_SANIYE", 120))

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

# --- WEB SCRAPING AYARLARI / WEB SCRAPING SETTINGS ---
URL_ALL = "https://www.vatanbilgisayar.com/pc-bilgisayar-bellek-ram/?opf=p26559%2F&srt=UP"
URL_STOCK = "https://www.vatanbilgisayar.com/pc-bilgisayar-bellek-ram/?opf=p26559%2F&srt=UP&stk=true"

TEBILON_COOKIE = os.getenv("TEBILON_COOKIE", "")
TEBILON_USER_AGENT = os.getenv("TEBILON_USER_AGENT", "")

SOURCES = {
    "vatan": {
        "enabled": True,
        "all_url": "https://www.vatanbilgisayar.com/pc-bilgisayar-bellek-ram/?opf=p26559%2F&srt=UP",
        "stock_url": "https://www.vatanbilgisayar.com/pc-bilgisayar-bellek-ram/?opf=p26559%2F&srt=UP&stk=true",
    },
    "sinerji": {
        "enabled": True,
        "all_url": "https://www.sinerji.gen.tr/bellek-ram-c-2010?fx=bellek-turu:6238&sx=PriceAsc",
        "stock_url": None,
    },
    "incehesap": {
        "enabled": True,
        "all_url": "https://www.incehesap.com/ram-fiyatlari/ozellik-4918/sirala-ucuz/",
        "stock_url": None,
    },
    "tebilon": {
        "enabled": True,
        "all_url": "https://www.tebilon.com/bilgisayar-parcalari/ram/ddr5-ram/?o=far",
        "stock_url": None,
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

