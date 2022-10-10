import os

import discord
from discord.ext import commands


class helpCommand(commands.Cog):

    def __init__(self, client):
        self.client: discord.Client = client

    @commands.command(aliases=['help', 'h'])
    async def _help(self, ctx):
        prefix = "+"
        desc = f"```Commands for {self.client.user.display_name}:\n\n" \
               f"1.  {prefix}join (aliases: {prefix}j, {prefix}summon) - Joins the channel\n" \
               f"2.  {prefix}leave (aliases: {prefix}dc, {prefix}disconnect) - Leaves the channel\n" \
               f"3.  {prefix}play [search] (aliases: {prefix}p) - Plays music ( can be link from spotify or youtube or you can just search for a name )\n" \
               f"4.  {prefix}pause - Pauses current playing music\n" \
               f"5.  {prefix}resume - Resumes current playing music\n" \
               f"6.  {prefix}np (aliases: {prefix}nowplaying, {prefix}currentsong, {prefix}current) - Displays the current playing song\n" \
               f"7.  {prefix}loop (aliases: {prefix}loopsong, {prefix}ls) - Loops current playing song\n" \
               f"8.  {prefix}queue (aliases: {prefix}q) - displays current queue\n" \
               f"9.  {prefix}clear (aliases: {prefix}clearqueue) - clears current queue\n" \
               f"10. {prefix}delete [index] (aliases: {prefix}del, {prefix}remove) - Deletes chosen song from the queue\n" \
               f"11. {prefix}shuffle - shuffles the queue\n" \
               f"12. {prefix}skip (aliases: {prefix}s) - Skip current playing song\n" \
               f"13. {prefix}back (aliases: {prefix}b) - Return to previous song\n" \
               f"14. {prefix}loopqueue (aliases: {prefix}lq) - Loop current playing queue\n" \
               f"15. {prefix}removeDupes - removes duplicates from the queue\n\n" \
               f"Created By Amit#5475```"
        await ctx.send(desc)

    @commands.command()
    async def re(self, ctx):
        if ctx.author.id == 231405897820143616:
            for fileName in os.listdir('./cogs'):
                if fileName.endswith('.py'):
                    await self.client.reload_extension(f'cogs.{fileName[:-3]}')
            msg = ctx.message
            await msg.delete()
            await ctx.author.send("Extensions Reloaded")


async def setup(client):
    await client.add_cog(helpCommand(client))
