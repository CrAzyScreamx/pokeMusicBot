import discord
from discord.ext import commands


class events(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is ready to function!")


def setup(client):
    client.add_cog(events(client))
