import aiohttp
import discord

async def fetch_epic_free_games():
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=US&allowCountries=US"
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
            return []

def build_free_games_embeds(free_games):
    embeds = []
    for game in free_games:
        embed = discord.Embed(
            title=f"🎮 {game['title']}",
            description=f"{game['description'][:200]}{'...' if len(game['description']) > 200 else ''}",
            color=0x00ff99
        )
        if game['image']:
            embed.set_image(url=game['image'])
        embed.set_footer(text="Epic Games Free Game | Click the button below to claim!")
        embeds.append(embed)
    return embeds
