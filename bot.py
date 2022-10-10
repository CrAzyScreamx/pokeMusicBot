import asyncio
import os
import discord
from discord.ext import commands
from dotenvy import load_env, read_file

client = commands.Bot(command_prefix=commands.when_mentioned_or("+"), case_insensitive=True,
                      intents=discord.Intents.all())
client.remove_command('help')
load_env(read_file("args.env"))


async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await client.load_extension(f'cogs.{filename[:-3]}')


if __name__ == "__main__":
    asyncio.run(load_cogs())

client.run(os.environ.get("DEV_TOKEN"))
