import json
import os
import discord
from discord.ext import commands
from dotenvy import read_file, load_env
import asyncio
import spotipy
from spotipy import SpotifyClientCredentials

load_env(read_file("configFiles/args.env"))

client = discord.Bot(intents=discord.Intents.all())


async def load_cogs():
    client.load_extension(name="cogs")


if __name__ == "__main__":
    asyncio.run(load_cogs())
    client.run(os.environ.get("TOKEN"))
