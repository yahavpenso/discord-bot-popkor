import aiohttp
import discord

async def fetch_fortnite_map():
    url = "https://fortnite-api.com/v1/map"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                images = data.get('data', {}).get('images', {})
                return images.get('pois') or images.get('main')
            return None

def build_map_embed(map_image_url):
    embed = discord.Embed(title="🗺️ Current Fortnite Map", color=0x00bfff)
    if map_image_url:
        embed.set_image(url=map_image_url)
    embed.set_footer(text="Source: fortnite-api.com | Popkor Bot")
    return embed
