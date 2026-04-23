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

## ☁️ Buluta Yükleme / Cloud Deployment (Render.com)

Uygulama, **Render.com** ücretsiz web servisi üzerine tamamen uyumludur.

1. GitHub deponuzu Render'a bağlayın.
2. Web Service olarak oluşturun.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python app.py`
5. **Environment Variables** bölümüne `.env` dosyanızdaki şifreleri manuel olarak eklemeyi unutmayın!

---
> 🤖 *Developed as an Agentic AI Assistant project.*
