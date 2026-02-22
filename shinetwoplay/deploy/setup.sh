#!/bin/bash
# ============================================
#  ShineTwo Play - First Time Server Setup
#  Run this ONCE on a fresh EC2 Ubuntu instance
#  Prerequisites: Python3, Redis, Nginx, Git
# ============================================

set -e  # Exit on any error

REPO_DIR="/opt/shinetwoplay"
APP_DIR="/opt/shinetwoplay/shinetwoplay"
LOG_DIR="/var/log/shinetwoplay"

echo "======================================"
echo "  ShineTwo Play - Server Setup"
echo "======================================"

# ── Step 1: Create log directory ──
echo ""
echo "📁 [1/6] Creating log directory..."
sudo mkdir -p "$LOG_DIR"
sudo chown ubuntu:ubuntu "$LOG_DIR"

# ── Step 2: Check if code exists ──
if [ ! -f "$APP_DIR/manage.py" ]; then
    echo ""
    echo "❌ Code not found at $APP_DIR/manage.py"
    echo "   Make sure you cloned the repo correctly."
    exit 1
fi

# ── Step 3: Setup Python virtualenv ──
echo ""
echo "🐍 [2/6] Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ── Step 4: Collect static files ──
echo ""
echo "📁 [3/6] Collecting static files..."
DJANGO_SETTINGS_MODULE=shinetwoplay.settings_prod python manage.py collectstatic --noinput

# ── Step 5: Install systemd service ──
echo ""
echo "⚙️  [4/6] Installing Daphne systemd service..."
sudo cp "$APP_DIR/deploy/systemd/shinetwoplay.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable shinetwoplay
sudo systemctl start shinetwoplay

# ── Step 6: Configure Nginx ──
echo ""
echo "🌐 [5/6] Configuring Nginx..."
sudo cp "$APP_DIR/deploy/nginx/shinetwoplay.conf" /etc/nginx/sites-available/shinetwoplay
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/shinetwoplay /etc/nginx/sites-enabled/shinetwoplay
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# ── Verify ──
echo ""
echo "🔍 [6/6] Verifying services..."
echo ""
echo "  Redis:      $(sudo systemctl is-active redis-server)"
echo "  Daphne:     $(sudo systemctl is-active shinetwoplay)"
echo "  Nginx:      $(sudo systemctl is-active nginx)"

# ── Done! ──
echo ""
echo "======================================"
echo "  ✅ Setup Complete!"
echo "======================================"
echo ""
echo "  🌐 Your app is live at: http://$(curl -s ifconfig.me)"
echo ""
echo "  📋 Check status:"
echo "    sudo systemctl status shinetwoplay"
echo "    sudo systemctl status nginx"
echo "    sudo systemctl status redis-server"
echo ""
echo "  📜 View logs:"
echo "    tail -f $LOG_DIR/django.log"
echo "    tail -f $LOG_DIR/daphne.log"
echo "    tail -f $LOG_DIR/nginx-error.log"
echo ""
echo "  🔄 Future code updates:"
echo "    bash $APP_DIR/deploy/deploy.sh"
echo "======================================"
