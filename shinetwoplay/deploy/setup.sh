#!/bin/bash
# ============================================
#  ShineTwo Play - First Time Server Setup
#  Run this ONCE on a fresh EC2 Ubuntu instance
# ============================================

set -e  # Exit on any error

APP_DIR="/opt/shinetwoplay"
LOG_DIR="/var/log/shinetwoplay"

echo "======================================"
echo "  ShineTwo Play - Server Setup"
echo "======================================"

# ── Step 1: Update system ──
echo ""
echo "📦 [1/8] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# ── Step 2: Install dependencies ──
echo ""
echo "📦 [2/8] Installing Python, Redis, Nginx, Git..."
sudo apt install -y python3 python3-pip python3-venv redis-server nginx git

# ── Step 3: Create log directory ──
echo ""
echo "📁 [3/8] Creating log directory..."
sudo mkdir -p "$LOG_DIR"
sudo chown ubuntu:ubuntu "$LOG_DIR"

# ── Step 4: Setup app directory ──
echo ""
echo "📁 [4/8] Setting up app directory..."
sudo mkdir -p "$APP_DIR"
sudo chown ubuntu:ubuntu "$APP_DIR"

echo ""
echo "======================================"
echo "  Now you need to get your code onto the server."
echo "  Choose ONE option:"
echo ""
echo "  Option A - Git Clone:"
echo "    cd $APP_DIR"
echo "    git clone <YOUR_REPO_URL> ."
echo ""
echo "  Option B - SCP Upload (from your Windows PC):"
echo "    scp -i your-key.pem -r ./shinetwoplay/* ubuntu@<EC2_IP>:$APP_DIR/"
echo ""
echo "  After uploading code, run this script again with: $0 --continue"
echo "======================================"

if [ "$1" != "--continue" ]; then
    exit 0
fi

# ── Step 5: Setup Python virtualenv ──
echo ""
echo "🐍 [5/8] Setting up Python virtual environment..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ── Step 6: Collect static & migrate ──
echo ""
echo "🗄️  [6/8] Running migrations & collecting static files..."
DJANGO_SETTINGS_MODULE=shinetwoplay.settings_prod python manage.py migrate --noinput
DJANGO_SETTINGS_MODULE=shinetwoplay.settings_prod python manage.py collectstatic --noinput

# ── Step 7: Install systemd service ──
echo ""
echo "⚙️  [7/8] Installing Daphne systemd service..."
sudo cp "$APP_DIR/deploy/systemd/shinetwoplay.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable shinetwoplay
sudo systemctl start shinetwoplay

# ── Step 8: Configure Nginx ──
echo ""
echo "🌐 [8/8] Configuring Nginx..."
sudo cp "$APP_DIR/deploy/nginx/shinetwoplay.conf" /etc/nginx/sites-available/shinetwoplay
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/shinetwoplay /etc/nginx/sites-enabled/shinetwoplay
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

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
echo "  🔄 Future deployments:"
echo "    bash $APP_DIR/deploy/deploy.sh"
echo "======================================"
