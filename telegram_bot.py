"""
[TR] Telegram Bot Entegrasyon Modülü / [EN] Telegram Bot Integration Module
[TR] Telegram Bot API'si aracılığıyla uyarılar ve satıniçi klavye butonları (linkler) gönderir. / [EN] Handles sending alerts and inline keyboard buttons (links) via Telegram Bot API.
"""

import requests
import sys
import config

# [TR] Windows konsolunda emoji çökmesini (UnicodeEncodeError) önlemek için UTF-8 ayarlama / [EN] Attempt to configure Windows console to UTF-8 to prevent emoji crash (UnicodeEncodeError)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


def telegram_mesaj_gonder(mesaj, buton_url=None):
    """
    [TR] Yapılandırılmış Telegram Sohbetine HTML formatında bir mesaj gönderir. / [EN] Sends an HTML formatted message to the configured Telegram Chat.
    
    Args:
        mesaj (str): [TR] HTML formatlı metin mesajı. / [EN] The HTML formatted text message.
        buton_url (str, optional): [TR] İsteğe bağlı bir URL. Verilirse, mesaja bir buton eklenir. / [EN] An optional URL. If provided, an inline button will be appended to the message.
    """
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": mesaj,
        "parse_mode": "HTML"
    }
    
    # [TR] Satıniçi Buton (Link) Ekleme / [EN] Add Inline Button (Link)
    if buton_url:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "🛒 Vatan'da İncele / Satın Al", "url": buton_url}]
            ]
        }
        
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print("✅ [TR] Telegram bildirimi gönderildi. / [EN] Telegram notification sent.")
    except Exception as e:
        print(f"❌ [TR] Telegram bildirimi gönderilemedi / [EN] Failed to send Telegram notification: {e}")

