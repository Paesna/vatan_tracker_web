"""
[TR] Veritabanı Temizlik Betiği / [EN] Database Cleanup Script
[TR] Kategorisinin (RAM / SSD / Anakart) kurallarına uymayan ürünleri - vitrin/kampanya bloklarından yanlışlıkla
     kaydedilmiş monitör, kulaklık, SSD kutusu, laptop vb. - ve fiyat geçmişlerini veritabanından siler.
     config.DB_URL hangi veritabanını gösteriyorsa onu temizler (Supabase veya yerel SQLite).
[EN] Deletes products that don't fit their category's (RAM / SSD / Motherboard) rules - monitors, headsets,
     SSD enclosures, laptops etc. accidentally saved from promo blocks - together with their price history.
     Cleans whatever database config.DB_URL points to.

Kullanım / Usage:
    python cleanup.py --kuru          # [TR] sadece listele, silme / [EN] dry run, list only
    python cleanup.py                 # [TR] sil / [EN] delete
    python cleanup.py --kategori ssd  # [TR] sadece bir kategori / [EN] only one category
"""

import argparse
import sys

import categories
import config
from database import SessionLocal, Product, PriceHistory, init_db

# [TR] Windows konsolu Türkçe karakter sorunu için / [EN] Configure Windows console to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


def temizle(kuru=False, kategori=None):
    init_db()
    with SessionLocal() as session:
        silinecekler = []
        for p in session.query(Product).all():
            kat = p.category or categories.kategori_tahmin_et(p.name)
            if kategori and kat != kategori:
                continue
            if not categories.kategoriye_uygun_mu(kat, p.name, notebook_ram_haric=config.NOTEBOOK_RAM_HARIC):
                silinecekler.append((p, kat))

        if not silinecekler:
            print("✅ [TR] Temizlenecek uygunsuz ürün bulunamadı. / [EN] No mismatching products found.")
            return 0

        eylem = "silinecek (kuru çalıştırma)" if kuru else "siliniyor"
        print(f"[TR] {len(silinecekler)} ürün {eylem}... / [EN] {len(silinecekler)} products {'to delete (dry run)' if kuru else 'deleting'}...")
        for p, kat in silinecekler:
            print(f"  🗑️ [{kat}] [{p.code}] {p.name}")
            if not kuru:
                session.query(PriceHistory).filter_by(code=p.code).delete()
                session.delete(p)
        if not kuru:
            session.commit()
            print("✅ [TR] Temizlik tamamlandı. / [EN] Cleanup complete.")
        return len(silinecekler)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Kategori kurallarına uymayan ürünleri siler / deletes mismatching products")
    ap.add_argument("--kuru", "--dry-run", action="store_true", help="Sadece listele / list only")
    ap.add_argument("--kategori", choices=list(config.KATEGORILER), help="Sadece bu kategori / only this category")
    args = ap.parse_args()
    temizle(args.kuru, args.kategori)
