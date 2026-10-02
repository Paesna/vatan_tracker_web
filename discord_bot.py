"""
[TR] Discord Webhook Entegrasyon Modülü / [EN] Discord Webhook Integration Module
[TR] Discord sunucularına Webhook üzerinden "Embed" formatında, resimli duyurular gönderir. / [EN] Sends "Embed" formatted, image-rich announcements to Discord servers via Webhook.
"""

import time

import requests

import config

# [TR] Discord webhook sınırı ~5 istek / 2 sn. / [EN] Discord webhook limit is ~5 requests / 2 s.
_MIN_ARALIK = 0.5
_son_gonderim = 0.0


def _tl(deger):
    try:
        return f"{float(deger):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"
    except (TypeError, ValueError):
        return f"{deger} TL"


def discord_mesaj_gonder(baslik, urun_adi, eski_fiyat, yeni_fiyat, stok_durumu, url, resim_url=None, renk=5814783,
                         kaynak="Vatan Bilgisayar", kategori=None, ozellikler=None):
    """
    [TR] Discord Webhook'una resimli bir "Embed" kartı gönderir. / [EN] Sends an image-rich "Embed" card to Discord Webhook.

    Args:
        baslik (str): [TR] Mesajın ana başlığı (Örn: "YENİ ÜRÜN" veya "BÜYÜK İNDİRİM")
        urun_adi (str): [TR] Ürünün adı
        eski_fiyat (float/str): [TR] Önceki fiyatı (Yoksa None)
        yeni_fiyat (float): [TR] Güncel fiyatı
        stok_durumu (str): [TR] "Var" veya "Yok"
        url (str): [TR] Ürün linki
        resim_url (str): [TR] Ürünün görsel linki
        renk (int): [TR] Embed kartının solundaki çizginin rengi (Ondalık kod. Yeşil=5814783, Kırmızı=15158332)
        kaynak (str): [TR] Ürünün çekildiği web sitesi adı (Vatan Bilgisayar, Sinerji vb.)
        kategori (str): [TR] "💾 SSD" gibi kategori etiketi / [EN] category label
        ozellikler (str): [TR] "1 TB • NVMe • Gen4" gibi özet / [EN] spec summary
    """
    global _son_gonderim
    webhook_url = config.DISCORD_WEBHOOK_URL
    if not webhook_url or webhook_url.startswith("your_") or not webhook_url.startswith("http"):
        # [TR] Eğer kullanıcı Webhook linki girmemişse (veya placeholder ise) işlemi sessizce atla. / [EN] Skip silently if no webhook url is provided (or it is a placeholder).
        return

    # [TR] Fiyat metnini oluştur / [EN] Create price text
    if eski_fiyat and eski_fiyat != yeni_fiyat:
        fiyat_metni = f"~~{_tl(eski_fiyat)}~~ ➡️ **{_tl(yeni_fiyat)}**"
    else:
        fiyat_metni = f"**{_tl(yeni_fiyat)}**"

    alanlar = [{"name": "Ürün / Product", "value": (urun_adi or "-")[:1024], "inline": False}]
    if kategori:
        alanlar.append({"name": "Kategori / Category", "value": kategori, "inline": True})
    alanlar += [
        {"name": "Kaynak / Source", "value": kaynak, "inline": True},
        {"name": "Fiyat / Price", "value": fiyat_metni, "inline": True},
        {"name": "Stok / Stock", "value": stok_durumu, "inline": True},
    ]
    if ozellikler:
        alanlar.append({"name": "Özellikler / Specs", "value": ozellikler[:1024], "inline": False})

    # [TR] Discord Embed Sözlüğü / [EN] Discord Embed Dictionary
    embed = {
        "title": baslik,
        "url": url,
        "color": renk,
        "fields": alanlar,
        "footer": {"text": f"{kaynak} • Donanım Fiyat Takip"},
    }

    # [TR] Resim varsa ekle / [EN] Add image if exists
    if resim_url and str(resim_url).startswith("http"):
        embed["thumbnail"] = {"url": resim_url}

    payload = {
        "embeds": [embed],
        # [TR] Linkin etrafına < > koyduk ki Discord kendi kendine sitenin reklamını (OpenGraph embed) oluşturmasın.
        "content": f"🛒 **Satın Al:** <{url}>"
    }

    for deneme in range(2):
        bekle = _son_gonderim + _MIN_ARALIK - time.monotonic()
        if bekle > 0:
            time.sleep(bekle)
        try:
            r = requests.post(webhook_url, json=payload, timeout=10)
            _son_gonderim = time.monotonic()
            if r.status_code == 429 and deneme == 0:
                # [TR] Hız sınırı: Discord'un söylediği kadar bekleyip bir kez daha dene. / [EN] Rate limited: retry once.
                time.sleep(float(r.json().get("retry_after", 2)))
                continue
            if r.status_code not in (200, 204):
                # [TR] Webhook adresini (gizli token içerir) loglara yazmıyoruz. / [EN] Never log the webhook URL (secret).
                print(f"❌ [TR] Discord HTTP {r.status_code}: {r.text[:300]}")
            r.raise_for_status()
            print("✅ [TR] Discord bildirimi gönderildi. / [EN] Discord notification sent.")
            return
        except Exception as e:
            print(f"❌ [TR] Discord bildirimi gönderilemedi / [EN] Failed to send Discord notification: {e}")
            return
