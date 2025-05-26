# Popkor Bot - games NEWS📣

A powerful Discord bot for Fortnite, Epic Games, and Steam news, free games, and more!

---

## 📊 Bot Stats (as of 2025-05-26)
- **Language:** Python 3.11
- **Framework:** discord.py
- **Main File:** bot.py
- **Commands:** 18+ rich slash commands
- **Channels Supported:** Fortnite news, Epic Games, Steam, logs, and more
- **Logging:** All actions/errors sent to a dedicated log channel

---

## 🛠️ Features
- 📰 **Fortnite News:** Posts the latest Fortnite news as rich embeds
- 🎮 **Epic Games Free Games:** Notifies about current free games on Epic Games Store with claim buttons
- 🎮 **Steam Free Games:** Notifies about current Steam free games (auto and on command)
- 📝 **Logging:** Sends bot actions and errors as embed logs to a dedicated channel
- 🖥️ **Terminal Output:** Redirects terminal output to Discord as embeds for easy monitoring
- 🔄 **Rich Presence:** Cycles through custom statuses to show bot activity
- ⚙️ **Slash Commands:** Use `/help` to see all available commands and features
- 🌐 **Webhooks:** Receives and posts external events to a channel
- 🪙 **Coin Flip:** Try `/coinflip` for a fun random heads/tails result!
- Modular, robust error handling, and easy to extend

---

## 📝 All Slash Commands
- `/help` — Show all bot commands and features
- `/ping` — Show the bot's latency in ms
- `/stopbot` — Stop the bot (owner only)
- `/testlog` — Send a test log message to the log channel
- `/news` — Fetch and post the latest Fortnite news
- `/freegames` — Fetch and post the current Epic Games free games
- `/steamfreegames` — Fetch and post the current Steam free games
- `/uptime` — Show how long the bot has been running
- `/about` — Show info about the bot and invite link
- `/coinflip` — Flip a coin and get heads or tails
- `/shop` — Post the current Fortnite shop as rich embeds
- `/map` — Show the latest Fortnite map image
- `/crew` — Post the current Fortnite Crew pack info
- `/battlepass` — Show the current Fortnite Battle Pass
- `/cosmetics` — Showcase new Fortnite cosmetics
- `/playlists` — List current Fortnite playlists/LTMs
- `/weapons` — Show new or featured Fortnite weapons
- `/achievements` — Post new Fortnite achievements
- `/upcoming` — Show upcoming Fortnite items
- `/livestats` — Show live Fortnite player/server stats

---

## 🌐 APIs & Data Sources
- **Fortnite News, Shop, Map, Cosmetics, etc.:** [fortnite-api.com](https://fortnite-api.com/)
- **Epic Games Free Games:** [Epic Games Store API](https://store-site-backend-static.ak.epicgames.com/)
- **Steam Free Games:** [SteamDB](https://steamdb.info/upcoming/free/) (web scraping)

---

## 🚀 Quick Start
1. Clone this repo and install requirements (`pip install discord.py aiohttp flask`)
2. Add your bot token to `token.txt` or set the `DISCORD_BOT_TOKEN` environment variable
3. Run the bot: `python bot.py` or use the provided batch/script files

---

## 🔒 Permissions & Channel Setup
- The bot requires the following permissions: `Send Messages`, `Embed Links`, `Read Message History`, `Manage Messages` (for cleanup), and `Use Slash Commands`.
- Recommended: Create dedicated channels for:
  - Fortnite News
  - Epic Games Free Games
  - Steam Free Games (can share with news)
  - Bot Logs (private, for errors and actions)
- Set the correct channel IDs in `bot.py` if you want to customize where each feature posts.

---

## ⚙️ Environment Variables & Configuration
- `DISCORD_BOT_TOKEN`: Your Discord bot token (required)
- `token.txt`: Alternatively, place your token in this file (one line, no spaces)
- Optional: Set up a `.env` file for local development

---

## 🛠️ Troubleshooting & Tips
- If the bot does not respond to slash commands, make sure it has the correct permissions and is invited with the `applications.commands` scope.
- If you see errors about missing modules, run `pip install -r requirements.txt` or install `discord.py`, `aiohttp`, and `flask` manually.
- For API issues, check the status of [fortnite-api.com](https://fortnite-api.com/) and [Epic Games Store](https://store.epicgames.com/).
- For Steam free games, the bot scrapes SteamDB and may miss some offers if the site layout changes.
- All logs and errors are sent to your configured log channel for easy debugging.

---

## 📚 Resources & Documentation
- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Fortnite-API Docs](https://dash.fortnite-api.com/docs)
- [Epic Games Free Games Info](https://store.epicgames.com/en-US/free-games)
- [SteamDB Free Games](https://steamdb.info/upcoming/free/)

---

## 🏆 Example Use Cases
- Auto-post Fortnite news and shop updates to your gaming community
- Alert your server to new free games on Epic and Steam
- Centralize all bot logs and errors for easy monitoring
- Use `/help` to discover all features and commands

---

## 📢 Contributing & Support
- PRs and suggestions welcome!
- For issues, open a GitHub issue or contact the maintainer.
