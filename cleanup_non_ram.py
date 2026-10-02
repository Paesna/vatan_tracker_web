"""
[TR] Eski isim: artık cleanup.py tüm kategorileri (RAM / SSD / Anakart) temizler; bu dosya geriye dönük uyumluluk içindir.
[EN] Legacy name: cleanup.py now cleans every category (RAM / SSD / Motherboard); kept for backward compatibility.

Kullanım / Usage:  python cleanup_non_ram.py   (= python cleanup.py)
"""

from cleanup import temizle

if __name__ == "__main__":
    temizle()
