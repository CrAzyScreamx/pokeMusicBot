import os

import discord

from importentFiles.songClasses import *
from discord.ext import commands


class musicCommands(commands.Cog):

    def __init__(self, client):
        self.client: discord.Client = client
        self.queue: Queue = None

    @commands.command(aliases=['join', 'j', 'summon'])
    async def _join(self, ctx: commands.Context):
        if not ctx.author.voice:
            await ctx.send(
                embed=self._embedSentence("You must be connected to a channel", discord.Color.from_rgb(0, 0, 0)))
            raise NotPlayingAnything("User not connected to the channel")
        message: discord.Message = ctx.message
        await message.add_reaction("👌")
        vc = await ctx.author.voice.channel.connect()
        self.queue = Queue(self.client, vc, ctx)

    @commands.command(aliases=['leave', 'dc', 'disconnect'])
    async def _leave(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel is self.queue.vc.channel:
            return await ctx.send(embed=self._embedSentence("You must be connected ot the same channel as the bot",
                                                            discord.Color.from_rgb(0, 0, 0)))
        await ctx.message.add_reaction('👋')
        await self.queue.vc.disconnect()

    @commands.command(aliases=['play', 'p'])
    async def _stream(self, ctx: commands.Context, *, search: str = None):
        if search is None:
            return await ctx.send(
                embed=self._embedSentence("You must provide a url or a search", discord.Color.from_rgb(0, 0, 0)))
        if self.queue is None:
            await ctx.invoke(self._join)

        ytdlSource = YTDLSource()
        await ytdlSource.extract_videos(search, ctx.author, ctx, self.client.loop)
        self.queue.addSongs(ytdlSource.results)
        if len(ytdlSource.results) == 1:
            return await ctx.send(
                embed=self._embedSentence(f"Enqueued ``{ytdlSource.results[0].title}``", discord.Color.blurple()))
        else:
            return await ctx.send(
                embed=self._embedSentence(f"Enqueued ``{len(ytdlSource.results)}`` songs", discord.Color.blurple()))

    @commands.command(aliases=['pause'])
    async def _pause(self, ctx: commands.Context):
        message: discord.Message = ctx.message
        await message.add_reaction('⏸')
        self.queue.pause()

    @commands.command(aliases=['resume'])
    async def _resume(self, ctx: commands.Context):
        if not self.queue.vc.is_paused():
            return await ctx.send(embed=self._embedSentence("Audio is not paused", discord.Color.from_rgb(0, 0, 0)))

        message: discord.Message = ctx.message
        await message.add_reaction('▶')
        self.queue.resume()

    @commands.command(aliases=['np', 'nowplaying', 'currentsong', 'current'])
    async def _now_playing(self, ctx: commands.Context):
        currentSong: Song = self.queue.current
        await ctx.send(embed=currentSong.create_embed())

    @commands.command(aliases=['loopsong', 'ls'])
    async def _loopSong(self, ctx: commands.Context):
        self.queue.current.loop = not self.queue.current.loop
        if self.queue.current.loop:
            return await ctx.send("Looping Song 🔂")
        else:
            return await ctx.send("Cancelled Song Loop ❌")

    @commands.command(aliases=['queue', 'q'])
    async def _queue(self, ctx: commands.Context):
        if len(self.queue.queue) == 0:
            return await ctx.send("```PokeMusic Queue\n```")
        sen = "```PokeMusic Queue\n-------------------\n"
        for i in range(len(self.queue.queue)):
            sen += str(i + 1) + ". " + self.queue.queue[i].title
            if i == self.queue.currentIndex:
                sen += " -> Current Song"
            sen += "\n"
        loopstate = " Song is Looped" if self.queue.current.loop else " Song is not Looped"
        queueLoop = "Queue is Looped" if self.queue.loop else "Queue is not Looped"
        sen += f"-----------------------------------------------\n{loopstate}\t\t{queueLoop}```"
        await ctx.send(sen)

    @commands.command(aliases=['clearqueue', 'clearq', 'clear'])
    async def _clear(self, ctx):
        self.queue.clear()
        await ctx.message.add_reaction('👌')

    @commands.command(aliases=['delete', 'del'])
    async def _delete(self, ctx: commands.Context, index):
        try:
            index = int(index)
        except ValueError as e:
            return await ctx.send(embed=self._embedSentence("Index must be a number!", discord.Color.from_rgb(0, 0, 0)))
        index = int(index)
        if 1 < index <= len(self.queue.queue):
            await ctx.send(embed=self._embedSentence(f"Song ``{self.queue.queue[index - 1].title}`` has been deleted",
                                                     discord.Color.blurple()))
            self.queue.deleteSong(index)
        else:
            if len(self.queue.queue) == 1 and index == 1:
                return await ctx.send(
                    embed=self._embedSentence("Cannot delete the only song", discord.Color.from_rgb(0, 0, 0)))
            else:
                return await ctx.send(embed=self._embedSentence(f"Index must be between 2 and {len(self.queue.queue)}",
                                                                discord.Color.from_rgb(0, 0, 0)))

    @commands.command(aliases=['shuffle'])
    async def _shuffle(self, ctx: commands.Context):
        self.queue.shuffle()
        await ctx.message.add_reaction('🔀')

    @commands.command(aliases=['skip', 's'])
    async def _skip(self, ctx: commands.Context):
        self.queue.skip()
        await ctx.message.add_reaction('⏭')

    @commands.command(aliases=['back', 'b'])
    async def _back(self, ctx: commands.Context):
        self.queue.back()
        await ctx.message.add_reaction('⏮')

    @commands.command(aliases=['lq', 'loopqueue'])
    async def _loopqueue(self, ctx: commands.Context):
        self.queue.loop = not self.queue.loop
        if self.queue.loop:
            return await ctx.send("Looping Queue 🔂")
        await ctx.send("Cancelled Queue Loop ❌")

    @commands.command(aliases=['removedupes'])
    async def _removeDupes(self, ctx: commands.Context):
        self.queue.removeDupes()
        await ctx.message.add_reaction('👍')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if int(member.id) == int(os.environ.get("BOT_ID")):
            if after.channel is None:
                self.queue.currentIndex = len(self.queue.queue)
                self.queue = None

    @_pause.before_invoke
    @_resume.before_invoke
    @_now_playing.before_invoke
    @_loopSong.before_invoke
    @_queue.before_invoke
    @_clear.before_invoke
    @_delete.before_invoke
    @_shuffle.before_invoke
    @_loopqueue.before_invoke
    @_removeDupes.before_invoke
    async def ensure_state(self, ctx):
        if self.queue is None or self.queue.vc and not self.queue.vc.is_playing() and not self.queue.vc.is_paused():
            await ctx.send(embed=self._embedSentence("Bot is not playing anything!", discord.Color.from_rgb(0, 0, 0)))
            raise NotPlayingAnything("Bot is not playing anything yet!")
        if not ctx.author.voice or ctx.author.voice.channel is not self.queue.vc.channel:
            await ctx.send(embed=self._embedSentence("You must be on the same channel as the bot!", discord.Color.from_rgb(0, 0, 0)))
            raise NotPlayingAnything("You must be on the same channel as the bot!")

    @staticmethod
    def _embedSentence(sen: str, color: discord.Color):
        emojis = ['✅', '❌']
        if color == discord.Color.blurple():
            emoji = emojis[0]
        else:
            emoji = emojis[1]

        embed = discord.Embed(
            description=emoji + "\t " + sen,
            color=color
        )
        return embed


def setup(client):
    client.add_cog(musicCommands(client))


def convertToSeconds(t):
    try:
        h, m, s = [int(i) for i in t.split(':')]
    except ValueError:
        m, s = [int(i) for i in t.split(':')]
        h = 0
    return 3600 * h + 60 * m + s


class NotPlayingAnything(Exception):
    pass
