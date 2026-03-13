# ShineTwoPlay ☀️

**A world built for just two players** — where connection, creativity, and fun come together.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

ShineTwoPlay is a real-time multiplayer gaming platform designed for **2 players**. Play games, chat, voice call, and compete — all in your browser with no downloads or sign-ups required.

> When the two of us play, the world becomes brighter. ✨

---

## 🎮 16 Multiplayer Games

| # | Game | Type | Description |
|---|------|------|-------------|
| 1 | **Ludo** | Turn-based | Classic Ludo! Roll the dice and race your pieces home |
| 2 | **Tic Tac Toe** | Turn-based | Classic 3×3 grid — get 3 in a row to win |
| 3 | **Paddle Arena** | Real-time | Pong with obstacles — don't miss the ball! |
| 4 | **Connect 4** | Turn-based | Drop discs to connect 4 in a row |
| 5 | **Beach Ball** | Real-time | Push the ball into your opponent's goal with stones |
| 6 | **Carrom** | Turn-based | Pocket all your coins before your opponent |
| 7 | **Diamond Heist** | Real-time | Grab the diamond when the case opens! |
| 8 | **Timber Chop** | Real-time | Race to chop 100 logs — dodge the branches! |
| 9 | **Snakes** | Real-time | 2-player snake battle — outlast your opponent |
| 10 | **Pull The Rope** | Real-time | Tap as fast as you can to pull the rope! |
| 11 | **Bamboo Breaker** | Real-time | Panda tile-breaking battle on cracking bamboo |
| 12 | **Simon Duel** | Turn-based | Memory battle — extend and repeat color sequences |
| 13 | **Pattern Clash** | Turn-based | See a pattern for 3 seconds, then recreate it |
| 14 | **Memory** | Turn-based | Flip cards and find matching pairs |
| 15 | **Bingo** | Turn-based | Classic Bingo showdown — complete a line first |
| 16 | **Dots & Boxes** | Turn-based | Draw lines to complete boxes — most boxes wins |

---

## 💬 Premium Chat & Communication

- **Glassmorphism UI** — Beautiful, premium interface with smooth animations
- **WebRTC Voice Calling** — Speak live while playing, with auto-reconnect
- **Voice Messages** — Record and send voice notes (up to 60 seconds)
- **Image Sharing** — Send pictures directly in the room
- **Interactive Chat** — Typing indicators, emoji reactions, smart input handling

## 🏠 Real-Time Rooms

- **WebSocket Connectivity** — Powered by Django Channels & Redis
- **Room Management** — Dynamic 4-letter room codes, automatic owner assignment
- **Lobby System** — Host picks the game and rounds (1, 3, or 5), both players ready up
- **Quick Share** — 1-click room link sharing

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2 |
| Real-time | Django Channels 4.0 |
| Database | SQLite |
| Channel Layer | Redis (`channels-redis`) |
| Server | Daphne (ASGI) |
| Production | Nginx + Certbot SSL + Daphne |

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.8+
- Redis Server (running on `localhost:6379`)
- Git

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/nikh27/shinetwoplay.git
cd shinetwoplay/shinetwoplay

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and set your DJANGO_SECRET_KEY
# Generate one: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 5. Apply database migrations
python manage.py migrate

# 6. Start Redis server (must be running on port 6379)

# 7. Run the development server
daphne -p 8000 shinetwoplay.asgi:application
```

Open **http://localhost:8000** and start playing!

---

## 🌍 Production Deployment (Ubuntu/EC2)

> HTTPS is **required** for microphone/WebRTC access.

1. Map your domain to your server IP via A Records
2. Install Nginx and Certbot:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```
3. Copy the Nginx configuration:
   ```bash
   sudo cp deploy/nginx/shinetwoplay.conf /etc/nginx/sites-available/shinetwoplay
   sudo ln -s /etc/nginx/sites-available/shinetwoplay /etc/nginx/sites-enabled/
   ```
4. Get an SSL Certificate:
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```
5. Run the deployment script:
   ```bash
   bash deploy/deploy.sh
   ```

---

## 📁 Project Structure

```
shinetwoplay/
├── games/              # All game modules (auto-discovered)
│   ├── base.py         # BaseGameHandler — extend this to create games
│   ├── tictactoe/      # Example: handler.py + game.html + __init__.py
│   ├── carrom/
│   ├── ... (16 games)
│   └── __init__.py     # Auto-discovery registry
├── rooms/              # Room management, WebSocket consumers
│   ├── consumers.py    # Main WebSocket logic (chat, lobby, WebRTC)
│   ├── games_list.py   # Static catalog of all games
│   ├── redis_client.py # Redis helper functions
│   └── templates/      # HTML templates (room.html, home.html)
├── shinetwoplay/       # Django project settings
│   ├── settings.py     # Development settings
│   └── settings_prod.py# Production settings (env vars)
├── deploy/             # Nginx configs and deployment scripts
├── media/              # User uploads (images, voice notes)
└── manage.py
```

### 🔒 Rate Limiting & Security

| Action | Limit |
|--------|-------|
| Chat messages | 10 / 10 seconds |
| Voice messages | 5 / 60 seconds |
| Image uploads | 10 / 60 seconds |
| Emoji reactions | 20 / 60 seconds |

Usernames enforce strict length/character validation. All games run securely without blocking the event loop.

---

## 🤝 Contributing

Contributions are welcome! You can:

- 🐛 **Report bugs** — [Open an issue](https://github.com/nikh27/shinetwoplay/issues)
- 💡 **Suggest features** — [Open an issue](https://github.com/nikh27/shinetwoplay/issues)
- 🎮 **Submit a game** — Create a standalone HTML file or fully integrate it
- 🔧 **Fix bugs** — Fork, fix, and submit a PR

👉 **Read the full [Contributing Guide](CONTRIBUTING.md)** for details on how to get started.

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

## 🛡️ Security

To report a security vulnerability, please see [SECURITY.md](SECURITY.md).

## 📋 Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

---

Made with ❤️ by [Nikhil Pandey](https://github.com/nikh27)
