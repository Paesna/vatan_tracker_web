#!/usr/bin/env bash
# [TR] RAM Tracker'i Linux'ta kalici bir arka plan servisi (systemd) olarak kurar.
#      Kullanim:  bash deploy/install_linux.sh
# [EN] Installs RAM Tracker as a persistent background service (systemd) on Linux.
#      Usage:  bash deploy/install_linux.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="ram-tracker"
RUN_USER="${SUDO_USER:-$USER}"

echo "=== RAM Tracker Linux Kurulumu / Linux Setup ==="
echo "Proje dizini / Project dir : $PROJECT_DIR"
echo "Servis kullanicisi / User  : $RUN_USER"
echo

# 1) Sanal ortam / Virtual environment
if ! command -v python3 >/dev/null; then
    echo "HATA: python3 bulunamadi. Once 'sudo apt install -y python3 python3-venv python3-pip' calistirin."
    exit 1
fi

if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "-> Sanal ortam (venv) olusturuluyor..."
    python3 -m venv "$PROJECT_DIR/venv" || {
        echo "HATA: venv olusturulamadi. 'sudo apt install -y python3-venv' deneyin."
        exit 1
    }
fi

echo "-> Bagimliliklar yukleniyor (requirements.txt)..."
"$PROJECT_DIR/venv/bin/pip" install --quiet --upgrade pip
"$PROJECT_DIR/venv/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

# 2) .env dosyasi / .env file
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo
    echo "!! .env dosyasi olusturuldu: $PROJECT_DIR/.env"
    echo "!! Telegram/Discord/DB ayarlarinizi girmek icin duzenleyin:  nano $PROJECT_DIR/.env"
    echo "!! (Bos birakirsaniz yerel SQLite kullanilir ve bildirimler kapali kalir.)"
    echo
fi

# 3) Hizli calisma testi / Quick smoke test
echo "-> Hizli test: moduller yukleniyor..."
"$PROJECT_DIR/venv/bin/python" -c "import config, scraper, database, main, telegram_bot, discord_bot" \
    && echo "   OK: tum moduller sorunsuz yuklendi."

# 4) systemd servisi / systemd service
echo "-> systemd servisi kuruluyor ($SERVICE_NAME)..."
TMP_UNIT="$(mktemp)"
sed -e "s|__USER__|$RUN_USER|g" -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
    "$PROJECT_DIR/deploy/ram-tracker.service" > "$TMP_UNIT"

sudo cp "$TMP_UNIT" "/etc/systemd/system/$SERVICE_NAME.service"
rm -f "$TMP_UNIT"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME.service"
sudo systemctl restart "$SERVICE_NAME.service"

echo
echo "=== KURULUM TAMAM / SETUP COMPLETE ==="
echo "Durum / Status      : sudo systemctl status $SERVICE_NAME"
echo "Canli log / Live log: journalctl -u $SERVICE_NAME -f"
echo "Durdur / Stop       : sudo systemctl stop $SERVICE_NAME"
echo "Dashboard           : http://localhost:8501  (RUN_MODE=ALL veya WEB_ONLY ise)"
