import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from fetch_HPB_data import search_book as search_hpb
from fetch_bookfinder_data import search_bookfinder
from fetch_openlibrary_data import search_openlibrary
from urllib.parse import urlparse
from database import db, add_book, remove_book, list_books, update_rating, mark_top_ten, list_top_ten, list_books_by_author, list_books_by_rating, list_books_by_title
from book_club import BookClub

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

search_requests = {}

def split_message(message, max_length=2000):
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def create_message(search_results, index=0):
    if len(search_results[index]) == 4:
        title, author, isbn, image_url = search_results[index]
    else:
        title, author, isbn = search_results[index]
        image_url = None

    message = (f"**Result {index + 1} of {len(search_results)}**\n"
               f"**Title:** {title}\n"
               f"**Author:** {author}\n"
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
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if self.index > 0:
            self.index -= 1
            self.children[-1].book = self.search_results[self.index]  # Update the book for the add to library button
            await interaction.response.edit_message(content=create_message(self.search_results, self.index), view=self)

    @discord.ui.button(label='Next', style=discord.ButtonStyle.primary, emoji='➡️')
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if self.index < len(self.search_results) - 1:
            self.index += 1
            self.children[-1].book = self.search_results[self.index]  # Update the book for the add to library button
            await interaction.response.edit_message(content=create_message(self.search_results, self.index), view=self)

    @discord.ui.button(label='Select', style=discord.ButtonStyle.success, emoji='✅')
    async def select(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        title, author, isbn, image_url = self.search_results[self.index]
        price_message = (f"**Title:** {title}\n"
                         f"**Author:** {author}\n"
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
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        title, author, isbn, image_url = self.book
        await add_book(self.user_id, title, author, isbn, image_url)
        await interaction.response.send_message(f'Added "{title}" by {author} to your library.', ephemeral=True)

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
        message = '\n'.join([f'{idx + 1}. **{title}** by **{author}** (ISBN: {isbn}) - Rating: {rating or "N/A"}' for idx, (title, author, isbn, rating) in enumerate(page_books)])
        return message

    @discord.ui.button(label='Previous', style=discord.ButtonStyle.primary, emoji='⬅️')
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if self.page_index > 0:
            self.page_index -= 1
            await interaction.response.edit_message(content=self.get_page(), view=self)

    @discord.ui.button(label='Next', style=discord.ButtonStyle.primary, emoji='➡️')
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this message.", ephemeral=True)
            return

        if (self.page_index + 1) * self.page_size < len(self.books):
            self.page_index += 1
            await interaction.response.edit_message(content=self.get_page(), view=self)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await db.connect()

@bot.command(name='search')
async def search(ctx):
    await ctx.send('Please enter the book title:')
    search_requests[ctx.author.id] = {'stage': 'awaiting_title'}

@bot.command(name='add')
async def add(ctx, title: str, author: str, isbn: str, image_url: str):
    await add_book(ctx.author.id, title, author, isbn, image_url)
    await ctx.send(f'Added "{title}" by {author} to your library.')

@bot.command(name='remove')
async def remove(ctx, isbn: str):
    await remove_book(ctx.author.id, isbn)
    await ctx.send(f'Removed book with ISBN {isbn} from your library.')

@bot.command(name='list')
async def list_books_command(ctx, filter_type: str = 'all', filter_value: str = None):
    if filter_type == 'all':
        books = await list_books(ctx.author.id)
        if not books:
            await ctx.send('Your library is empty.')
        else:
            view = LibraryView(ctx.author.id, books)
            await ctx.send(view.get_page(), view=view)
    
    elif filter_type == 'author':
        books = await list_books_by_author(ctx.author.id, filter_value)
        if not books:
            await ctx.send(f'No books by {filter_value} found in your library.')
        else:
            author_books_message = '\n'.join([f'{idx + 1}. **{title}** (ISBN: {isbn}) - Rating: {rating or "N/A"}' for idx, (title, isbn, rating) in enumerate(books)])
            await ctx.send(f'**Books by {filter_value} in Your Library:**\n{author_books_message}')
    
    elif filter_type == 'rating':
        try:
            min_rating = int(filter_value)
            books = await list_books_by_rating(ctx.author.id, min_rating)
            if not books:
                await ctx.send(f'No books with rating {min_rating} or higher found in your library.')
            else:
                rating_books_message = '\n'.join([f'{idx + 1}. **{title}** by **{author}** (ISBN: {isbn}) - Rating: {rating or "N/A"}' for idx, (title, author, isbn, rating) in enumerate(books)])
                await ctx.send(f'**Books with Rating {min_rating} or Higher in Your Library:**\n{rating_books_message}')
        except ValueError:
            await ctx.send('Invalid rating. Please enter a number.')
    
    elif filter_type == 'title':
        books = await list_books_by_title(ctx.author.id, filter_value)
        if not books:
            await ctx.send(f'No books with title containing "{filter_value}" found in your library.')
        else:
            title_books_message = '\n'.join([f'{idx + 1}. **{title}** by **{author}** (ISBN: {isbn}) - Rating: {rating or "N/A"}' for idx, (title, author, isbn, rating) in enumerate(books)])
            await ctx.send(f'**Books with Title Containing "{filter_value}" in Your Library:**\n{title_books_message}')
    
    else:
        await ctx.send('Invalid filter type. Use "author", "rating", "title", or "all".')

@bot.command(name='rate')
async def rate(ctx, isbn: str, rating: int):
    if 1 <= rating <= 10:
        await update_rating(ctx.author.id, isbn, rating)
        await ctx.send(f'Updated rating for book with ISBN {isbn} to {rating}.')
    else:
        await ctx.send('Rating must be between 1 and 10.')

@bot.command(name='marktopten')
async def mark_top_ten_command(ctx, isbn: str):
    await mark_top_ten(ctx.author.id, isbn, True)
    await ctx.send(f'Marked book with ISBN {isbn} as one of your top 10.')

@bot.command(name='unmarktopten')
async def unmark_top_ten_command(ctx, isbn: str):
    await mark_top_ten(ctx.author.id, isbn, False)
    await ctx.send(f'Removed book with ISBN {isbn} from your top 10.')

@bot.command(name='topten')
async def top_ten(ctx):
    books = await list_top_ten(ctx.author.id)
    if not books:
        await ctx.send('Your top 10 list is empty.')
    else:
        top_ten_message = '\n'.join([f'{idx + 1}. **{title}** by **{author}** (ISBN: {isbn}) - Rating: {rating or "N/A"}' for idx, (title, author, isbn, rating) in enumerate(books)])
        await ctx.send(f'**Your Top 10 Books:**\n{top_ten_message}')

@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.author.id in search_requests:
        user_request = search_requests[message.author.id]

        if user_request['stage'] == 'awaiting_title':
            book_title = message.content.strip()
            if book_title.startswith('$'):  # Ignore commands
                return
            
            logger.info(f"Searching for book title: {book_title}")
            
            search_results = search_openlibrary(book_title)

            logger.info(f"Search results: {search_results}")
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

bot.add_cog(BookClub(bot))

bot.run(os.getenv('TOKEN'))
