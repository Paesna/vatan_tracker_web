import subprocess
import time
import os
import sys

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
        port = os.environ.get("PORT", "8501")
        dashboard_process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard.py", f"--server.port={port}", "--server.address=0.0.0.0"])
        
    try:
        # Ana thread'i canlı tut
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSistem kapatılıyor...")
        if bot_process:
            bot_process.terminate()
        if dashboard_process:
            dashboard_process.terminate()
        print("Tüm servisler durduruldu.")

if __name__ == "__main__":
    run_services()
