import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import os
import sys
import aiohttp
import asyncio
import itertools
import platform
import datetime
import re
try:
    from flask import Flask, request, jsonify
    import threading
    flask_available = True
except ImportError:
    flask_available = False
import logging
from discord import FFmpegPCMAudio
import yt_dlp

# Imports for new modules
from fortnite_shop import fetch_fortnite_shop, build_shop_embeds
from fortnite_map import fetch_fortnite_map, build_map_embed
from fortnite_news import fetch_fortnite_news, build_news_embeds
from epic_free_games import fetch_epic_free_games, build_free_games_embeds
from embeds import build_startup_embed
from logger import log_bot_action

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

NEWS_CHANNEL_ID =  Channel-id  # Fortnite news channel ID
EPIC_FREE_GAMES_CHANNEL_ID = Channel-id  # Channel for Epic Games free games
STEAM_FREE_GAMES_CHANNEL_ID = Channel-id  # Channel for Steam free games
LOG_CHANNEL_ID = Channel-id  # Channel for bot logs

class DiscordLogHandler(logging.Handler):
    def __init__(self, bot, channel_id):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id

    def emit(self, record):
        log_entry = self.format(record)
        embed = discord.Embed(title="📝 Bot Log", description=log_entry[:2048], color=0xffcc00)
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            asyncio.run_coroutine_threadsafe(channel.send(embed=embed), self.bot.loop)

class TerminalLogStream:
    def __init__(self, bot, channel_id):
        self.bot = bot
        self.channel_id = channel_id
        self.buffer = ""

    def write(self, message):
        if message.strip() == "":
            return
        self.buffer += message
        if "\n" in self.buffer:
            lines = self.buffer.split("\n")
            for line in lines[:-1]:
                asyncio.run_coroutine_threadsafe(self.send_to_discord(line), self.bot.loop)
            self.buffer = lines[-1]

    def flush(self):
        if self.buffer:
            asyncio.run_coroutine_threadsafe(self.send_to_discord(self.buffer), self.bot.loop)
            self.buffer = ""

    async def send_to_discord(self, message):
        channel = self.bot.get_channel(self.channel_id)
        if channel and message.strip():
            embed = discord.Embed(title="🖥️ Terminal Log", description=message[:2048], color=0x888888)
            await channel.send(embed=embed)

if flask_available:
    app = Flask(__name__)

    @app.route('/webhook', methods=['POST'])
    def webhook():
        data = request.json
        channel = bot.get_channel(1375833494026064065)
        if channel:
            content = f"Webhook event received: {data}"
            asyncio.run_coroutine_threadsafe(channel.send(content), bot.loop)
        return jsonify({'status': 'received'}), 200

    def run_flask():
        app.run(host='0.0.0.0', port=5000)

    threading.Thread(target=run_flask, daemon=True).start()

async def fetch_fortnite_news():
    url = "https://fortnite-api.com/v2/news"  # Public Fortnite news API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    br_news = data.get('data', {}).get('br', {}).get('motds', [])
                    embeds = []
                    for item in br_news:
                        title = item.get('title', '')
                        body = item.get('body', '')
                        image = item.get('image', '')
                        embed = discord.Embed(title=title, description=body, color=0x00bfff)
                        if image:
                            embed.set_image(url=image)
                        embeds.append(embed)
                    return embeds if embeds else None
                else:
                    return None
    except Exception as e:
        print(f"[Network Error] Could not fetch Fortnite news: {e}")
        await log_bot_action(bot, f"Network error fetching Fortnite news: {e}", channel_id=1375833494026064065)
        return None

async def fetch_epic_free_games():
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US&allowCountries=US"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    games = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
                    free_games = []
                    for game in games:
                        title = game.get('title', 'Unknown')
                        description = game.get('description', 'No description.')
                        image = None
                        for img in game.get('keyImages', []):
                            if img.get('type', '').lower() in ['dieselstorefrontwide', 'offerimagewide', 'dieselstorefront']:
                                image = img.get('url')
                                break
                            elif not image:
                                image = img.get('url')
                        offer = game.get('productSlug')
                        url = f"https://store.epicgames.com/en-US/p/{offer}" if offer else "https://store.epicgames.com/en-US/free-games"
                        is_free = False
                        for promo_block in ['promotions', 'upcomingPromotions']:
                            promo_data = game.get(promo_block)
                            if not promo_data:
                                continue
                            for promo in promo_data.get('promotionalOffers', []):
                                for offer_detail in promo.get('promotionalOffers', []):
                                    if offer_detail.get('discountSetting', {}).get('discountPercentage') == 0:
                                        is_free = True
                        if is_free:
                            free_games.append({
                                'title': title,
                                'description': description,
                                'image': image,
                                'url': url
                            })
                    return free_games
                else:
                    return []
    except Exception as e:
        print(f"[Network Error] Could not fetch Epic Games free games: {e}")
        await log_bot_action(bot, f"Network error fetching Epic Games free games: {e}", channel_id=1375833494026064065)
        return []

async def fetch_steam_free_games():
    """
    Fetches current Steam free games from SteamDB (web scraping, as there is no public API for this).
    Returns a list of dicts: [{ 'title': ..., 'url': ... }]
    """
    url = "https://steamdb.info/upcoming/free/"
    free_games = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # Find all free game rows (very basic HTML parsing)
                    pattern = re.compile(r'<a href="(/app/\d+/)"[^>]*>([^<]+)</a>')
                    for match in pattern.finditer(text):
                        app_url, title = match.groups()
                        free_games.append({
                            'title': title.strip(),
                            'url': f'https://store.steampowered.com{app_url}'
                        })
    except Exception as e:
        await log_bot_action(bot, f"Error fetching Steam free games: {e}", channel_id=1375833494026064065)
    return free_games

async def send_fortnite_news():
    channel = bot.get_channel(NEWS_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, f"Channel with ID {NEWS_CHANNEL_ID} not found for Fortnite news.", channel_id=1375833494026064065)
        return
    embeds = await fetch_fortnite_news()
    if not embeds:
        embed = discord.Embed(title="Fortnite News", description="No Fortnite news found.", color=0x00bfff)
        await channel.send(embed=embed)
        await log_bot_action(bot, "No Fortnite news found.", channel_id=1375833494026064065)
        return
    for embed in embeds:
        await channel.send(embed=embed)
        await log_bot_action(bot, f"Posted Fortnite news: {embed.title}", channel_id=1375833494026064065)

async def send_epic_free_games():
    channel = bot.get_channel(EPIC_FREE_GAMES_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, f"Channel with ID {EPIC_FREE_GAMES_CHANNEL_ID} not found for Epic Games free games.", channel_id=1375833494026064065)
        return
    free_games = await fetch_epic_free_games()
    if not free_games:
        embed = discord.Embed(title="Epic Games Free Games", description="No free games found on Epic Games Store right now.", color=0x00ff99)
        await channel.send(embed=embed)
        await log_bot_action(bot, "No free games found on Epic Games Store.", channel_id=1375833494026064065)
        return
    embeds = build_free_games_embeds(free_games)
    for embed in embeds:
        await channel.send(embed=embed)
        await log_bot_action(bot, f"Posted Epic Games free game: {embed.title}", channel_id=1375833494026064065)

async def send_steam_free_games():
    channel = bot.get_channel(STEAM_FREE_GAMES_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Steam free games channel not found.", channel_id=1375833494026064065)
        return
    free_games = await fetch_steam_free_games()
    if not free_games:
        embed = discord.Embed(title="Steam Free Games", description="No free games found on Steam right now.", color=0x1b2838)
        await channel.send(embed=embed)
        await log_bot_action(bot, "No free games found on Steam.", channel_id=1375833494026064065)
        return
    for game in free_games[:5]:  # Limit to 5 for spam prevention
        embed = discord.Embed(title=f"🎮 {game['title']}", url=game['url'], description="Free for a limited time on Steam!", color=0x1b2838)
        embed.set_footer(text="Steam Free Game | Popkor Bot")
        await channel.send(embed=embed)
        await log_bot_action(bot, f"Posted Steam free game: {game['title']}", channel_id=1375833494026064065)

async def cycle_presence():
    # This is the maximum Rich Presence you can achieve with a Discord bot using discord.py
    # Only the application's icon will show as the large image (if set in the Developer Portal)
    activities = [
        discord.Activity(type=discord.ActivityType.watching, name="Epic Games & Fortnite News"),
        discord.Activity(type=discord.ActivityType.playing, name="popkor bot | /ping for latency"),
        discord.Activity(type=discord.ActivityType.listening, name="/stopbot | /testlog | /ping"),
        discord.Game(name="Epic Games & Fortnite News | popkor bot"),
    ]
    for activity in itertools.cycle(activities):
        await bot.change_presence(status=discord.Status.online, activity=activity)
        await asyncio.sleep(5)

bot_start_time = datetime.datetime.utcnow()

async def safe_fetch_fortnite_news():
    try:
        news_items = await fetch_fortnite_news()
        return build_news_embeds(news_items)
    except Exception as e:
        await log_bot_action(bot, f"Error fetching Fortnite news: {e}", channel_id=1375833494026064065)
        return None

async def safe_fetch_epic_free_games():
    try:
        return await fetch_epic_free_games()
    except Exception as e:
        await log_bot_action(bot, f"Error fetching Epic Games free games: {e}", channel_id=1375833494026064065)
        return []

@bot.tree.command(name="help", description="Show all bot commands and features.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Bot Help", color=0x5865F2)
    embed.add_field(name="/ping", value="Show the bot's latency in ms.", inline=False)
    embed.add_field(name="/stopbot", value="Stop the bot (owner only).", inline=False)
    embed.add_field(name="/testlog", value="Send a test log message to the log channel.", inline=False)
    embed.add_field(name="/news", value="Fetch and post the latest Fortnite news.", inline=False)
    embed.add_field(name="/freegames", value="Fetch and post the current Epic Games free games.", inline=False)
    embed.add_field(name="/about", value="Show info about the bot and invite link.", inline=False)
    embed.add_field(name="/uptime", value="Show how long the bot has been running.", inline=False)
    embed.set_footer(text="Popkor Bot | Epic Games & Fortnite News")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_bot_action(bot, "Help command used.", channel_id=1375833494026064065)

@bot.tree.command(name="news", description="Fetch and post the latest Fortnite news.")
async def news_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel = bot.get_channel(NEWS_CHANNEL_ID)
    embeds = await safe_fetch_fortnite_news()
    if channel and embeds:
        for embed in embeds:
            await channel.send(embed=embed)
            await log_bot_action(bot, f"/news command: Posted Fortnite news: {embed.title}", channel_id=1375833494026064065)
        await interaction.followup.send("Fortnite news posted!", ephemeral=True)
    else:
        await interaction.followup.send("No Fortnite news found or channel not found.", ephemeral=True)
        await log_bot_action(bot, "/news command: No Fortnite news found or channel not found.", channel_id=1375833494026064065)

@bot.tree.command(name="freegames", description="Fetch and post the current Epic Games free games.")
async def freegames_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel = bot.get_channel(EPIC_FREE_GAMES_CHANNEL_ID)
    free_games = await safe_fetch_epic_free_games()
    if channel and free_games:
        for game in free_games:
            embed = discord.Embed(
                title=f"🎮 {game['title']}",
                description=f"{game['description'][:200]}{'...' if len(game['description']) > 200 else ''}",
                color=0x00ff99
            )
            if game['image']:
                embed.set_image(url=game['image'])
            embed.set_footer(text="Epic Games Free Game | Click the button below to claim!")
            view = View()
            green_button = Button(label="🎁 Claim Game", url=game['url'], style=discord.ButtonStyle.success)
            view.add_item(green_button)
            await channel.send(embed=embed, view=view)
            await log_bot_action(bot, f"/freegames command: Posted Epic Games free game: {game['title']}", channel_id=1375833494026064065)
        await interaction.followup.send("Epic Games free games posted!", ephemeral=True)
    else:
        await interaction.followup.send("No free games found or channel not found.", ephemeral=True)
        await log_bot_action(bot, "/freegames command: No free games found or channel not found.", channel_id=1375833494026064065)

@bot.tree.command(name="steamfreegames", description="Fetch and post the current Steam free games.")
async def steamfreegames_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel = bot.get_channel(STEAM_FREE_GAMES_CHANNEL_ID)
    free_games = await fetch_steam_free_games()
    if channel and free_games:
        for game in free_games[:5]:
            embed = discord.Embed(
                title=f"🎮 {game['title']}",
                url=game['url'],
                description="Free for a limited time on Steam!",
                color=0x1b2838
            )
            embed.set_footer(text="Steam Free Game | Popkor Bot")
            await channel.send(embed=embed)
            await log_bot_action(bot, f"/steamfreegames command: Posted Steam free game: {game['title']}", channel_id=1375833494026064065)
        await interaction.followup.send("Steam free games posted!", ephemeral=True)
    else:
        await interaction.followup.send("No free games found or channel not found.", ephemeral=True)
        await log_bot_action(bot, "/steamfreegames command: No free games found or channel not found.", channel_id=1375833494026064065)

async def send_startup_status():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = build_startup_embed()
        await channel.send(embed=embed)

# --- Startup Tasks ---
async def startup_post_fortnite_news():
    channel = bot.get_channel(NEWS_CHANNEL_ID)
    embeds = await safe_fetch_fortnite_news()
    if channel:
        if embeds:
            for embed in embeds:
                await channel.send(embed=embed)
                await log_bot_action(bot, f"Posted Fortnite news: {embed.title}", channel_id=LOG_CHANNEL_ID)
        else:
            embed = discord.Embed(title="Fortnite News", description="No Fortnite news found.", color=0x00bfff)
            await channel.send(embed=embed)
            await log_bot_action(bot, "No Fortnite news found.", channel_id=LOG_CHANNEL_ID)
    else:
        print(f"Channel with ID {NEWS_CHANNEL_ID} not found.")
        await log_bot_action(bot, f"Channel with ID {NEWS_CHANNEL_ID} not found for Fortnite news.", channel_id=LOG_CHANNEL_ID)

async def startup_post_epic_free_games():
    await send_epic_free_games()

async def startup_post_steam_free_games():
    await send_steam_free_games()

async def startup_post_fortnite_map():
    await post_fortnite_map()

async def startup_post_fortnite_shop():
    await post_fortnite_shop()

async def startup_post_fortnite_creative_discovery():
    await post_fortnite_creative_discovery()

async def startup_post_fortnite_battlepass():
    await post_fortnite_battlepass()

async def startup_post_fortnite_crew():
    await post_fortnite_crew()

async def startup_post_fortnite_cosmetics():
    await post_fortnite_cosmetics()

async def startup_post_fortnite_playlists():
    await post_fortnite_playlists()

async def startup_post_fortnite_weapons():
    await post_fortnite_weapons()

async def startup_post_fortnite_achievements():
    await post_fortnite_achievements()

async def startup_post_fortnite_upcoming():
    await post_fortnite_upcoming()

async def startup_all():
    await startup_post_fortnite_news()
    await startup_post_epic_free_games()
    await startup_post_steam_free_games()
    await startup_post_fortnite_map()
    await startup_post_fortnite_shop()
    await startup_post_fortnite_creative_discovery()
    await startup_post_fortnite_battlepass()
    await startup_post_fortnite_crew()
    await startup_post_fortnite_cosmetics()
    await startup_post_fortnite_playlists()
    await startup_post_fortnite_weapons()
    await startup_post_fortnite_achievements()
    await startup_post_fortnite_upcoming()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Set up logging to Discord channel
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = DiscordLogHandler(bot, LOG_CHANNEL_ID)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    if not any(isinstance(h, DiscordLogHandler) for h in logger.handlers):
        logger.addHandler(handler)
    logger.info('Bot is online and logging to Discord!')
    # Redirect terminal output to Discord
    sys.stdout = TerminalLogStream(bot, LOG_CHANNEL_ID)
    sys.stderr = TerminalLogStream(bot, LOG_CHANNEL_ID)
    await bot.tree.sync()
    await send_startup_status()
    await log_bot_action(bot, "Bot is online and ready.", channel_id=LOG_CHANNEL_ID)
    # Start cycling Rich Presence
    bot.loop.create_task(cycle_presence())
    # Organized startup tasks
    await startup_all()
    # Start live stats loop
    bot.loop.create_task(live_stats_loop())

@bot.event
async def on_disconnect():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="❌ Bot Offline", description=f"The bot has gone offline. (Time: {discord.utils.format_dt(discord.utils.utcnow(), style='F')})", color=0xED4245)
        await channel.send(embed=embed)

@bot.tree.command(name="stopbot", description="Stop the bot (owner only)")
async def stopbot(interaction: discord.Interaction):
    owner_id = 847791089803984936  # Replace with your Discord user ID if needed
    if interaction.user.id != owner_id:
        embed = discord.Embed(title="Permission Denied", description="You do not have permission to stop the bot.", color=0xED4245)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_bot_action(bot, f"Unauthorized stopbot attempt by user {interaction.user.id}.", channel_id=1375833494026064065)
        return
    embed = discord.Embed(title="Bot Shutdown", description="Bot is shutting down...", color=0xED4245)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_bot_action(bot, f"Bot is shutting down by owner {interaction.user.id}.", channel_id=1375833494026064065)
    await bot.close()

@bot.tree.command(name="ping", description="Show the bot's latency in ms.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Latency: {latency}ms", color=0x5865F2)
    await interaction.response.send_message(embed=embed)
    await log_bot_action(bot, f"Responded to /ping with {latency}ms.", channel_id=1375833494026064065)

@bot.tree.command(name="testlog", description="Send a test log message to the log channel.")
async def testlog(interaction: discord.Interaction):
    embed = discord.Embed(title="✅ Test Log", description="This is a test log message. The bot is working!", color=0x43b581)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_bot_action(bot, "Test log command was used.", channel_id=1375833494026064065)

# Add a /uptime command to show how long the bot has been running
@bot.tree.command(name="uptime", description="Show how long the bot has been running.")
async def uptime_command(interaction: discord.Interaction):
    now = datetime.datetime.utcnow()
    delta = now - bot_start_time
    days, seconds = delta.days, delta.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    embed = discord.Embed(title="⏱️ Bot Uptime", description=f"Uptime: {uptime_str}", color=0x5865F2)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_bot_action(bot, f"Responded to /uptime: {uptime_str}", channel_id=1375833494026064065)

# Add error handler for commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    embed = discord.Embed(title="❌ Command Error", description=str(error), color=0xED4245)
    asyncio.create_task(interaction.response.send_message(embed=embed, ephemeral=True))
    asyncio.create_task(log_bot_action(bot, f"Command error: {error}", channel_id=1375833494026064065))

# Add a /about command for bot info and invite link
@bot.tree.command(name="about", description="Show info about the bot and invite link.")
async def about_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 About Popkor Bot", color=0x5865F2)
    embed.add_field(name="Features", value="Fortnite news, Epic Games free games, logging, webhooks, slash commands, and more!", inline=False)
    embed.add_field(name="Invite Link", value="[Invite Popkor Bot](https://discord.com/api/oauth2/authorize?client_id=1375832348553379850&permissions=8&scope=bot%20applications.commands)", inline=False)
    embed.set_footer(text="Created with discord.py | Popkor Bot")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_bot_action(bot, "About command used.", channel_id=1375833494026064065)

@bot.tree.command(name="coinflip", description="Flip a coin and get heads or tails.")
async def coinflip_command(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    emoji = "🪙" if result == "Heads" else "🪙"
    embed = discord.Embed(title="Coin Flip", description=f"{emoji} {result}", color=0xFFD700)
    await interaction.response.send_message(embed=embed)
    await log_bot_action(bot, f"Coin flip: {result}", channel_id=1375833494026064065)

# --- Fortnite API: Creative Discovery ---
async def post_fortnite_creative_discovery():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Creative Discovery channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v1/creative/discovery") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rows = data.get('data', {}).get('rows', [])
                    if not rows:
                        await channel.send("No creative discovery data found.")
                        return
                    for row in rows[:3]:
                        name = row.get('name', 'Unknown')
                        desc = row.get('description', 'No description.')
                        embed = discord.Embed(title=f"🎮 Creative Discovery: {name}", description=desc, color=0x00bfff)
                        await channel.send(embed=embed)
                    await log_bot_action(bot, "Posted Fortnite Creative Discovery.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite Creative Discovery: {e}", channel_id=1375833494026064065)

# --- Fortnite API: Battle Pass ---
async def post_fortnite_battlepass():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Battle Pass channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v2/battlepass/current") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bp = data.get('data', {})
                    name = bp.get('name', 'Battle Pass')
                    desc = bp.get('description', 'No description.')
                    image = bp.get('image', None)
                    embed = discord.Embed(title=f"🎟️ {name}", description=desc, color=0x00bfff)
                    if image:
                        embed.set_image(url=image)
                    await channel.send(embed=embed)
                    await log_bot_action(bot, "Posted Fortnite Battle Pass.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite Battle Pass: {e}", channel_id=1375833494026064065)

# --- Fortnite API: Crew ---
async def post_fortnite_crew():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Crew channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v2/crew/current") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    crew = data.get('data', {})
                    name = crew.get('name', 'Fortnite Crew')
                    desc = crew.get('description', 'No description.')
                    image = crew.get('image', None)
                    embed = discord.Embed(title=f"👑 {name}", description=desc, color=0x00bfff)
                    if image:
                        embed.set_image(url=image)
                    await channel.send(embed=embed)
                    await log_bot_action(bot, "Posted Fortnite Crew.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite Crew: {e}", channel_id=1375833494026064065)

# --- Fortnite API: Cosmetics (showcase 3) ---
async def post_fortnite_cosmetics():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Cosmetics channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v2/cosmetics/br") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get('data', [])
                    for item in items[:3]:
                        name = item.get('name', 'Unknown')
                        desc = item.get('description', 'No description.')
                        image = item.get('images', {}).get('icon', None)
                        embed = discord.Embed(title=f"🎨 Cosmetic: {name}", description=desc, color=0x00bfff)
                        if image:
                            embed.set_thumbnail(url=image)
                        await channel.send(embed=embed)
                    await log_bot_action(bot, "Posted Fortnite Cosmetics.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite Cosmetics: {e}", channel_id=1375833494026064065)

# --- Fortnite API: Playlists (LTMs) ---
async def post_fortnite_playlists():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Playlists channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v1/playlists") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    playlists = data.get('data', [])
                    for pl in playlists[:3]:
                        name = pl.get('name', 'Unknown')
                        desc = pl.get('description', 'No description.')
                        embed = discord.Embed(title=f"🎲 Playlist: {name}", description=desc, color=0x00bfff)
                        await channel.send(embed=embed)
                    await log_bot_action(bot, "Posted Fortnite Playlists.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite Playlists: {e}", channel_id=1375833494026064065)

# --- Fortnite API: Weapons (showcase 3) ---
async def post_fortnite_weapons():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Weapons channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v2/weapons") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    weapons = data.get('data', [])
                    for w in weapons[:3]:
                        name = w.get('name', 'Unknown')
                        desc = w.get('description', 'No description.')
                        image = w.get('images', {}).get('icon', None)
                        embed = discord.Embed(title=f"🔫 Weapon: {name}", description=desc, color=0x00bfff)
                        if image:
                            embed.set_thumbnail(url=image)
                        await channel.send(embed=embed)
                    await log_bot_action(bot, "Posted Fortnite Weapons.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite Weapons: {e}", channel_id=1375833494026064065)

# --- Fortnite API: Achievements (showcase 3) ---
async def post_fortnite_achievements():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Achievements channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v2/achievements") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    achievements = data.get('data', [])
                    for a in achievements[:3]:
                        name = a.get('name', 'Unknown')
                        desc = a.get('description', 'No description.')
                        embed = discord.Embed(title=f"🏆 Achievement: {name}", description=desc, color=0x00bfff)
                        await channel.send(embed=embed)
                    await log_bot_action(bot, "Posted Fortnite Achievements.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite Achievements: {e}", channel_id=1375833494026064065)

# --- Fortnite API: Upcoming Items (showcase 3) ---
async def post_fortnite_upcoming():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        await log_bot_action(bot, "Upcoming Items channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v2/cosmetics/br/upcoming") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get('data', [])
                    for item in items[:3]:
                        name = item.get('name', 'Unknown')
                        desc = item.get('description', 'No description.')
                        image = item.get('images', {}).get('icon', None)
                        embed = discord.Embed(title=f"⏳ Upcoming: {name}", description=desc, color=0x00bfff)
                        if image:
                            embed.set_thumbnail(url=image)
                        await channel.send(embed=embed)
                    await log_bot_action(bot, "Posted Fortnite Upcoming Items.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite Upcoming Items: {e}", channel_id=1375833494026064065)

async def update_fortnite_live_stats():
    channel = bot.get_channel(1376596132146450604)
    if not channel:
        await log_bot_action(bot, "Fortnite live stats channel not found.", channel_id=1375833494026064065)
        return
    try:
        async with aiohttp.ClientSession() as session:
            # Example API for Fortnite player count (replace with a real one if available)
            async with session.get("https://fortnite-api.com/v2/stats/br/players") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    players = data.get('data', {}).get('total', 'N/A')
                else:
                    players = 'N/A'
            # Improved Fortnite server status parsing and display
            async with session.get("https://fortnite-api.com/v2/status") as resp:
                if resp.status == 200:
                    status_data = await resp.json()
                    status_info = status_data.get('data', {})
                    status = status_info.get('status', 'Unknown')
                    # Show more details if available
                    maintenance = status_info.get('maintenance', False)
                    message = status_info.get('message', '')
                    update = status_info.get('update', '')
                    status_display = f"{status}"
                    if maintenance:
                        status_display += " (Maintenance)"
                    if message:
                        status_display += f"\n{message}"
                    if update:
                        status_display += f"\nUpdate: {update}"
                else:
                    status = 'Unavailable'
                    status_display = 'Unavailable'
        players_display = players if players not in ('N/A', None, '', 0) else 'Unavailable'
        embed = discord.Embed(title="Fortnite Live Stats", color=0x00bfff)
        embed.add_field(name="Live Players", value=str(players_display), inline=True)
        embed.add_field(name="Server Status", value=status_display, inline=True)
        if players_display == 'Unavailable' or status_display == 'Unavailable':
            embed.description = "Live player count or server status is currently unavailable. This may be due to API limitations."
        embed.set_footer(text="Updated live | Popkor Bot")
        # Try to find the last bot message and edit it, else send new
        async for msg in channel.history(limit=10):
            if msg.author == bot.user and msg.embeds and msg.embeds[0].title == "Fortnite Live Stats":
                await msg.edit(embed=embed)
                break
        else:
            await channel.send(embed=embed)
        await log_bot_action(bot, f"Updated Fortnite live stats: Players={players}, Status={status}", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error updating Fortnite live stats: {e}", channel_id=1375833494026064065)

async def live_stats_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await update_fortnite_live_stats()
        await asyncio.sleep(60)  # Update every 60 seconds

async def post_fortnite_map():
    channel = bot.get_channel(1376600328820097054)
    if not channel:
        await log_bot_action(bot, "Fortnite map channel not found.", channel_id=1375833494026064065)
        return
    try:
        map_image = await fetch_fortnite_map()
        if map_image:
            embed = build_map_embed(map_image)
            await channel.send(embed=embed)
            await log_bot_action(bot, "Posted current Fortnite map image.", channel_id=1375833494026064065)
        else:
            await channel.send("Could not fetch the Fortnite map image.")
            await log_bot_action(bot, "Fortnite map image not found in API response.", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite map: {e}", channel_id=1375833494026064065)

async def post_fortnite_shop():
    channel = bot.get_channel(1376600679786745856)
    if not channel:
        await log_bot_action(bot, "Fortnite shop channel not found.", channel_id=1375833494026064065)
        return
    try:
        # Update the API endpoint to the correct Fortnite shop endpoint
        async with aiohttp.ClientSession() as session:
            async with session.get("https://fortnite-api.com/v2/shop") as resp:
                if resp.status == 200:
                    shop_data = await resp.json()
                    shop_data = shop_data.get('data', {})
                else:
                    shop_data = None
        if not shop_data:
            await channel.send("Could not fetch the Fortnite shop (no data found).")
            await log_bot_action(bot, "Fortnite shop data not found in API response.", channel_id=1375833494026064065)
            return
        embeds = build_shop_embeds(shop_data)
        for embed in embeds:
            await channel.send(embed=embed)
        await log_bot_action(bot, f"Posted Fortnite shop ({len(embeds)} items).", channel_id=1375833494026064065)
    except Exception as e:
        await log_bot_action(bot, f"Error posting Fortnite shop: {e}", channel_id=1375833494026064065)

if __name__ == "__main__":
    # Get token from environment variable or file
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token and os.path.exists("token.txt"):
        with open("token.txt", "r") as f:
            token = f.read().strip()
    if not token:
        print("Error: Discord bot token not found. Set DISCORD_BOT_TOKEN env variable or create token.txt.")
        exit(1)
    bot.run(token)