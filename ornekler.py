"""
[TR] Örnek Sayfa Üretici / [EN] Sample Page Generator
[TR] Her ayrıştırıcının beklediği HTML yapısında sahte kategori sayfaları üretir. İnternet olmadan
     birim testleri ve benchmark.py'nin CPU ölçümü bunları kullanır. İtopya için depodaki gerçek sayfa
     (itopya_temp.html) kullanılır.
[EN] Generates fake category pages in the HTML structure each parser expects. Used by offline unit tests
     and benchmark.py's CPU measurement. For İtopya the real page in the repo (itopya_temp.html) is used.
"""

import html as _html
import json
import os
import random

KOK = os.path.dirname(os.path.abspath(__file__))
ITOPYA_ORNEK = os.path.join(KOK, "itopya_temp.html")

_SSD = ["Samsung 990 EVO Plus {c} NVMe M.2 SSD (Okuma 7150MB / Yazma 6300MB)",
        "Kingston NV3 {c} PCIe 4.0 NVMe M.2 SSD", "WD Black SN850X {c} Soğutuculu NVMe M.2 SSD",
        "Crucial P3 Plus {c} PCIe Gen4 NVMe M.2 SSD", "Lexar NM790 {c} PCIe 4.0 NVMe SSD",
        "Kioxia Exceria Plus G3 {c} NVMe M.2 SSD", "Samsung 870 EVO {c} 2.5\" SATA 3.0 SSD"]
_ANAKART = ["MSI PRO B650M-P DDR5 AM5 mATX Anakart", "ASUS TUF GAMING B850-PLUS WIFI AM5 ATX Anakart",
            "GIGABYTE B760M DS3H DDR4 LGA1700 mATX Anakart", "ASROCK B650M PRO RS WIFI AM5 Anakart",
            "MSI MAG X870 TOMAHAWK WIFI AM5 ATX Anakart", "ASUS PRIME Z890-P WIFI LGA1851 ATX Anakart",
            "GIGABYTE B650 AORUS ELITE AX DDR5 ATX Anakart"]
_RAM = ["Kingston Fury Beast {c} DDR5 6000MHz CL36 RAM", "Corsair Vengeance RGB {c} (2x16GB) DDR5 6400MHz CL32 Ram",
        "G.Skill Trident Z5 {c} DDR5 6000MHz CL30 Ram", "Lexar Thor {c} DDR5 5600MHz CL40 Ram"]
_KAPASITE = {"ssd": ["500GB", "1TB", "2TB", "4TB"], "ram": ["16GB", "32GB", "64GB"], "anakart": [""]}
_SABLON = {"ssd": _SSD, "anakart": _ANAKART, "ram": _RAM}


def urun_listesi(kategori="ssd", adet=24, baslangic_fiyat=1500.0, artis=650.0, tohum=7, on_ek="P"):
    """[TR] Fiyata göre artan sıralı sahte ürünler: [(kod, isim, fiyat)]. / [EN] Ascending fake products."""
    rnd = random.Random(tohum)
    urunler = []
    for i in range(adet):
        sablon = rnd.choice(_SABLON[kategori])
        isim = sablon.format(c=rnd.choice(_KAPASITE[kategori]))
        urunler.append((f"{on_ek}{1000 + i}", isim, round(baslangic_fiyat + i * artis, 2)))
    return urunler


def _tr(fiyat, kurus=True):
    metin = f"{fiyat:,.2f}" if kurus else f"{fiyat:,.0f}"
    return metin.replace(",", "X").replace(".", ",").replace("X", ".")


def _e(x):
    return _html.escape(x, quote=True)


def vatan_sayfasi(urunler):
    kartlar = "".join(
        f'<div class="product-list product-list--list-page"><a class="product-list-link" href="/{k.lower()}.html">'
        f'<div class="slider-img"><img class="lazyimg" data-src="https://cdn.vatan.test/{k}.jpg" src="/x.gif"></div></a>'
        f'<div class="product-list__content"><div class="product-list__product-name"><h3>{_e(i)}</h3></div>'
        f'<div class="product-list__product-code">{k}</div><div class="product-list__cost">'
        f'<span class="product-list__price">{_tr(f, kurus=False)}</span><span class="product-list__currency">TL</span>'
        f'</div></div></div>' for k, i, f in urunler)
    return f"<html><body><div class='wrapper-product'>{kartlar}</div></body></html>"


def sinerji_sayfasi(urunler):
    kartlar = "".join(
        f'<article class="product"><div class="img"><img src="https://cdn.sinerji.test/{k}.jpg"></div>'
        f'<div class="title"><a href="/{k.lower()}-p-{k}">{_e(i)}</a><span class="sku">SKU: {k}</span></div>'
        f'<div class="priceWrapper"><span class="price">{_tr(f)} ₺</span></div>'
        f'<button class="addToCart" value="{k}">Sepete Ekle</button></article>' for k, i, f in urunler)
    oneri = ('<div class="row productList"><article class="product"><div class="title"><a href="/m-p-9">'
             'Samsung Odyssey G5 27" Monitör</a></div><span class="price">9.999,00 ₺</span></article></div>')
    return f"<html><body><section class='productList'>{kartlar}</section>{oneri}</body></html>"


def incehesap_sayfasi(urunler):
    kartlar = []
    for k, i, f in urunler:
        veri = _e(json.dumps({"id": int(k[1:]), "name": i, "price": f}, ensure_ascii=False))
        ga = _e(json.dumps({"url": f"/{k.lower()}-fiyati-{k[1:]}/", "image": f"/resim/{k}.jpg"}))
        kartlar.append(f'<a class="product d-flex" data-product="{veri}" data-gaitem="{ga}" href="/{k.lower()}/">'
                       f'<img src="/resim/{k}.jpg"><span>{_e(i)}</span></a>')
    return f"<html><body><div id='product-grid'>{''.join(kartlar)}</div></body></html>"


def tebilon_sayfasi(urunler):
    kartlar = "".join(
        f'<div class="showcase__product"><div class="showcase__image"><a class="ajaxLink" href="/{k.lower()}/" '
        f'title="{_e(i)}"><img class="primaryImage" src="/img/{k}.jpg"></a><span>{k}</span></div>'
        f'<div class="showcase__title desktopShow"><a href="/{k.lower()}/">{_e(i)}</a></div>'
        f'<div class="newPrice">{_tr(f)} TL</div></div>' for k, i, f in urunler)
    return f"<html><body>{kartlar}</body></html>"


def itopya_sayfasi():
    with open(ITOPYA_ORNEK, encoding="utf-8-sig") as dosya:
        return dosya.read()


def woocommerce_sayfasi(urunler, stok_disi=()):
    kartlar = []
    for k, i, f in urunler:
        no = k[1:]
        stok = "outofstock" if k in stok_disi else "instock"
        kartlar.append(
            f'<li class="product type-product post-{no} status-publish {stok} product_cat-ssd">'
            f'<a href="https://www.gaming.gen.tr/urun/{no}/{k.lower()}-slug/" class="woocommerce-LoopProduct-link '
            f'woocommerce-loop-product__link"><img src="https://cdn.gg.test/{k}.jpg" alt="{_e(i)}">'
            f'<h2 class="woocommerce-loop-product__title">{_e(i)}</h2><span class="price">'
            f'<del><span class="woocommerce-Price-amount amount"><bdi>{_tr(f * 1.2)}&nbsp;₺</bdi></span></del> '
            f'<ins><span class="woocommerce-Price-amount amount"><bdi>{_tr(f)}&nbsp;₺</bdi></span></ins></span></a>'
            f'<a href="?add-to-cart={no}" data-product_id="{no}" class="button add_to_cart_button">Sepete ekle</a></li>')
    return f"<html><body><ul class='products columns-4'>{''.join(kartlar)}</ul></body></html>"


def amazon_sayfasi(urunler):
    kartlar = "".join(
        f'<div data-asin="B0{k[1:]:0>8}" data-index="{n}" data-component-type="s-search-result" class="s-result-item">'
        f'<img class="s-image" src="https://m.media-amazon.test/{k}.jpg">'
        f'<a class="a-link-normal" href="/{k}-slug/dp/B0{k[1:]:0>8}/ref=sr_1_{n}"><h2 aria-label="{_e(i)}" '
        f'class="a-size-base-plus"><span>{_e(i)}</span></h2></a>'
        f'<span class="a-price" data-a-size="xl"><span class="a-offscreen">{_tr(f)} TL</span>'
        f'<span aria-hidden="true"><span class="a-price-whole">{_tr(f, False)}<span class="a-price-decimal">,</span>'
        f'</span><span class="a-price-fraction">00</span></span></span>'
        f'<span class="a-price a-text-price" data-a-strike="true"><span class="a-offscreen">{_tr(f * 1.3)} TL</span></span>'
        f'</div>' for n, (k, i, f) in enumerate(urunler, 1))
    return f"<html><body><div class='s-main-slot'>{kartlar}</div></body></html>"


def trendyol_sayfasi(urunler):
    kartlar = "".join(
        f'<div class="p-card-wrppr with-campaign-view" data-id="{k[1:]}"><div class="p-card-chldrn-cntnr">'
        f'<a href="/marka/{k.lower()}-p-{k[1:]}0000?boutiqueId=1"><img class="p-card-img" src="https://cdn.dsmcdn.com/{k}.jpg">'
        f'<div class="prdct-desc-cntnr-ttl-w"><span class="prdct-desc-cntnr-ttl">{_e(i.split()[0])}</span>'
        f'<span class="prdct-desc-cntnr-name">{_e(" ".join(i.split()[1:]))}</span></div>'
        f'<div class="prc-box-dscntd">{_tr(f, False)} TL</div></a></div></div>' for k, i, f in urunler)
    return f"<html><body><div class='prdct-cntnr-wrppr'>{kartlar}</div></body></html>"


def akakce_sayfasi(urunler):
    kartlar = "".join(
        f'<li data-pr="{k[1:]}"><a href="/ssd/en-ucuz-{k.lower()}-fiyati,{k[1:]}.html" title="{_e(i)}">'
        f'<span class="w_v8"><img src="https://cdn.akakce.test/{k}.jpg" alt=""></span><h3 class="pn_v8">{_e(i)}</h3>'
        f'<span class="pt_v8">{_tr(f, False)}<span class="pt_v8b">,00 TL</span></span></a></li>' for k, i, f in urunler)
    return f"<html><body><ul id='APL' class='pl_v9'>{kartlar}</ul></body></html>"


def genel_kart_sayfasi(urunler):
    """[TR] Hepsiburada benzeri, sınıf adları belirsiz kartlar. / [EN] Hepsiburada-like cards with opaque classes."""
    kartlar = "".join(
        f'<li class="productListContent-zAP0Y5msy8OHn5z7T_K_"><div class="moria-ProductCard-gyqBb">'
        f'<a href="https://www.hepsiburada.com/{k.lower()}-p-HBCV0000{k[1:]}XY" title="{_e(i)}">'
        f'<img src="https://productimages.hepsiburada.test/{k}.jpg" alt="{_e(i)}"><h3 data-test-id="product-card-name">{_e(i)}</h3></a>'
        f'<div data-test-id="price-prev-price">{_tr(f * 1.25)} TL</div>'
        f'<div data-test-id="price-current-price">{_tr(f)} TL</div>'
        f'<div class="campaign">₺250 indirim kuponu</div></div></li>' for k, i, f in urunler)
    return f"<html><body><ul class='productListContent-wrapper'>{kartlar}</ul></body></html>"


def jsonld_sayfasi(urunler):
    liste = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": n, "item": {
            "@type": "Product", "name": i, "sku": k, "image": f"https://cdn.test/{k}.jpg",
            "url": f"https://www.teknosa.com/{k.lower()}-p-{k[1:]}00000",
            "offers": {"@type": "Offer", "price": f"{f:.2f}", "priceCurrency": "TRY",
                       "availability": "https://schema.org/InStock"}}}
        for n, (k, i, f) in enumerate(urunler, 1)]}
    return f'<html><head><script type="application/ld+json">{json.dumps(liste, ensure_ascii=False)}</script></head><body></body></html>'


def gomulu_json_sayfasi(urunler):
    durum = {"search": {"products": [
        {"id": int(k[1:]), "name": i, "brand": {"name": i.split()[0]},
         "url": f"/{i.split()[0].lower()}/{k.lower()}-p-{k[1:]}0000",
         "images": [f"/ty{k[1:]}/product/{k}.jpg"], "price": {"sellingPrice": f, "originalPrice": round(f * 1.2, 2)}}
        for k, i, f in urunler], "totalCount": len(urunler)}}
    return (f"<html><body><div id='app'></div><script>window.__SEARCH_APP_INITIAL_STATE__ = "
            f"{json.dumps(durum, ensure_ascii=False)};window.x=1;</script></body></html>")


SAYFA_URETICILERI = {
    "vatan": vatan_sayfasi, "sinerji": sinerji_sayfasi, "incehesap": incehesap_sayfasi,
    "tebilon": tebilon_sayfasi, "woocommerce": woocommerce_sayfasi, "amazon": amazon_sayfasi,
    "trendyol": trendyol_sayfasi, "akakce": akakce_sayfasi, "genel": genel_kart_sayfasi,
}

# [TR] Benchmark için her ayrıştırıcıya örnek (parser, link deseni, html). / [EN] Benchmark samples per parser.
LINK_DESENLERI = {
    "woocommerce": r"/urun/(\d+)/", "amazon": r"/dp/([A-Z0-9]{10})", "trendyol": r"-p-(\d{5,})",
    "akakce": r"en-ucuz-[^,\"']+,(\d+)\.html", "genel": r"-pm?-([A-Za-z0-9]{8,})(?:[/?#\"']|$)",
}


def benchmark_ornekleri(adet=24):
    ornekler = []
    if os.path.exists(ITOPYA_ORNEK):
        ornekler.append(("itopya", None, itopya_sayfasi(), "https://www.itopya.com/rambellek_k10"))
    for parser, uretici in SAYFA_URETICILERI.items():
        ornekler.append((parser, LINK_DESENLERI.get(parser), uretici(urun_listesi("ssd", adet)), "https://example.test/"))
    return ornekler
