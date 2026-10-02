"""
[TR] Streamlit Web Dashboard Modülü / [EN] Streamlit Web Dashboard Module
[TR] RAM, SSD ve anakart fiyatlarını; kategori, site, bütçe ve teknik özellik filtreleriyle gösterir. Fırsatlar,
     bütçe planlayıcı ve site sağlığı / tarama hızı sekmeleri içerir. / [EN] Shows RAM, SSD and motherboard prices
     with category, site, budget and spec filters, plus deals, a budget planner and site health / scan speed tabs.

[TR] Performans: son fiyatlar ürün tablosunda tutulduğu için tüm fiyat geçmişi okunmaz; grafikler sadece
     açıldığında ilgili ürünün geçmişini (indeksli sorguyla) yükler; galeri sayfalıdır.
[EN] Performance: latest prices live in the products table so the full history is never read; charts load one
     product's history (indexed query) only when opened; the gallery is paginated.
"""

import datetime
import json
import math

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import categories
import config
import database

st.set_page_config(page_title="Donanım Fiyat Takip Paneli", page_icon="📈", layout="wide")

# [TR] Sayfayı her 120 saniyede bir otomatik yenile / [EN] Auto-refresh page every 120 seconds
st_autorefresh(interval=120000, key="datarefresh")

KATEGORI_SECENEKLERI = {"Tümü": None, "🧠 RAM": "ram", "💾 SSD": "ssd", "🧩 Anakart": "anakart"}
SAYFA_BOYUTU = 24
YER_TUTUCU = "https://images.unsplash.com/photo-1591488320449-011701bb6704?q=80&w=300&auto=format&fit=crop"
OZELLIK_ALANLARI = ["kapasite_gb", "arayuz", "pcie_gen", "form", "okuma_mbs", "platform", "soket", "chipset",
                    "bellek", "wifi", "hiz_mhz", "cl", "tip", "kit"]


def tl(deger, kurus=True):
    if deger is None or (isinstance(deger, float) and math.isnan(deger)):
        return "-"
    metin = f"{deger:,.2f}" if kurus else f"{deger:,.0f}"
    return metin.replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


def kapasite_etiketi(kategori, gb):
    if not gb or (isinstance(gb, float) and math.isnan(gb)):
        return None
    gb = float(gb)
    if kategori == "ssd":
        for sinir, etiket in ((300, "≤256 GB"), (750, "512 GB"), (1500, "1 TB"), (3000, "2 TB"), (6000, "4 TB")):
            if gb < sinir:
                return etiket
        return "8 TB+"
    return f"{gb:g} GB"


@st.cache_resource
def veritabanini_hazirla():
    try:
        database.init_db()
    except Exception as e:  # [TR] Bot aynı anda geçiş yapıyor olabilir. / [EN] The bot may be migrating too.
        print(f"init_db (dashboard): {e}")
    return True


@st.cache_data(ttl=60, show_spinner=False)
def urunleri_yukle():
    satirlar = database.urun_tablosu()
    if not satirlar:
        return pd.DataFrame()
    df = pd.DataFrame(satirlar)
    df["site"] = [s or config.site_bul(k, u) for s, k, u in zip(df["site"], df["code"], df["url"])]
    df["category"] = [c or categories.kategori_tahmin_et(n) for c, n in zip(df["category"], df["name"])]
    df["oz"] = [json.loads(s) if isinstance(s, str) and s else categories.ozellikleri_cikar(c, n)
                for s, c, n in zip(df["specs"], df["category"], df["name"])]
    df["fiyat"] = df["last_price"].fillna(df["base_price"])
    df["stok"] = df["in_stock"].fillna(0).astype(int)
    df["site_adi"] = df["site"].map(config.site_adi)
    df["site_renk"] = df["site"].map(lambda s: config.SITES.get(s, {}).get("renk", "#7F8C8D"))
    birimler = [categories.birim_fiyat(c, f, o) for c, f, o in zip(df["category"], df["fiyat"], df["oz"])]
    df["birim"] = pd.to_numeric(pd.Series([b[0] for b in birimler], index=df.index), errors="coerce")
    df["birim_ad"] = [b[1] for b in birimler]
    df["ozet"] = [categories.ozet_metni(c, o) for c, o in zip(df["category"], df["oz"])]
    for alan in OZELLIK_ALANLARI:
        df[alan] = df["oz"].map(lambda o: o.get(alan))
    df["kapasite"] = [kapasite_etiketi(c, g) for c, g in zip(df["category"], df["kapasite_gb"])]
    return df


@st.cache_data(ttl=120, show_spinner=False)
def gecmis_yukle(code):
    return pd.DataFrame(database.fiyat_gecmisi(code))


@st.cache_data(ttl=300, show_spinner=False)
def pencere_yukle(gun):
    baslangic = database.get_tr_time() - datetime.timedelta(days=gun)
    return database.pencere_fiyatlari(baslangic)


@st.cache_data(ttl=300, show_spinner=False)
def en_dusukler_yukle():
    return database.tum_zamanlar_en_dusuk()


@st.cache_data(ttl=60, show_spinner=False)
def saglik_yukle():
    return pd.DataFrame(database.hedef_durumlari()), pd.DataFrame(database.tarama_istatistikleri(300))


def grafik(code):
    """[TR] Ürünün fiyat geçmişi grafiği (sadece açılınca yüklenir). / [EN] Price history chart (lazy)."""
    gecmis = gecmis_yukle(code)
    if gecmis.empty:
        st.info("Henüz geçmiş yok / No history yet")
        return
    gecmis["Stok Durumu"] = gecmis["in_stock"].apply(lambda x: 'Var' if x == 1 else 'Yok')
    fig = px.line(gecmis, x='timestamp', y='price', markers=True, line_shape='hv',
                  labels={"timestamp": "Zaman", "price": "Fiyat (TL)"}, hover_data=["Stok Durumu"])
    son = pd.Timestamp(database.get_tr_time())
    ilk = pd.Timestamp(gecmis["timestamp"].min())
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=60), height=330,
        xaxis=dict(
            # [TR] Varsayılan olarak son 7 günü göster / [EN] Show the last 7 days by default
            range=[max(ilk, son - pd.Timedelta(days=7)), son],
            rangeselector=dict(buttons=[
                dict(count=1, label="1 Gün", step="day", stepmode="backward"),
                dict(count=7, label="1 Hafta", step="day", stepmode="backward"),
                dict(count=1, label="1 Ay", step="month", stepmode="backward"),
                dict(step="all", label="Tümü"),
            ], y=-0.3, x=0.5, xanchor="center", yanchor="top"),
            type="date"))
    # [TR] Mobildeki zoom alet çantası (Modebar) ve fare tekerleğiyle zoom (scrollZoom) aktif edildi.
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True},
                    key=f"chart_{code}")


def _md(metin):
    return str(metin).replace("[", "\\[").replace("]", "\\]").replace("*", "\\*").replace("_", "\\_")


def urun_karti(r):
    img_url = r["image_url"] if isinstance(r["image_url"], str) and r["image_url"].startswith("http") else YER_TUTUCU
    st.image(img_url, use_column_width=True)
    ad = r["name"] if len(r["name"]) < 75 else r["name"][:72] + "..."
    st.markdown(f"**[{_md(ad)}]({r['url']})**")
    kat = config.KATEGORILER.get(r["category"], {})
    st.markdown(
        f"<span style='background-color:{r['site_renk']};color:white;padding:2px 6px;border-radius:4px;"
        f"font-size:11px;font-weight:bold;'>{r['site_adi']}</span> "
        f"<span style='background-color:#34495E;color:white;padding:2px 6px;border-radius:4px;font-size:11px;'>"
        f"{kat.get('emoji', '')} {kat.get('ad', r['category'])}</span>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:#FF4B4B;margin-top:5px;margin-bottom:0px;'>{tl(r['fiyat'])}</h3>",
                unsafe_allow_html=True)
    alt = []
    if pd.notna(r["birim"]):
        alt.append(f"{tl(r['birim'], kurus=False).replace(' TL', '')} {r['birim_ad']}")
    if r["ozet"]:
        alt.append(r["ozet"])
    if alt:
        st.caption(" | ".join(alt))
    stok_renk, stok_metin = ("green", "Stokta Var") if r["stok"] == 1 else ("red", "Stokta Yok")
    st.markdown(f"<p style='color:{stok_renk};font-size:14px;margin-bottom:0'>{stok_metin}</p>", unsafe_allow_html=True)
    if st.toggle("📉 Grafiği Gör / View Chart", key=f"tg_{r['code']}"):
        grafik(r["code"])


def kenar_cubugu(df):
    """[TR] Filtre seçimleri. / [EN] Filter selections."""
    sb = st.sidebar
    sb.header("🔎 Filtreler / Filters")
    kat_etiket = sb.radio("Kategori / Category", list(KATEGORI_SECENEKLERI), horizontal=True)
    kategori = KATEGORI_SECENEKLERI[kat_etiket]
    arama = sb.text_input("Ürün Ara / Search", "")
    site_secenek = sorted(df["site_adi"].dropna().unique())
    siteler = sb.multiselect("Siteler / Sites", site_secenek, default=site_secenek)
    ust = int(math.ceil(max(config.BUTCE, df["fiyat"].max() if not df.empty else config.BUTCE) / 500) * 500)
    butce = int(config.kategori_butcesi(kategori) if kategori else config.BUTCE)
    fiyat_araligi = sb.slider("Fiyat aralığı (TL) / Price range", 0, ust, (0, min(butce, ust)), step=250,
                              format="%d TL")
    sadece_stok = sb.checkbox("📦 Sadece Stoktakiler / In stock only", value=True)
    guncel = sb.checkbox("🕒 Eski kayıtları gizle (24 saattir görülmeyen)", value=True)
    oz = {}
    if kategori:
        alt = df[df["category"] == kategori]
        with sb.expander("⚙️ Teknik özellikler / Specs", expanded=False):
            def coklu(etiket, alan, sirala=None):
                secenekler = sorted(alt[alan].dropna().unique(), key=sirala)
                return st.multiselect(etiket, secenekler) if len(secenekler) else []
            if kategori == "ssd":
                oz["kapasite"] = coklu("Kapasite", "kapasite",
                                       sirala=lambda x: ["≤256 GB", "512 GB", "1 TB", "2 TB", "4 TB", "8 TB+"].index(x))
                oz["arayuz"] = coklu("Arayüz / Interface", "arayuz")
                oz["pcie_gen"] = coklu("PCIe nesli", "pcie_gen")
                oz["form"] = coklu("Form faktörü", "form")
            elif kategori == "anakart":
                oz["platform"] = coklu("Platform", "platform")
                oz["soket"] = coklu("Soket", "soket")
                oz["chipset"] = coklu("Chipset", "chipset")
                oz["bellek"] = coklu("Bellek tipi", "bellek")
                oz["form"] = coklu("Form faktörü", "form")
                oz["wifi"] = [True] if st.checkbox("Sadece Wi-Fi'li") else []
            elif kategori == "ram":
                oz["kapasite"] = coklu("Toplam kapasite", "kapasite", sirala=lambda x: float(x.split()[0]))
                hizlar = alt["hiz_mhz"].dropna()
                if not hizlar.empty and hizlar.max() > hizlar.min():
                    oz["_min_hiz"] = st.slider("En az hız (MHz)", int(hizlar.min()), int(hizlar.max()), int(hizlar.min()), step=200)
                oz["form"] = coklu("Form", "form")
    siralama = sb.selectbox("⇅ Sırala / Sort by", ["Fiyat (Artan)", "Fiyat (Azalan)", "Birim fiyat (TL/TB, TL/GB)",
                                                    "En yeni ürünler", "Son değişenler"])
    return {"kategori": kategori, "arama": arama, "siteler": siteler, "fiyat": fiyat_araligi,
            "stok": sadece_stok, "guncel": guncel, "oz": oz, "siralama": siralama}


def filtrele(df, f):
    if df.empty:
        return df
    sonuc = df
    if f["kategori"]:
        sonuc = sonuc[sonuc["category"] == f["kategori"]]
    if f["siteler"]:
        sonuc = sonuc[sonuc["site_adi"].isin(f["siteler"])]
    if f["arama"]:
        for kelime in f["arama"].split():
            sonuc = sonuc[sonuc["name"].str.contains(kelime, case=False, na=False, regex=False)]
    sonuc = sonuc[(sonuc["fiyat"] >= f["fiyat"][0]) & (sonuc["fiyat"] <= f["fiyat"][1])]
    if f["stok"]:
        sonuc = sonuc[sonuc["stok"] == 1]
    if f["guncel"]:
        esik = pd.Timestamp(database.get_tr_time() - datetime.timedelta(hours=24))
        son = pd.to_datetime(sonuc["last_seen"]).fillna(pd.to_datetime(sonuc["first_seen"]))
        sonuc = sonuc[son >= esik]
    for alan, degerler in f["oz"].items():
        if alan == "_min_hiz":
            sonuc = sonuc[sonuc["hiz_mhz"].fillna(0) >= degerler]
        elif degerler:
            sonuc = sonuc[sonuc[alan].isin(degerler)]
    return siralama_uygula(sonuc, f["siralama"])


def siralama_uygula(df, siralama):
    if siralama == "Fiyat (Azalan)":
        return df.sort_values("fiyat", ascending=False)
    if siralama.startswith("Birim"):
        return df.sort_values(["birim", "fiyat"], ascending=True, na_position="last")
    if siralama == "En yeni ürünler":
        return df.sort_values("first_seen", ascending=False)
    if siralama == "Son değişenler":
        return df.sort_values("last_change", ascending=False, na_position="last")
    return df.sort_values("fiyat", ascending=True)


def tablo_goster(df, ek_sutunlar=None):
    sutunlar = ["image_url", "name", "site_adi", "category", "fiyat", "birim", "stok", "ozet", "url", "last_change"]
    sutunlar += ek_sutunlar or []
    if df["birim"].isna().all():
        sutunlar.remove("birim")
    gorunum = df[sutunlar].copy()
    gorunum["stok"] = gorunum["stok"] == 1
    gorunum["category"] = gorunum["category"].map(lambda k: config.KATEGORILER.get(k, {}).get("ad", k))
    st.dataframe(gorunum, hide_index=True, use_container_width=True, height=min(900, 40 + 36 * len(gorunum)),
                 column_config={
                     "image_url": st.column_config.ImageColumn("Görsel", width="small"),
                     "name": st.column_config.TextColumn("Ürün", width="large"),
                     "site_adi": "Site", "category": "Kategori",
                     "fiyat": st.column_config.NumberColumn("Fiyat", format="%.0f TL"),
                     "birim": st.column_config.NumberColumn("Birim (TL/TB · TL/GB)", format="%.0f"),
                     "stok": st.column_config.CheckboxColumn("Stok"),
                     "ozet": "Özellikler",
                     "url": st.column_config.LinkColumn("Link", display_text="Aç ↗"),
                     "last_change": st.column_config.DatetimeColumn("Son değişim", format="DD.MM HH:mm"),
                     "dusus_yuzde": st.column_config.NumberColumn("Düşüş %", format="%.1f"),
                     "max_fiyat": st.column_config.NumberColumn("Dönem en yüksek", format="%.0f TL"),
                 })


def urunler_sekmesi(sonuc, f):
    ust = st.columns([3, 1])
    ust[0].markdown(f"**{len(sonuc)}** ürün listeleniyor / products listed")
    gorunum = ust[1].radio("Görünüm", ["Galeri", "Tablo"], horizontal=True, label_visibility="collapsed")
    if sonuc.empty:
        st.info("Filtrelere uyan ürün yok. / No products match the filters.")
        return
    if gorunum == "Tablo":
        tablo_goster(sonuc)
        return
    sayfa_sayisi = max(1, math.ceil(len(sonuc) / SAYFA_BOYUTU))
    # [TR] Filtre değişince ilk sayfaya dön. / [EN] Go back to page 1 when filters change.
    imza = json.dumps({k: v for k, v in f.items()}, default=str, sort_keys=True)
    if st.session_state.get("_filtre_imza") != imza:
        st.session_state["_filtre_imza"] = imza
        st.session_state["sayfa_no"] = 1
    st.session_state["sayfa_no"] = min(st.session_state.get("sayfa_no", 1), sayfa_sayisi)
    sayfa = st.number_input(f"Sayfa (toplam {sayfa_sayisi})", min_value=1, max_value=sayfa_sayisi, key="sayfa_no")
    dilim = sonuc.iloc[(sayfa - 1) * SAYFA_BOYUTU: sayfa * SAYFA_BOYUTU]
    sutunlar = st.columns(4)
    # [TR] Sıralama sonrası DataFrame indeksleri karışık olduğundan grid için sıra numarası (enumerate) kullanılır.
    # [EN] DataFrame labels are shuffled after sorting, so use the positional counter (enumerate) for the grid.
    for sira, (_, r) in enumerate(dilim.iterrows()):
        with sutunlar[sira % 4]:
            with st.container(border=True):
                urun_karti(r)


def firsatlar_sekmesi(sonuc):
    st.markdown("Seçili filtrelerdeki stoktaki ürünlerin, seçilen dönemdeki en yüksek fiyatına göre düşüşü. "
                "/ Drop versus the period's highest price for in-stock products in the current filters.")
    secim = st.radio("Dönem / Period", ["24 saat", "7 gün", "30 gün"], index=1, horizontal=True)
    gun = {"24 saat": 1, "7 gün": 7, "30 gün": 30}[secim]
    pencere = pencere_yukle(gun)
    df = sonuc[sonuc["stok"] == 1].copy()
    if df.empty:
        st.info("Ürün yok. / No products.")
        return
    df["max_fiyat"] = df["code"].map(lambda k: (pencere.get(k) or (None, None))[0])
    df["max_fiyat"] = df[["max_fiyat", "fiyat"]].max(axis=1)
    df["dusus_yuzde"] = (df["max_fiyat"] - df["fiyat"]) / df["max_fiyat"] * 100
    firsat = df[df["dusus_yuzde"] >= 1].sort_values("dusus_yuzde", ascending=False).head(60)
    st.subheader(f"🔥 {secim} içinde ucuzlayanlar ({len(firsat)})")
    if firsat.empty:
        st.info("Bu dönemde fiyatı düşen ürün yok. / No price drops in this period.")
    else:
        tablo_goster(firsat, ["max_fiyat", "dusus_yuzde"])
    en_dusuk = en_dusukler_yukle()
    dip = df[df.apply(lambda r: en_dusuk.get(r["code"]) is not None and r["fiyat"] <= en_dusuk[r["code"]]
                      and r["max_fiyat"] > r["fiyat"], axis=1)]
    st.subheader(f"📉 Tüm zamanların en düşük fiyatında ({len(dip)})")
    if not dip.empty:
        tablo_goster(dip.sort_values("dusus_yuzde", ascending=False).head(60), ["max_fiyat", "dusus_yuzde"])


def planlayici_sekmesi(df):
    st.markdown("Seçtiğiniz parçalar için kısıtlara uyan **stoktaki** en uygun ürünleri bulur ve toplamı bütçeyle "
                "karşılaştırır. / Finds the best in-stock parts that satisfy the constraints and compares the total "
                "with your budget.")
    c = st.columns(4)
    toplam_butce = c[0].number_input("Toplam bütçe (TL)", min_value=0.0, value=float(config.BUTCE), step=500.0)
    dahil = {"anakart": c[1].checkbox("🧩 Anakart", True), "ram": c[2].checkbox("🧠 RAM", True),
             "ssd": c[3].checkbox("💾 SSD", True)}
    k = st.columns(4)
    olcut = k[0].radio("Seçim ölçütü", ["En ucuz", "En iyi birim fiyat"], help="Birim fiyat: SSD için TL/TB, RAM için TL/GB")
    stok = df[(df["stok"] == 1)]
    platformlar = ["Farketmez"] + sorted(stok.loc[stok["category"] == "anakart", "platform"].dropna().unique())
    platform = k[1].selectbox("Platform", platformlar)
    soketler = ["Farketmez"] + sorted(stok.loc[stok["category"] == "anakart", "soket"].dropna().unique())
    soket = k[2].selectbox("Soket", soketler)
    ddr5 = k[3].checkbox("DDR5 uyumlu (anakart DDR5 + DDR5 RAM)", True)
    s = st.columns(3)
    ssd_min = s[0].select_slider("SSD en az", options=[256, 512, 1000, 2000, 4000], value=1000,
                                 format_func=lambda g: f"{g // 1000} TB" if g >= 1000 else f"{g} GB")
    nvme = s[1].checkbox("Sadece NVMe SSD", True)
    ram_min = s[2].select_slider("RAM en az (GB)", options=[8, 16, 32, 48, 64, 96], value=32)

    adaylar = {}
    if dahil["anakart"]:
        a = stok[stok["category"] == "anakart"]
        if platform != "Farketmez":
            a = a[a["platform"] == platform]
        if soket != "Farketmez":
            a = a[a["soket"] == soket]
        if ddr5:
            a = a[a["bellek"] == "DDR5"]
        adaylar["anakart"] = a.sort_values("fiyat")
    if dahil["ram"]:
        r = stok[(stok["category"] == "ram") & (stok["kapasite_gb"].fillna(0) >= ram_min)]
        r = r[r["form"] != "SODIMM"]
        if ddr5:
            r = r[r["tip"].fillna("DDR5") == "DDR5"]
        adaylar["ram"] = r.sort_values(["birim", "fiyat"] if olcut != "En ucuz" else ["fiyat"])
    if dahil["ssd"]:
        d = stok[(stok["category"] == "ssd") & (stok["kapasite_gb"].fillna(0) >= ssd_min * 0.94)]
        if nvme:
            d = d[d["arayuz"] == "NVMe"]
        adaylar["ssd"] = d.sort_values(["birim", "fiyat"] if olcut != "En ucuz" else ["fiyat"])

    secilen = {kat: liste.iloc[0] for kat, liste in adaylar.items() if not liste.empty}
    toplam = sum(r["fiyat"] for r in secilen.values())
    m = st.columns(3)
    m[0].metric("Toplam / Total", tl(toplam))
    m[1].metric("Bütçe / Budget", tl(toplam_butce))
    m[2].metric("Kalan / Left", tl(toplam_butce - toplam), delta=f"{toplam_butce - toplam:,.0f} TL".replace(",", "."),
                delta_color="normal")
    if toplam > toplam_butce:
        st.warning("⚠️ Seçim bütçeyi aşıyor. Kısıtları gevşetmeyi ya da 'En ucuz' ölçütünü deneyin.")
    for kat, liste in adaylar.items():
        kat_ad = config.KATEGORILER[kat]
        st.markdown(f"#### {kat_ad['emoji']} {kat_ad['ad']}")
        if liste.empty:
            st.info("Kısıtlara uyan stokta ürün yok. / No in-stock product fits the constraints.")
            continue
        r = secilen[kat]
        birim = f" · {tl(r['birim'], False).replace(' TL', '')} {r['birim_ad']}" if pd.notna(r["birim"]) else ""
        st.success(f"**[{_md(r['name'])}]({r['url']})** — {r['site_adi']} — **{tl(r['fiyat'])}**{birim}  \n{r['ozet']}")
        with st.expander(f"Alternatifler ({min(len(liste) - 1, 10)})"):
            tablo_goster(liste.iloc[1:11])


def sistem_sekmesi():
    hedefler, istat = saglik_yukle()
    st.markdown("Her site x kategori için son tarama sonucu ve botun tarama hızı. (beta) = canlı sitede henüz "
                "doğrulanmamış ayrıştırıcı. / Last crawl result per site x category and the bot's throughput.")
    if not istat.empty:
        son = istat.iloc[-1]
        m = st.columns(6)
        m[0].metric("Son tur süresi", f"{son['duration']:.1f} sn")
        m[1].metric("Sayfa/sn", f"{son['pages_per_sec']:.1f}")
        m[2].metric("Ürün/sn", f"{son['products_per_sec']:.0f}")
        m[3].metric("Ort. gecikme", f"{son['avg_latency']:.2f} sn")
        m[4].metric("DB süresi", f"{(son['db_seconds'] or 0):.2f} sn")
        m[5].metric("Başarılı hedef", f"{son['ok_targets']}/{son['targets']}")
        istat["timestamp"] = pd.to_datetime(istat["timestamp"])
        g = st.columns(2)
        fig = px.line(istat, x="timestamp", y=["pages_per_sec", "products_per_sec"], markers=True,
                      labels={"timestamp": "Zaman", "value": "Hız", "variable": ""})
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=30, b=0), title="Tarama hızı (sayfa/sn, ürün/sn)")
        g[0].plotly_chart(fig, use_container_width=True)
        fig2 = px.bar(istat, x="timestamp", y="duration", labels={"timestamp": "Zaman", "duration": "Süre (sn)"})
        fig2.update_layout(height=280, margin=dict(l=0, r=0, t=30, b=0), title="Tur süresi (sn)")
        g[1].plotly_chart(fig2, use_container_width=True)
    if hedefler.empty:
        st.info("Henüz tarama kaydı yok. / No crawl records yet.")
        return
    hedefler["Site"] = hedefler["site"].map(
        lambda s: config.site_adi(s) + ("" if config.SITES.get(s, {}).get("dogrulandi", True) else " (beta)"))
    hedefler["Durum"] = [("⛔ Engel" if b else "❌ Hata") if not o else "✅" for o, b in zip(hedefler["ok"], hedefler["blocked"])]
    hedefler = hedefler.sort_values(["ok", "site", "category"])
    st.dataframe(hedefler[["Durum", "Site", "category", "product_count", "pages", "requests", "duration",
                           "stop_reason", "last_run", "last_ok", "error"]],
                 hide_index=True, use_container_width=True,
                 column_config={"category": "Kategori", "product_count": "Ürün", "pages": "Sayfa",
                                "requests": "İstek", "duration": st.column_config.NumberColumn("Süre (sn)", format="%.1f"),
                                "stop_reason": "Durma nedeni",
                                "last_run": st.column_config.DatetimeColumn("Son çalışma", format="DD.MM HH:mm"),
                                "last_ok": st.column_config.DatetimeColumn("Son başarı", format="DD.MM HH:mm"),
                                "error": st.column_config.TextColumn("Hata", width="large")})
    with st.expander("⚙️ Performans ayarları / Performance settings"):
        import crawler
        st.json({"MAX_ESZAMANLI_ISTEK": crawler.otomatik_eszamanlilik(), "SITE_BASINA_ESZAMANLI": config.SITE_BASINA_ESZAMANLI,
                 "SITE_ISTEK_ARALIGI_SANIYE": config.SITE_ISTEK_ARALIGI_SANIYE, "PARSE_ISCI_SAYISI": crawler.otomatik_isci_sayisi(),
                 "KONTROL_SIKLIGI_SANIYE": config.KONTROL_SIKLIGI_SANIYE, "PAZARYERI_SIKLIGI_SANIYE": config.PAZARYERI_SIKLIGI_SANIYE,
                 "BUTCE": {k: config.kategori_butcesi(k) for k in config.KATEGORILER}})


# =====================================================================================
st.title("🖥️ Donanım Fiyat Takip Paneli")
st.markdown("[TR] RAM (DDR5), SSD ve anakart fiyatları — "
            f"{len([s for s in config.SITES.values() if s['enabled']])} site. / [EN] RAM, SSD and motherboard prices.")

try:
    veritabanini_hazirla()
    df = urunleri_yukle()
    last_scan = database.get_last_scan()
    ust = st.columns(5)
    if last_scan:
        next_scan = last_scan + datetime.timedelta(seconds=config.KONTROL_SIKLIGI_SANIYE)
        ust[0].info(f"🔄 **Son Tarama:** {last_scan.strftime('%H:%M')}")
        ust[1].warning(f"⏳ **Sonraki Tarama:** {next_scan.strftime('%H:%M')}")
    if not df.empty:
        ust[2].metric("Takip edilen ürün", f"{len(df)}")
        ust[3].metric("Stokta", f"{int((df['stok'] == 1).sum())}")
        ust[4].metric("Bütçe (ürün başı)", tl(config.BUTCE, kurus=False))
    st.markdown("---")

    if df.empty:
        st.warning("[TR] Veritabanında henüz ürün bulunmuyor. Lütfen botun çalışmasını bekleyin. / [EN] No products in the database yet. Please wait for the bot to run.")
        sistem_sekmesi()
        st.stop()

    secim = kenar_cubugu(df)
    sonuc = filtrele(df, secim)
    t1, t2, t3, t4 = st.tabs(["🛒 Ürünler / Products", "🔥 Fırsatlar / Deals", "🧮 Bütçe Planlayıcı / Planner",
                              "📡 Site Sağlığı & Hız / Health"])
    with t1:
        urunler_sekmesi(sonuc, secim)
    with t2:
        firsatlar_sekmesi(sonuc)
    with t3:
        planlayici_sekmesi(df)
    with t4:
        sistem_sekmesi()
except Exception as e:
    st.error(f"[TR] Veri çekilirken bir hata oluştu / [EN] Error fetching data: {e}")
