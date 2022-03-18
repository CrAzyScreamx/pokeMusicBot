import os
import discord
from discord.ext import commands

client = commands.Bot(command_prefix=commands.when_mentioned_or("+"), case_insensitive=True,
                      intents=discord.Intents.all())
client.remove_command('help')


@client.command()
async def re(ctx):
    if ctx.author.id == 231405897820143616:
        for fileName in os.listdir('./cogs'):
            if fileName.endswith('.py'):
                client.reload_extension(f'cogs.{fileName[:-3]}')
        msg = ctx.message
        await msg.delete()
        await ctx.author.send("Extensions Reloaded")


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        await client.load_extension(f'cogs.{filename[:-3]}')

client.run(os.environ.get("TOKEN"))
