"""
[TR] Ana Düzenleyici Modülü / [EN] Main Orchestrator Module
[TR] Scraper, veritabanı ve Telegram botunu birbirine bağlar. / [EN] Ties the scraper, database, and Telegram bot together.
[TR] Vatan Bilgisayar'ı periyodik olarak kontrol edip veritabanını güncelleyen ve koşullar sağlanırsa Telegram uyarısı gönderen sonsuz bir döngü çalıştırır. / [EN] Runs an infinite loop to periodically check Vatan Bilgisayar for RAM prices, update the database, and trigger Telegram alerts if conditions are met.
"""

import time
import datetime
import sys

import config
from database import (init_db, is_db_empty, get_product_base, get_last_history, 
                      add_product, add_price_history, update_base_price, update_last_scan,
                      update_product_image)
from scraper import ramleri_getir
from telegram_bot import telegram_mesaj_gonder
from discord_bot import discord_mesaj_gonder

# [TR] Windows konsolu Türkçe karakter sorunu için / [EN] Attempt to configure Windows console to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def taramayi_baslat():
    """
    [TR] Sürekli izleme döngüsünü başlatır. / [EN] Starts the continuous monitoring loop.
    [TR] Veritabanını başlatır, ürünleri çeker, fiyatları karşılaştırır ve uyarıları gönderir. / [EN] Initializes the database, fetches products, compares prices, and sends alerts.
    """
    print("=== VATAN RAM TAKİP BOTU (CLOUD DB & MODÜLER) BAŞLADI ===")
    
    # [TR] Veritabanı tablolarını başlat / [EN] Initialize database tables
    init_db()
    
    while True:
        try:
            simdi = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')
            print(f"[{simdi}] [TR] Site taranıyor... / [EN] Scanning site...")
            
            ilk_calistirma = is_db_empty()
            
            all_products = ramleri_getir(config.URL_ALL)
            stock_products = ramleri_getir(config.URL_STOCK)
            
            if not all_products:
                print("[TR] Ürün bulunamadı, bekleniyor... / [EN] No products found, waiting...")
                time.sleep(config.KONTROL_SIKLIGI_SANIYE)
                continue
                
            islem_sayisi = 0
            
            for kod, veri in all_products.items():
                isim = veri["isim"]
                fiyat = veri["fiyat"]
                urun_url = veri["url"]
                resim_url = veri.get("image_url", "")
                
                stokta_mi = 1 if kod in stock_products else 0
                stok_durumu_metin = "Var" if stokta_mi else "Yok"
                
                base_info = get_product_base(kod)
                last_history = get_last_history(kod)
                
                # [TR] YENİ ÜRÜN (Veritabanında Yok) / [EN] NEW PRODUCT (Not in DB)
                if not base_info:
                    add_product(kod, isim, urun_url, fiyat, resim_url)
                    add_price_history(kod, fiyat, stokta_mi)
                    
                    if ilk_calistirma:
                        print(f"✅ [İLK BASE OLUŞTURULDU / INITIAL BASE CREATED] {fiyat} TL - {isim}")
                    else:
                        if fiyat <= config.HEDEF_FIYAT:
                            mesaj = (f"🟢 <b>YENİ ÜRÜN SIRALAMAYA GİRDİ! / NEW PRODUCT IN RANKING!</b>\n\n"
                                     f"<b>Ürün / Product:</b> {isim}\n"
                                     f"<b>Fiyat / Price:</b> {fiyat} TL\n"
                                     f"<b>Stok / Stock:</b> {stok_durumu_metin}")
                            print(f"🚀 YENİ ÜRÜN / NEW PRODUCT: {isim} - {fiyat} TL")
                            discord_mesaj_gonder("🚀 YENİ ÜRÜN SIRALAMAYA GİRDİ!", isim, None, fiyat, stok_durumu_metin, urun_url, resim_url, renk=5814783)
                            telegram_mesaj_gonder(mesaj, urun_url)
                    islem_sayisi += 1
                    
                # [TR] ZATEN BİLİNEN BİR ÜRÜN / [EN] ALREADY KNOWN PRODUCT
                else:
                    base_price = base_info["base_price"]
                    kayitli_url = base_info["url"]
                    
                    # [TR] Eski ürünün resmi yoksa güncelle / [EN] If old product has no image, update it
                    if resim_url and not base_info.get("image_url"):
                        update_product_image(kod, resim_url)
                    
                    eski_fiyat = last_history["price"] if last_history else base_price
                    eski_stok = last_history["in_stock"] if last_history else stokta_mi
                    
                    # [TR] Sadece fiyat veya stok değiştiyse DB'ye yeni satır ekle / [EN] Add new row to DB only if price or stock changed
                    if fiyat != eski_fiyat or stokta_mi != eski_stok:
                        add_price_history(kod, fiyat, stokta_mi)
                        islem_sayisi += 1
                    
                    # [TR] FİYAT DÜŞÜŞÜ VEYA ARTIŞI KONTROLÜ (Base Fiyatına Göre) / [EN] PRICE DROP OR INCREASE CHECK (Based on Base Price)
                    if fiyat < base_price:
                        indirim_orani = ((base_price - fiyat) / base_price) * 100
                        
                        if indirim_orani >= config.INDIRIM_YUZDESI and fiyat <= config.HEDEF_FIYAT:
                            print(f"🔥 BÜYÜK DÜŞÜŞ / BIG DROP: {isim} | {base_price} -> {fiyat} (%{indirim_orani:.1f})")
                            mesaj = (f"🔥 <b>BÜYÜK İNDİRİM! / BIG DISCOUNT! (%{indirim_orani:.1f})</b>\n\n"
                                     f"<b>Ürün / Product:</b> {isim}\n"
                                     f"<b>Eski Base Fiyat / Old Base Price:</b> <s>{base_price} TL</s>\n"
                                     f"<b>Yeni Fiyat / New Price:</b> {fiyat} TL\n"
                                     f"<b>Stok / Stock:</b> {stok_durumu_metin}")
                            discord_mesaj_gonder(f"🔥 BÜYÜK İNDİRİM! (%{indirim_orani:.1f})", isim, base_price, fiyat, stok_durumu_metin, kayitli_url, resim_url, renk=15158332)
                            telegram_mesaj_gonder(mesaj, kayitli_url)
                            
                            update_base_price(kod, fiyat)
                            
                        elif fiyat != eski_fiyat:
                            print(f"📉 Küçük Düşüş / Small Drop: {isim} | {eski_fiyat} -> {fiyat}")
                            
                    elif fiyat > base_price:
                        if fiyat != eski_fiyat:
                            print(f"📈 ARTIŞ (Base Güncellendi) / INCREASE (Base Updated): {isim} | {base_price} -> {fiyat}")
                        update_base_price(kod, fiyat)
            
            if ilk_calistirma:
                print("\n✅ [TR] BULUT (CLOUD) VERİTABANI OLUŞTURULDU. / [EN] CLOUD DATABASE CREATED.")
                print("[TR] Bundan sonraki tüm kıyaslamalar bu fiyatlara göre yapılacak. / [EN] All future comparisons will be based on these prices.")
            else:
                print(f"✅ [TR] Tarama tamamlandı. {islem_sayisi} değişiklik DB'ye kaydedildi. / [EN] Scan complete. {islem_sayisi} changes saved to DB.")
                
            # [TR] Son tarama saatini kaydet / [EN] Save last scan time
            update_last_scan()
            
        except Exception as e:
            print(f"❌ [TR] Tarama sırasında kritik bir hata oluştu (Ağ koptu vb.). Bot devam edecek: {e}")
            
        print(f"⏳ [TR] {config.KONTROL_SIKLIGI_SANIYE // 60} dakika bekleniyor... / [EN] Waiting for {config.KONTROL_SIKLIGI_SANIYE // 60} minutes...\n")
        time.sleep(config.KONTROL_SIKLIGI_SANIYE)

if __name__ == "__main__":
    taramayi_baslat()
