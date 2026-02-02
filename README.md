# ShineTwoPlay

ShineTwoPlay is a real-time, two-player game platform built with Django and Django Channels. It features interactive game rooms with rich communication capabilities including text, voice, and image messaging, along with game session management.

## Features

### Real-Time Rooms
- **WebSocket Connectivity**: Powered by Django Channels and Redis for low-latency communication.
- **Room Management**: 
  - Dynamic room creation and joining via room codes.
  - Strict 2-player capacity enforcement.
  - Duplicate username detection.
  - Automatic owner assignment.

### Rich Communication
- **Chat System**: Real-time text messaging with rate limiting (10 messages per 10 seconds).
- **Multimedia Support**: 
  - Voice messages (up to 60 seconds).
  - Image sharing support.
- **Interactive Elements**:
  - Typing indicators.
  - Message reactions (emoji support).
  - Online/Offline status tracking.

### Game Session Control
- **Lobby System**: 
  - Players can mark themselves as "Ready".
  - Room owners can configure game settings (selection, number of rounds).
- **Game Orchestration**:
  - Support for selecting different games.
  - Round configuration (1, 3, or 5 rounds).
  - Synchronized game start for all players.

## Tech Stack

- **Backend Framework**: Django 4.2
- **Real-time WebSockets**: Django Channels 4.0
- **Database**: SQLite (Default)
- **Channel Layer**: Redis (via `channels-redis`)
- **Server**: Daphne (ASGI)

## Prerequisites

- Python 3.8+
- Redis Server (running on `localhost:6379`)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd shinetwoplay
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
   pip install -r shinetwoplay/requirements.txt
   ```

4. **Apply database migrations**
   ```bash
   cd shinetwoplay
   python manage.py migrate
   ```

5. **Start Redis Server**
   Ensure your Redis server is running locally on port 6379.
   ```bash
   # Example command if you have redis-server installed
   redis-server
   ```

6. **Run the Development Server**
   ```bash
   python manage.py runserver
   ```
   
   Or run with Daphne for production-like behavior:
   ```bash
   daphne -p 8000 shinetwoplay.asgi:application
   ```

## Project Structure

```
shinetwoplay/
├── games/              # Game specific logic and consumers
├── rooms/              # Room management, WebSocket consumers (chat, lobby)
│   ├── consumers.py    # Main WebSocket logic for rooms
│   ├── models.py       # Database models for Room, Player, Message
│   ├── redis_client.py # Redis helper functions
│   └── templates/      # HTML templates
├── shinetwoplay/       # Project settings and configuration
├── media/              # User uploaded media (images, voice)
└── manage.py
```

## detailed Feature Implementation

### Rate Limiting
To prevent spam, the following limits are enforced per user:
- **Chat**: 10 messages / 10 seconds
- **Voice**: 5 messages / 60 seconds
- **Images**: 10 messages / 60 seconds
- **Reactions**: 20 reactions / 60 seconds

### Room Logic
- **Room Code**: Unique identifier for users to join.
- **Ownership**: The creator of the room is the owner and has special privileges (selecting games, changing rounds, starting the game).
- **State Sync**: Complete room state is synced to clients upon reconnection or specific events.
