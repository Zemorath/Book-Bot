import discord
import os
from dotenv import load_dotenv
from fetch_HPB_data import search_book as search_hpb
from fetch_bookfinder_data import search_bookfinder
from fetch_openlibrary_data import search_openlibrary
from urllib.parse import urlparse
from database import db, add_book, remove_book, list_books, update_rating, mark_top_ten, list_top_ten

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
    title, isbn, image_url = search_results[index]
    message = (f"**Result {index + 1} of {len(search_results)}**\n"
               f"**Title:** {title}\n"
               f"**ISBN:** {isbn}\n")
    if is_valid_url(image_url):
        message += f"**Image:** {image_url}\n"
    return message

class NavigationView(discord.ui.View):
    def __init__(self, user_id, search_results):
        super().__init__()
        self.user_id = user_id
        self.search_results = search_results
        self.index = 0
        self.add_item(AddToLibraryButton(user_id, search_results[self.index]))

    @discord.ui.button(label='Previous', style=discord.ButtonStyle.primary, emoji='⬅️')
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"Previous button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if self.index > 0:
            self.index -= 1
            self.children[-1].book = self.search_results[self.index]  # Update the book for the add to library button
            await interaction.response.edit_message(content=create_message(self.search_results, self.index), view=self)

    @discord.ui.button(label='Next', style=discord.ButtonStyle.primary, emoji='➡️')
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"Next button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if self.index < len(self.search_results) - 1:
            self.index += 1
            self.children[-1].book = self.search_results[self.index]  # Update the book for the add to library button
            await interaction.response.edit_message(content=create_message(self.search_results, self.index), view=self)

    @discord.ui.button(label='Select', style=discord.ButtonStyle.success, emoji='✅')
    async def select(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"Select button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        title, isbn, image_url = self.search_results[self.index]
        price_message = (f"**Title:** {title}\n"
                         f"**ISBN:** {isbn}\n")
        await interaction.response.send_message(price_message)
        if is_valid_url(image_url):
            await interaction.channel.send(f"**Image:** {image_url}")

        # Perform HPB search
        hpb_results = search_hpb(title)
        if hpb_results:
            for idx, (hpb_title, hpb_url, hpb_isbn, hpb_image_url, hpb_prices) in enumerate(hpb_results):
                hpb_price_text = " - ".join(hpb_prices) if hpb_prices else "N/A"
                hpb_message = (f"**Match found at Half Price Books:**\n"
                               f"**Title:** {hpb_title}\n"
                               f"**Price Range:** {hpb_price_text}\n"
                               f"**ISBN:** {hpb_isbn}\n"
                               f"**Link:** [HPB]({hpb_url})\n")
                await interaction.channel.send(hpb_message)
                if is_valid_url(hpb_image_url):
                    embed = discord.Embed()
                    embed.set_image(url=hpb_image_url)
                    await interaction.channel.send(embed=embed)
        else:
            await interaction.channel.send("No matches found at Half Price Books.")

        # Perform BookFinder search
        bookfinder_data = search_bookfinder(isbn)
        if bookfinder_data:
            bookfinder_message = (f"**BookFinder Price Range:** {bookfinder_data['price_range']}\n"
                                  f"**Range Minimum:** {bookfinder_data['first_listing_price']}\n"
                                  f"**Range Maximum:** {bookfinder_data['fifth_listing_price']}")
            await interaction.channel.send(bookfinder_message)
        else:
            await interaction.channel.send('No suitable format found on BookFinder.')

class AddToLibraryButton(discord.ui.Button):
    def __init__(self, user_id, book):
        super().__init__(label='Add to Library', style=discord.ButtonStyle.secondary, emoji='📚')
        self.user_id = user_id
        self.book = book

    async def callback(self, interaction: discord.Interaction):
        print(f"Add to Library button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        title, isbn, image_url = self.book
        await add_book(self.user_id, title, isbn, image_url)
        await interaction.response.send_message(f'Added "{title}" to your library.', ephemeral=True)

class LibraryView(discord.ui.View):
    def __init__(self, user_id, books, page_size=5):
        super().__init__()
        self.user_id = user_id
        self.books = books
        self.page_size = page_size
        self.page_index = 0

    def get_page(self):
        start = self.page_index * self.page_size
        end = start + self.page_size
        page_books = self.books[start:end]
        message = '\n'.join([f'{idx + 1}. **{title}** (ISBN: {isbn}) - Rating: {rating or "N/A"}' for idx, (title, isbn, rating) in enumerate(page_books)])
        return message

    @discord.ui.button(label='Previous', style=discord.ButtonStyle.primary, emoji='⬅️')
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"Previous button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if self.page_index > 0:
            self.page_index -= 1
            await interaction.response.edit_message(content=self.get_page(), view=self)

    @discord.ui.button(label='Next', style=discord.ButtonStyle.primary, emoji='➡️')
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"Next button clicked by user: {interaction.user.id if interaction.user else 'Unknown'}")
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if (self.page_index + 1) * self.page_size < len(self.books):
            self.page_index += 1
            await interaction.response.edit_message(content=self.get_page(), view=self)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await db.connect()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$search'):
        await message.channel.send('Please enter the book title:')
        search_requests[message.author.id] = {'stage': 'awaiting_title'}

    elif message.content.startswith('$add'):
        parts = message.content.split(maxsplit=3)
        if len(parts) < 4:
            await message.channel.send('Usage: $add <title> <isbn> <image_url>')
        else:
            title, isbn, image_url = parts[1], parts[2], parts[3]
            await add_book(message.author.id, title, isbn, image_url)
            await message.channel.send(f'Added "{title}" to your library.')

    elif message.content.startswith('$remove'):
        parts = message.content.split(maxsplit=1)
        if len(parts) < 2:
            await message.channel.send('Usage: $remove <isbn>')
        else:
            isbn = parts[1]
            await remove_book(message.author.id, isbn)
            await message.channel.send(f'Removed book with ISBN {isbn} from your library.')

    elif message.content.startswith('$list'):
        books = await list_books(message.author.id)
        if not books:
            await message.channel.send('Your library is empty.')
        else:
            view = LibraryView(message.author.id, books)
            await message.channel.send(view.get_page(), view=view)

    elif message.content.startswith('$rate'):
        parts = message.content.split(maxsplit=2)
        if len(parts) < 3:
            await message.channel.send('Usage: $rate <isbn> <rating (1-10)>')
        else:
            isbn = parts[1]
            try:
                rating = int(parts[2])
                if 1 <= rating <= 10:
                    await update_rating(message.author.id, isbn, rating)
                    await message.channel.send(f'Updated rating for book with ISBN {isbn} to {rating}.')
                else:
                    await message.channel.send('Rating must be between 1 and 10.')
            except ValueError:
                await message.channel.send('Invalid rating. Please enter a number between 1 and 10.')

    elif message.content.startswith('$marktopten'):
        parts = message.content.split(maxsplit=2)
        if len(parts) < 2:
            await message.channel.send('Usage: $marktopten <isbn>')
        else:
            isbn = parts[1]
            await mark_top_ten(message.author.id, isbn, True)
            await message.channel.send(f'Marked book with ISBN {isbn} as one of your top 10.')

    elif message.content.startswith('$unmarktopten'):
        parts = message.content.split(maxsplit=2)
        if len(parts) < 2:
            await message.channel.send('Usage: $unmarktopten <isbn>')
        else:
            isbn = parts[1]
            await mark_top_ten(message.author.id, isbn, False)
            await message.channel.send(f'Removed book with ISBN {isbn} from your top 10.')

    elif message.content.startswith('$topten'):
        books = await list_top_ten(message.author.id)
        if not books:
            await message.channel.send('Your top 10 list is empty.')
        else:
            top_ten_message = '\n'.join([f'{idx + 1}. **{title}** (ISBN: {isbn}) - Rating: {rating or "N/A"}' for idx, (title, isbn, rating) in enumerate(books)])
            await message.channel.send(f'**Your Top 10 Books:**\n{top_ten_message}')

    elif message.author.id in search_requests:
        user_request = search_requests[message.author.id]

        if user_request['stage'] == 'awaiting_title':
            book_title = message.content.strip()
            search_results = search_openlibrary(book_title)
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
