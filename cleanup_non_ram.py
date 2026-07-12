"""
[TR] Veritabanı Temizlik Betiği / [EN] Database Cleanup Script
[TR] Sitelerin vitrin/kampanya bloklarından yanlışlıkla kaydedilmiş RAM olmayan ürünleri
     (monitör, kulaklık, işlemci vb.) ve fiyat geçmişlerini veritabanından siler.
     config.DB_URL hangi veritabanını gösteriyorsa onu temizler (Supabase veya yerel SQLite).
[EN] Deletes non-RAM products (monitors, headsets, CPUs etc.) accidentally saved from promo/carousel
     blocks, together with their price history. Cleans whatever database config.DB_URL points to.

Kullanım / Usage:  python cleanup_non_ram.py
"""

import sys

from database import SessionLocal, Product, PriceHistory
from scraper import ram_urunu_mu

# [TR] Windows konsolu Türkçe karakter sorunu için / [EN] Configure Windows console to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def temizle():
    with SessionLocal() as session:
        silinecekler = [p for p in session.query(Product).all() if not ram_urunu_mu(p.name)]

        if not silinecekler:
            print("✅ [TR] Temizlenecek RAM dışı ürün bulunamadı. / [EN] No non-RAM products found.")
            return

        print(f"[TR] {len(silinecekler)} RAM dışı ürün siliniyor... / [EN] Deleting {len(silinecekler)} non-RAM products...")
        for p in silinecekler:
            print(f"  🗑️ [{p.code}] {p.name}")
            session.query(PriceHistory).filter_by(code=p.code).delete()
            session.delete(p)
        session.commit()
        print("✅ [TR] Temizlik tamamlandı. / [EN] Cleanup complete.")

if __name__ == "__main__":
    temizle()
