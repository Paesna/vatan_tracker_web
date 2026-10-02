"""
[TR] Ana Düzenleyici Modülü / [EN] Main Orchestrator Module
[TR] Crawler, veritabanı ve bildirim botlarını birbirine bağlar. Her turda vadesi gelen (site x kategori)
     hedeflerini aynı anda tarar, sonuçları tek seferde işler/yazar ve koşullar sağlanırsa Telegram/Discord
     bildirimi gönderir. / [EN] Ties the crawler, database and notification bots together. Every round it crawls
     the due (site x category) targets concurrently, processes/writes results in one go and sends alerts.

Kullanım / Usage:
    python main.py                       # [TR] sürekli çalış / [EN] run forever
    python main.py --tek-sefer           # [TR] tek tur tara ve çık / [EN] one round then exit
    python main.py --site vatan,itopya --kategori ssd --bildirim-yok
"""

import argparse
import asyncio
import datetime
import html
import json
import sys
import time
import traceback
from collections import Counter

import categories
import config
import crawler
import scraper
from database import init_db, durum_yukle, toplu_yaz, get_tr_time
from telegram_bot import telegram_mesaj_gonder
from discord_bot import discord_mesaj_gonder

# [TR] Windows konsolu Türkçe karakter sorunu için / [EN] Attempt to configure Windows console to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# [TR] Bir turda gönderilecek en fazla bildirim; fazlası tek özet mesajda toplanır (bildirim seli olmasın).
# [EN] Max alerts per round; the rest are summarised in a single message (prevents alert floods).
MAX_BILDIRIM_TUR = 20


def log(mesaj):
    print(f"[{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}] {mesaj}", flush=True)


def tl(deger):
    """[TR] 12499.5 -> '12.499,50 TL' / [EN] Turkish money format."""
    if deger is None:
        return "-"
    return f"{deger:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


def global_kod(site, kod):
    """[TR] Siteye özgü ürün kodunu DB'deki benzersiz koda çevirir. / [EN] Site-local code -> unique DB code."""
    return f"{config.SITES[site]['kod_on_eki']}{kod}"


def _hedef_durumu(s, simdi):
    return {
        "key": s.anahtar, "site": s.site, "category": s.kategori, "last_run": simdi,
        "last_ok": simdi if s.basarili else None, "ok": int(s.basarili), "blocked": int(s.engellendi),
        "product_count": len(s.urunler), "pages": s.sayfa, "requests": s.istek, "duration": round(s.sure, 2),
        "stop_reason": s.durma_nedeni or None, "error": (s.hata or None) and s.hata[:500],
    }


def sonuclari_isle(sonuclar, durum, simdi=None):
    """
    [TR] Tarama sonuçlarını mevcut durumla karşılaştırır; DB'ye yazılacakları ve bildirimleri üretir.
         Ağ ve DB erişimi yapmaz (test edilebilir). `durum` sözlüğü yerinde güncellenir.
    [EN] Compares crawl results with the current state; produces DB writes and alerts.
         No network/DB access (testable). The `durum` dict is updated in place.

    Returns:
        dict: yeni_urunler, guncellemeler, gecmis, bildirimler, hedef_durumlari, sayac
    """
    simdi = simdi or get_tr_time()
    yeni_urunler, guncellemeler, gecmis, bildirimler = [], {}, [], []
    hedef_durumlari = [_hedef_durumu(s, simdi) for s in sonuclar if not (s.engellendi and s.istek == 0)]
    sayac = Counter()
    # [TR] Daha önce hiç ürünü olmayan site x kategori ilk kez taranıyorsa yeni ürün bildirimi atılmaz (baseline).
    # [EN] A site x category with no products yet is being baselined: no "new product" alerts.
    bilinen_hedefler = {(d.get("site"), d.get("category")) for d in durum.values()}
    gorulme_esigi = datetime.timedelta(minutes=config.SON_GORULME_GUNCELLEME_DAKIKA)
    stok_esigi = datetime.timedelta(minutes=config.STOK_BILDIRIM_DAKIKA)
    gorulen_kodlar = set()

    def guncelle(kod, **alanlar):
        guncellemeler.setdefault(kod, {}).update(alanlar)
        durum[kod].update(alanlar)

    def bildirim(tur, kod, st, **ek):
        bildirimler.append({"tur": tur, "kod": kod, "isim": st["name"], "site": st["site"],
                            "kategori": st["category"], "url": st["url"], "resim": st.get("image_url") or "",
                            "ozellikler": st.get("_ozellikler") or {}, **ek})

    # --- 1. TUR: GÖRÜLEN ÜRÜNLER / PASS 1: SEEN PRODUCTS ---
    for s in sonuclar:
        if not s.basarili:
            continue
        site_ayar = config.SITES[s.site]
        butce = config.kategori_butcesi(s.kategori)
        limit = config.tarama_limiti(s.kategori)
        baseline = (s.site, s.kategori) not in bilinen_hedefler
        if baseline:
            sayac["baseline_hedef"] += 1
        for yerel_kod, veri in s.urunler.items():
            kod = global_kod(s.site, yerel_kod)
            if kod in gorulen_kodlar:
                continue
            fiyat = float(veri["fiyat"])
            stok = 1 if veri.get("in_stock", True) else 0
            isim = veri.get("isim") or ""
            url = veri.get("url") or ""
            resim = veri.get("image_url") or ""
            st = durum.get(kod)

            # [TR] YENİ ÜRÜN (Veritabanında Yok) / [EN] NEW PRODUCT (Not in DB)
            if st is None:
                if fiyat > limit:
                    sayac["butce_disi"] += 1
                    continue
                gorulen_kodlar.add(kod)
                oz = categories.ozellikleri_cikar(s.kategori, isim)
                satir = {"code": kod, "name": isim, "url": url, "image_url": resim, "base_price": fiyat,
                         "first_seen": simdi, "site": s.site, "category": s.kategori,
                         "specs": json.dumps(oz, ensure_ascii=False), "last_price": fiyat, "in_stock": stok,
                         "last_seen": simdi, "last_change": simdi}
                yeni_urunler.append(satir)
                durum[kod] = {**satir, "_ozellikler": oz}
                gecmis.append({"code": kod, "price": fiyat, "in_stock": stok, "timestamp": simdi})
                sayac["yeni"] += 1
                if not baseline and site_ayar["yeni_urun_bildirimi"] and stok and fiyat <= butce:
                    bildirim("yeni", kod, durum[kod], fiyat=fiyat, stok=stok)
                continue

            # [TR] ZATEN BİLİNEN BİR ÜRÜN / [EN] ALREADY KNOWN PRODUCT
            gorulen_kodlar.add(kod)
            alanlar = {}
            if resim and not st.get("image_url"):
                alanlar["image_url"] = resim
            if url and url != st.get("url"):
                alanlar["url"] = url
            if isim and isim != st.get("name"):
                alanlar["name"] = isim
                alanlar["specs"] = json.dumps(categories.ozellikleri_cikar(st.get("category") or s.kategori, isim),
                                              ensure_ascii=False)

            base_price = st.get("base_price") or fiyat
            eski_fiyat = st["last_price"] if st.get("last_price") is not None else base_price
            eski_stok = st.get("in_stock")
            if eski_stok is None:
                eski_stok = stok
            # [TR] Sadece fiyat veya stok değiştiyse geçmişe yeni satır ekle / [EN] History row only on change
            if fiyat != eski_fiyat or stok != eski_stok:
                gecmis.append({"code": kod, "price": fiyat, "in_stock": stok, "timestamp": simdi})
                alanlar.update(last_price=fiyat, in_stock=stok, last_change=simdi)
                sayac["degisim"] += 1

            tur, ek = None, {}
            if eski_stok == 0 and stok == 1 and config.STOK_BILDIRIM_DAKIKA > 0 and fiyat <= butce:
                kapali = simdi - (st.get("last_change") or simdi)
                if kapali >= stok_esigi:
                    tur, ek = "stok", {"kapali_saat": kapali.total_seconds() / 3600}
                sayac["stoga_girdi"] += 1

            # [TR] FİYAT DÜŞÜŞÜ VEYA ARTIŞI KONTROLÜ (Base Fiyatına Göre) / [EN] PRICE DROP OR INCREASE CHECK (Based on Base Price)
            if fiyat < base_price:
                indirim_orani = ((base_price - fiyat) / base_price) * 100
                if indirim_orani >= config.INDIRIM_YUZDESI and fiyat <= butce:
                    tur, ek = "indirim", {"eski_fiyat": base_price, "oran": indirim_orani}
                    alanlar["base_price"] = fiyat
                    sayac["buyuk_dusus"] += 1
                    print(f"🔥 BÜYÜK DÜŞÜŞ / BIG DROP: [{s.site}/{s.kategori}] {isim} | {tl(base_price)} -> {tl(fiyat)} (%{indirim_orani:.1f})")
                elif fiyat != eski_fiyat:
                    sayac["kucuk_dusus"] += 1
            elif fiyat > base_price:
                if fiyat != eski_fiyat:
                    sayac["artis"] += 1
                alanlar["base_price"] = fiyat

            son_gorulme = st.get("last_seen")
            if alanlar or son_gorulme is None or simdi - son_gorulme >= gorulme_esigi:
                alanlar["last_seen"] = simdi
            if alanlar:
                guncelle(kod, **alanlar)
            if tur:
                st.setdefault("_ozellikler", categories.ozellikleri_cikar(st.get("category") or s.kategori, st["name"]))
                bildirim(tur, kod, st, fiyat=fiyat, stok=stok, **ek)

    # --- 2. TUR: LİSTEDEN DÜŞENLER -> STOK DIŞI / PASS 2: MISSING PRODUCTS -> OUT OF STOCK ---
    eskime = datetime.timedelta(hours=config.ESKIME_SAAT)
    hedef_index = {}
    for kod, st in durum.items():
        hedef_index.setdefault((st.get("site"), st.get("category")), []).append(kod)
    for s in sonuclar:
        # [TR] Taranamayan (hata/engel/0 ürün) hedefte yanlış alarm vermemek için dokunma.
        # [EN] Skip targets that failed this round (error/block/0 products) to avoid false alarms.
        if not s.basarili:
            continue
        for kod in hedef_index.get((s.site, s.kategori), []):
            st = durum[kod]
            if kod in gorulen_kodlar or st.get("in_stock") != 1:
                continue
            son_fiyat = st.get("last_price") or st.get("base_price") or 0
            if s.tam:
                # [TR] Liste kapsam fiyatına kadar eksiksiz tarandı; bu fiyatın altındaki ürün görünmüyorsa stokta yok.
                # [EN] Listing fully crawled up to the coverage price; a cheaper product that is missing is out of stock.
                if s.kapsam is not None and son_fiyat >= s.kapsam:
                    continue
            else:
                # [TR] Sadece ilk sayfalar tarandı (pazar yeri): uzun süredir görünmeyenleri stok dışı say.
                # [EN] Only the first pages were crawled (marketplace): treat long-unseen items as out of stock.
                son_gorulme = st.get("last_seen")
                if son_gorulme is None or simdi - son_gorulme < eskime:
                    continue
            gecmis.append({"code": kod, "price": son_fiyat, "in_stock": 0, "timestamp": simdi})
            guncelle(kod, in_stock=0, last_change=simdi)
            sayac["stok_disi"] += 1

    return {"yeni_urunler": yeni_urunler, "guncellemeler": guncellemeler, "gecmis": gecmis,
            "bildirimler": bildirimler, "hedef_durumlari": hedef_durumlari, "sayac": sayac}


def isle_ve_yaz(sonuclar, ozet):
    """[TR] Durumu yükler, sonuçları işler ve tek işlemde yazar. / [EN] Load state, process, write atomically."""
    t0 = time.monotonic()
    simdi = get_tr_time()
    durum = durum_yukle()
    islem = sonuclari_isle(sonuclar, durum, simdi)
    degisiklik = len(islem["yeni_urunler"]) + len(islem["gecmis"])
    toplu_yaz(islem["yeni_urunler"], islem["guncellemeler"], islem["gecmis"], islem["hedef_durumlari"],
              son_tarama=simdi)
    db_suresi = time.monotonic() - t0
    # [TR] İstatistik satırı, ölçülen DB süresini de içersin diye ayrı (küçük) bir işlemde yazılır.
    # [EN] The stats row is written in a separate tiny transaction so it can include the measured DB time.
    toplu_yaz(istatistik={
        "timestamp": simdi, "duration": round(ozet["sure"], 2), "targets": ozet["hedef"],
        "ok_targets": ozet["basarili"], "blocked": ozet["engel"], "requests": ozet["istek"], "pages": ozet["sayfa"],
        "products": ozet["urun"], "bytes": ozet["bayt"], "pages_per_sec": round(ozet["sayfa_sn"], 3),
        "products_per_sec": round(ozet["urun_sn"], 2), "avg_latency": round(ozet["ort_gecikme"], 3),
        "parse_seconds": round(ozet["ayristirma"], 2), "db_seconds": round(db_suresi, 3), "changes": degisiklik,
        "alerts": len(islem["bildirimler"]),
    })
    return islem, db_suresi


# =====================================================================================
# [TR] BİLDİRİMLER / [EN] NOTIFICATIONS
# =====================================================================================

def _bildirim_metinleri(b):
    kategori = b["kategori"]
    kaynak = config.site_adi(b["site"])
    kat_ad = f"{categories.KATEGORI_EMOJI.get(kategori, '')} {config.KATEGORILER.get(kategori, {}).get('ad', kategori)}".strip()
    ozet = categories.ozet_metni(kategori, b["ozellikler"])
    birim, birim_ad = categories.birim_fiyat(kategori, b["fiyat"], b["ozellikler"])
    fiyat_metni = tl(b["fiyat"]) + (f" ({tl(birim).replace(' TL', '')} {birim_ad})" if birim else "")
    stok = "Var" if b.get("stok", 1) else "Yok"
    isim = html.escape(b["isim"] or "")
    if b["tur"] == "indirim":
        baslik = f"🔥 BÜYÜK İNDİRİM! (%{b['oran']:.1f})"
        ust = f"🔥 <b>BÜYÜK İNDİRİM! / BIG DISCOUNT! (%{b['oran']:.1f})</b>"
        fiyat_satiri = (f"<b>Eski Base Fiyat / Old Base Price:</b> <s>{tl(b['eski_fiyat'])}</s>\n"
                        f"<b>Yeni Fiyat / New Price:</b> {fiyat_metni}")
        renk = 15158332
    elif b["tur"] == "stok":
        baslik = "📦 STOĞA GİRDİ!"
        ust = f"📦 <b>STOĞA GİRDİ! / BACK IN STOCK!</b> ({b.get('kapali_saat', 0):.0f} saat sonra / hours later)"
        fiyat_satiri = f"<b>Fiyat / Price:</b> {fiyat_metni}"
        renk = 3447003
    else:
        baslik = "🚀 YENİ ÜRÜN SIRALAMAYA GİRDİ!"
        ust = "🟢 <b>YENİ ÜRÜN SIRALAMAYA GİRDİ! / NEW PRODUCT IN RANKING!</b>"
        fiyat_satiri = f"<b>Fiyat / Price:</b> {fiyat_metni}"
        renk = 5814783
    mesaj = (f"{ust}\n\n"
             f"<b>Kategori / Category:</b> {html.escape(kat_ad)}\n"
             f"<b>Ürün / Product:</b> {isim}\n"
             + (f"<b>Özellikler / Specs:</b> {html.escape(ozet)}\n" if ozet else "")
             + f"<b>Kaynak / Source:</b> {html.escape(kaynak)}\n"
             f"{fiyat_satiri}\n"
             f"<b>Stok / Stock:</b> {stok}")
    return baslik, mesaj, renk, kaynak, kat_ad, ozet, stok


def bildirimleri_gonder(bildirimler):
    """[TR] Bildirimleri (en büyük indirim önce) gönderir; fazlasını özetler. / [EN] Sends alerts, biggest first."""
    if not bildirimler:
        return
    oncelik = {"indirim": 0, "stok": 1, "yeni": 2}
    sirali = sorted(bildirimler, key=lambda b: (oncelik.get(b["tur"], 9), -b.get("oran", 0), b["fiyat"]))
    for b in sirali[:MAX_BILDIRIM_TUR]:
        baslik, mesaj, renk, kaynak, kat_ad, ozet, stok = _bildirim_metinleri(b)
        eski = b.get("eski_fiyat") if b["tur"] == "indirim" else None
        discord_mesaj_gonder(baslik, b["isim"], eski, b["fiyat"], stok, b["url"], b["resim"], renk=renk,
                             kaynak=kaynak, kategori=kat_ad, ozellikler=ozet)
        telegram_mesaj_gonder(mesaj, b["url"], buton_metni=f"🛒 {kaynak}'de İncele / Satın Al")
    kalan = sirali[MAX_BILDIRIM_TUR:]
    if kalan:
        satirlar = "\n".join(f"• {html.escape((b['isim'] or '')[:60])} — {tl(b['fiyat'])} ({html.escape(config.site_adi(b['site']))})"
                             for b in kalan[:30])
        telegram_mesaj_gonder(f"📋 <b>+{len(kalan)} bildirim daha / more alerts</b>\n\n{satirlar}")


# =====================================================================================
# [TR] RAPOR VE DÖNGÜ / [EN] REPORT AND LOOP
# =====================================================================================

def rapor_yazdir(sonuclar, ozet, islem, db_suresi):
    for s in sorted(sonuclar, key=lambda x: (x.site, x.kategori)):
        if s.basarili:
            isaret = "✅" if s.tam or config.SITES[s.site]["pazaryeri"] else "🟡"
            print(f"  {isaret} {s.site:<12} {s.kategori:<8} | {s.sayfa:>2} sayfa | {len(s.urunler):>4} ürün"
                  f" ({s.elenen} elendi) | {s.sure:5.1f} sn | {s.durma_nedeni or '-'}"
                  + (f" | ⚠️ {s.hata}" if s.hata else ""))
        else:
            isaret = "⛔" if s.engellendi else "❌"
            print(f"  {isaret} {s.site:<12} {s.kategori:<8} | {s.hata}")
    sayac = islem["sayac"]
    print(f"📊 [TR] Tarama: {ozet['hedef']} hedef ({ozet['basarili']} başarılı, {ozet['engel']} engelli) | "
          f"{ozet['sayfa']} sayfa, {ozet['bayt'] / 1e6:.2f} MB | {ozet['urun']} ürün | {ozet['sure']:.1f} sn -> "
          f"{ozet['sayfa_sn']:.1f} sayfa/sn, {ozet['urun_sn']:.0f} ürün/sn | ort. gecikme {ozet['ort_gecikme']:.2f} sn | "
          f"ayrıştırma {ozet['ayristirma']:.1f} sn | DB {db_suresi:.2f} sn")
    print(f"   [TR] {sayac['yeni']} yeni, {sayac['degisim']} fiyat/stok değişimi, {sayac['buyuk_dusus']} büyük düşüş, "
          f"{sayac['stok_disi']} stok dışı, {sayac['butce_disi']} bütçe dışı yeni ürün atlandı, "
          f"{len(islem['bildirimler'])} bildirim"
          + (f" | {sayac['baseline_hedef']} hedef ilk kez tarandı (bildirim yok / baseline)" if sayac['baseline_hedef'] else ""))


async def dongu(tek_sefer=False, siteler=None, kategoriler=None, bildirim_gonder=True):
    """[TR] Sürekli izleme döngüsü. / [EN] Continuous monitoring loop."""
    hedefler = crawler.hedefleri_olustur(siteler, kategoriler)
    if not hedefler:
        log("❌ [TR] Taranacak hedef yok (site/kategori ayarlarını kontrol edin). / [EN] No targets to crawl.")
        return
    sonraki = {h.anahtar: 0.0 for h in hedefler}
    async with crawler.Tarayici() as tarayici:
        log(f"⚙️ {len(hedefler)} hedef ({len({h.site for h in hedefler})} site x {len({h.kategori for h in hedefler})} kategori) | "
            f"eşzamanlı istek: {tarayici.max_eszamanli} (site başına {tarayici.site_basina}) | "
            f"ayrıştırma süreci: {tarayici.parse_isci or 'ana süreç'} | HTML parser: {scraper.HTML_PARSER} | "
            f"bütçe: {', '.join(f'{k}={tl(config.kategori_butcesi(k))}' for k in config.AKTIF_KATEGORILER)}")
        while True:
            hazir = [h for h in hedefler if sonraki[h.anahtar] <= time.monotonic()]
            if hazir:
                log(f"[TR] {len(hazir)} hedef taranıyor... / [EN] Crawling {len(hazir)} targets...")
                t0 = time.monotonic()
                try:
                    sonuclar = await tarayici.hepsini_tara(hazir)
                    ozet = crawler.ozet_istatistik(sonuclar, time.monotonic() - t0)
                    islem, db_suresi = await asyncio.to_thread(isle_ve_yaz, sonuclar, ozet)
                    rapor_yazdir(sonuclar, ozet, islem, db_suresi)
                    if bildirim_gonder:
                        await asyncio.to_thread(bildirimleri_gonder, islem["bildirimler"])
                except Exception as e:
                    log(f"❌ [TR] Tarama sırasında kritik bir hata oluştu (Ağ/DB koptu vb.). Bot devam edecek: {e}")
                    traceback.print_exc()
                bitis = time.monotonic()
                for h in hazir:
                    sonraki[h.anahtar] = bitis + max(h.ayar["aralik"], tarayici.engel_kalan(h.host))
            if tek_sefer:
                return
            bekle = max(1.0, min(sonraki.values()) - time.monotonic())
            log(f"⏳ [TR] {bekle:.0f} sn bekleniyor... / [EN] Waiting {bekle:.0f} s...\n")
            await asyncio.sleep(bekle)


def taramayi_baslat(tek_sefer=False, siteler=None, kategoriler=None, bildirim_gonder=True):
    """
    [TR] Sürekli izleme döngüsünü başlatır. / [EN] Starts the continuous monitoring loop.
    [TR] Veritabanını başlatır, ürünleri çeker, fiyatları karşılaştırır ve uyarıları gönderir. / [EN] Initializes the database, fetches products, compares prices, and sends alerts.
    """
    print("=== DONANIM FİYAT TAKİP BOTU (RAM + SSD + ANAKART) BAŞLADI ===")
    init_db()
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(dongu(tek_sefer, siteler, kategoriler, bildirim_gonder))


def _liste(deger):
    return [p.strip().lower() for p in deger.split(",") if p.strip()] if deger else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="RAM / SSD / Anakart fiyat takip botu")
    ap.add_argument("--tek-sefer", "--once", action="store_true", help="Tek tur tara ve çık / one round then exit")
    ap.add_argument("--site", help="Sadece bu siteler (virgülle) / only these sites, e.g. vatan,itopya")
    ap.add_argument("--kategori", help="Sadece bu kategoriler / only these categories, e.g. ssd,anakart")
    ap.add_argument("--bildirim-yok", action="store_true", help="Bildirim gönderme / don't send alerts")
    args = ap.parse_args()
    taramayi_baslat(args.tek_sefer, _liste(args.site), _liste(args.kategori), not args.bildirim_yok)
