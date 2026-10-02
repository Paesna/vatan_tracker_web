"""
[TR] Scraper (Veri Ayrıştırıcı) Modülü / [EN] Scraper (Parser) Module
[TR] Sitelerin kategori sayfalarındaki HTML'den ürün kodu, isim, fiyat, link, resim ve stok bilgisini çıkarır.
     Ağ işlemleri crawler.py'dedir; buradaki fonksiyonlar saf HTML -> ürün dönüşümüdür, bu sayede ayrı
     süreçlerde (çok çekirdekli) paralel çalıştırılabilir ve internet olmadan test edilebilir.
[EN] Extracts product code, name, price, link, image and stock info from category page HTML.
     Networking lives in crawler.py; these functions are pure HTML -> products transforms, so they can run
     in parallel worker processes (multi-core) and be tested offline.

[TR] Her ayrıştırıcı {kod: {"isim", "fiyat", "url", "image_url", "in_stock"}} sözlüğü döndürür.
[EN] Every parser returns {code: {"isim", "fiyat", "url", "image_url", "in_stock"}}.
"""

import re
import json
import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import categories

try:
    import lxml  # noqa: F401
    # [TR] lxml, yerleşik html.parser'dan ~1.5-2 kat hızlıdır (benchmark.py ölçer). / [EN] lxml is ~1.5-2x faster.
    HTML_PARSER = "lxml"
except ImportError:  # pragma: no cover - lxml kurulmamışsa / lxml not installed
    HTML_PARSER = "html.parser"


def corba(html):
    """[TR] HTML'i BeautifulSoup ağacına çevirir (mümkünse lxml ile). / [EN] Builds the soup (lxml if available)."""
    return BeautifulSoup(html or "", HTML_PARSER)


# [TR] Sitelerin kategori sayfalarındaki vitrin/kampanya blokları (monitör, kulaklık vb.) da ürün kartı
#      işaretlemesi kullandığından, sadece isminde "DDR..." veya "RAM" kelimesi geçen ürünleri kabul ediyoruz.
# [EN] Category pages contain promo/carousel blocks (monitors, headsets etc.) using the same product card
#      markup, so we only accept products whose name contains the word "DDR..." or "RAM".
RAM_DESEN = re.compile(r"\b(ddr\d*|ram)\b", re.IGNORECASE)


def ram_urunu_mu(isim):
    """[TR] Ürün isminin RAM ürününe ait olup olmadığını kontrol eder. / [EN] Checks whether a product name belongs to a RAM product."""
    return categories.kategoriye_uygun_mu("ram", isim)


def fiyati_sayiya_cevir(fiyat_metni):
    """
    [TR] Fiyat metnini ondalık sayıya çevirir. Türkçe ('12.499', '15.239,50 TL', '₺1.299') ve noktalı
         ondalık ('1299.90') biçimlerini anlar. / [EN] Converts a price string into a float. Understands
         Turkish ('12.499', '15.239,50 TL', '₺1.299') and dot-decimal ('1299.90') formats.

    Returns:
        float: [TR] Sayısal fiyat veya başarısız olursa None. / [EN] The numerical price, or None if conversion fails.
    """
    if fiyat_metni is None:
        return None
    if isinstance(fiyat_metni, (int, float)):
        return float(fiyat_metni) if fiyat_metni > 0 else None
    s = re.sub(r"[^\d.,]", "", str(fiyat_metni))
    if not s or not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")      # 1.234,56
        else:
            s = s.replace(",", "")                        # 1,234.56
    elif "," in s:
        parcalar = s.split(",")
        if len(parcalar) == 2 and len(parcalar[1]) in (1, 2):
            s = s.replace(",", ".")                       # 1234,5 / 1234,56
        else:
            s = s.replace(",", "")                        # 1,234 / 1,234,567
    elif "." in s:
        parcalar = s.split(".")
        if len(parcalar) > 2 or len(parcalar[1]) == 3:
            s = s.replace(".", "")                        # 12.499 / 1.234.567
    try:
        deger = float(s.strip("."))
    except ValueError:
        return None
    return deger if deger > 0 else None


fiyat_coz = fiyati_sayiya_cevir


# --- ORTAK YARDIMCILAR / SHARED HELPERS ---
_STOK_YOK = re.compile(r"tukendi|stokta yok|stok disi|gelince haber ver|temin edilemiyor|satista degil|"
                       r"out of stock|gecici olarak|stoklarimizda yok|urun mevcut degil")


def _stok_disi_mi(metin):
    return bool(_STOK_YOK.search(categories.normalize(metin)))


def _mutlak(href, taban):
    if not href:
        return ""
    href = href.strip()
    if href.startswith("//"):
        return "https:" + href
    return urljoin(taban, href) if not href.startswith("http") else href


def _resim(img, taban):
    """[TR] Lazy-load özniteliklerini de deneyerek resim linkini bulur. / [EN] Image URL incl. lazy-load attrs."""
    if img is None:
        return ""
    for nitelik in ("data-src", "data-original", "data-lazy-src", "data-lazy", "data-srcset", "srcset", "src"):
        deger = (img.get(nitelik) or "").strip()
        if not deger or deger.startswith("data:"):
            continue
        if "srcset" in nitelik:
            deger = deger.split(",")[0].strip().split(" ")[0]
        return _mutlak(deger, taban)
    return ""


def _temiz_metin(metin):
    return re.sub(r"\s+", " ", metin or "").strip()


# =====================================================================================
# [TR] DOĞRULANMIŞ SİTE AYRIŞTIRICILARI (seçiciler canlı sitede çalışan eski koddan aynen alındı)
# [EN] VERIFIED SITE PARSERS (selectors kept verbatim from the previously working code)
# =====================================================================================

def parse_vatan(html, url=""):
    """[TR] Vatan Bilgisayar kategori sayfası. / [EN] Vatan Bilgisayar category page."""
    soup = corba(html)
    cekilen_urunler = {}
    for kutu in soup.select(".product-list"):
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


def parse_sinerji(html, url=""):
    """[TR] Sinerji kategori sayfası. / [EN] Sinerji category page."""
    soup = corba(html)
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


def parse_incehesap(html, url=""):
    """[TR] İncehesap kategori sayfası. / [EN] İncehesap category page."""
    soup = corba(html)
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

        code = str(prod_json.get("id") or "")
        if not code or code == "None":
            continue

        name = prod_json.get("name")
        try:
            price = float(prod_json.get("price", 0) or 0)
        except (TypeError, ValueError):
            price = fiyati_sayiya_cevir(prod_json.get("price")) or 0

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

        if price > 0 and name:
            cekilen_urunler[code] = {"isim": name, "fiyat": price, "url": href, "image_url": img_url, "in_stock": in_stock}
    return cekilen_urunler


def parse_tebilon(html, url=""):
    """[TR] Tebilon kategori sayfası. / [EN] Tebilon category page."""
    soup = corba(html)
    cekilen_urunler = {}
    for card in soup.select(".showcase__product"):
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


_ITOPYA_TOPLAM = re.compile(r"urunSayisi\s*=\s*(\d+)\s*;")


def parse_itopya(html, url=""):
    """[TR] İtopya kategori sayfası (ve 'Daha Fazla' AJAX parçası). / [EN] İtopya page (and 'load more' fragment)."""
    soup = corba(html)
    cekilen_urunler = {}
    for p in soup.select(".product"):
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
            # [TR] Sepette indirimli fiyat varsa onu kullan / [EN] Prefer the basket discount price (Sepette)
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


def itopya_toplam_sayfa(html, sayfa_boyutu=20):
    """[TR] Sayfadaki 'urunSayisi = N;' değerinden toplam sayfa sayısı. / [EN] Total pages from 'urunSayisi = N;'."""
    sayilar = [int(x) for x in _ITOPYA_TOPLAM.findall(html or "")]
    toplam = max(sayilar) if sayilar else 0
    return -(-toplam // sayfa_boyutu) if toplam else None


# =====================================================================================
# [TR] GENEL STRATEJİLER (yeni siteler için) / [EN] GENERIC STRATEGIES (for new sites)
#   1) JSON-LD (schema.org Product / ItemList)
#   2) Sayfaya gömülü JSON (Next.js __NEXT_DATA__, window.__STATE__ = {...}, JSON.parse("..."))
#   3) Ürün linki deseninden yola çıkarak kart bulma (link-anchored cards)
# =====================================================================================

def _kod_ve_url(url, desen_rx, yedek_kod=None):
    eslesme = desen_rx.search(url) if (desen_rx and url) else None
    if eslesme:
        return eslesme.group(1), url
    return (str(yedek_kod) if yedek_kod not in (None, "") else None), url


def _jsonld_bloklari(soup):
    for script in soup.find_all("script", type=lambda t: t and "ld+json" in t.lower()):
        metin = script.string or script.get_text() or ""
        try:
            yield json.loads(metin)
        except (ValueError, TypeError):
            continue


def _jsonld_teklif(teklif):
    """[TR] offers alanından (fiyat, stokta_mi). / [EN] (price, in_stock) from an offers field."""
    if isinstance(teklif, list):
        sonuc = [_jsonld_teklif(t) for t in teklif]
        sonuc = [s for s in sonuc if s[0]]
        return min(sonuc, key=lambda s: s[0]) if sonuc else (None, True)
    if not isinstance(teklif, dict):
        return None, True
    fiyat = teklif.get("price") or teklif.get("lowPrice")
    if fiyat is None and isinstance(teklif.get("priceSpecification"), dict):
        fiyat = teklif["priceSpecification"].get("price")
    if isinstance(teklif.get("offers"), (dict, list)) and fiyat is None:
        return _jsonld_teklif(teklif["offers"])
    stok = str(teklif.get("availability", "")).lower()
    return fiyati_sayiya_cevir(fiyat), not any(x in stok for x in ("outofstock", "soldout", "discontinued"))


def jsonld_urunleri(soup, taban, desen_rx=None):
    """[TR] JSON-LD içindeki fiyatlı Product kayıtları. / [EN] Priced Product entries inside JSON-LD."""
    urunler = {}

    def gez(dugum):
        if isinstance(dugum, list):
            for x in dugum:
                gez(x)
            return
        if not isinstance(dugum, dict):
            return
        tip = dugum.get("@type")
        tipler = tip if isinstance(tip, list) else [tip]
        if "Product" in tipler and dugum.get("offers"):
            fiyat, stokta = _jsonld_teklif(dugum["offers"])
            isim = _temiz_metin(dugum.get("name"))
            url = _mutlak(dugum.get("url") or dugum.get("@id") or "", taban)
            yedek = dugum.get("sku") or dugum.get("productID") or dugum.get("mpn") or url
            kod, url = _kod_ve_url(url, desen_rx, yedek)
            resim = dugum.get("image")
            if isinstance(resim, list):
                resim = resim[0] if resim else ""
            if isinstance(resim, dict):
                resim = resim.get("url", "")
            if kod and isim and fiyat:
                urunler[kod] = {"isim": isim, "fiyat": fiyat, "url": url,
                                "image_url": _mutlak(resim or "", taban), "in_stock": stokta}
        for anahtar in ("@graph", "itemListElement", "item", "mainEntity", "hasPart"):
            if anahtar in dugum:
                gez(dugum[anahtar])

    for blok in _jsonld_bloklari(soup):
        gez(blok)
    return urunler


_ATAMA_JSON = re.compile(r"(?:window\.|self\.)?[\w$.\[\]\"']{2,80}\s*=\s*(?=[{\[])")
_JSON_PARSE = re.compile(r"JSON\.parse\(\s*(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')\s*\)")
_DECODER = json.JSONDecoder()

_ISIM_ANAHTARLARI = ("name", "productName", "title", "displayName", "product_name")
_URL_ANAHTARLARI = ("url", "productUrl", "link", "href", "canonicalUrl", "seoUrl", "detailUrl")
_ID_ANAHTARLARI = ("id", "productId", "contentId", "sku", "code", "itemId", "product_id")
_RESIM_ANAHTARLARI = ("image", "imageUrl", "images", "img", "thumbnail", "mainImage", "imageURL")
# [TR] Öncelik sırası: indirimli/satış fiyatı önce, liste fiyatı en son. / [EN] Discounted price first.
_FIYAT_ANAHTARLARI = ("discountedPrice", "sellingPrice", "salePrice", "finalPrice", "currentPrice",
                      "price", "lowPrice", "amount", "value", "priceValue")


def _sayisal_fiyat(deger, derinlik=0):
    if isinstance(deger, bool) or deger is None:
        return None
    if isinstance(deger, (int, float)):
        return float(deger) if deger > 0 else None
    if isinstance(deger, str):
        return fiyati_sayiya_cevir(deger) if re.search(r"\d", deger) and len(deger) < 30 else None
    if isinstance(deger, dict) and derinlik < 3:
        for anahtar in _FIYAT_ANAHTARLARI:
            if anahtar in deger:
                fiyat = _sayisal_fiyat(deger[anahtar], derinlik + 1)
                if fiyat:
                    return fiyat
    return None


def _ilk_str(sozluk, anahtarlar):
    for anahtar in anahtarlar:
        deger = sozluk.get(anahtar)
        if isinstance(deger, list) and deger:
            deger = deger[0]
        if isinstance(deger, dict):
            deger = deger.get("url") or deger.get("src") or deger.get("value")
        if isinstance(deger, (str, int)) and str(deger).strip():
            return str(deger).strip()
    return None


def _json_bloklari(soup):
    """[TR] Sayfadaki ayrıştırılabilir JSON blokları. / [EN] Parseable JSON blobs in the page."""
    for script in soup.find_all("script"):
        metin = script.string or script.get_text() or ""
        if len(metin) < 50:
            continue
        tip = (script.get("type") or "").lower()
        if "json" in tip and "ld+json" not in tip:
            try:
                yield json.loads(metin)
            except (ValueError, TypeError):
                pass
            continue
        for m in _JSON_PARSE.finditer(metin):
            try:
                yield json.loads(json.loads(m.group(1)) if m.group(1)[0] == '"' else m.group(1)[1:-1])
            except (ValueError, TypeError):
                pass
        for m in _ATAMA_JSON.finditer(metin):
            try:
                deger, _ = _DECODER.raw_decode(metin, m.end())
                yield deger
            except ValueError:
                pass


def gomulu_json_urunleri(soup, taban, desen_rx=None):
    """
    [TR] Sayfaya gömülü JSON içinde "ürüne benzeyen" sözlükleri bulur (isim + fiyat + link/kod).
    [EN] Finds product-like dicts (name + price + link/id) in JSON embedded in the page.
    """
    urunler = {}

    def gez(dugum, derinlik=0):
        if derinlik > 40:
            return
        if isinstance(dugum, list):
            for x in dugum:
                gez(x, derinlik + 1)
            return
        if not isinstance(dugum, dict):
            return
        isim = _ilk_str(dugum, _ISIM_ANAHTARLARI)
        fiyat = None
        for anahtar in _FIYAT_ANAHTARLARI:
            if anahtar in dugum:
                fiyat = _sayisal_fiyat(dugum[anahtar])
                if fiyat:
                    break
        if isim and fiyat and len(isim) >= 6 and re.search(r"[a-zA-Z]", isim):
            url = _ilk_str(dugum, _URL_ANAHTARLARI)
            url = _mutlak(url, taban) if url else ""
            kod, url = _kod_ve_url(url, desen_rx, _ilk_str(dugum, _ID_ANAHTARLARI))
            # [TR] Desen verildiyse link desene uymalı (banner/kategori sözlüklerini elemek için).
            # [EN] With a pattern, the link must match it (filters out banner/category dicts).
            if kod and (not desen_rx or (url and desen_rx.search(url))):
                marka = dugum.get("brand")
                if isinstance(marka, dict):
                    marka = marka.get("name")
                if isinstance(marka, str) and marka and not categories.normalize(isim).startswith(categories.normalize(marka)):
                    isim = f"{marka} {isim}"
                stok = dugum.get("inStock", dugum.get("isInStock", dugum.get("available", True)))
                urunler.setdefault(kod, {"isim": _temiz_metin(isim), "fiyat": fiyat, "url": url,
                                         "image_url": _mutlak(_ilk_str(dugum, _RESIM_ANAHTARLARI) or "", taban),
                                         "in_stock": stok is not False})
        for deger in dugum.values():
            if isinstance(deger, (dict, list)):
                gez(deger, derinlik + 1)

    for blok in _json_bloklari(soup):
        gez(blok)
    return urunler


# --- LİNK TABANLI KART ÇIKARIMI / LINK-ANCHORED CARD EXTRACTION ---
_FIYAT_SINIF = re.compile(r"price|prc|fiyat|amount|tutar", re.IGNORECASE)
# [TR] Sınıf adındaki ayrı kelimeler (old-price, price_old, eski-fiyat); "font-bold" gibi sınıflara takılmaz.
# [EN] Separate words in class names (old-price, price_old); does not trip on classes like "font-bold".
_ESKI_FIYAT_SINIF = re.compile(r"(?:^|[\s_-])(?:old|eski|prev|previous|before|original|strike|striked|"
                               r"strikethrough|crossed|indirimsiz)(?:[\s_-]|$)|list-?price|liste-?fiyat|"
                               r"taksit|install|month|aylik|unit-?price|per-?unit|line-through", re.IGNORECASE)
_TERCIH_SINIF = re.compile(r"sepet|basket|final|discount|sale|current|new|indirimli|special", re.IGNORECASE)
_FIYAT_NITELIKLERI = ("data-price", "data-product-price", "data-sale-price", "data-final-price")
_METIN_FIYAT = re.compile(r"(?:₺|\btl\b|\btry\b)\s*(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)"
                          r"|(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)\s*(?:₺|\btl\b|\btry\b)",
                          re.IGNORECASE)
_FIYAT_DISI = re.compile(r"indirim|kupon|kazan|puan|kargo|taksit|aylik|ay x|x \d|pesin|tasarruf|"
                         r"cashback|iade|bonus", re.IGNORECASE)
_SAYI = re.compile(r"\d[\d.,]*")
_JENERIK_ISIM = re.compile(r"^(sepete ekle|incele|hemen al|satin al|detay|karsilastir|favori|"
                           r"tukendi|stokta yok|yeni|indirim|kampanya)\b", re.IGNORECASE)
_MIN_MANTIKLI_FIYAT = 50.0


def _eski_fiyat_mi(el, kart):
    """[TR] Eleman üstü çizili/eski/taksit fiyatı mı? / [EN] Is the element a struck/old/installment price?"""
    dugum = el
    while dugum is not None and dugum is not kart:
        if dugum.name in ("del", "s", "strike"):
            return True
        siniflar = " ".join(dugum.get("class") or []) + " " + (dugum.get("data-testid") or dugum.get("data-test-id") or "")
        if _ESKI_FIYAT_SINIF.search(siniflar):
            return True
        dugum = dugum.parent
    return False


def _en_iyi_fiyat(adaylar):
    """[TR] Tercihli (sepet/indirimli) adaylar varsa onların en düşüğü, yoksa tümünün en düşüğü.
    [EN] Lowest preferred (basket/discounted) candidate if any, otherwise the lowest of all."""
    if not adaylar:
        return None
    en_yuksek_oncelik = max(o for o, _ in adaylar)
    return min(f for o, f in adaylar if o == en_yuksek_oncelik)


def _kart_fiyati(kart):
    """[TR] Kart içindeki geçerli (eski/taksit olmayan) fiyat. / [EN] Current (non-old, non-installment) price."""
    adaylar = []
    for el in [kart] + kart.find_all(True):
        for nitelik in _FIYAT_NITELIKLERI:
            if el.get(nitelik):
                fiyat = fiyati_sayiya_cevir(el[nitelik])
                if fiyat and fiyat >= _MIN_MANTIKLI_FIYAT:
                    adaylar.append((1, fiyat))
        if el is kart:
            continue
        if el.get("itemprop") == "price" and el.get("content"):
            fiyat = fiyati_sayiya_cevir(el["content"])
            if fiyat:
                adaylar.append((2, fiyat))
            continue
        siniflar = " ".join(el.get("class") or []) + " " + (el.get("data-testid") or el.get("data-test-id") or "")
        if not _FIYAT_SINIF.search(siniflar):
            continue
        if _eski_fiyat_mi(el, kart):
            continue
        metin = _temiz_metin(el.get_text(" ", strip=True))
        if not metin or len(metin) > 40 or _FIYAT_DISI.search(categories.normalize(metin)):
            continue
        # [TR] Birden çok sayı varsa (örn. "2.500 TL 3.000 TL") iç elemanlar ayrıca değerlendirilir.
        # [EN] Several numbers (e.g. "2.500 TL 3.000 TL") means inner elements are evaluated separately.
        bitisik = el.get_text("", strip=True)
        if len(_SAYI.findall(bitisik)) != 1:
            continue
        fiyat = fiyati_sayiya_cevir(bitisik)
        if fiyat and fiyat >= _MIN_MANTIKLI_FIYAT:
            adaylar.append((1 if _TERCIH_SINIF.search(siniflar) else 0, fiyat))
    if adaylar:
        return _en_iyi_fiyat(adaylar)

    # [TR] Sınıf ipucu yoksa metindeki "1.234,56 TL" kalıpları. / [EN] Fallback: "1.234,56 TL" patterns in text.
    for metin in kart.find_all(string=True):
        ust = metin.parent
        if ust is None or ust.name in ("script", "style") or _eski_fiyat_mi(ust, kart):
            continue
        satir = _temiz_metin(ust.get_text(" ", strip=True))
        if len(satir) > 60 or _FIYAT_DISI.search(categories.normalize(satir)):
            continue
        for m in _METIN_FIYAT.finditer(satir):
            fiyat = fiyati_sayiya_cevir(m.group(1) or m.group(2))
            if fiyat and fiyat >= _MIN_MANTIKLI_FIYAT:
                adaylar.append((0, fiyat))
    return min(f for _, f in adaylar) if adaylar else None


def _kart_ismi(linkler, kart):
    """[TR] Kartın en olası ürün adı. / [EN] The most likely product name in a card."""
    gruplar = [
        [el.get_text(" ", strip=True) for el in kart.find_all(True)
         if re.search(r"name|title|isim|baslik|prdct-desc", " ".join(el.get("class") or []), re.IGNORECASE)
         or el.get("itemprop") == "name"],
        [h.get_text(" ", strip=True) for h in kart.find_all(["h1", "h2", "h3", "h4"])],
        [a.get("title", "") for a in linkler] + [a.get("aria-label", "") for a in linkler],
        [img.get("alt", "") for img in kart.find_all("img")],
        [a.get_text(" ", strip=True) for a in linkler],
    ]
    for grup in gruplar:
        adaylar = [_temiz_metin(x) for x in grup if x]
        adaylar = [x for x in adaylar if len(x) >= 6 and len(x) <= 300 and re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", x)
                   and not _JENERIK_ISIM.search(categories.normalize(x)) and not _METIN_FIYAT.fullmatch(x)]
        if adaylar:
            return max(adaylar, key=len)
    return None


_LOGO = re.compile(r"logo|brand|marka|badge|rozet|icon|ikon|sprite|placeholder|loading|kargo|flag", re.IGNORECASE)
_COKLU = object()


def _kart_resmi(linkler, kart, taban):
    """[TR] Ürün görseli: önce ürün linkinin içindeki, sonra logo/ikon olmayan ilk resim.
    [EN] Product image: first the one inside the product link, then the first non-logo/icon image."""
    adaylar = [img for a in linkler for img in a.find_all("img")] + kart.find_all("img")
    for img in adaylar:
        ipucu = " ".join([img.get("src") or "", img.get("data-src") or "", " ".join(img.get("class") or []),
                          img.get("alt") or "" if len(img.get("alt") or "") < 25 else ""])
        if not _LOGO.search(ipucu):
            url = _resim(img, taban)
            if url:
                return url
    return _resim(adaylar[0], taban) if adaylar else ""


def kart_urunleri(soup, taban, desen_rx):
    """
    [TR] Ürün linki desenine uyan <a> etiketlerinden yola çıkıp her ürünün kartını (başka ürün linki
         içermeyen en büyük üst eleman) bulur ve isim/fiyat/resim çıkarır. Site HTML'i değişse bile çalışır.
    [EN] Starts from <a> tags matching the product link pattern, climbs to each product's card (the largest
         ancestor holding no other product's link) and extracts name/price/image. Survives markup changes.
    """
    if desen_rx is None:
        return {}
    gruplar = {}
    # [TR] Her elemanın altındaki ürün kodu: tek kod ise o kod, birden fazlaysa _COKLU. Tek geçişte hesaplanır
    #      (link sayısı x derinlik); böylece büyük sayfalarda her ürün için alt ağacı yeniden taramayız.
    # [EN] Product code under each element: the code if unique, _COKLU if several. Computed in one pass
    #      (links x depth) so big pages don't rescan subtrees for every product.
    alt_kod = {}
    for a in soup.find_all("a", href=True):
        m = desen_rx.search(a["href"])
        if not m:
            continue
        kod = m.group(1)
        gruplar.setdefault(kod, []).append(a)
        el = a
        while el is not None:
            onceki = alt_kod.get(id(el))
            if onceki is None:
                alt_kod[id(el)] = kod
            elif onceki == kod:
                break  # [TR] bu kodla üstler zaten işlendi / [EN] ancestors already processed for this code
            else:
                if onceki is _COKLU:
                    break  # [TR] üstleri zaten çoklu / [EN] ancestors are already multi
                alt_kod[id(el)] = _COKLU
            el = el.parent

    urunler = {}
    for kod, linkler in gruplar.items():
        kart = linkler[0]
        while kart.parent is not None and kart.parent.name not in ("body", "html", "[document]"):
            if alt_kod.get(id(kart.parent)) != kod:
                break
            kart = kart.parent
        isim = _kart_ismi(linkler, kart)
        fiyat = _kart_fiyati(kart)
        if not isim or not fiyat:
            continue
        url = _mutlak(linkler[0]["href"], taban)
        urunler[kod] = {"isim": isim, "fiyat": fiyat, "url": url,
                        "image_url": _kart_resmi(linkler, kart, taban),
                        "in_stock": not _stok_disi_mi(kart.get_text(" ", strip=True))}
    return urunler


def _birlestir(*kaynaklar):
    """[TR] Sözlükleri öncelik sırasıyla birleştirir (ilk görülen ürün verisi kalır). / [EN] Priority union."""
    sonuc = {}
    for kaynak in kaynaklar:
        for kod, veri in kaynak.items():
            sonuc.setdefault(kod, veri)
    return sonuc


def parse_genel(html, url="", desen=None, soup=None):
    """
    [TR] Genel ayrıştırıcı. Güvenilirlik sırasıyla JSON-LD > gömülü JSON > link tabanlı kartlar birleştirilir;
         böylece biri eksik kalsa da diğerleri tamamlar. / [EN] Generic parser. Merges JSON-LD > embedded JSON >
         link-anchored cards in order of reliability so one strategy fills the gaps of another.
    """
    soup = soup if soup is not None else corba(html)
    desen_rx = re.compile(desen) if isinstance(desen, str) else desen
    return _birlestir(jsonld_urunleri(soup, url, desen_rx),
                      gomulu_json_urunleri(soup, url, desen_rx),
                      kart_urunleri(soup, url, desen_rx))


# =====================================================================================
# [TR] PLATFORMA / SİTEYE ÖZEL AYRIŞTIRICILAR (genel stratejiye düşerler)
# [EN] PLATFORM / SITE SPECIFIC PARSERS (fall back to the generic strategy)
# =====================================================================================

def parse_woocommerce(html, url="", desen=None):
    """[TR] WooCommerce (WordPress) mağaza listesi, örn. Gaming.gen.tr. / [EN] WooCommerce shop loop."""
    soup = corba(html)
    desen_rx = re.compile(desen) if isinstance(desen, str) else desen
    urunler = {}
    for kart in soup.select("li.product, div.product.type-product, div.product-grid-item, div.product-small.product"):
        siniflar = kart.get("class") or []
        link = (kart.select_one("a.woocommerce-LoopProduct-link, a.woocommerce-loop-product__link")
                or kart.select_one(".product-title a, .wd-entities-title a, h2 a, h3 a")
                or kart.select_one("a[href]"))
        if not link:
            continue
        href = _mutlak(link.get("href", ""), url)
        isim_el = kart.select_one(".woocommerce-loop-product__title, .product-title, .wd-entities-title, "
                                  ".product-name, h2, h3")
        isim = _temiz_metin(isim_el.get_text(" ", strip=True) if isim_el else link.get("title", ""))
        if not isim:
            img = kart.find("img")
            isim = _temiz_metin(img.get("alt", "") if img else "")

        fiyat_el = kart.select(".price ins .woocommerce-Price-amount, .price ins .amount")
        if not fiyat_el:
            fiyat_el = [el for el in kart.select(".price .woocommerce-Price-amount, .price .amount")
                        if el.find_parent("del") is None]
        fiyatlar = [fiyati_sayiya_cevir(el.get_text(" ", strip=True)) for el in fiyat_el]
        fiyatlar = [f for f in fiyatlar if f]
        fiyat = min(fiyatlar) if fiyatlar else None

        yedek = next((s.split("-", 1)[1] for s in siniflar if re.fullmatch(r"post-\d+", s)), None)
        sepet = kart.select_one("[data-product_id]")
        yedek = yedek or (sepet.get("data-product_id") if sepet else None) or href
        kod, href = _kod_ve_url(href, desen_rx, yedek)
        stokta = "outofstock" not in siniflar and not _stok_disi_mi(kart.get_text(" ", strip=True))
        if kod and isim and fiyat:
            urunler[kod] = {"isim": isim, "fiyat": fiyat, "url": href,
                            "image_url": _resim(kart.find("img"), url), "in_stock": stokta}
    return urunler or parse_genel(html, url, desen_rx, soup=soup)


def parse_amazon(html, url="", desen=None):
    """[TR] Amazon.com.tr arama/kategori sonuçları. / [EN] Amazon.com.tr search/category results."""
    soup = corba(html)
    urunler = {}
    for kart in soup.select('div[data-component-type="s-search-result"][data-asin]'):
        asin = (kart.get("data-asin") or "").strip()
        if not asin:
            continue
        baslik = kart.select_one("h2")
        isim = _temiz_metin(baslik.get("aria-label") or baslik.get_text(" ", strip=True)) if baslik else ""
        fiyat = None
        for el in kart.select(".a-price .a-offscreen"):
            if el.find_parent(class_="a-text-price") is None:
                fiyat = fiyati_sayiya_cevir(el.get_text(strip=True))
                if fiyat:
                    break
        if not fiyat:
            tam = kart.select_one(".a-price-whole")
            kesir = kart.select_one(".a-price-fraction")
            if tam:
                fiyat = fiyati_sayiya_cevir(tam.get_text(strip=True).rstrip(",.") + "," + (kesir.get_text(strip=True) if kesir else "00"))
        link = kart.select_one("a[href*='/dp/']")
        href = f"https://www.amazon.com.tr/dp/{asin}"
        if link and "/sspa/" not in link.get("href", ""):
            href = _mutlak(link["href"].split("/ref=")[0], "https://www.amazon.com.tr/")
        if isim and fiyat:
            urunler[asin] = {"isim": isim, "fiyat": fiyat, "url": href,
                             "image_url": _resim(kart.select_one("img.s-image"), url), "in_stock": True}
    return urunler or parse_genel(html, url, desen, soup=soup)


def parse_trendyol(html, url="", desen=None):
    """[TR] Trendyol kategori sayfası. / [EN] Trendyol category page."""
    soup = corba(html)
    desen_rx = re.compile(desen) if isinstance(desen, str) else desen
    taban = "https://www.trendyol.com/"
    kartlar = {}
    for kart in soup.select("div.p-card-wrppr"):
        link = kart.select_one("a[href]")
        if not link:
            continue
        href = _mutlak(link["href"], taban)
        kod, href = _kod_ve_url(href, desen_rx, kart.get("data-id"))
        marka = kart.select_one(".prdct-desc-cntnr-ttl")
        ad = kart.select_one(".prdct-desc-cntnr-name")
        isim = _temiz_metin(" ".join(x.get_text(" ", strip=True) for x in (marka, ad) if x)) or kart.get("title", "")
        fiyat_el = kart.select_one(".prc-box-dscntd, .prc-box-sllng, .price-item, .discounted-price")
        fiyat = fiyati_sayiya_cevir(fiyat_el.get_text(" ", strip=True)) if fiyat_el else None
        if kod and isim and fiyat:
            kartlar[kod] = {"isim": isim, "fiyat": fiyat, "url": href,
                            "image_url": _resim(kart.find("img"), taban), "in_stock": True}
    urunler = _birlestir(gomulu_json_urunleri(soup, taban, desen_rx), kartlar, kart_urunleri(soup, taban, desen_rx))
    # [TR] Trendyol görselleri CDN'dedir (göreli "/ty..." yolları). / [EN] Trendyol images live on its CDN.
    for veri in urunler.values():
        if "trendyol.com/ty" in (veri.get("image_url") or ""):
            veri["image_url"] = veri["image_url"].replace("www.trendyol.com/", "cdn.dsmcdn.com/", 1)
    return urunler


def parse_akakce(html, url="", desen=None):
    """[TR] Akakçe kategori listesi (her ürünün en ucuz satıcı fiyatı). / [EN] Akakçe listing (lowest seller price)."""
    soup = corba(html)
    desen_rx = re.compile(desen) if isinstance(desen, str) else desen
    urunler = {}
    for li in soup.select("#APL > li, ul[class^='pl_'] > li, li[data-pr]"):
        link = li.select_one("a[href]")
        if not link:
            continue
        href = _mutlak(link["href"], "https://www.akakce.com/")
        kod, href = _kod_ve_url(href, desen_rx, li.get("data-pr"))
        baslik = li.select_one("h3, [class^='pn_']")
        isim = _temiz_metin(link.get("title") or (baslik.get_text(" ", strip=True) if baslik else ""))
        fiyat_el = li.select_one("[class^='pt_'], .pt")
        fiyat = fiyati_sayiya_cevir(fiyat_el.get_text("", strip=True)) if fiyat_el else _kart_fiyati(li)
        if kod and isim and fiyat:
            urunler[kod] = {"isim": isim, "fiyat": fiyat, "url": href,
                            "image_url": _resim(li.find("img"), "https://www.akakce.com/"), "in_stock": True}
    return urunler or parse_genel(html, url, desen_rx, soup=soup)


PARSERS = {
    "vatan": parse_vatan,
    "sinerji": parse_sinerji,
    "incehesap": parse_incehesap,
    "tebilon": parse_tebilon,
    "itopya": parse_itopya,
    "woocommerce": parse_woocommerce,
    "amazon": parse_amazon,
    "trendyol": parse_trendyol,
    "akakce": parse_akakce,
    "genel": parse_genel,
}
_DESEN_ALAN = {"woocommerce", "amazon", "trendyol", "akakce", "genel"}


def sayfa_ayristir(parser_adi, html, url, urun_link_deseni=None):
    """
    [TR] Tek bir sayfayı ayrıştırır. Süreç havuzunda (ProcessPool) çalıştırılabilir; hata fırlatmaz.
    [EN] Parses a single page. Safe to run in a process pool; never raises.

    Returns:
        tuple: (urunler: dict, meta: dict) - meta: {"toplam_sayfa": int|None, "hata": str|None}
    """
    meta = {"toplam_sayfa": None, "hata": None}
    try:
        fonksiyon = PARSERS[parser_adi]
        if parser_adi in _DESEN_ALAN:
            urunler = fonksiyon(html, url, urun_link_deseni)
        else:
            urunler = fonksiyon(html, url)
        if parser_adi == "itopya":
            meta["toplam_sayfa"] = itopya_toplam_sayfa(html)
        return urunler, meta
    except Exception as e:  # [TR] Bozuk HTML botu düşürmesin. / [EN] Broken HTML must not kill the bot.
        meta["hata"] = f"{type(e).__name__}: {e}"
        return {}, meta


# =====================================================================================
# [TR] ESKİ API (geriye dönük uyumluluk; tek sayfa, senkron) / [EN] LEGACY API (single page, sync)
# =====================================================================================

def _eski_getir(url, etiket, headers=None):
    from curl_cffi import requests as curl_requests
    try:
        response = curl_requests.get(url, impersonate="chrome", headers=headers, timeout=15)
        if response.status_code == 403:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {etiket} HATA: 403 Forbidden.")
            return None
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {etiket} HATA: {e}")
        return None


def _tebilon_basliklari():
    import config
    headers = {"User-Agent": config.TEBILON_USER_AGENT or config.HEADERS["User-Agent"]}
    if config.TEBILON_COOKIE:
        headers["Cookie"] = config.TEBILON_COOKIE
    return headers


def ramleri_getir(url):
    """[TR] (Eski) Vatan sayfasını çekip ayrıştırır. / [EN] (Legacy) Fetch + parse a Vatan page."""
    html = _eski_getir(url, "Vatan")
    return parse_vatan(html, url) if html else {}


def scrape_sinerji(url):
    html = _eski_getir(url, "Sinerji")
    return parse_sinerji(html, url) if html else {}


def scrape_incehesap(url):
    html = _eski_getir(url, "İncehesap")
    return parse_incehesap(html, url) if html else {}


def scrape_tebilon(url):
    html = _eski_getir(url, "Tebilon", _tebilon_basliklari())
    return parse_tebilon(html, url) if html else {}


def scrape_itopya(url):
    html = _eski_getir(url, "Itopya")
    return parse_itopya(html, url) if html else {}


def scrape_site(site_name, site_config):
    """
    [TR] (Eski) Sitenin adına göre ilgili kazıma fonksiyonunu tetikler; sadece RAM ürünlerini döndürür.
    [EN] (Legacy) Triggers the relevant scraper based on the site name; returns RAM products only.
    """
    url = site_config["all_url"]
    fonksiyonlar = {"vatan": ramleri_getir, "sinerji": scrape_sinerji, "incehesap": scrape_incehesap,
                    "tebilon": scrape_tebilon, "itopya": scrape_itopya}
    if site_name not in fonksiyonlar:
        return {}
    urunler = fonksiyonlar[site_name](url)
    # [TR] RAM olmayan vitrin/kampanya ürünlerini ayıkla. / [EN] Filter out non-RAM promo/carousel products.
    return {kod: veri for kod, veri in urunler.items() if ram_urunu_mu(veri.get("isim", ""))}
