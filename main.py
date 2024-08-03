import discord
import os
from dotenv import load_dotenv
from fetch_HPB_data import search_book
from fetch_bookfinder_data import search_bookfinder
from urllib.parse import urlparse

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

search_requests = {}

def split_message(message, max_length=2000):
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def create_embed(search_results, index=0):
    embed = discord.Embed(title="HPB Listings", description=f"Showing result {index + 1} of {len(search_results)}")
    title, listing_url, isbn, image_url, prices = search_results[index]
    price_text = " - ".join(prices) if prices else "N/A"
    embed.add_field(name="Title", value=title, inline=False)
    embed.add_field(name="Price Range", value=price_text, inline=False)
    embed.add_field(name="ISBN", value=isbn, inline=False)
    embed.add_field(name="Link", value=f"[HPB]({listing_url})", inline=False)
    if is_valid_url(image_url):
        embed.set_image(url=image_url)
    return embed

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

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
            search_requests[message.author.id]['index'] = 0
            search_requests[message.author.id]['stage'] = 'awaiting_selection'

            embed = create_embed(search_results)
            result_message = await message.channel.send(embed=embed)
            await result_message.add_reaction('⬅️')
            await result_message.add_reaction('➡️')
            await result_message.add_reaction('✅')

        elif search_requests[message.author.id]['stage'] == 'viewing_results':
            try:
                selection = int(message.content.strip()) - 1
                search_results = search_requests[message.author.id]['results']
                if 0 <= selection < len(search_results):
                    title, listing_url, isbn, image_url, prices = search_results[selection]
                    price_message = f"**Title:** {title}\n**Price Range:** {' - '.join(prices)}\n**ISBN:** {isbn}\n**Link:** {listing_url}"
                    await message.channel.send(price_message)
                    if is_valid_url(image_url):
                        embed = discord.Embed()
                        embed.set_image(url=image_url)
                        await message.channel.send(embed=embed)

                    bookfinder_data = search_bookfinder(isbn)
                    if bookfinder_data:
                        bookfinder_message = (f"**BookFinder Price Range:** {bookfinder_data['price_range']}\n"
                                    f"**Range Minimum:** [{bookfinder_data['first_store']}]({bookfinder_data['first_listing_url']}) - {bookfinder_data['first_listing_price']}\n"
                                    f"**Range Maximum:** [{bookfinder_data['fifth_store']}]({bookfinder_data['fifth_listing_url']}) - {bookfinder_data['fifth_listing_price']}")
                        await message.channel.send(bookfinder_message)
                    else:
                        await message.channel.send('No suitable format found on BookFinder.')
                else:
                    await message.channel.send('Invalid selection. Please try again.')
            except ValueError:
                await message.channel.send('Please enter a valid number.')
            del search_requests[message.author.id]

@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return
    
    if user.id in search_requests:
        if search_requests[user.id]['stage'] == 'viewing_results':
            search_results = search_requests[user.id]['results']
            current_index = search_requests[user.id]['index']

            if reaction.emoji == '⬅️' and current_index > 0:
                current_index -= 1
            elif reaction.emoji == '➡️' and current_index < len(search_results) - 1:
                current_index += 1
            elif reaction.emoji == '✅':
                search_requests[user.id]['stage'] = 'awaiting_selection'
                await reaction.message.channel.send('Please enter the number corresponding to the book you want to see the details for.')
                return

            search_requests[user.id]['index'] = current_index

            embed = create_embed(search_results, current_index)
            await reaction.message.edit(embed=embed)
            await reaction.remove(user)


        #     results_message = "Here are the search results:\n"
        #     await message.channel.send(results_message)
        #     for idx, (title, listing_url, isbn, image_url, prices) in enumerate(search_results):
        #         result_message = f"{idx + 1}. **{title}**\n   ISBN: {isbn}\n  Price Range: {' - '.join(prices)}"
        #         await message.channel.send(result_message)
        #         if is_valid_url(image_url):
        #             embed = discord.Embed()
        #             embed.set_image(url=image_url)
        #             await message.channel.send(embed=embed)
            
        #     await message.channel.send("Please enter the number corresponding to the book you want to see the details for.")

        # elif search_requests[message.author.id]['stage'] == 'awaiting_selection':
        #     try:
        #         selection = int(message.content.strip()) - 1
        #         search_results = search_requests[message.author.id]['results']
        #         if 0 <= selection < len(search_results):
        #             title, listing_url, isbn, image_url, prices = search_results[selection]
        #             price_message = f"**Title:** {title}\n**Price Range:** {' - '.join(prices)}\n**ISBN:** {isbn}\n**Link:** {listing_url}"
        #             await message.channel.send(price_message)
        #             if is_valid_url(image_url):
        #                 embed = discord.Embed()
        #                 embed.set_image(url=image_url)
        #                 await message.channel.send(embed=embed)

        #             bookfinder_data = search_bookfinder(isbn)
        #             if bookfinder_data:
        #                 bookfinder_message = (f"**BookFinder Price Range:** {bookfinder_data['price_range']}\n"
        #                           f"**Range Minimum:** [{bookfinder_data['first_store']}]({bookfinder_data['first_listing_url']}) - {bookfinder_data['first_listing_price']}\n"
        #                           f"**Range Maximum:** [{bookfinder_data['fifth_store']}]({bookfinder_data['fifth_listing_url']}) - {bookfinder_data['fifth_listing_price']}")
        #                 await message.channel.send(bookfinder_message)
        #             else:
        #                 await message.channel.send('No suitable format found on BookFinder.')
        #         else:
        #             await message.channel.send('Invalid selection. Please try again.')
        #     except ValueError:
        #         await message.channel.send('Please enter a valid number.')
        #     del search_requests[message.author.id]

client.run(os.getenv('TOKEN'))