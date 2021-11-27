import discord
from discord.ext import commands


class events(commands.Cog):

    def __init__(self, client):
        self.client: discord.Client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot ready!")
        await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="+help"))


def setup(client):
    client.add_cog(events(client))