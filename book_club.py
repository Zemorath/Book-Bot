import discord
from discord.ext import commands
from datetime import datetime, timedelta

class BookClub(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='create_book_club')
    async def create_book_club(self, ctx, title: str, date: str, time: str, description: str):
        """Creates a book club event"""
        guild = ctx.guild
        event_name = f"Book Club: {title}"
        event_description = description
        event_start_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        event_end_time = event_start_time + timedelta(hours=2)  # Default duration of 2 hours

        event = await guild.create_scheduled_event(
            name=event_name,
            description=event_description,
            start_time=event_start_time,
            end_time=event_end_time,
            location="Voice Channel"  # Modify as needed
        )

        await ctx.send(f"Book club event '{event_name}' created successfully! [Join Event]({event.url})")

def setup(bot):
    bot.add_cog(BookClub(bot))
