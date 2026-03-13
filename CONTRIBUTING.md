# Contributing to ShineTwoPlay

Thank you for your interest in contributing to **ShineTwoPlay**! Whether you want to report a bug, suggest a feature, submit a game idea, or write code — you're welcome here.

This guide will walk you through everything step by step.

---

## 📋 Table of Contents

- [Ways to Contribute](#ways-to-contribute)
- [Reporting Bugs](#-reporting-bugs)
- [Suggesting Features / Ideas](#-suggesting-features--ideas)
- [Contributing a New Game](#-contributing-a-new-game)
  - [Option A: Submit a Standalone HTML Game](#option-a-submit-a-standalone-html-game-easy)
  - [Option B: Fully Integrate a Game](#option-b-fully-integrate-a-game-advanced)
- [Fixing Bugs or Improving Code](#-fixing-bugs-or-improving-code)
- [Development Setup](#-development-setup)
- [Code Style Guidelines](#-code-style-guidelines)
- [Commit Message Convention](#-commit-message-convention)
- [Pull Request Process](#-pull-request-process)

---

## Ways to Contribute

| Type | Difficulty | Description |
|------|-----------|-------------|
| 🐛 Bug Report | Easy | Found something broken? Tell us! |
| 💡 Feature Request | Easy | Have an idea? Share it! |
| 🎮 Submit a Game (HTML only) | Medium | Create a 2-player game as a single HTML file |
| 🎮 Integrate a Game (Full) | Advanced | Build and wire a game into the multiplayer system |
| 🔧 Bug Fix / Code Improvement | Medium–Advanced | Fix issues or improve existing code |

---

## 🐛 Reporting Bugs

Found a bug? Please [open an issue](https://github.com/nikh27/shinetwoplay/issues/new) with:

1. **Title**: Short, descriptive title (e.g., "Carrom: Ball goes through wall on mobile")
2. **Description**: What happened vs. what you expected
3. **Steps to Reproduce**:
   - Step 1: Go to...
   - Step 2: Click on...
   - Step 3: See error
4. **Screenshots/Videos**: If possible, attach screenshots or recordings
5. **Environment**: Browser name/version, device type (desktop/mobile)

> **Label your issue** with `bug` when creating it.

---

## 💡 Suggesting Features / Ideas

Have an idea to make ShineTwoPlay better? [Open an issue](https://github.com/nikh27/shinetwoplay/issues/new) with:

1. **Title**: What you'd like to see (e.g., "Add emoji reactions in game chat")
2. **Description**: Explain the idea in detail
3. **Why**: How does this improve the experience?
4. **Mockups**: Attach any sketches or UI ideas if you have them

> **Label your issue** with `enhancement` or `feature-request`.

---

## 🎮 Contributing a New Game

ShineTwoPlay is built around **2-player real-time games**. There are two ways to contribute a game:

### Option A: Submit a Standalone HTML Game (Easy)

If you're not comfortable with Django/WebSockets, you can still contribute! Just build a **single HTML file** with a fun 2-player game — we'll handle the integration.

**What to do:**

1. Create a single `.html` file with your game (HTML + CSS + JavaScript — all in one file)
2. The game should be **2-player** (played on the same screen or turn-based)
3. Include a simple UI with player scores and a restart button
4. Name your file after the game (e.g., `my_awesome_game.html`)
5. Place it in the **root directory** of the project (alongside the other `.html` files like `bingo.html`, `corridor.html`)
6. Open a Pull Request with:
   - A description of the game
   - How to play (rules)
   - A screenshot or GIF showing the game

**Example standalone games in the repo:**  
Look at files in the root directory like `bingo.html`, `corridor.html`, `shipbattle.html` for reference.

> We'll review your game and integrate it into the multiplayer system if it's a good fit!

---

### Option B: Fully Integrate a Game (Advanced)

If you know Django and WebSockets, you can fully wire a game into the multiplayer system.

**Each game requires 3 files** inside a new folder under `shinetwoplay/games/`:

```
shinetwoplay/games/yourgame/
├── __init__.py        # Empty file (required for Python)
├── handler.py         # Game backend logic (extends BaseGameHandler)
└── game.html          # Game frontend UI
```

#### Step 1: Create `handler.py`

Your handler must extend `BaseGameHandler` from `games/base.py`:

```python
from games.base import BaseGameHandler
from rooms.redis_client import get_game_state, set_game_state, clear_game_state

class YourGameHandler(BaseGameHandler):
    game_id = "yourgame"          # Must match your folder name
    game_name = "Your Game Name"  # Display name
    game_mode = "turn_based"      # or "real_time"
    min_players = 2
    max_players = 2

    def initialize(self, room_code, players, total_rounds):
        """Set up the initial game state"""
        state = {
            'players': players,
            'current_round': 1,
            'total_rounds': total_rounds,
            'scores': {p: 0 for p in players},
            # ... your game-specific state
        }
        set_game_state(room_code, state)
        return state

    def handle_move(self, room_code, player, action, data):
        """Process a player's action"""
        state = get_game_state(room_code)
        # ... your game logic
        set_game_state(room_code, state)
        return {'state': state}

    def start_next_round(self, room_code):
        """Reset state for the next round"""
        state = get_game_state(room_code)
        # ... reset round-specific state
        state['current_round'] += 1
        set_game_state(room_code, state)
        return {'state': state, 'round_started': True}
```

> 📖 **Reference**: Look at `shinetwoplay/games/tictactoe/handler.py` for a complete example.

#### Step 2: Create `game.html`

This is the in-game UI that gets injected into the room page. The WebSocket connection is already available.

> 📖 **Reference**: Look at any existing `game.html` inside `shinetwoplay/games/tictactoe/` for structure.

#### Step 3: Register in Games List

Add your game to `shinetwoplay/rooms/games_list.py`:

```python
{
    'game_id': 'yourgame',
    'name': 'Your Game Name',
    'image_url': '/static/games/yourgame.png',
    'description': 'Short description of your game.',
    'min_players': 2,
    'max_players': 2,
},
```

#### Step 4: Add a Game Icon

Place a game icon image at `shinetwoplay/static/games/yourgame.png` (recommended: 200×200px PNG).

#### Step 5: Create an Empty `__init__.py`

```bash
# Create the empty init file
touch shinetwoplay/games/yourgame/__init__.py
```

> The game will be **auto-discovered** — no additional registration code is needed! The system scans `shinetwoplay/games/` for folders with `handler.py` on startup.

---

## 🔧 Fixing Bugs or Improving Code

1. Browse [open issues](https://github.com/nikh27/shinetwoplay/issues) for bugs to fix
2. Comment on the issue to let others know you're working on it
3. Fork → Branch → Fix → PR (see [Pull Request Process](#-pull-request-process) below)

---

## 🛠 Development Setup

### Prerequisites
- Python 3.8+
- Redis Server (running on `localhost:6379`)
- Git

### Steps

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/shinetwoplay.git
cd shinetwoplay/shinetwoplay

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the environment file and configure
cp .env.example .env
# Edit .env and set your DJANGO_SECRET_KEY (see .env.example for instructions)

# 5. Apply database migrations
python manage.py migrate

# 6. Start Redis server (must be running)
# Ubuntu: sudo service redis-server start
# macOS:  brew services start redis
# Windows: Use Redis for Windows or WSL

# 7. Run the development server
daphne -p 8000 shinetwoplay.asgi:application

# 8. Open http://localhost:8000 in your browser
```

---

## 📝 Code Style Guidelines

- **Python**: Follow [PEP 8](https://peps.python.org/pep-0008/). Use 4 spaces for indentation.
- **HTML/CSS/JS**: Use 4 spaces for indentation. Keep game files self-contained.
- **Naming**: Use `snake_case` for Python files and variables, `camelCase` for JavaScript.
- **Comments**: Write comments for complex logic. Docstrings for all Python functions.
- **No hardcoded secrets**: Always use environment variables for sensitive values.

---

## 📌 Commit Message Convention

Use clear, descriptive commit messages:

```
<type>: <short description>

Examples:
feat: add memory match game
fix: carrom ball collision on mobile
docs: update README with new games
style: clean up tictactoe CSS
refactor: simplify game state initialization
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

---

## 🚀 Pull Request Process

1. **Fork** the repository on GitHub
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/your-game-name
   # or
   git checkout -b fix/bug-description
   ```
3. **Make your changes** following the guidelines above
4. **Test your changes** locally — make sure nothing is broken
5. **Commit** with a clear message
6. **Push** to your fork:
   ```bash
   git push origin feat/your-game-name
   ```
7. **Open a Pull Request** against `main` on [github.com/nikh27/shinetwoplay](https://github.com/nikh27/shinetwoplay)
8. In your PR description, include:
   - What you changed and why
   - Screenshots/GIFs if it's a visual change
   - Link to the related issue (if any)

### PR Review

- The maintainer will review your PR
- You may be asked to make changes — this is normal!
- Once approved, your PR will be merged 🎉

---

## 💬 Questions?

If you have any questions about contributing, feel free to [open a discussion](https://github.com/nikh27/shinetwoplay/discussions) or [create an issue](https://github.com/nikh27/shinetwoplay/issues/new).

Thank you for helping make ShineTwoPlay better! ☀️
