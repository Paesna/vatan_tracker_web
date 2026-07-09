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
├── .gitignore           # Git'e yüklenmeyecek dosyalar
├── app.py               # Ana başlatıcı (Orchestrator)
├── config.py            # Merkezi ayar modülü (.env okuyucu)
├── main.py              # Fiyat takip botu (Scraper + Alert)
├── dashboard.py         # Streamlit Web Paneli
├── database.py          # Supabase PostgreSQL ORM (SQLAlchemy)
├── scraper.py           # Vatan Bilgisayar veri çekici
├── telegram_bot.py      # Telegram bildirim modülü
├── discord_bot.py       # Discord Webhook bildirim modülü
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

#### Adım C: Sanal Ortam Oluşturup Bağımlılıkları Yükleyin
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Adım D: `.env` Dosyasını Ayarlayın
Proje klasöründe `.env` dosyasını oluşturun ve `RUN_MODE` değerini `BOT_ONLY` yapın:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url
DB_URL=your_supabase_postgresql_url
RUN_MODE=BOT_ONLY
TEBILON_COOKIE="kopyaladiginiz_cerez"
TEBILON_USER_AGENT="kopyaladiginiz_user_agent"
```

#### Adım E: Botu Arka Plan Servisi (Systemd) Yapın
Botun bilgisayarınız kapansa/açılsa dahi otomatik olarak arka planda çalışması için bir servis dosyası oluşturun:
```bash
sudo nano /etc/systemd/system/ram-tracker.service
```
Açılan editöre aşağıdaki içeriği yapıştırın (**Kullanıcı adınızı ve klasör yollarını kendinize göre güncelleyin!**):
```ini
[Unit]
Description=RAM Tracker Scraping Bot Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vatan_tracker_web
ExecStart=/home/ubuntu/vatan_tracker_web/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
*Nano'dan kaydedip çıkmak için: `Ctrl + O`, `Enter`, `Ctrl + X`.*

Servisi etkinleştirin ve başlatın:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ram-tracker.service
sudo systemctl start ram-tracker.service
```

Durumunu kontrol etmek ve logları görmek için:
```bash
sudo systemctl status ram-tracker.service
journalctl -u ram-tracker.service -f
```

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
