"""
[TR] Streamlit Web Sunucusu Modülü / [EN] Streamlit Web Server Module
[TR] Render.com veya Heroku gibi servisler uygulamanın 7/24 çalışması için bir "Web Sunucusu" (Port) açık olmasını zorunlu kılar.
Bu dosya ana web sunucusu olarak Streamlit Dashboard'ı başlatırken, arka planda (iş parçacığında) botumuzu çalıştırır.
"""

import os
import threading
import sys

# [TR] Ana bot döngüsünü içeri aktarıyoruz / [EN] Import the main bot loop
from main import taramayi_baslat

def botu_arka_planda_calistir():
    """
    [TR] Botun Streamlit sunucusunu kilitlememesi için ayrı bir iş parçacığında çalıştırılması.
    [EN] Running the bot on a separate thread so it doesn't block the Streamlit server.
    """
    taramayi_baslat()

if __name__ == "__main__":
    # 1. [TR] Botu arka planda başlat / [EN] Start the bot in the background
    bot_thread = threading.Thread(target=botu_arka_planda_calistir)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. [TR] Streamlit web sunucusunu başlat / [EN] Start the Streamlit web server
    # [TR] Port numarası bulut servisi tarafından (Render) otomatik atanır. Bulamazsa 8501 kullanılır.
    port = os.environ.get("PORT", "8501")
    
    # [TR] Streamlit'i sistem komutu olarak başlatıyoruz.
    print(f"🚀 Streamlit {port} portunda başlatılıyor...")
    os.system(f"python -m streamlit run dashboard.py --server.port {port} --server.address 0.0.0.0")
