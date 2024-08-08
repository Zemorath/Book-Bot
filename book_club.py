import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import aiosqlite

class BookClub(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_requests = {}
        self.active_book_clubs = {}
        self.db_lock = asyncio.Lock()
        self.check_join_phase.start()

    async def connect_db(self):
        self.db = await aiosqlite.connect("book_club.db")
        await self.db.execute('''CREATE TABLE IF NOT EXISTS book_clubs (
                                    guild_id INTEGER PRIMARY KEY,
                                    title TEXT,
                                    description TEXT,
                                    start_time TEXT,
                                    end_time TEXT,
                                    join_phase_end_time TEXT,
                                    voting_enabled BOOLEAN
                                 )''')
        await self.db.execute('''CREATE TABLE IF NOT EXISTS book_club_members (
                                    guild_id INTEGER,
                                    user_id INTEGER,
                                    is_member BOOLEAN,
                                    PRIMARY KEY (guild_id, user_id)
                                 )''')
        await self.db.execute('''CREATE TABLE IF NOT EXISTS book_suggestions (
                                    guild_id INTEGER,
                                    title TEXT,
                                    user_id INTEGER,
                                    PRIMARY KEY (guild_id, title COLLATE NOCASE)
                                 )''')
        await self.db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.connect_db()

    @commands.command(name='create_book_club')
    async def create_book_club(self, ctx, title: str, date: str, time: str, *, description: str):
        """Starts the process to create a book club event"""
        await ctx.send('Please specify the duration of the event (e.g., 1 week, 2 weeks, 1 month):')
        self.pending_requests[ctx.author.id] = {
            'ctx': ctx,
            'guild_id': ctx.guild.id,
            'title': title,
            'date': date,
            'time': time,
            'description': description
        }

    async def handle_duration(self, ctx, duration: str):
        request = self.pending_requests.pop(ctx.author.id, None)
        if request is None:
            await ctx.send("No book club creation in progress.")
            return

        try:
            duration_amount, duration_unit = duration.split()
            duration_amount = int(duration_amount)
        except ValueError:
            await ctx.send("Invalid duration format. Please specify the duration as '<number> <unit>', e.g., '1 week'.")
            return

        event_start_time = datetime.strptime(f"{request['date']} {request['time']}", "%Y-%m-%d %H:%M")
        if duration_unit.lower() in ['week', 'weeks']:
            event_end_time = event_start_time + timedelta(weeks=duration_amount)
        elif duration_unit.lower() in ['month', 'months']:
            event_end_time = event_start_time + timedelta(days=30 * duration_amount)
        else:
            await ctx.send("Invalid duration unit. Please use 'weeks' or 'months'.")
            return

        join_phase_end_time = datetime.now() + timedelta(days=3)

        async with self.db_lock:
            await self.db.execute('''INSERT OR REPLACE INTO book_clubs (
                                        guild_id, title, description, start_time, end_time, join_phase_end_time, voting_enabled
                                     ) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                  (request['guild_id'], request['title'], request['description'], 
                                   event_start_time.isoformat(), event_end_time.isoformat(), join_phase_end_time.isoformat(), True))
            await self.db.commit()

        self.active_book_clubs[request['guild_id']] = {
            'title': request['title'],
            'description': request['description'],
            'start_time': event_start_time,
            'end_time': event_end_time,
            'join_phase_end_time': join_phase_end_time,
            'members': set(),
            'non_members': set(),
            'end_vote': False,
            'votes': {},
            'suggestions': {}
        }

        event_name = f"Book Club: {request['title']}"
        event_description = f"{request['description']}\n\nJoin Phase ends on: {join_phase_end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        join_message = await ctx.send(
            f"**{event_name}**\n{event_description}\n\nClick the button below to join or leave the book club.",
            view=JoinBookClubView(self, ctx.guild.id)
        )
        self.active_book_clubs[request['guild_id']]['message_id'] = join_message.id

    @commands.command(name='join_book_club')
    async def join_book_club(self, ctx):
        book_club = self.active_book_clubs.get(ctx.guild.id)
        if book_club is None or datetime.now() > book_club['join_phase_end_time']:
            await ctx.send("There is no active book club join phase at the moment.")
            return

        async with self.db_lock:
            await self.db.execute('''INSERT OR REPLACE INTO book_club_members (
                                        guild_id, user_id, is_member
                                     ) VALUES (?, ?, ?)''',
                                  (ctx.guild.id, ctx.author.id, True))
            await self.db.commit()

        book_club['members'].add(ctx.author.id)
        book_club['non_members'].discard(ctx.author.id)
        await ctx.send(f"{ctx.author.mention}, you have joined the book club.")

    @commands.command(name='leave_book_club')
    async def leave_book_club(self, ctx):
        book_club = self.active_book_clubs.get(ctx.guild.id)
        if book_club is None or datetime.now() > book_club['join_phase_end_time']:
            await ctx.send("There is no active book club join phase at the moment.")
            return

        async with self.db_lock:
            await self.db.execute('''INSERT OR REPLACE INTO book_club_members (
                                        guild_id, user_id, is_member
                                     ) VALUES (?, ?, ?)''',
                                  (ctx.guild.id, ctx.author.id, False))
            await self.db.commit()

        book_club['non_members'].add(ctx.author.id)
        book_club['members'].discard(ctx.author.id)
        await ctx.send(f"{ctx.author.mention}, you have left the book club.")

    @commands.command(name='suggest_book')
    async def suggest_book(self, ctx, *, title: str):
        book_club = self.active_book_clubs.get(ctx.guild.id)
        if not book_club or datetime.now() > book_club['join_phase_end_time']:
            await ctx.send("There is no active book club or join phase has ended.")
            return

        if ctx.author.id not in book_club['members']:
            await ctx.send("Only members can suggest books.")
            return

        normalized_title = title.strip().title()

        async with self.db_lock:
            await self.db.execute('''INSERT OR IGNORE INTO book_suggestions (
                                        guild_id, title, user_id
                                     ) VALUES (?, ?, ?)''',
                                  (ctx.guild.id, normalized_title, ctx.author.id))
            await self.db.commit()

        book_club['suggestions'][normalized_title] = book_club['suggestions'].get(normalized_title, 0) + 1
        await ctx.send(f"{ctx.author.mention} suggested the book: {normalized_title}")

    @commands.command(name='enable_voting')
    @commands.has_permissions(administrator=True)
    async def enable_voting(self, ctx):
        async with self.db_lock:
            await self.db.execute('UPDATE book_clubs SET voting_enabled = 1 WHERE guild_id = ?', (ctx.guild.id,))
            await self.db.commit()

        await ctx.send("Book club voting has been enabled.")

    @commands.command(name='disable_voting')
    @commands.has_permissions(administrator=True)
    async def disable_voting(self, ctx):
        async with self.db_lock:
            await self.db.execute('UPDATE book_clubs SET voting_enabled = 0 WHERE guild_id = ?', (ctx.guild.id,))
            await self.db.commit()

        await ctx.send("Book club voting has been disabled.")

    @commands.command(name='end_book_club')
    async def end_book_club(self, ctx):
        book_club = self.active_book_clubs.get(ctx.guild.id)
        if not book_club:
            await ctx.send("There is no active book club to end.")
            return

        if book_club['end_vote']:
            await ctx.send("A vote to end the book club is already in progress.")
            return

        book_club['end_vote'] = True
        book_club['votes'] = {}
        await ctx.send("A vote to end the book club early has been initiated. Members can vote with the command `$vote_end`.")

    @commands.command(name='vote_end')
    async def vote_end(self, ctx):
        book_club = self.active_book_clubs.get(ctx.guild.id)
        if not book_club or not book_club['end_vote']:
            await ctx.send("There is no active vote to end the book club.")
            return

        if ctx.author.id not in book_club['members']:
            await ctx.send("You are not a member of the book club.")
            return

        book_club['votes'][ctx.author.id] = True
        total_members = len(book_club['members'])
        total_votes = len(book_club['votes'])

        if total_votes > total_members / 2:
            await self.end_book_club_early(ctx.guild.id)
            await ctx.send("The vote to end the book club has passed. The book club has been ended early.")
        else:
            await ctx.send(f"{ctx.author.mention}, your vote has been recorded. {total_votes}/{total_members} members have voted to end the book club.")

    async def end_book_club_early(self, guild_id):
        async with self.db_lock:
            await self.db.execute('DELETE FROM book_clubs WHERE guild_id = ?', (guild_id,))
            await self.db.execute('DELETE FROM book_club_members WHERE guild_id = ?', (guild_id,))
            await self.db.execute('DELETE FROM book_suggestions WHERE guild_id = ?', (guild_id,))
            await self.db.commit()

        if guild_id in self.active_book_clubs:
            del self.active_book_clubs[guild_id]

    @tasks.loop(hours=1)
    async def check_join_phase(self):
        async with self.db_lock:
            async with self.db.execute('SELECT guild_id, join_phase_end_time, voting_enabled FROM book_clubs') as cursor:
                async for row in cursor:
                    guild_id, join_phase_end_time, voting_enabled = row
                    join_phase_end_time = datetime.fromisoformat(join_phase_end_time)
                    if datetime.now() > join_phase_end_time:
                        channel = self.bot.get_channel(self.active_book_clubs[guild_id]['message_id'])
                        if channel:
                            await channel.send("The join phase for the book club has ended.")
                        if voting_enabled:
                            await self.start_book_poll(guild_id)
                        async with self.db.execute('UPDATE book_clubs SET join_phase_end_time = NULL WHERE guild_id = ?', (guild_id,)):
                            await self.db.commit()

    async def start_book_poll(self, guild_id):
        book_club = self.active_book_clubs.get(guild_id)
        if not book_club:
            return

        suggestions = book_club.get('suggestions', {})
        if not suggestions:
            return

        poll_message = "The join phase has ended. Please vote for the next book club book:\n\n"
        poll_message += "\n".join([f"{idx+1}. {title} ({count} suggestion(s))" for idx, (title, count) in enumerate(suggestions.items())])

        channel = self.bot.get_channel(book_club['message_id'])
        poll = await channel.send(poll_message, view=BookPollView(self, guild_id, list(suggestions.keys())))
        book_club['poll_message_id'] = poll.id
        book_club['poll_end_time'] = datetime.now() + timedelta(days=1)

    @tasks.loop(hours=1)
    async def check_poll_end(self):
        async with self.db_lock:
            async with self.db.execute('SELECT guild_id, poll_end_time FROM book_clubs WHERE poll_end_time IS NOT NULL') as cursor:
                async for row in cursor:
                    guild_id, poll_end_time = row
                    poll_end_time = datetime.fromisoformat(poll_end_time)
                    if datetime.now() > poll_end_time:
                        await self.end_poll(guild_id)

    async def end_poll(self, guild_id):
        book_club = self.active_book_clubs.get(guild_id)
        if not book_club:
            return

        poll_message_id = book_club.get('poll_message_id')
        if not poll_message_id:
            return

        channel = self.bot.get_channel(book_club['message_id'])
        poll_message = await channel.fetch_message(poll_message_id)

        reactions = poll_message.reactions
        max_votes = 0
        winning_book = None

        for reaction in reactions:
            if reaction.count > max_votes:
                max_votes = reaction.count
                winning_book = reaction.emoji

        if winning_book:
            book_title = book_club['suggestions'][winning_book]
            await channel.send(f"The book club has chosen: {book_title}")

        async with self.db_lock:
            await self.db.execute('UPDATE book_clubs SET poll_end_time = NULL WHERE guild_id = ?', (guild_id,))
            await self.db.execute('DELETE FROM book_suggestions WHERE guild_id = ?', (guild_id,))
            await self.db.commit()

        book_club['poll_end_time'] = None
        book_club['suggestions'] = {}

    @check_join_phase.before_loop
    @check_poll_end.before_loop
    async def before_tasks(self):
        await self.bot.wait_until_ready()

class JoinBookClubView(discord.ui.View):
    def __init__(self, book_club_cog, guild_id):
        super().__init__(timeout=259200)  # 3 days in seconds
        self.book_club_cog = book_club_cog
        self.guild_id = guild_id

    @discord.ui.button(label='Join', style=discord.ButtonStyle.success, emoji='✅')
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await self.book_club_cog.bot.get_context(interaction.message)
        await self.book_club_cog.join_book_club(ctx)

    @discord.ui.button(label='Leave', style=discord.ButtonStyle.danger, emoji='❌')
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await self.book_club_cog.bot.get_context(interaction.message)
        await self.book_club_cog.leave_book_club(ctx)

class BookPollView(discord.ui.View):
    def __init__(self, book_club_cog, guild_id, suggestions):
        super().__init__(timeout=86400)  # 1 day in seconds
        self.book_club_cog = book_club_cog
        self.guild_id = guild_id
        self.suggestions = suggestions
        self.add_item(discord.ui.Select(
            placeholder="Select a book to vote for",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=title) for title in self.suggestions],
            custom_id="book_select"
        ))

    @discord.ui.select(custom_id="book_select")
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_book = select.values[0]
        book_club = self.book_club_cog.active_book_clubs.get(self.guild_id)
        if book_club:
            book_club['votes'][interaction.user.id] = selected_book
            await interaction.response.send_message(f"You voted for: {selected_book}", ephemeral=True)


def setup(bot):
    bot.add_cog(BookClub(bot))
