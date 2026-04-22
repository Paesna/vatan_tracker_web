"""
[TR] Scraper (Veri Çekici) Modülü / [EN] Scraper Module
[TR] Vatan Bilgisayar'dan ürün verilerini çekmek ve ayrıştırmakla sorumludur. / [EN] Responsible for fetching and parsing product data from Vatan Bilgisayar.
[TR] Ürün kodlarını, isimlerini, fiyatlarını ve bağlantılarını çıkarmak için BeautifulSoup4 kullanır. / [EN] Uses BeautifulSoup4 to extract product codes, names, prices, and URLs.
"""

import requests
import cloudscraper
from bs4 import BeautifulSoup
import datetime
import config

def fiyati_sayiya_cevir(fiyat_metni):
    """
    [TR] Türkçe fiyat metnini (örn: '12.499', '15.239,50') ondalık sayıya çevirir. / [EN] Converts a Turkish price string into a float.
    
    Args:
        fiyat_metni (str): [TR] HTML'den çekilen fiyat metni. / [EN] The price string extracted from HTML.
        
    Returns:
        float: [TR] Sayısal fiyat veya başarısız olursa None. / [EN] The numerical price, or None if conversion fails.
    """
    try:
        # [TR] Binlik ayracını (.) kaldırıp ondalık ayracını (,) noktaya çevirir. / [EN] Remove thousands separator (.) and replace decimal separator (,) with dot (.)
        temiz_fiyat = fiyat_metni.replace(".", "").replace(",", ".")
        return float(temiz_fiyat)
    except ValueError:
        return None

def ramleri_getir(url):
    """
    [TR] Verilen URL'den HTML'i çeker ve RAM ürünlerini ayıklar. / [EN] Fetches the HTML from the given URL and extracts RAM products.
    
    Args:
        url (str): [TR] Vatan Bilgisayar kategori URL'si. / [EN] The Vatan Bilgisayar category URL.
        
    Returns:
        dict: [TR] Ürün kodlarını detaylarıyla eşleştiren bir sözlük. / [EN] A dictionary mapping product codes (str) to their details (dict).
    """
    try:
        # [TR] Vatan Bilgisayar bot korumalarını aşmak için cloudscraper kullanıyoruz. / [EN] Use cloudscraper to bypass bot protections.
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        response = scraper.get(url, timeout=15)
        
        # [TR] Status code 403 ise (Yasaklı), bu hala banlandığımız anlamına gelir.
        if response.status_code == 403:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] HATA / ERROR: 403 Forbidden. IP adresiniz engellenmiş olabilir!")
            return {}
            
        response.raise_for_status()
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] HATA / ERROR: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    urun_kutulari = soup.select(".product-list")
    
    cekilen_urunler = {}
    for kutu in urun_kutulari:
        isim_etiketi = kutu.select_one(".product-list__product-name h3")
        kod_etiketi = kutu.select_one(".product-list__product-code")
        fiyat_etiketi = kutu.select_one(".product-list__price")
        link_etiketi = kutu.select_one("a.product-list-link")
        
        # [TR] Resim etiketini bul / [EN] Find image tag
        img_etiketi = kutu.select_one(".slider-img img.lazyimg")
        
        if isim_etiketi and kod_etiketi and fiyat_etiketi and link_etiketi:
            isim = isim_etiketi.text.strip()
            kod = kod_etiketi.text.strip()
            fiyat = fiyati_sayiya_cevir(fiyat_etiketi.text.strip())
            
            href = link_etiketi.get("href", "")
            if not href.startswith("http") and href:
                href = "https://www.vatanbilgisayar.com" + href
                
            img_url = ""
            if img_etiketi:
                img_url = img_etiketi.get("data-src") or img_etiketi.get("src", "")
                
            if fiyat is not None:
                cekilen_urunler[kod] = {"isim": isim, "fiyat": fiyat, "url": href, "image_url": img_url}
                
    return cekilen_urunler
