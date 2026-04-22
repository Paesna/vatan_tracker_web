# 🚀 Vatan RAM Tracker Web (v1.0)

[TR] Vatan Bilgisayar'daki DDR5 RAM'lerin fiyatlarını anlık olarak takip eden, bulut veritabanına kaydeden, Streamlit Dashboard ile görselleştiren ve **Discord/Telegram** üzerinden bildirim gönderen otonom bir bottur.

[EN] An autonomous bot that tracks DDR5 RAM prices on Vatan Bilgisayar, saves them to a cloud database, visualizes them using a Streamlit Dashboard, and sends alerts via **Discord/Telegram**.

---

## 🌟 Özellikler / Features

- 📦 **Otomatik Fiyat Takibi:** Vatan Bilgisayar'dan sürekli güncel fiyat ve stok çekme.
- 📉 **İndirim & Yeni Ürün Bildirimi:** %15 üzeri indirimlerde veya listeye yeni bir ürün girdiğinde Discord ve Telegram'a anında "Embed" resimli mesaj atma.
- ☁️ **Bulut Veritabanı:** Supabase PostgreSQL ile kalıcı ve güvenli fiyat geçmişi kaydı.
- 📊 **Streamlit Dashboard (Galeri):** Ürünlerin fotoğraflarını, güncel fiyatlarını ve interaktif Plotly grafikleriyle fiyat zaman çizelgesini (1 Gün, 1 Hafta, Tüm Zamanlar) sunan e-ticaret tarzı arayüz.
- 🔍 **Arama ve Sıralama:** Dashboard üzerinde fiyata göre sıralama ve RAM ismiyle arama yapabilme.

---

## 🛠️ Kurulum / Setup

### 1. Gereksinimleri Yükleyin / Install Requirements
```bash
pip install -r requirements.txt
```

### 2. .env Dosyasını Oluşturun / Create .env File
Projeyi kendi bilgisayarınızda çalıştırmak için ana dizine `.env` isminde bir dosya oluşturun ve şifrelerinizi içine yazın:
*(To run the project locally, create a `.env` file in the root directory and add your credentials)*

```env
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url
DB_URL=your_supabase_postgresql_url
```
**Güvenlik Uyarısı (Security Warning):** Bu şifreleri asla `config.py` içerisine manuel olarak yazmayın! Aksi takdirde GitHub gibi açık platformlarda sızdırılabilir.

### 3. Uygulamayı Başlatın / Run the Application
Hem arka plandaki tarayıcı botu hem de Web Paneli'ni aynı anda çalıştırmak için:
*(To run both the background scraper bot and the Web Dashboard simultaneously)*
```bash
python app.py
```
*(Uygulama başladığında `http://localhost:8501` adresine giderek paneli görebilirsiniz.)*

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
