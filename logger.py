import discord
import datetime

async def log_bot_action(bot, message: str, channel_id: int = None, extra: dict = None):
    LOG_CHANNEL_ID = 1375833494026064065
    log_channel = bot.get_channel(channel_id or LOG_CHANNEL_ID)
    now = datetime.datetime.utcnow()
    embed = discord.Embed(title="🤖 Bot Action", description=message, color=0x5865F2)
    embed.timestamp = now
    if channel_id:
        embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=True)
    if extra:
        for k, v in extra.items():
            embed.add_field(name=k, value=str(v), inline=True)
    embed.set_footer(text=f"Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if log_channel:
        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            print(f"[Log Error] Could not send log to Discord: {e}")
    else:
        print("[Log Error] Log channel not found.")
