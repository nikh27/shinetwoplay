#!/bin/bash
# ============================================
#  ShineTwo Play - Code Update Script
#  Run this on EC2 after pushing new code
# ============================================

set -e  # Exit on any error

APP_DIR="/opt/shinetwoplay"
VENV="$APP_DIR/venv"
LOG_DIR="/var/log/shinetwoplay"

echo "🚀 Deploying ShineTwo Play..."

# Pull latest code
cd "$APP_DIR"
echo "📥 Pulling latest code..."
git pull

# Activate virtualenv
source "$VENV/bin/activate"

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

# Collect static files
echo "📁 Collecting static files..."
DJANGO_SETTINGS_MODULE=shinetwoplay.settings_prod python manage.py collectstatic --noinput

# Restart Daphne
echo "🔄 Restarting Daphne..."
sudo systemctl restart shinetwoplay

# Show status
echo ""
echo "✅ Deployment complete!"
echo ""
sudo systemctl status shinetwoplay --no-pager
echo ""
echo "📋 Recent logs:"
tail -5 "$LOG_DIR/daphne.log" 2>/dev/null || echo "  (no logs yet)"
