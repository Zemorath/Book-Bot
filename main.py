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

def create_message(search_results, index=0):
    title, listing_url, isbn, image_url, prices = search_results[index]
    price_text = " - ".join(prices) if prices else "N/A"
    message = (f"**Result {index + 1} of {len(search_results)}**\n"
               f"**Title:** {title}\n"
               f"**Price Range:** {price_text}\n"
               f"**ISBN:** {isbn}\n"
               f"**Link:** [HPB]({listing_url})\n")
    if is_valid_url(image_url):
        message += f"**Image:** {image_url}\n"
    return message

class NavigationView(discord.ui.View):
    def __init__(self, user_id, search_results):
        super().__init__()
        self.user_id = user_id
        self.search_results = search_results
        self.index = 0

    @discord.ui.button(label='Previous', style=discord.ButtonStyle.primary, emoji='⬅️')
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"Previous button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if self.index > 0:
            self.index -= 1
            await interaction.response.edit_message(content=create_message(self.search_results, self.index), view=self)

    @discord.ui.button(label='Next', style=discord.ButtonStyle.primary, emoji='➡️')
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"Next button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if self.index < len(self.search_results) - 1:
            self.index += 1
            await interaction.response.edit_message(content=create_message(self.search_results, self.index), view=self)

    @discord.ui.button(label='Select', style=discord.ButtonStyle.success, emoji='✅')
    async def select(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"Select button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        title, listing_url, isbn, image_url, prices = self.search_results[self.index]
        price_message = (f"**Title:** {title}\n"
                         f"**Price Range:** {' - '.join(prices)}\n"
                         f"**ISBN:** {isbn}\n"
                         f"**Link:** {listing_url}")
        await interaction.response.send_message(price_message)
        if is_valid_url(image_url):
            await interaction.channel.send(f"**Image:** {image_url}")

        bookfinder_data = search_bookfinder(isbn)
        if bookfinder_data:
            bookfinder_message = (f"**BookFinder Price Range:** {bookfinder_data['price_range']}\n"
                                  f"**Range Minimum:** [{bookfinder_data['first_store']}]({bookfinder_data['first_listing_url']}) - {bookfinder_data['first_listing_price']}\n"
                                  f"**Range Maximum:** [{bookfinder_data['fifth_store']}]({bookfinder_data['fifth_listing_url']}) - {bookfinder_data['fifth_listing_price']}")
            await interaction.channel.send(bookfinder_message)
        else:
            await interaction.channel.send('No suitable format found on BookFinder.')

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
        user_request = search_requests[message.author.id]

        if user_request['stage'] == 'awaiting_title':
            book_title = message.content.strip()
            search_results = search_book(book_title)
            if not search_results:
                await message.channel.send('No results found.')
                del search_requests[message.author.id]
                return

            user_request['results'] = search_results
            user_request['index'] = 0
            user_request['stage'] = 'viewing_results'

            result_message = create_message(search_results)
            view = NavigationView(message.author.id, search_results)
            await message.channel.send(result_message, view=view)
            print("Sent initial message with navigation buttons")

client.run(os.getenv('TOKEN'))
