import aiohttp
import discord
from discord.ext import commands

async def fetch_fortnite_shop():
    url = "https://fortnite-api.com/v2/shop/br/combined"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('data', {}).get('featured', {}).get('entries', [])
            return []

def build_shop_embeds(shop_data):
    embeds = []
    for entry in shop_data[:10]:
        items = entry.get('items', [])
        if not items:
            continue
        item = items[0]
        name = item.get('name', 'Unknown')
        description = item.get('description', 'No description.')
        images = item.get('images', {})
        image = images.get('featured') or images.get('icon') or images.get('smallIcon')
        price = entry.get('finalPrice', 'Unknown')
        regular_price = entry.get('regularPrice', 'Unknown')
        currency = 'V-Bucks'
        embed = discord.Embed(title=f"🛒 {name}", description=description, color=0x00bfff)
        if image:
            embed.set_thumbnail(url=image)
        embed.add_field(name="Price", value=f"{price} {currency}", inline=True)
        if str(price) != str(regular_price):
            embed.add_field(name="Regular Price", value=f"{regular_price} {currency}", inline=True)
        embed.set_footer(text="Fortnite Shop | Popkor Bot")
        embeds.append(embed)
    return embeds
