"""
[TR] Discord Webhook Entegrasyon Modülü / [EN] Discord Webhook Integration Module
[TR] Discord sunucularına Webhook üzerinden "Embed" formatında, resimli duyurular gönderir. / [EN] Sends "Embed" formatted, image-rich announcements to Discord servers via Webhook.
"""

import requests
import config

def discord_mesaj_gonder(baslik, urun_adi, eski_fiyat, yeni_fiyat, stok_durumu, url, resim_url=None, renk=5814783):
    """
    [TR] Discord Webhook'una resimli bir "Embed" kartı gönderir. / [EN] Sends an image-rich "Embed" card to Discord Webhook.
    
    Args:
        baslik (str): [TR] Mesajın ana başlığı (Örn: "YENİ ÜRÜN" veya "BÜYÜK İNDİRİM")
        urun_adi (str): [TR] Ürünün adı
        eski_fiyat (float/str): [TR] Önceki fiyatı (Yoksa None)
        yeni_fiyat (float): [TR] Güncel fiyatı
        stok_durumu (str): [TR] "Var" veya "Yok"
        url (str): [TR] Vatan Bilgisayar ürün linki
        resim_url (str): [TR] Ürünün görsel linki
        renk (int): [TR] Embed kartının solundaki çizginin rengi (Ondalık kod. Yeşil=5814783, Kırmızı=15158332)
    """
    webhook_url = config.DISCORD_WEBHOOK_URL
    if not webhook_url:
        # [TR] Eğer kullanıcı Webhook linki girmemişse işlemi sessizce atla. / [EN] Skip silently if no webhook url is provided.
        return

    # [TR] Fiyat metnini oluştur / [EN] Create price text
    if eski_fiyat and eski_fiyat != yeni_fiyat:
        fiyat_metni = f"~~{eski_fiyat} TL~~ ➡️ **{yeni_fiyat} TL**"
    else:
        fiyat_metni = f"**{yeni_fiyat} TL**"

    # [TR] Discord Embed Sözlüğü / [EN] Discord Embed Dictionary
    embed = {
        "title": baslik,
        "url": url,
        "color": renk,
        "fields": [
            {"name": "Ürün / Product", "value": urun_adi, "inline": False},
            {"name": "Fiyat / Price", "value": fiyat_metni, "inline": True},
            {"name": "Stok / Stock", "value": stok_durumu, "inline": True}
        ],
        "footer": {
            "text": "Vatan RAM Tracker Bot"
        }
    }

    # [TR] Resim varsa ekle / [EN] Add image if exists
    if resim_url:
        embed["thumbnail"] = {"url": resim_url}

    payload = {
        "embeds": [embed],
        # [TR] Linkin etrafına < > koyduk ki Discord kendi kendine Vatan'ın reklamını (OpenGraph embed) oluşturmasın.
        "content": f"🛒 **Satın Al:** <{url}>"
    }

    try:
        print(f"🔍 [DEBUG] Discord Webhook URL başlangıcı: {webhook_url[:50]}...")
        r = requests.post(webhook_url, json=payload, timeout=10)
        print(f"🔍 [DEBUG] Discord HTTP Status: {r.status_code}")
        if r.status_code != 204:
            print(f"🔍 [DEBUG] Discord Response Body: {r.text}")
        r.raise_for_status()
        print("✅ [TR] Discord bildirimi gönderildi. / [EN] Discord notification sent.")
    except Exception as e:
        print(f"❌ [TR] Discord bildirimi gönderilemedi / [EN] Failed to send Discord notification: {e}")
        import traceback
        traceback.print_exc()
