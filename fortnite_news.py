import aiohttp
import discord

async def fetch_fortnite_news():
    url = "https://fortnite-api.com/v2/news"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                br_news = data.get('data', {}).get('br', {}).get('motds', [])
                return br_news
            return []

def build_news_embeds(news_items):
    embeds = []
    for item in news_items:
        title = item.get('title', '')
        body = item.get('body', '')
        image = item.get('image', '')
        embed = discord.Embed(title=title, description=body, color=0x00bfff)
        if image:
            embed.set_image(url=image)
        embeds.append(embed)
    return embeds
