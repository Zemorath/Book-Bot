import discord
from discord.ext import commands
from datetime import datetime, timedelta

class BookClub(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_requests = {}

    @commands.command(name='create_book_club')
    async def create_book_club(self, ctx, title: str, date: str, time: str, *, description: str):
        """Starts the process to create a book club event"""
        await ctx.send('Please specify the duration of the event (e.g., 1 week, 2 weeks, 1 month):')
        self.pending_requests[ctx.author.id] = {
            'ctx': ctx,
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

        guild = ctx.guild
        event_name = f"Book Club: {request['title']}"
        event_description = request['description']

        event = await guild.create_scheduled_event(
            name=event_name,
            description=event_description,
            start_time=event_start_time,
            end_time=event_end_time,
            location=None
        )

        await ctx.send(f"Book club event '{event_name}' created successfully! [Join Event]({event.url})")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.author.id in self.pending_requests:
            await self.handle_duration(message.channel, message.content.strip())

def setup(bot):
    bot.add_cog(BookClub(bot))
