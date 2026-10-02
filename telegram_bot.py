"""
[TR] Telegram Bot Entegrasyon Modülü / [EN] Telegram Bot Integration Module
[TR] Telegram Bot API'si aracılığıyla uyarılar ve satıniçi klavye butonları (linkler) gönderir. / [EN] Handles sending alerts and inline keyboard buttons (links) via Telegram Bot API.
"""

import sys
import time

import requests

import config

# [TR] Windows konsolunda emoji çökmesini (UnicodeEncodeError) önlemek için UTF-8 ayarlama / [EN] Attempt to configure Windows console to UTF-8 to prevent emoji crash (UnicodeEncodeError)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# [TR] Telegram aynı sohbete saniyede ~1 mesaj kabul eder. / [EN] Telegram accepts ~1 message/second per chat.
_MIN_ARALIK = 1.1
_son_gonderim = 0.0


def telegram_mesaj_gonder(mesaj, buton_url=None, buton_metni=None):
    """
    [TR] Yapılandırılmış Telegram Sohbetine HTML formatında bir mesaj gönderir. / [EN] Sends an HTML formatted message to the configured Telegram Chat.

    Args:
        mesaj (str): [TR] HTML formatlı metin mesajı. / [EN] The HTML formatted text message.
        buton_url (str, optional): [TR] İsteğe bağlı bir URL. Verilirse, mesaja bir buton eklenir. / [EN] An optional URL. If provided, an inline button will be appended to the message.
        buton_metni (str, optional): [TR] Buton yazısı (verilmezse siteden üretilir). / [EN] Button label (derived from the site if omitted).
    """
    global _son_gonderim
    # [TR] Token veya Chat ID ayarlanmamışsa (ya da placeholder ise) işlemi sessizce atla. / [EN] Skip silently if token or chat id is not configured (or is a placeholder).
    if (not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_ID
            or config.TELEGRAM_TOKEN.startswith("your_") or str(config.TELEGRAM_CHAT_ID).startswith("your_")):
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": mesaj,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    # [TR] Satıniçi Buton (Link) Ekleme / [EN] Add Inline Button (Link)
    if buton_url:
        if not buton_metni:
            site_name = config.site_adi(config.site_bul("", buton_url))
            buton_metni = f"🛒 {site_name}'de İncele / Satın Al"
        payload["reply_markup"] = {"inline_keyboard": [[{"text": buton_metni, "url": buton_url}]]}

    for deneme in range(2):
        bekle = _son_gonderim + _MIN_ARALIK - time.monotonic()
        if bekle > 0:
            time.sleep(bekle)
        try:
            r = requests.post(url, json=payload, timeout=10)
            _son_gonderim = time.monotonic()
            if r.status_code == 429 and deneme == 0:
                # [TR] Hız sınırı: Telegram'ın söylediği kadar bekleyip bir kez daha dene. / [EN] Rate limited: retry once.
                time.sleep(float(r.json().get("parameters", {}).get("retry_after", 3)))
                continue
            r.raise_for_status()
            print("✅ [TR] Telegram bildirimi gönderildi. / [EN] Telegram notification sent.")
            return
        except Exception as e:
            print(f"❌ [TR] Telegram bildirimi gönderilemedi / [EN] Failed to send Telegram notification: {e}")
            return
