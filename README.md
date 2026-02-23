# ShineTwoPlay

ShineTwoPlay is a world built for just two players — a place where connection, creativity, and fun come together. Inspired by the warmth of sunshine and the joy of companionship, this platform represents the bright bond between two people who choose to play, grow, and shine together.

Every match, every moment, every victory on ShineTwoPlay reflects a simple idea: when the two of us play, the world becomes brighter.


## ✨ Features

### 🎮 8 Multiplayer Games
Play a variety of real-time synchronized games with animated UI and score tracking:
- **Tic Tac Toe**
- **Connect 4**
- **Paddle Arena** (Pong)
- **Timber Chop** (Treecutter)
- **Carrom**
- **Snakes**
- **Diamond Heist** (Stealth Ring)
- **Beach Ball** (Volleyball)

### 💬 Premium Chat & Communication
- **Glassmorphism UI**: Beautiful, premium interface with smooth bounce animations and soft shadows.
- **WebRTC Voice Calling**: Speak live with your opponent while playing games! Auto-reconnects symmetrically if either player drops.
- **Voice Messages**: Record and send voice notes up to 60 seconds directly in the chat.
- **Image Sharing**: Send pictures directly in the room.
- **Interactive Chat**: Typing indicators, emoji reactions to messages, and smart input handling that won't freeze your virtual keyboard.

### 🏠 Real-Time Rooms
- **WebSocket Connectivity**: Powered by Django Channels and Redis for low-latency state synchronization.
- **Room Management**: Dynamic room creation via 4-letter codes. Automatic owner assignment.
- **Lobby System & Matchmaking**: 
  - Host configures the game and number of rounds (1, 3, or 5).
  - Both players must mark themselves as "Ready" to start.
- **Quick Share**: 1-click room link sharing (copies to clipboard or fallback textarea).

---

## 🛠️ Tech Stack

- **Backend Framework**: Django 4.2
- **Real-time WebSockets**: Django Channels 4.0
- **Database**: SQLite (Default)
- **Channel Layer**: Redis (via `channels-redis`)
- **Server**: Daphne (ASGI)
- **Production**: Nginx + Certbot (Let's Encrypt SSL) + Gunicorn/Daphne

---

## 🚀 Installation (Local Development)

### Prerequisites

- Python 3.8+
- Redis Server (running on `localhost:6379`)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd shinetwoplay/shinetwoplay
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Start Redis Server**
   Ensure your Redis server is running locally on port 6379.

6. **Run the Development Server**
   ```bash
   daphne -p 8000 shinetwoplay.asgi:application
   ```

---

## 🌍 Production Deployment (Ubuntu/EC2)

To deploy with **HTTPS** (required for microphone/WebRTC access) using Nginx and Certbot:

1. Map your domain (e.g., `shinetwoplay.online`) to your server IP via A Records.
2. Install Nginx and Certbot:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```
3. Copy the provided Nginx configuration:
   ```bash
   sudo cp deploy/nginx/shinetwoplay.conf /etc/nginx/sites-available/shinetwoplay
   sudo ln -s /etc/nginx/sites-available/shinetwoplay /etc/nginx/sites-enabled/
   ```
4. Get an SSL Certificate:
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```
5. Run the deployment script to start Daphne in the background:
   ```bash
   bash deploy/deploy.sh
   ```

---

## 📁 Project Structure

```
shinetwoplay/
├── games/              # Game specific logic, HTML templates, and backend Handlers
├── rooms/              # Room management, WebSocket consumers (chat, lobby, WebRTC)
│   ├── consumers.py    # Main WebSocket logic for rooms
│   ├── models.py       # Database models for Room, Player, Message
│   ├── redis_client.py # Redis helper functions
│   └── templates/      # HTML templates (room.html, home.html)
├── shinetwoplay/       # Project settings (settings.py, settings_prod.py, asgi.py)
├── deploy/             # Nginx configs and deployment bash scripts
├── media/              # User uploaded media (images, voice notes)
└── manage.py
```

### Rate Limiting & Security
To prevent spam, the following limits are enforced per user:
- **Chat**: 10 messages / 10 seconds
- **Voice**: 5 messages / 60 seconds
- **Images**: 10 messages / 60 seconds
- **Reactions**: 20 reactions / 60 seconds
- Extracted games run securely without blocking the event loop. Usernames enforce strict length/character validation.
