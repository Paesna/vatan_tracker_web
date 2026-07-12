# 🚀 Vatan RAM Tracker Web (v1.2)

[TR] Vatan Bilgisayar'daki DDR5 RAM'lerin fiyatlarını anlık olarak takip eden, bulut veritabanına kaydeden, Streamlit Dashboard ile görselleştiren ve **Discord/Telegram** üzerinden bildirim gönderen otonom bir bottur.

[EN] An autonomous bot that tracks DDR5 RAM prices on Vatan Bilgisayar, saves them to a cloud database, visualizes them using a Streamlit Dashboard, and sends alerts via **Discord/Telegram**.

---

## 🌟 Özellikler / Features

- 📦 **Otomatik Fiyat Takibi:** Vatan Bilgisayar'dan sürekli güncel fiyat ve stok çekme.
- 📉 **İndirim & Yeni Ürün Bildirimi:** %15 üzeri indirimlerde veya listeye yeni bir ürün girdiğinde Discord ve Telegram'a anında "Embed" resimli mesaj atma.
- ☁️ **Bulut Veritabanı:** Supabase PostgreSQL ile kalıcı ve güvenli fiyat geçmişi kaydı.
- 📊 **Streamlit Dashboard (Galeri):** Ürünlerin fotoğraflarını, güncel fiyatlarını ve interaktif Plotly grafikleriyle fiyat zaman çizelgesini (1 Gün, 1 Hafta, Tüm Zamanlar) sunan e-ticaret tarzı arayüz.
- 🔍 **Arama ve Sıralama:** Dashboard üzerinde fiyata göre sıralama ve RAM ismiyle arama yapabilme.
- 🖥️ **Çapraz Platform Desteği:** Windows ve Linux'ta ek ayar yapmadan doğrudan çalışır.

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

### 2. `.env` Dosyasını Oluşturun / Create `.env` File

Projeyi kendi bilgisayarınızda çalıştırmak için ana dizine `.env` isminde bir dosya oluşturun ve şifrelerinizi içine yazın:
*(To run the project locally, create a `.env` file in the root directory and add your credentials)*

```env
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url
DB_URL=your_supabase_postgresql_url
RUN_MODE=BOT_ONLY
```

> [!IMPORTANT]
> **Güvenlik Uyarısı (Security Warning):** Bu şifreleri asla `config.py` içerisine manuel olarak yazmayın! Aksi takdirde GitHub gibi açık platformlarda sızdırılabilir.

### 3. `RUN_MODE` Ayarları / RUN_MODE Options

`.env` dosyasındaki `RUN_MODE` değişkeniyle uygulamanın çalışma modunu kontrol edersiniz. **Artık terminal'de ayrıca ortam değişkeni set etmenize gerek yok!**

| RUN_MODE | Açıklama / Description |
|---|---|
| `BOT_ONLY` | Sadece fiyat takip botu çalışır (Dashboard açılmaz) |
| `WEB_ONLY` | Sadece Streamlit Dashboard açılır (Bot çalışmaz) |
| `ALL` | Hem bot hem dashboard aynı anda çalışır (Varsayılan) |

---

## 🚀 Çalıştırma / Running

`.env` dosyasını ayarladıktan sonra tek komutla başlatın:

**Windows:**
```bash
python app.py
```

**Linux / macOS:**
```bash
python3 app.py
```

> [!TIP]
> Eski yöntem olan `$env:RUN_MODE="BOT_ONLY"; python app.py` gibi komutlara **artık gerek yoktur**. Tüm ayarlar `.env` dosyasından otomatik okunur.

*(Uygulama `RUN_MODE=ALL` veya `RUN_MODE=WEB_ONLY` modunda başlatıldığında `http://localhost:8501` adresine giderek paneli görebilirsiniz.)*

---

## 📁 Proje Yapısı / Project Structure

```
vatan_tracker_web/
├── .env                 # Gizli ayarlar (Git'e yüklenmez)
├── .env.example         # Ayar şablonu (.env olarak kopyalayın)
├── .gitignore           # Git'e yüklenmeyecek dosyalar
├── app.py               # Ana başlatıcı (Orchestrator, çöken servisi yeniden başlatır)
├── config.py            # Merkezi ayar modülü (.env okuyucu, SQLite fallback)
├── main.py              # Fiyat takip botu (Scraper + Alert)
├── dashboard.py         # Streamlit Web Paneli
├── database.py          # PostgreSQL/SQLite ORM (SQLAlchemy)
├── scraper.py           # 5 site için veri çekici (Vatan, Sinerji, İncehesap, Tebilon, Itopya)
├── telegram_bot.py      # Telegram bildirim modülü
├── discord_bot.py       # Discord Webhook bildirim modülü
├── cleanup_non_ram.py   # Yanlış kaydedilmiş RAM dışı ürünleri DB'den temizler
├── deploy/
│   ├── install_linux.sh     # Tek komutluk Linux systemd kurulumu
│   └── ram-tracker.service  # systemd servis şablonu
├── requirements.txt     # Python bağımlılıkları
└── README.md            # Bu dosya
```

---

## 🌐 Hibrit Dağıtım Rehberi / Hybrid Deployment Guide (Ubuntu PC + Render.com)

Bu projeyi en kararlı ve engellemelere karşı en dayanıklı şekilde çalıştırmak için **Hibrit Mimariyi (Hybrid Architecture)** öneriyoruz:
- **Backend (Veri Kazıma Botu):** Evdeki Linux Ubuntu bilgisayarınızda çalışır. Ev (bireysel) internet IP'niz kullanıldığı için e-ticaret sitelerinin bot korumalarına takılma ihtimali çok düşüktür.
- **Frontend (Streamlit Dashboard):** Render.com üzerinde ücretsiz olarak çalışır. Böylece paneline dünyanın her yerinden erişebilirsiniz. Render sunucuları doğrudan e-ticaret sitelerine istek atmadığı için engellenme riski yoktur.
- **Ortak Nokta (PostgreSQL / Supabase):** Hem evdeki Ubuntu bilgisayarınız hem de Render sunucusu aynı Supabase veritabanına bağlanır.

---

### 🖥️ 1. Evdeki Ubuntu PC Kurulumu (Backend / Sadece Bot)

Ubuntu bilgisayarınızda botu arka planda sürekli çalışacak bir servis (**systemd**) haline getirmek için şu adımları uygulayın:

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
Kurulum betiği `.env.example` şablonundan bir `.env` oluşturur. Kendi değerlerinizi girin:
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
journalctl -u ram-tracker -f           # canlı log takibi
sudo systemctl stop ram-tracker        # durdurma
```

> [!NOTE]
> Elle kurulum yapmak isterseniz `deploy/ram-tracker.service` şablonundaki `__USER__` ve `__PROJECT_DIR__` alanlarını kendinize göre değiştirip `/etc/systemd/system/` altına kopyalamanız yeterlidir. Servis `app.py`'yi çalıştırır; `app.py` hem botu hem (RUN_MODE'a göre) dashboard'u yönetir ve çöken alt süreçleri otomatik yeniden başlatır.

---

### ☁️ 2. Render.com Kurulumu (Frontend / Sadece Web Panel)

Streamlit web panelini Render üzerinde yayına almak için:

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

Render uygulamanızı derleyip başlattıktan sonra size verilen `https://xxx.onrender.com` bağlantısından panelinize 7/24 erişebilirsiniz!

---
> 🤖 *Developed as an Agentic AI Assistant project.*
