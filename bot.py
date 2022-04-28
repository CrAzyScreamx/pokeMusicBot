import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

client = commands.Bot(command_prefix=commands.when_mentioned_or("+"), case_insensitive=True,
                      intents=discord.Intents.all())
client.remove_command('help')

load_dotenv("args.env")

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
        client.load_extension(f'cogs.{filename[:-3]}')

client.run(os.environ.get("TOKEN"))