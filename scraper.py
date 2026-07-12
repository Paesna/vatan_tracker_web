"""
[TR] Scraper (Veri Çekici) Modülü / [EN] Scraper Module
[TR] Vatan Bilgisayar'dan ürün verilerini çekmek ve ayrıştırmakla sorumludur. / [EN] Responsible for fetching and parsing product data from Vatan Bilgisayar.
[TR] Ürün kodlarını, isimlerini, fiyatlarını ve bağlantılarını çıkarmak için BeautifulSoup4 kullanır. / [EN] Uses BeautifulSoup4 to extract product codes, names, prices, and URLs.
"""

import re
import requests
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup
import datetime
import json
import config

# [TR] Sitelerin kategori sayfalarındaki vitrin/kampanya blokları (monitör, kulaklık vb.) da ürün kartı
#      işaretlemesi kullandığından, sadece isminde "DDR..." veya "RAM" kelimesi geçen ürünleri kabul ediyoruz.
# [EN] Category pages contain promo/carousel blocks (monitors, headsets etc.) using the same product card
#      markup, so we only accept products whose name contains the word "DDR..." or "RAM".
RAM_DESEN = re.compile(r"\b(ddr\d*|ram)\b", re.IGNORECASE)

def ram_urunu_mu(isim):
    """[TR] Ürün isminin RAM ürününe ait olup olmadığını kontrol eder. / [EN] Checks whether a product name belongs to a RAM product."""
    return bool(RAM_DESEN.search(isim or ""))

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
        # [TR] Vatan Bilgisayar bot korumalarını aşmak için TLS parmak izini Chrome gibi gösteren curl_cffi kullanıyoruz.
        # [EN] Use curl_cffi to impersonate Chrome TLS fingerprint to bypass bot protections.
        response = curl_requests.get(url, impersonate="chrome110", timeout=15)
        
        # [TR] Status code 403 ise (Yasaklı), bu hala banlandığımız anlamına gelir.
        if response.status_code == 403:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] HATA / ERROR: 403 Forbidden. IP adresiniz donanımsal olarak engellenmiş olabilir!")
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

def scrape_sinerji(url):
    """
    [TR] Sinerji'den RAM ürünlerini çeker. / [EN] Fetches RAM products from Sinerji.
    """
    try:
        response = curl_requests.get(url, impersonate="chrome110", timeout=15)
        if response.status_code == 403:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sinerji HATA: 403 Forbidden.")
            return {}
        response.raise_for_status()
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sinerji HATA: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    # [TR] Sadece asıl ürün listesini (section.productList) tara; sayfa altındaki "size özel seçtiklerimiz"
    #      bloğu (div.row.productList) monitör gibi alakasız ürünler içeriyor.
    # [EN] Only scan the main listing (section.productList); the "picked for you" block at the bottom
    #      (div.row.productList) contains unrelated products like monitors.
    product_articles = soup.select("section.productList article.product") or soup.select("article.product")
    
    cekilen_urunler = {}
    for article in product_articles:
        title_a = article.select_one(".title a")
        if not title_a:
            continue
            
        name = title_a.text.strip()
        href = title_a.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.sinerji.gen.tr" + href
            
        sku_span = article.select_one(".title .sku")
        if sku_span:
            code = sku_span.text.replace("SKU:", "").strip()
        else:
            btn = article.select_one("button.addToCart")
            if btn and btn.get("value"):
                code = btn.get("value")
            else:
                code = href.split("-p-")[-1] if "-p-" in href else href.split("/")[-1]
                
        price_span = article.select_one("span.price")
        out_of_stock = False
        warning = article.select_one(".alert.alert-warning")
        if warning and "yakında" in warning.text:
            out_of_stock = True
            
        fiyat = None
        if price_span and not out_of_stock:
            fiyat_text = price_span.text.replace("₺", "").strip()
            fiyat = fiyati_sayiya_cevir(fiyat_text)
            
        img_tag = article.select_one(".img img")
        img_url = ""
        if img_tag:
            img_url = img_tag.get("src") or img_tag.get("data-src", "")
            
        if fiyat is not None:
            cekilen_urunler[code] = {"isim": name, "fiyat": fiyat, "url": href, "image_url": img_url, "in_stock": not out_of_stock}
            
    return cekilen_urunler

def scrape_incehesap(url):
    """
    [TR] İncehesap'tan RAM ürünlerini çeker. / [EN] Fetches RAM products from İncehesap.
    """
    try:
        response = curl_requests.get(url, impersonate="chrome110", timeout=15)
        if response.status_code == 403:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] İncehesap HATA: 403 Forbidden.")
            return {}
        response.raise_for_status()
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] İncehesap HATA: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    # [TR] Sadece asıl ürün listesini (#product-grid) tara; sayfadaki "popüler ürünler" karuselleri
    #      monitör/kulaklık gibi alakasız ürünler içeriyor.
    # [EN] Only scan the main listing (#product-grid); the page's "popular products" carousels
    #      contain unrelated products like monitors/headsets.
    kapsayici = soup.select_one("#product-grid") or soup
    product_links = kapsayici.find_all("a", class_=lambda x: x and any("product" in c for c in x.split()))
    
    cekilen_urunler = {}
    for a in product_links:
        data_product = a.get("data-product")
        data_gaitem = a.get("data-gaitem")
        if not data_product:
            continue
            
        try:
            prod_json = json.loads(data_product)
            ga_json = json.loads(data_gaitem) if data_gaitem else {}
        except Exception:
            continue
            
        code = str(prod_json.get("id"))
        if not code:
            continue
            
        name = prod_json.get("name")
        price = float(prod_json.get("price", 0))
        
        href = ga_json.get("url") or a.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.incehesap.com" + href
            
        img_url = ga_json.get("image")
        if not img_url:
            img_tag = a.find("img")
            if img_tag:
                img_url = img_tag.get("src") or img_tag.get("data-src", "")
        if img_url and not img_url.startswith("http"):
            img_url = "https://www.incehesap.com" + img_url
            
        in_stock = True
        if "tükendi" in a.text.lower() or "stokta yok" in a.text.lower():
            in_stock = False
            
        if price > 0:
            cekilen_urunler[code] = {"isim": name, "fiyat": price, "url": href, "image_url": img_url, "in_stock": in_stock}
            
    return cekilen_urunler

def scrape_tebilon(url):
    """
    [TR] Tebilon'dan RAM ürünlerini çeker. / [EN] Fetches RAM products from Tebilon.
    """
    headers = {}
    if config.TEBILON_USER_AGENT:
        headers["User-Agent"] = config.TEBILON_USER_AGENT
    else:
        headers["User-Agent"] = config.HEADERS["User-Agent"]
        
    if config.TEBILON_COOKIE:
        headers["Cookie"] = config.TEBILON_COOKIE

    try:
        response = curl_requests.get(url, impersonate="chrome110", headers=headers, timeout=15)
        if response.status_code == 403:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Tebilon HATA: 403 Forbidden. Cloudflare bypass cookie GEREKLİ!")
            return {}
        response.raise_for_status()
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Tebilon HATA: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    product_cards = soup.select(".showcase__product")
    
    cekilen_urunler = {}
    for card in product_cards:
        title_a = card.select_one(".showcase__title.desktopShow a")
        if not title_a:
            title_a = card.select_one(".showcase__image a.ajaxLink")
            
        if not title_a:
            continue
            
        name = title_a.text.strip() or title_a.get("title", "").strip()
        href = title_a.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.tebilon.com" + href
            
        sku_span = card.select_one(".showcase__image span")
        if sku_span:
            code = sku_span.text.strip()
        else:
            basket_btn = card.select_one(".add-basket")
            if basket_btn and basket_btn.get("data-id"):
                code = basket_btn.get("data-id")
            else:
                code = href.split("/")[-2] if href.endswith("/") else href.split("/")[-1]
                
        price_div = card.select_one(".newPrice")
        fiyat = None
        in_stock = False
        if price_div:
            price_text = price_div.text.replace("TL", "").strip()
            fiyat = fiyati_sayiya_cevir(price_text)
            if fiyat is not None and fiyat > 0:
                in_stock = True
                
        img_tag = card.select_one(".showcase__image img.primaryImage")
        img_url = ""
        if img_tag:
            img_url = img_tag.get("src") or img_tag.get("data-src", "")
        if img_url and not img_url.startswith("http"):
            img_url = "https://www.tebilon.com" + img_url
            
        if code and fiyat is not None:
            cekilen_urunler[code] = {"isim": name, "fiyat": fiyat, "url": href, "image_url": img_url, "in_stock": in_stock}
            
    return cekilen_urunler

def scrape_itopya(url):
    """
    [TR] Itopya'dan RAM ürünlerini çeker. / [EN] Fetches RAM products from Itopya.
    """
    try:
        response = curl_requests.get(url, impersonate="chrome110", timeout=15)
        if response.status_code == 403:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Itopya HATA: 403 Forbidden.")
            return {}
        response.raise_for_status()
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Itopya HATA: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    product_divs = soup.select(".product")
    
    cekilen_urunler = {}
    for p in product_divs:
        code = p.get("data-urun-id")
        if not code:
            continue
            
        title_a = p.select_one("a.title")
        if not title_a:
            continue
            
        name = title_a.text.strip()
        href = title_a.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.itopya.com" + href
            
        img_tag = p.select_one(".product-image img.lozad")
        img_url = ""
        if img_tag:
            img_url = img_tag.get("data-src") or img_tag.get("src", "")
            if img_url and not img_url.startswith("http"):
                img_url = "https://www.itopya.com" + img_url
            
        price_span = p.select_one(".product-price")
        fiyat = None
        if price_span:
            # Check for basket discount price (Sepette fiyatı)
            sepette_span = price_span.select_one(".product-price-warning")
            if sepette_span:
                price_text = sepette_span.text.lower().replace("sepette", "").replace("tl", "").replace("₺", "").strip()
                fiyat = fiyati_sayiya_cevir(price_text)
            else:
                strong_tag = price_span.select_one("strong")
                if strong_tag:
                    price_text = strong_tag.text.lower().replace("tl", "").replace("₺", "").strip()
                    fiyat = fiyati_sayiya_cevir(price_text)
                else:
                    price_text = price_span.text.lower().replace("tl", "").replace("₺", "").strip()
                    fiyat = fiyati_sayiya_cevir(price_text)
                    
        in_stock = True
        p_text_lower = p.text.lower()
        if "tükendi" in p_text_lower or "stokta yok" in p_text_lower:
            in_stock = False
            
        if code and fiyat is not None:
            cekilen_urunler[code] = {"isim": name, "fiyat": fiyat, "url": href, "image_url": img_url, "in_stock": in_stock}
            
    return cekilen_urunler

def scrape_site(site_name, site_config):
    """
    [TR] Sitenin adına göre ilgili kazıma fonksiyonunu tetikler. / [EN] Triggers the relevant scraper based on the site name.
    """
    url = site_config["all_url"]
    if site_name == "vatan":
        urunler = ramleri_getir(url)
    elif site_name == "sinerji":
        urunler = scrape_sinerji(url)
    elif site_name == "incehesap":
        urunler = scrape_incehesap(url)
    elif site_name == "tebilon":
        urunler = scrape_tebilon(url)
    elif site_name == "itopya":
        urunler = scrape_itopya(url)
    else:
        return {}

    # [TR] RAM olmayan vitrin/kampanya ürünlerini ayıkla. / [EN] Filter out non-RAM promo/carousel products.
    return {kod: veri for kod, veri in urunler.items() if ram_urunu_mu(veri.get("isim", ""))}
