import discord
import os
from dotenv import load_dotenv
from fetch_data import search_book

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

search_requests = {}

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith('$search'):
        await message.channel.send('Please enter the book title:')
        search_requests[message.author.id] = {'stage': 'awaiting_title'}

    elif message.author.id in search_requests:
        if search_requests[message.author.id]['stage'] == 'awaiting_title':
            book_title = message.content.strip()
            search_results = search_book(book_title)
            if not search_results:
                await message.channel.send('No results found.')
                del search_requests[message.author.id]
                return

            search_requests[message.author.id]['results'] = search_results
            search_requests[message.author.id]['stage'] = 'awaiting_selection'

            results_message = "Here are the search results:\n"
            for idx, (title, prices, listing_url, isbn, image_url) in enumerate(search_results):
                results_message += f"{idx + 1}. {title}\n   ISBN: {isbn}\n  Link: {listing_url}\n   Image: {image_url}\n"
            results_message += "Please enter the number corresponding to the book you want to see the price range for."
            await message.channel.send(results_message)

        elif search_requests[message.author.id]['stage'] == 'awaiting_selection':
            try:
                selection = int(message.content.strip()) - 1
                search_results = search_requests[message.author.id]['results']
                if 0 <= selection < len(search_results):
                    title, prices = search_results[selection]
                    price_message = f"**Title:** {title}\n**Price Range:** {' - '.join(prices)}\n**ISBN:** {isbn}\n**Link:** {listing_url}"
                    embed = discord.Embed()
                    embed.set_image(url=image_url)
                    await message.channel.send(price_message, embed=embed)
                else:
                    await message.channel.send('Invalid selection. Please try again.')
            except ValueError:
                await message.channel.send('Please enter a valid number.')
            del search_requests[message.author.id]

client.run(os.getenv('TOKEN'))