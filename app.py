import subprocess
import time
import os
import sys
from dotenv import load_dotenv

# [TR] .env dosyasını oku, böylece RUN_MODE gibi değişkenler otomatik yüklenir.
# [EN] Load .env file so variables like RUN_MODE are available without manual shell export.
load_dotenv()

# [TR] Windows konsolu Türkçe karakter sorunu için / [EN] Configure console to UTF-8 for Turkish characters
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def dashboard_komutu():
    """[TR] Streamlit dashboard başlatma komutunu oluşturur. / [EN] Builds the Streamlit dashboard launch command."""
    port = os.environ.get("PORT", "8501")
    # [TR] --server.headless=true: TTY olmayan ortamlarda (systemd servisi) Streamlit'in interaktif
    #      "e-posta girin" karşılama istemiyle çakılmasını önler.
    # [EN] --server.headless=true: prevents Streamlit from crashing on its interactive "enter email"
    #      welcome prompt in environments without a TTY (e.g. a systemd service).
    return [sys.executable, "-m", "streamlit", "run", "dashboard.py",
            f"--server.port={port}", "--server.address=0.0.0.0", "--server.headless=true"]

def run_services():
    print("=== VATAN RAM TRACKER BAŞLATILIYOR ===")
    
    run_mode = os.getenv("RUN_MODE", "ALL").upper()
    print(f"Sistem Modu (RUN_MODE): {run_mode}")
    
    bot_process = None
    dashboard_process = None
    
    # 1. Veri Çekici Botu Başlat (Arka Planda)
    if run_mode in ["ALL", "BOT_ONLY"]:
        print("Bot başlatılıyor (main.py)...")
        bot_process = subprocess.Popen([sys.executable, "main.py"])
        time.sleep(3) # Botun veritabanını kurması için kısa bir süre bekle
        
    # 2. Streamlit Dashboard Başlat
    if run_mode in ["ALL", "WEB_ONLY"]:
        print("Dashboard başlatılıyor (dashboard.py)...")
        dashboard_process = subprocess.Popen(dashboard_komutu())
        
    try:
        # [TR] Ana thread'i canlı tut ve çöken servisleri otomatik yeniden başlat.
        # [EN] Keep the main thread alive and auto-restart crashed services.
        while True:
            time.sleep(5)

            if bot_process and bot_process.poll() is not None:
                print(f"⚠️ Bot durdu (çıkış kodu: {bot_process.returncode}). 10 sn sonra yeniden başlatılıyor...")
                time.sleep(10)
                bot_process = subprocess.Popen([sys.executable, "main.py"])

            if dashboard_process and dashboard_process.poll() is not None:
                print(f"⚠️ Dashboard durdu (çıkış kodu: {dashboard_process.returncode}). 10 sn sonra yeniden başlatılıyor...")
                time.sleep(10)
                dashboard_process = subprocess.Popen(dashboard_komutu())
    except KeyboardInterrupt:
        print("\nSistem kapatılıyor...")
        if bot_process:
            bot_process.terminate()
        if dashboard_process:
            dashboard_process.terminate()
        print("Tüm servisler durduruldu.")

if __name__ == "__main__":
    run_services()
