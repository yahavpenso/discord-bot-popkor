import discord
import platform
import datetime

BOT_VERSION = "1.0.0"

def build_startup_embed():
    embed = discord.Embed(title="✅ Bot Started", color=0x43b581)
    embed.add_field(name="Bot Version", value=BOT_VERSION, inline=True)
    embed.add_field(name="Python Version", value=platform.python_version(), inline=True)
    embed.add_field(name="discord.py Version", value=discord.__version__, inline=True)
    embed.add_field(name="Uptime", value="0 seconds", inline=True)
    embed.timestamp = datetime.datetime.utcnow()
    return embed
