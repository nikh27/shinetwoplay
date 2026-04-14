# 🌍 Open Source Contribution Guide
### From Zero to First Pull Request — A Complete Guide for Everyone

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Open Source Love](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-red.svg)](https://opensource.org/)
[![GitHub Issues](https://img.shields.io/github/issues/nikh27/shinetwoplay)](https://github.com/nikh27/shinetwoplay/issues)

**This guide uses [ShineTwoPlay](https://github.com/nikh27/shinetwoplay) as a real example, but the workflow applies to ANY open source project on GitHub.**

</div>

---

## 📋 Table of Contents

| # | Section | Level |
|---|---------|-------|
| 1 | [What is Open Source?](#-what-is-open-source) | Beginner |
| 2 | [Prerequisites](#-prerequisites) | Beginner |
| 3 | [Key Concepts (Visual Guide)](#-key-concepts-visual-guide) | Beginner |
| 4 | [Your First Contribution (Step-by-Step)](#-your-first-contribution-step-by-step) | Beginner |
| 5 | [Working with Branches](#-working-with-branches) | Intermediate |
| 6 | [Making Changes & Committing](#-making-changes--committing) | Intermediate |
| 7 | [Creating a Pull Request](#-creating-a-pull-request) | Intermediate |
| 8 | [Keeping Your Fork in Sync](#-keeping-your-fork-in-sync) | Intermediate |
| 9 | [Handling Code Reviews](#-handling-code-reviews) | Intermediate |
| 10 | [Resolving Merge Conflicts](#-resolving-merge-conflicts) | Advanced |
| 11 | [Squashing Commits](#-squashing-commits) | Advanced |
| 12 | [Using Multiple GitHub Accounts](#-using-multiple-github-accounts) | Advanced |
| 13 | [Open Source Etiquette](#-open-source-etiquette) | Everyone |
| 14 | [Quick Reference Cheat Sheet](#-quick-reference-cheat-sheet) | Everyone |

---

## 🔓 What is Open Source?

Open source means the **source code is publicly available**. Anyone can view, use, modify, and contribute to it.

```
┌─────────────────────────────────────────────────────────┐
│                    OPEN SOURCE                          │
│                                                         │
│   👀 VIEW      →  Read all the source code              │
│   🍴 FORK      →  Make your own copy on GitHub          │
│   ✏️  MODIFY    →  Change code in your copy              │
│   🤝 CONTRIBUTE →  Submit changes back to the project   │
│   📦 USE       →  Use it in your own projects           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 📜 Understanding Licenses

Every open source project has a **license** that defines the rules:

| License | What It Means |
|---------|--------------|
| **MIT** ⭐ | Do almost anything, just include the license. Most permissive. |
| **Apache 2.0** | Like MIT but includes patent protection |
| **GPL** | Must open-source your derivative work too |
| **BSD** | Similar to MIT with slight variations |

> ⚠️ **Always check a project's `LICENSE` file before contributing.** ShineTwoPlay uses the **MIT License** — one of the most open and permissive licenses.

---

## 🛠 Prerequisites

### 1. Install Git

```bash
# Check if Git is already installed
git --version

# If not installed:
# Windows → Download from https://git-scm.com/download/win
# macOS   → brew install git
# Linux   → sudo apt install git
```

### 2. Configure Git (One-Time Setup)

```bash
# Set your identity (use the email linked to your GitHub account!)
git config --global user.name "Your Full Name"
git config --global user.email "your-email@example.com"

# Verify your config
git config --list
```

### 3. Create a GitHub Account

Go to [github.com](https://github.com) → Sign up → Done! 🎉

---

## 🧠 Key Concepts (Visual Guide)

### The Open Source Workflow

```
   ┌────────────────────┐
   │   ORIGINAL REPO    │ ← The project you want to contribute to
   │  (called UPSTREAM)  │
   └───────┬────────────┘
           │
       🍴 FORK (on GitHub)
           │
   ┌───────▼────────────┐
   │    YOUR FORK       │ ← Your personal copy on GitHub
   │  (called ORIGIN)    │
   └───────┬────────────┘
           │
       📥 CLONE (to your PC)
           │
   ┌───────▼────────────┐
   │   LOCAL MACHINE    │ ← Where you write code
   │  (your computer)    │
   └───────┬────────────┘
           │
       ✏️  MAKE CHANGES
       💾 COMMIT
       📤 PUSH (to your fork)
           │
   ┌───────▼────────────┐
   │    YOUR FORK       │
   │  (on GitHub)        │
   └───────┬────────────┘
           │
       📩 PULL REQUEST
           │
   ┌───────▼────────────┐
   │   ORIGINAL REPO    │ ← Maintainer reviews & merges
   │  (UPSTREAM)         │
   └────────────────────┘
```

### Glossary

| Term | Meaning | Analogy |
|------|---------|---------|
| **Repository** | A project folder tracked by Git | 📁 A project folder |
| **Fork** | Your copy of someone else's repo | 📋 Photocopying a document |
| **Clone** | Download a repo to your computer | ⬇️ Downloading a file |
| **Branch** | A parallel version for isolated changes | 🌿 A tree branch |
| **Commit** | A saved snapshot of changes | 💾 Saving a game checkpoint |
| **Push** | Upload commits to GitHub | 📤 Uploading to the cloud |
| **Pull Request (PR)** | Request to merge your changes | ✉️ Sending a proposal |
| **Upstream** | The original repo you forked from | 🏠 The main headquarters |
| **Origin** | Your forked copy on GitHub | 🏡 Your personal copy |
| **Merge** | Combining changes together | 🔀 Mixing two ingredients |
| **Conflict** | Two people edited the same line | ⚔️ Two edits collided |

---

## 🚀 Your First Contribution (Step-by-Step)

### 📖 Step 0: Read the Project Docs First!

Before writing any code, **always read these files**:

```
✅ README.md          → What the project does, how to set it up
✅ CONTRIBUTING.md    → Rules and guidelines for contributing
✅ CODE_OF_CONDUCT.md → Behavioral expectations
✅ LICENSE            → Legal terms
✅ Open Issues        → Find what needs help (look for "good first issue" label!)
```

### 🍴 Step 1: Fork the Repository

1. Go to the project: `https://github.com/nikh27/shinetwoplay`
2. Click the **"Fork"** button (top-right corner)
3. GitHub creates your copy at `https://github.com/YOUR-USERNAME/shinetwoplay`

```
  ┌─────────────────────────┐         ┌─────────────────────────┐
  │ nikh27/shinetwoplay     │  FORK   │ YOUR-NAME/shinetwoplay  │
  │ (Original)              │ ──────► │ (Your Copy)             │
  └─────────────────────────┘         └─────────────────────────┘
```

### 📥 Step 2: Clone Your Fork

```bash
# Clone YOUR fork (not the original!)
git clone https://github.com/YOUR-USERNAME/shinetwoplay.git

# Navigate into the project
cd shinetwoplay
```

### 🔗 Step 3: Add Upstream Remote

This links your local copy to the **original** repo so you can stay in sync:

```bash
# Add the original repo
git remote add upstream https://github.com/nikh27/shinetwoplay.git

# Verify — you should see BOTH "origin" and "upstream"
git remote -v
```

**Expected output:**
```
origin    https://github.com/YOUR-USERNAME/shinetwoplay.git (fetch)
origin    https://github.com/YOUR-USERNAME/shinetwoplay.git (push)
upstream  https://github.com/nikh27/shinetwoplay.git (fetch)
upstream  https://github.com/nikh27/shinetwoplay.git (push)
```

```
  ┌──────────────┐
  │   UPSTREAM   │ ← github.com/nikh27/shinetwoplay (original)
  └──────┬───────┘
         │ git fetch upstream
  ┌──────▼───────┐
  │  YOUR LOCAL  │ ← Your computer
  └──────┬───────┘
         │ git push origin
  ┌──────▼───────┐
  │   ORIGIN     │ ← github.com/YOUR-USERNAME/shinetwoplay (your fork)
  └──────────────┘
```

### ⚙️ Step 4: Set Up the Project Locally

Follow the project's README. For **ShineTwoPlay**:

```bash
cd shinetwoplay    # Enter the Django project directory

# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy the environment file
cp .env.example .env
# Edit .env and set your DJANGO_SECRET_KEY

# Start Redis server (must be running on port 6379)

# Run the development server
daphne -p 8000 shinetwoplay.asgi:application

# Open http://localhost:8000 in your browser 🎉
```

> 💡 **Always verify the project runs locally BEFORE making any changes!**

---

## 🌿 Working with Branches

> **Golden Rule: NEVER work directly on `main`. Always create a feature branch.**

```
main ─────────────────────────────────────────────────────
       \                                      /
        \─── feat/add-chess-game ────────────/  ← Your work happens here
```

### Create a Branch

```bash
# Make sure you're on the latest main
git checkout main
git pull upstream main

# Create and switch to a new branch
git checkout -b feat/add-chess-game
```

### Branch Naming Convention

```
<type>/<short-description>

Examples:
  feat/add-chess-game        → New feature
  fix/carrom-collision-bug   → Bug fix
  docs/update-readme         → Documentation
  style/dark-mode-fix        → UI/CSS changes
  refactor/game-state-logic  → Code refactoring
  test/add-tictactoe-tests   → Adding tests
```

| Prefix | When to Use |
|--------|------------|
| `feat/` | Adding a new feature or game |
| `fix/` | Fixing a bug |
| `docs/` | Documentation updates |
| `style/` | UI, CSS, formatting changes |
| `refactor/` | Code restructuring (no new features) |
| `test/` | Adding or updating tests |
| `chore/` | Maintenance tasks |

---

## ✏️ Making Changes & Committing

### 1. Make Your Changes

Edit files as needed. For ShineTwoPlay:

| Contribution | What to Edit |
|-------------|-------------|
| 🐛 Bug report | Open an Issue on GitHub |
| 🎮 Simple game | Add `.html` file to `new_game_html_folder/` |
| 🎮 Full game | Create files in `games/yourgame/` (see [CONTRIBUTING.md](CONTRIBUTING.md)) |
| 🔧 Bug fix | Fix the relevant source files |
| 📝 Docs | Edit `README.md`, `CONTRIBUTING.md`, etc. |

### 2. Check & Stage Your Changes

```bash
# See what files changed
git status

# See actual code changes (line by line)
git diff

# Stage specific files
git add path/to/changed-file.py
git add path/to/another-file.html

# Or stage ALL changes at once
git add .
```

```
  Working Directory          Staging Area           Repository
  (your edits)               (ready to commit)      (saved history)
                git add                  git commit
  ┌──────────┐ ──────────► ┌──────────┐ ──────────► ┌──────────┐
  │ Modified  │             │  Staged  │             │ Committed│
  │   files   │             │  files   │             │ snapshot │
  └──────────┘              └──────────┘             └──────────┘
```

### 3. Commit with a Clear Message

```bash
git commit -m "feat: add chess game with turn-based logic"
```

#### Commit Message Format

```
<type>: <short description>

Types:
  feat:     → New feature
  fix:      → Bug fix
  docs:     → Documentation
  style:    → Formatting, CSS (no logic change)
  refactor: → Code restructuring
  test:     → Adding tests
  chore:    → Maintenance / tooling
```

**Good Examples:**
```
✅ feat: add memory match game
✅ fix: carrom ball collision on mobile
✅ docs: update README with new games
✅ style: clean up tictactoe CSS
```

**Bad Examples:**
```
❌ "fixed stuff"
❌ "update"
❌ "asdfgh"
❌ "changes"
```

> ⚠️ **One commit = one logical change.** Don't mix unrelated changes in a single commit.

---

## 📩 Creating a Pull Request

### 1. Push Your Branch to GitHub

```bash
git push origin feat/add-chess-game
```

### 2. Open a Pull Request

1. Go to your fork on GitHub
2. You'll see a yellow banner: **"Compare & pull request"** — click it!
3. Fill in the details:

```markdown
## What does this PR do?
Added a chess game with full turn-based multiplayer support.

## Type of change
- [x] New feature (game)
- [ ] Bug fix
- [ ] Documentation update

## How to test
1. Run the server locally
2. Create a room → Select "Chess"
3. Play with two browser tabs

## Screenshots
(Attach screenshots or GIFs)
```

4. Make sure **base** = `main` on the original repo
5. Click **"Create pull request"** 🎉

```
  YOUR FORK (GitHub)                    ORIGINAL REPO (GitHub)
  ┌──────────────────┐                  ┌──────────────────┐
  │ feat/chess-game  │ ── PULL REQUEST ──►│      main       │
  └──────────────────┘     (review)      └──────────────────┘
                                                 │
                                            ✅ MERGED!
```

---

## 🔄 Keeping Your Fork in Sync

The original project keeps updating. **Sync regularly** to avoid conflicts:

```bash
# 1. Switch to main
git checkout main

# 2. Fetch latest changes from original repo
git fetch upstream

# 3. Merge upstream into your local main
git merge upstream/main

# 4. Push updated main to YOUR fork
git push origin main
```

### Update Your Working Branch

```bash
# Switch to your feature branch
git checkout feat/add-chess-game

# Rebase your changes on top of latest main
git rebase main
```

```
  BEFORE SYNC:
  upstream/main:  A ── B ── C ── D ── E     (original has new commits)
  your main:      A ── B ── C               (your fork is behind)

  AFTER SYNC:
  your main:      A ── B ── C ── D ── E     (now up to date! ✅)
```

> 💡 **Sync your fork BEFORE starting new work and BEFORE creating a PR.**

---

## 🔍 Handling Code Reviews

After you submit a PR, a maintainer will review it:

```
  YOU submit PR
       │
       ▼
  ┌────────────────┐
  │ MAINTAINER     │
  │ REVIEWS CODE   │
  └───────┬────────┘
          │
    ┌─────┼──────────────┐
    │     │              │
    ▼     ▼              ▼
  ✅       💬             ❓
 APPROVED  CHANGES       QUESTIONS
           REQUESTED
    │      │              │
    │      ▼              ▼
    │   Fix code &     Reply in
    │   push again     PR comments
    │      │
    ▼      ▼
  🎉 MERGED!
```

### Making Changes After Review

```bash
# Fix the requested changes in your code
# Then commit and push to the SAME branch

git add .
git commit -m "fix: address review feedback - improve error handling"
git push origin feat/add-chess-game

# The PR updates automatically — no need to create a new one!
```

---

## ⚔️ Resolving Merge Conflicts

Conflicts happen when two people change the **same lines** of code:

```bash
# When you try to merge or rebase, Git shows:
git merge main
# CONFLICT in game.py
```

**The file will have conflict markers:**
```python
<<<<<<< HEAD (your changes)
def calculate_score(player):
    return player.points * 2
=======
def calculate_score(player):
    return player.points + bonus
>>>>>>> main (their changes)
```

**How to resolve:**

1. Open the file
2. **Choose** which version to keep (or combine both):
```python
def calculate_score(player):
    return player.points * 2 + bonus   # Combined both changes
```
3. **Remove** the `<<<<<<<`, `=======`, `>>>>>>>` markers
4. Stage and commit:
```bash
git add game.py
git commit -m "fix: resolve merge conflict in score calculation"
```

```
  CONFLICT:
  Your code:  ──── A ── B ──── X (your edit)
                              ╲
  Their code: ──── A ── B ──── Y (their edit)     CONFLICT! ⚔️

  RESOLVED:
  Merged:     ──── A ── B ──── Z (you combined both)  ✅
```

---

## 📦 Squashing Commits

Maintainers may ask you to **squash** many small commits into one clean one:

```bash
# Squash the last 3 commits into one
git rebase -i HEAD~3
```

In the editor:
```
pick abc1234 feat: add chess board
squash def5678 fix: typo in chess
squash ghi9012 style: clean up CSS
```

Change `pick` to `squash` (or `s`) for all but the first. Save, write a new message.

```bash
# Force push (ONLY to YOUR feature branch, NEVER to main!)
git push origin feat/add-chess-game --force
```

```
  BEFORE SQUASH:
    commit 1: "add chess board"
    commit 2: "fix typo"
    commit 3: "clean CSS"

  AFTER SQUASH:
    commit 1: "feat: add chess game with board UI"    ← Clean! ✨
```

---

## 🔑 Using Multiple GitHub Accounts

If you have a **second GitHub account** and want to contribute from it:

### Option A: HTTPS (Simple)

```bash
# Clone with your second account
git clone https://github.com/SECOND-ACCOUNT/shinetwoplay.git

# If Git uses cached credentials from your primary account:
# Windows → Control Panel → Credential Manager → Windows Credentials
#           → Find "github.com" → Remove it
# Git will prompt you to log in with your second account
```

### Option B: SSH Keys (Recommended)

```
  ┌─────────────────┐         ┌────────────────────┐
  │ Primary Account │         │  Second Account     │
  │ ~/.ssh/id_ed25519│         │ ~/.ssh/id_second    │
  │ Host: github.com│         │ Host: github-second │
  └────────┬────────┘         └────────┬────────────┘
           │                           │
           └──────────┬────────────────┘
                      │
              ~/.ssh/config
              (routes each host
               to correct key)
```

**Step 1: Generate SSH key for second account**
```bash
ssh-keygen -t ed25519 -C "second@email.com" -f ~/.ssh/id_ed25519_second
```

**Step 2: Add to ssh-agent**
```bash
# Start ssh-agent
eval "$(ssh-agent -s)"

# Add both keys
ssh-add ~/.ssh/id_ed25519           # primary
ssh-add ~/.ssh/id_ed25519_second    # second
```

**Step 3: Configure `~/.ssh/config`**
```
# Primary GitHub account
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519

# Second GitHub account
Host github-second
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_second
```

**Step 4: Add public key to GitHub**
```bash
cat ~/.ssh/id_ed25519_second.pub
# Copy output → GitHub → Settings → SSH Keys → New SSH Key → Paste
```

**Step 5: Clone using custom host**
```bash
# Instead of: git@github.com:SECOND-ACCOUNT/shinetwoplay.git
git clone git@github-second:SECOND-ACCOUNT/shinetwoplay.git
```

**Step 6: Set per-repo identity**
```bash
cd shinetwoplay
git config user.name "Second Account Name"
git config user.email "second@email.com"
# Without --global, this applies ONLY to this repo
```

---

## 📜 Open Source Etiquette

### ✅ DO These

```
✅  Read CONTRIBUTING.md and CODE_OF_CONDUCT.md first
✅  Search existing issues before creating new ones
✅  Comment "I'd like to work on this!" before starting
✅  Keep PRs small and focused (1 feature/fix per PR)
✅  Write clear commit messages
✅  Test your changes locally before submitting
✅  Be respectful and patient — maintainers are volunteers
✅  Respond promptly to review feedback
✅  Give credit where it's due
✅  Start with small contributions (typo fixes, docs) to build trust
```

### ❌ DON'T Do These

```
❌  Don't submit untested code
❌  Don't make massive PRs with unrelated changes
❌  Don't ignore the project's code style guidelines
❌  Don't be rude if your PR isn't reviewed immediately
❌  Don't push directly to main
❌  Don't copy code without attribution
❌  Don't open duplicate issues
❌  Don't spam maintainers for reviews
❌  Don't force push to shared branches
```

### Your Contribution Journey

```
  🌱 Beginner                🌿 Intermediate              🌳 Advanced
  ─────────────────────      ─────────────────────        ─────────────────
  ★ Star the repo            ★ Fix bugs                   ★ Add new features
  ★ Report bugs              ★ Improve documentation      ★ Review others' PRs
  ★ Fix typos                ★ Submit simple games         ★ Mentor newcomers
  ★ Improve README           ★ Add tests                  ★ Architecture changes
```

---

## 📌 Quick Reference Cheat Sheet

### 🔟 Complete Workflow in 10 Steps

```bash
# 1. Fork the repo on GitHub (browser) 🍴

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/shinetwoplay.git
cd shinetwoplay

# 3. Add upstream remote
git remote add upstream https://github.com/nikh27/shinetwoplay.git

# 4. Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# 5. Create a feature branch
git checkout -b feat/my-awesome-feature

# 6. Make changes, then stage them
git add .

# 7. Commit with a clear message
git commit -m "feat: add awesome feature"

# 8. Push to your fork
git push origin feat/my-awesome-feature

# 9. Open a Pull Request on GitHub (browser) 📩

# 10. After PR is merged, clean up 🧹
git checkout main
git pull upstream main
git push origin main
git branch -d feat/my-awesome-feature
```

### 📖 Essential Commands

| Command | What It Does |
|---------|-------------|
| `git clone <url>` | Download a repo |
| `git status` | Check current state |
| `git diff` | See uncommitted changes |
| `git add .` | Stage all changes |
| `git commit -m "msg"` | Save a snapshot |
| `git push origin <branch>` | Upload to GitHub |
| `git pull upstream main` | Get latest from original |
| `git checkout -b <branch>` | Create & switch to new branch |
| `git checkout main` | Switch to main branch |
| `git log --oneline -10` | View last 10 commits |
| `git stash` | Temporarily save changes |
| `git stash pop` | Restore stashed changes |
| `git remote -v` | List remote connections |
| `git branch` | List local branches |
| `git branch -d <name>` | Delete a local branch |
| `git fetch upstream` | Download upstream changes |
| `git merge upstream/main` | Merge upstream into main |
| `git rebase main` | Rebase branch on latest main |

---

## 🎯 ShineTwoPlay Contribution Map

| What You Can Do | Files to Touch | Difficulty |
|----------------|---------------|-----------|
| 🐛 Report a bug | GitHub Issue (use bug template) | ⭐ |
| 💡 Suggest a feature | GitHub Issue (use feature template) | ⭐ |
| 📝 Improve documentation | `README.md`, `CONTRIBUTING.md` | ⭐ |
| 🎮 Submit a simple game | Add `.html` to `new_game_html_folder/` | ⭐⭐ |
| 🎨 Improve UI/CSS | Templates in `rooms/templates/` | ⭐⭐ |
| 🔧 Fix a bug | Relevant source files | ⭐⭐ |
| 🎮 Fully integrate a game | `games/yourgame/` + `rooms/games_list.py` | ⭐⭐⭐ |

👉 **Read the full [Contributing Guide](CONTRIBUTING.md) for project-specific instructions.**

---

<div align="center">

### 🌟 Remember: Every Expert Was Once a Beginner

Your first PR might be fixing a typo — and that's **perfectly fine!**

The open source community values **every** contribution.

**Happy Contributing! 🎉**

---

Made with ❤️ for the open source community

</div>
