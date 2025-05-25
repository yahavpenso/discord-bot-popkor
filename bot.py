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
try:
    from flask import Flask, request, jsonify
    import threading
    flask_available = True
except ImportError:
    flask_available = False
import logging
from discord import FFmpegPCMAudio
import yt_dlp

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

NEWS_CHANNEL_ID = 1375833494026064066  # Fortnite news channel ID
EPIC_FREE_GAMES_CHANNEL_ID = 1375833494026064067  # Channel for Epic Games free games
LOG_CHANNEL_ID = 1375833494026064065  # Channel for bot logs

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
        await log_bot_action(f"Network error fetching Fortnite news: {e}")
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
        await log_bot_action(f"Network error fetching Epic Games free games: {e}")
        return []

async def log_bot_action(message: str):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        try:
            embed = discord.Embed(title="🤖 Bot Action", description=message, color=0x5865F2)
            await channel.send(embed=embed)
            terminal_embed = discord.Embed(title="🖥️ Terminal", description=message, color=0x888888)
            await channel.send(embed=terminal_embed)
        except Exception as e:
            print(f"[Log Error] Could not send log to Discord: {e}")
    else:
        print("[Log Error] Log channel not found.")

async def send_epic_free_games():
    channel = bot.get_channel(EPIC_FREE_GAMES_CHANNEL_ID)
    if not channel:
        await log_bot_action(f"Channel with ID {EPIC_FREE_GAMES_CHANNEL_ID} not found for Epic Games free games.")
        return
    free_games = await fetch_epic_free_games()
    if not free_games:
        embed = discord.Embed(title="Epic Games Free Games", description="No free games found on Epic Games Store right now.", color=0x00ff99)
        await channel.send(embed=embed)
        await log_bot_action("No free games found on Epic Games Store.")
        return
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
        await log_bot_action(f"Posted Epic Games free game: {game['title']}")

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
        return await fetch_fortnite_news()
    except Exception as e:
        await log_bot_action(f"Error fetching Fortnite news: {e}")
        return None

async def safe_fetch_epic_free_games():
    try:
        return await fetch_epic_free_games()
    except Exception as e:
        await log_bot_action(f"Error fetching Epic Games free games: {e}")
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
    await log_bot_action("Help command used.")

@bot.tree.command(name="news", description="Fetch and post the latest Fortnite news.")
async def news_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel = bot.get_channel(NEWS_CHANNEL_ID)
    embeds = await safe_fetch_fortnite_news()
    if channel and embeds:
        for embed in embeds:
            await channel.send(embed=embed)
            await log_bot_action(f"/news command: Posted Fortnite news: {embed.title}")
        await interaction.followup.send("Fortnite news posted!", ephemeral=True)
    else:
        await interaction.followup.send("No Fortnite news found or channel not found.", ephemeral=True)
        await log_bot_action("/news command: No Fortnite news found or channel not found.")

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
            await log_bot_action(f"/freegames command: Posted Epic Games free game: {game['title']}")
        await interaction.followup.send("Epic Games free games posted!", ephemeral=True)
    else:
        await interaction.followup.send("No free games found or channel not found.", ephemeral=True)
        await log_bot_action("/freegames command: No free games found or channel not found.")

async def send_startup_status():
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="✅ Bot Started", color=0x43b581)
        embed.add_field(name="Bot Version", value="1.0.0", inline=True)
        embed.add_field(name="Python Version", value=platform.python_version(), inline=True)
        embed.add_field(name="discord.py Version", value=discord.__version__, inline=True)
        embed.add_field(name="Uptime", value="0 seconds", inline=True)
        embed.timestamp = datetime.datetime.utcnow()
        await channel.send(embed=embed)

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
    await log_bot_action("Bot is online and ready.")
    # Start cycling Rich Presence
    bot.loop.create_task(cycle_presence())
    # Fortnite news
    channel = bot.get_channel(NEWS_CHANNEL_ID)
    embeds = await safe_fetch_fortnite_news()
    if channel:
        if embeds:
            for embed in embeds:
                await channel.send(embed=embed)
                await log_bot_action(f"Posted Fortnite news: {embed.title}")
        else:
            embed = discord.Embed(title="Fortnite News", description="No Fortnite news found.", color=0x00bfff)
            await channel.send(embed=embed)
            await log_bot_action("No Fortnite news found.")
    else:
        print(f"Channel with ID {NEWS_CHANNEL_ID} not found.")
        await log_bot_action(f"Channel with ID {NEWS_CHANNEL_ID} not found for Fortnite news.")
    # Epic Games free games
    await send_epic_free_games()
    # Send a test message for Epic Games free games
    test_channel = bot.get_channel(EPIC_FREE_GAMES_CHANNEL_ID)
    if test_channel:
        test_embed = discord.Embed(
            title="🎮 Test Game",
            description="This is a test free game from Epic Games Store!",
            color=0x00ff99
        )
        test_embed.set_image(url="https://static-cdn.jtvnw.net/jtv_user_pictures/6e7e2e2e-7e2e-4e2e-8e2e-2e2e2e2e2e-profile_image-300x300.png")
        test_embed.set_footer(text="Epic Games Free Game | Click the button below to claim!")
        test_view = View()
        test_green_button = Button(label="🎁 Claim Game", url="https://store.epicgames.com/en-US/free-games", style=discord.ButtonStyle.success)
        test_view.add_item(test_green_button)
        await test_channel.send(embed=test_embed, view=test_view)
        await log_bot_action("Posted test Epic Games free game embed.")

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
        await log_bot_action(f"Unauthorized stopbot attempt by user {interaction.user.id}.")
        return
    embed = discord.Embed(title="Bot Shutdown", description="Bot is shutting down...", color=0xED4245)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_bot_action(f"Bot is shutting down by owner {interaction.user.id}.")
    await bot.close()

@bot.tree.command(name="ping", description="Show the bot's latency in ms.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Latency: {latency}ms", color=0x5865F2)
    await interaction.response.send_message(embed=embed)
    await log_bot_action(f"Responded to /ping with {latency}ms.")

@bot.tree.command(name="testlog", description="Send a test log message to the log channel.")
async def testlog(interaction: discord.Interaction):
    embed = discord.Embed(title="✅ Test Log", description="This is a test log message. The bot is working!", color=0x43b581)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_bot_action("Test log command was used.")

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
    await log_bot_action(f"Responded to /uptime: {uptime_str}")

# Add error handler for commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    embed = discord.Embed(title="❌ Command Error", description=str(error), color=0xED4245)
    asyncio.create_task(interaction.response.send_message(embed=embed, ephemeral=True))
    asyncio.create_task(log_bot_action(f"Command error: {error}"))

# Add a /about command for bot info and invite link
@bot.tree.command(name="about", description="Show info about the bot and invite link.")
async def about_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 About Popkor Bot", color=0x5865F2)
    embed.add_field(name="Features", value="Fortnite news, Epic Games free games, logging, webhooks, slash commands, and more!", inline=False)
    embed.add_field(name="Invite Link", value="[Invite Popkor Bot](https://discord.com/api/oauth2/authorize?client_id=1375832348553379850&permissions=8&scope=bot%20applications.commands)", inline=False)
    embed.set_footer(text="Created with discord.py | Popkor Bot")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_bot_action("About command used.")

@bot.tree.command(name="coinflip", description="Flip a coin and get heads or tails.")
async def coinflip_command(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    emoji = "🪙" if result == "Heads" else "🪙"
    embed = discord.Embed(title="Coin Flip", description=f"{emoji} {result}", color=0xFFD700)
    await interaction.response.send_message(embed=embed)
    await log_bot_action(f"Coin flip: {result}")