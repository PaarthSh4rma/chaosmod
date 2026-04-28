# ChaosMod

A chaos-powered Discord bot that roasts users, tracks humiliation stats, and keeps dead chats alive.

## Features

- `/roast` with adjustable levels (mild → nuclear)
- Persistent roast tracking (SQLite)
- `/roastboard` leaderboard
- `/roaststats` personal stats
- Slash command interface

## Tech Stack

- Python (discord.py)
- Async architecture
- SQLite (aiosqlite)
- Environment-based config

## Setup

```bash
git clone ...
pip install -r requirements.txt
```
create .env
```text
DISCORD_TOKEN=your_token
```
run
```bash
python bot.py
```
