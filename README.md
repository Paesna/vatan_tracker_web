# 🚀 Donanım Fiyat Takip — RAM • SSD • Anakart (v2.0)

[TR] Türkiye'deki 14 bilgisayar mağazası / pazar yerinde **DDR5 RAM, SSD ve anakart** fiyatlarını anlık takip eden, bulut ya da yerel veritabanına kaydeden, Streamlit paneliyle görselleştiren ve **Discord/Telegram** üzerinden bildirim gönderen otonom bir bottur. Varsayılan bütçe ürün başına **20.000 TL**'dir.

[EN] An autonomous bot that tracks **DDR5 RAM, SSD and motherboard** prices on 14 Turkish shops/marketplaces, stores them in a cloud or local database, visualizes them with a Streamlit dashboard and sends **Discord/Telegram** alerts. Default budget is **20,000 TL** per product.

---

## 🌟 Özellikler / Features

- 🧩 **3 kategori:** DDR5 RAM, SSD (dahili NVMe/SATA) ve anakart. Kategori sayfalarındaki çöpler (SSD kutusu, taşınabilir SSD, RAM soğutucu, laptop, telefon anakartı, CPU+anakart paketleri, ikinci el/arızalı) otomatik elenir.
- 🏪 **14 site:** uzman mağazalar + pazar yerleri + Akakçe (her ürünün en ucuz satıcısı). Tablo aşağıda.
- 💰 **Bütçe (20.000 TL):** Bütçenin üstündeki ürünler için bildirim gelmez. Fiyata göre sıralı sitelerde tarama bütçe (+%15 pay) aşılınca durur → gereksiz sayfa indirilmez.
- 🔬 **Teknik özellik çıkarımı:** SSD → kapasite, NVMe/SATA, PCIe nesli, M.2/2.5", okuma hızı, **TL/TB**; Anakart → AMD/Intel, soket (AM5, LGA1700, LGA1851...), chipset, DDR4/DDR5, ATX/mATX/ITX, Wi-Fi; RAM → kapasite, kit, MHz, CL, **TL/GB**.
- 🔔 **Bildirimler:** 🟢 yeni ürün, 🔥 büyük indirim (base fiyata göre %15+), 📦 stoğa girdi. Bir site/kategori ilk kez tarandığında bildirim seli olmaz (sessiz "baseline"); bir turda en fazla 20 bildirim, fazlası tek özet mesajda.
- 📊 **Panel:** kategori/site/fiyat/özellik filtreleri, galeri + tablo görünümü, tembel yüklenen fiyat grafikleri, **🔥 Fırsatlar** (24 saat/7 gün/30 gün düşüşleri, tüm zamanların en düşüğü), **🧮 Bütçe Planlayıcı** (anakart + DDR5 RAM + SSD'yi bütçeye sığdırır), **📡 Site Sağlığı & Hız** (site başına son durum, sayfa/sn, ürün/sn).
- ⚡ **Performans:** eşzamanlı asenkron tarama (curl_cffi, kalıcı bağlantılar), site başına nazik limitler, engel (403/429/captcha) alan siteyi otomatik dinlendirme, çok çekirdekli HTML ayrıştırma, tek sorguda durum yükleme + tek işlemde toplu DB yazma, indeksli geçmiş tablosu.
- 🖥️ **Çapraz platform:** Windows ve Linux'ta ek ayar yapmadan çalışır; Linux için systemd servisi hazır.

### 🏪 Siteler / Sites

| Anahtar | Site | RAM | SSD | Anakart | Durum |
|---|---|:-:|:-:|:-:|---|
| `vatan` | Vatan Bilgisayar | ✅ | ✅ | ✅ | ✅ doğrulanmış ayrıştırıcı |
| `sinerji` | Sinerji | ✅ | ✅ | ✅ | ✅ doğrulanmış ayrıştırıcı |
| `incehesap` | İncehesap | ✅ | ✅ | ✅ | ✅ doğrulanmış ayrıştırıcı |
| `tebilon` | Tebilon | ✅ | ✅ | ✅ | ✅ doğrulanmış ayrıştırıcı |
| `itopya` | İtopya | ✅ | ✅ | ✅ | ✅ doğrulanmış ayrıştırıcı |
| `gaming` | Gaming.gen.tr (WooCommerce) | ✅ | ✅ | ✅ | 🧪 beta |
| `gamegaraj` | GameGaraj | ✅ | ✅ | ✅ | 🧪 beta |
| `teknosa` | Teknosa | – | ✅ | ✅ | 🧪 beta |
| `mediamarkt` | MediaMarkt | – | ✅ | ✅ | 🧪 beta |
| `amazon` | Amazon.com.tr | ✅ | ✅ | ✅ | 🧪 beta, pazar yeri |
| `hepsiburada` | Hepsiburada | ✅ | ✅ | ✅ | 🧪 beta, pazar yeri |
| `trendyol` | Trendyol | ✅ | ✅ | ✅ | 🧪 beta, pazar yeri |
| `n11` | n11 | – | ✅ | ✅ | 🧪 beta, pazar yeri |
| `akakce` | Akakçe (en ucuz satıcı) | ✅ | ✅ | ✅ | 🧪 beta, pazar yeri |

- **Doğrulanmış:** ayrıştırıcı seçicileri canlı sitede çalışan eski koddan alındı; SSD/anakart için sadece kategori URL'si eklendi (sayfa yapısı aynı).
- **Beta:** site yapısına göre yazıldı ama canlı sitede henüz denenmedi. Her beta site 3 katmanlı ayrıştırıcı kullanır (JSON-LD → sayfaya gömülü JSON → ürün linki deseninden kart bulma), bu sayede site HTML'i değişse de çoğunlukla çalışmaya devam eder. Çalışmayan site sadece kendi satırında ❌ gösterir, diğerlerini etkilemez. Kontrol için: `python benchmark.py --canli`
- **Pazar yeri:** daha seyrek taranır (`PAZARYERI_SIKLIGI_SANIYE`, varsayılan 10 dk), sadece ilk sayfalar okunur, yeni ürün bildirimi kapalıdır (sürekli yeni ilan açıldığı için); indirim ve stok bildirimleri açıktır.

---

## 🛠️ Kurulum / Setup

### 1. Gereksinimleri Yükleyin / Install Requirements

**Windows:**
```bash
pip install -r requirements.txt
```

**Linux / macOS:**
```bash
pip3 install -r requirements.txt
```

> [!NOTE]
> v2 ile `lxml` eklendi (HTML'i ~2 kat hızlı ayrıştırır). Güncelleme yaptıysanız `pip install -r requirements.txt` komutunu tekrar çalıştırın; systemd kurulumunda `bash deploy/install_linux.sh` bunu yapar.

### 2. `.env` Dosyasını Oluşturun / Create `.env` File

`.env.example` dosyasını `.env` olarak kopyalayıp değerlerinizi girin. En önemli ayarlar:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url
DB_URL=your_supabase_postgresql_url
RUN_MODE=BOT_ONLY
BUTCE=20000
```

> [!IMPORTANT]
> **Güvenlik Uyarısı (Security Warning):** Bu şifreleri asla `config.py` içerisine manuel olarak yazmayın! Aksi takdirde GitHub gibi açık platformlarda sızdırılabilir.

### 3. `RUN_MODE` Ayarları / RUN_MODE Options

| RUN_MODE | Açıklama / Description |
|---|---|
| `BOT_ONLY` | Sadece fiyat takip botu çalışır (Dashboard açılmaz) |
| `WEB_ONLY` | Sadece Streamlit Dashboard açılır (Bot çalışmaz) |
| `ALL` | Hem bot hem dashboard aynı anda çalışır (Varsayılan) |

### 4. Tüm Ayarlar / All Settings (`.env`)

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `BUTCE` | `20000` | Ürün başına üst fiyat (TL). Üstündekiler için bildirim yok; yeni ürün olarak eklenmez (`HEDEF_FIYAT` eski adıdır) |
| `BUTCE_RAM` / `BUTCE_SSD` / `BUTCE_ANAKART` | `BUTCE` | Kategoriye özel bütçe |
| `BUTCE_PAYI_YUZDE` | `15` | Sıralı sitelerde taramanın bütçenin ne kadar üstüne kadar süreceği (bütçeyi az aşan ürünlerin fiyatı da izlenir) |
| `INDIRIM_YUZDESI` | `15` | "Büyük indirim" bildirimi için base fiyata göre düşüş yüzdesi |
| `STOK_BILDIRIM_DAKIKA` | `60` | En az bu kadar stok dışı kalıp dönen ürün için "stoğa girdi" bildirimi (0 = kapalı) |
| `AKTIF_KATEGORILER` | `ram,ssd,anakart` | Takip edilecek kategoriler |
| `DEVRE_DISI_SITELER` | – | Kapatılacak siteler, örn. `amazon,akakce` |
| `SADECE_SITELER` | – | Doluysa sadece bu siteler, örn. `vatan,itopya,incehesap` |
| `NOTEBOOK_RAM_HARIC` | `0` | `1` ise SODIMM/notebook RAM'ler takip edilmez |
| `KONTROL_SIKLIGI_SANIYE` | `120` | Uzman sitelerin tarama aralığı |
| `PAZARYERI_SIKLIGI_SANIYE` | `600` | Pazar yerleri + Akakçe tarama aralığı |
| `MAX_ESZAMANLI_ISTEK` | `0` (otomatik) | Toplam eşzamanlı HTTP isteği (otomatik: CPU çekirdeği × 4, 8–32) |
| `SITE_BASINA_ESZAMANLI` | `2` | Tek siteye aynı anda en fazla istek |
| `SITE_ISTEK_ARALIGI_SANIYE` | `0.75` | Aynı siteye iki istek arası en kısa süre (±%30 rastgele) |
| `PARSE_ISCI_SAYISI` | `-1` (otomatik) | HTML ayrıştırma süreç sayısı (otomatik: çekirdek − 1, en fazla 4; `0` = ana süreç) |
| `MAX_SAYFA` / `PAZARYERI_MAX_SAYFA` | `15` / `3` | Kategori başına en fazla sayfa |
| `ENGEL_BEKLEME_SANIYE` | `600` | 403/429/captcha alan siteyi dinlendirme süresi (üst üste engelde 2 katına çıkar, en fazla 2 saat) |
| `IMPERSONATE` | `chrome` | curl_cffi tarayıcı taklidi (en yeni Chrome TLS parmak izi) |

---

## 🚀 Çalıştırma / Running

```bash
python3 app.py                 # .env'deki RUN_MODE'a göre bot ve/veya panel
python3 main.py                # sadece bot
python3 main.py --tek-sefer --bildirim-yok                   # tek tur tara, bildirim gönderme (deneme)
python3 main.py --tek-sefer --site vatan,itopya --kategori ssd,anakart
python3 cleanup.py --kuru      # kategori kurallarına uymayan kayıtları listele (silmeden)
```

*(Panel: `http://localhost:8501`)*

Her turun sonunda bot site/kategori başına özet ve hız raporu yazar (örnek biçim):

```
  ✅ vatan        ssd      |  6 sayfa |  131 ürün (2 elendi) |   7.9 sn | butce
  ⛔ amazon       anakart  | HTTP 503 (engel / blocked); 600 sn dinlendirilecek
📊 Tarama: 39 hedef (37 başarılı, 1 engelli) | 188 sayfa, 41.3 MB | 4.120 ürün | 27.4 sn -> 6.9 sayfa/sn, 150 ürün/sn | ...
```

---

## ⚡ Performans: Linux makine saniyede kaç sayfa tarayabilir? / Throughput

```bash
python3 benchmark.py               # çevrimdışı: CPU ayrıştırma hızı + DB hızı + ayar önerileri
python3 benchmark.py --canli       # + her site/kategorinin 1. sayfası (site sağlığı, gecikme)
python3 benchmark.py --canli --tam # + gerçek tam tarama turu (DB'ye yazmaz)
```

Bu projenin geliştirildiği 4 çekirdekli Linux makinede `benchmark.py` sonuçları (sizin makinenizde farklı olacaktır):

| Ölçüm | Sonuç |
|---|---|
| HTML ayrıştırma, 1 süreç | ~75 sayfa/sn (~1.800 ürün/sn) |
| HTML ayrıştırma, 4 süreç | ~240 sayfa/sn (~5.700 ürün/sn) |
| lxml vs html.parser | ~1,7 kat hızlı |
| DB: eski (ürün başına 2–4 sorgu) → yeni (tek sorgu + toplu yazma) | ~200 → ~21.000 ürün/sn (**~100 kat**; Supabase'de fark daha da büyük) |
| Ağ (site başına 2 eşzamanlı, 0,75 sn aralık, 14 site) | ~14 sayfa/sn (ayarlardan hesaplanan üst sınır) |
| Tam tur (39 hedef, ~190 sayfa) | ~30 sn (tahmini; gerçeğini `--canli --tam` ölçer) |

**Sonuç:** Darboğaz CPU değil, sitelere karşı nazik ağ limitleridir — bilerek böyle: siteleri hızlı taramak IP'nizin engellenmesine yol açar. v1 siteleri sırayla tek tek tarıyor ve her ürün için ayrı DB sorgusu atıyordu; v2'de tüm siteler aynı anda taranır, her site kendi limitinde çalışır.

İpuçları:
- `SITE_BASINA_ESZAMANLI` ve `SITE_ISTEK_ARALIGI_SANIYE` hızı en çok etkileyen ayarlardır; 403 görmeye başlarsanız geri alın.
- Zayıf makinede (Raspberry Pi vb.) `PARSE_ISCI_SAYISI=1` RAM tasarrufu sağlar; ağ zaten darboğaz olduğu için hız düşmez.
- `KONTROL_SIKLIGI_SANIYE`, bir tam turun en az ~3 katı olmalı (benchmark önerir).

---

## 📁 Proje Yapısı / Project Structure

```
vatan_tracker_web/
├── app.py               # Ana başlatıcı (bot + panel, çökeni yeniden başlatır)
├── config.py            # Ayarlar + 14 sitenin tanımı (URL, sayfalama, ayrıştırıcı)
├── categories.py        # RAM/SSD/Anakart kuralları + teknik özellik çıkarıcı
├── scraper.py           # HTML -> ürün ayrıştırıcıları (site özel + genel stratejiler)
├── crawler.py           # Asenkron tarayıcı (eşzamanlılık, nezaket, engel, sayfalama)
├── main.py              # Bot döngüsü: tara -> karşılaştır -> toplu yaz -> bildir
├── database.py          # SQLAlchemy modelleri, otomatik geçiş, toplu işlemler
├── dashboard.py         # Streamlit paneli
├── benchmark.py         # Hız ölçümü + site sağlık kontrolü + ayar önerisi
├── ornekler.py          # Testler/benchmark için örnek site sayfaları
├── cleanup.py           # Kategori kuralına uymayan kayıtları temizler (cleanup_non_ram.py = eski ad)
├── telegram_bot.py / discord_bot.py
├── tests/               # Çevrimdışı testler: python -m unittest discover -s tests -t .
└── deploy/              # install_linux.sh + systemd servisi
```

### Yeni site eklemek / Adding a site

`config.py` → `SITES` sözlüğüne bir kayıt ekleyin. Çoğu site için genel ayrıştırıcı yeterlidir:

```python
"yenisite": {
    "ad": "Yeni Site", "renk": "#123456", "parser": "genel", "dogrulandi": False,
    "kategoriler": {"ssd": "https://www.yenisite.com/ssd?sort=price_asc"},
    "sayfalama": {"tip": "query", "param": "page"},   # veya "yol" / "wordpress" / "akakce"
    "fiyata_gore_sirali": True,                       # bütçe aşılınca dur
    "urun_link_deseni": r"/urun/(\d+)",               # ürün linki; grup 1 = ürün kodu
},
```

Ardından `python benchmark.py --canli --site yenisite` ile deneyin.

### v1'den geçiş / Upgrading from v1

- Veritabanı **otomatik** taşınır (yeni sütunlar, indeks, eski kayıtların site/kategori/son fiyat bilgisi). Fiyat geçmişi korunur, ürün kodları değişmez.
- Vatan artık sadece "stoktakiler" listesini tarar (eskiden tümü + stoktakiler, 2 kat istek); listeden düşen ürün stok dışı sayılır.
- İlk turda SSD ve anakartlar sessizce eklenir (bildirim seli olmaz); sonraki turlardan itibaren bildirimler başlar.

---

## 🌐 Hibrit Dağıtım Rehberi / Hybrid Deployment Guide (Ubuntu PC + Render.com)

Bu projeyi en kararlı ve engellemelere karşı en dayanıklı şekilde çalıştırmak için **Hibrit Mimariyi (Hybrid Architecture)** öneriyoruz:
- **Backend (Veri Kazıma Botu):** Evdeki Linux Ubuntu bilgisayarınızda çalışır. Ev (bireysel) internet IP'niz kullanıldığı için e-ticaret sitelerinin bot korumalarına takılma ihtimali çok düşüktür.
- **Frontend (Streamlit Dashboard):** Render.com üzerinde ücretsiz olarak çalışır. Böylece paneline dünyanın her yerinden erişebilirsiniz. Render sunucuları doğrudan e-ticaret sitelerine istek atmadığı için engellenme riski yoktur.
- **Ortak Nokta (PostgreSQL / Supabase):** Hem evdeki Ubuntu bilgisayarınız hem de Render sunucusu aynı Supabase veritabanına bağlanır.

---

### 🖥️ 1. Evdeki Ubuntu PC Kurulumu (Backend / Sadece Bot)

#### Adım A: Bağımlılıkları Kurun
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git
```

#### Adım B: Projeyi Klonlayın ve Klasöre Geçin
```bash
git clone <github_repo_linkiniz>
cd vatan_tracker_web
```

#### Adım C: Otomatik Kurulum Betiğini Çalıştırın (Önerilen)
Tek komutla sanal ortamı kurar, bağımlılıkları yükler, `.env` şablonunu oluşturur ve botu **systemd** servisi olarak kaydeder (bilgisayar yeniden başlasa bile bot otomatik açılır, çökerse 15 saniye içinde yeniden başlatılır):
```bash
bash deploy/install_linux.sh
```

#### Adım D: `.env` Dosyasını Düzenleyin
```bash
nano .env
sudo systemctl restart ram-tracker   # ayar değişikliğinden sonra
```
- `DB_URL` **boş bırakılırsa** proje klasöründe yerel SQLite (`ram_tracker.db`) kullanılır — Supabase şart değildir.
- `TELEGRAM_TOKEN` / `DISCORD_WEBHOOK_URL` boşsa o bildirim kanalı sessizce atlanır.
- Her şey tek makinede çalışacaksa `RUN_MODE=ALL` yapın (bot + dashboard); dashboard'u Render'da barındırıyorsanız `BOT_ONLY` bırakın.

#### Adım E: Servisi Kontrol Edin
```bash
sudo systemctl status ram-tracker      # durum
journalctl -u ram-tracker -f           # canlı log takibi (tur raporları burada)
sudo systemctl stop ram-tracker        # durdurma
./venv/bin/python benchmark.py --canli # site sağlığı + hız
```

> [!NOTE]
> Elle kurulum yapmak isterseniz `deploy/ram-tracker.service` şablonundaki `__USER__` ve `__PROJECT_DIR__` alanlarını kendinize göre değiştirip `/etc/systemd/system/` altına kopyalamanız yeterlidir. Servis `app.py`'yi çalıştırır; `app.py` hem botu hem (RUN_MODE'a göre) dashboard'u yönetir ve çöken alt süreçleri otomatik yeniden başlatır.

---

### ☁️ 2. Render.com Kurulumu (Frontend / Sadece Web Panel)

1. Projenizi GitHub'a yükleyin.
2. Render.com'a giriş yapın ve **New +** -> **Web Service** seçeneğine tıklayın.
3. GitHub deponuzu bağlayın.
4. Ayarları şu şekilde yapın:
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run dashboard.py --server.port=$PORT --server.address=0.0.0.0`
5. **Environment Variables** (Ortam Değişkenleri) bölümünü açın ve şunları ekleyin:
   - `DB_URL` = *(Supabase PostgreSQL bağlantı adresiniz)*
   - `RUN_MODE` = `WEB_ONLY`
   - `BUTCE` = `20000` *(panelin varsayılan fiyat filtresi)*

Render uygulamanızı derleyip başlattıktan sonra size verilen `https://xxx.onrender.com` bağlantısından panelinize 7/24 erişebilirsiniz!

---
> 🤖 *Developed as an Agentic AI Assistant project.*
