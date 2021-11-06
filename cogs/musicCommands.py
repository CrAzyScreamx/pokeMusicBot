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
            return await ctx.send("You must be connected to a channel!")
        vc = await ctx.author.voice.channel.connect()
        self.queue = Queue(self.client, vc, ctx)

    @commands.command(aliases=['leave', 'dc', 'disconnect'])
    async def _leave(self, ctx: commands.Context):
        if not ctx.author.voice.channel is self.queue.vc.channel:
            return await ctx.send("You must be connected to the same channel as the bot")
        await self.queue.vc.disconnect()

    @commands.command(aliases=['play', 'p'])
    async def _stream(self, ctx: commands.Context, *, search: str):
        if search is None:
            return await ctx.send('You must provide a url or a search string')
        if ctx.author.voice is None:
            return await ctx.send('You need to be in a voice channel to use this command!')
        if self.queue is None:
            await ctx.invoke(self._join)

        ytdlSource = YTDLSource()
        await ytdlSource.extract_videos(search, ctx.author, self.client.loop)

        self.queue.addSongs(ytdlSource.results)
        if len(ytdlSource.results) == 1:
            return await ctx.send(f"Enqueued ``{ytdlSource.results[0].title}``")
        else:
            return await ctx.send(f"Enqueued ``{len(ytdlSource.results)}`` songs")

    @commands.command(aliases=['pause'])
    async def _pause(self, ctx: commands.Context):
        self.queue.pause()

    @commands.command(aliases=['resume'])
    async def _resume(self, ctx: commands.Context):
        if not self.queue.vc.is_paused():
            return await ctx.send("Audio is not paused!")

        self.queue.resume()

    @commands.command(aliases=['np', 'nowplaying', 'currentsong'])
    async def _now_playing(self, ctx: commands.Context):
        currentSong: Song = self.queue.current
        await ctx.send(embed=currentSong.create_embed())

    @commands.command(aliases=['loop', 'l'])
    async def _loop(self, ctx: commands.Context):
        self.queue.current.loop = not self.queue.current.loop
        if self.queue.current.loop:
            return await ctx.send("Looped Song!")
        else:
            return await ctx.send("Cancelled Loop")

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
        if len(self.queue.queue) > 1:
            sen += f"-------------------\nnext Song -> {self.queue.next.title}"
        sen += "```"
        await ctx.send(sen)

    @commands.command(aliases=['clearqueue', 'clearq', 'clear'])
    async def _clear(self, ctx):
        self.queue.clear()
        await ctx.send("Queue has been reset")

    @commands.command(aliases=['delete', 'del'])
    async def _delete(self, ctx: commands.Context, index):
        try:
            index = int(index)
        except ValueError as e:
            return await ctx.send("Index must be a number!")
        index = int(index)
        if 1 < index <= len(self.queue.queue):
            await ctx.send(f"Song ``{self.queue.queue[index - 1].title}`` has been deleted")
            self.queue.deleteSong(index)
        else:
            if len(self.queue.queue) == 1 and index == 1:
                return await ctx.send("Cannot delete current playing song!")
            else:
                return await ctx.send(f"Index must be between 2 and {len(self.queue.queue)}")

    @commands.command(aliases=['shuffle'])
    async def _shuffle(self, ctx: commands.Context):
        self.queue.shuffle()
        return await ctx.send("Queue has been shuffled")

    @commands.command(aliases=['skip', 's'])
    async def _skip(self, ctx: commands.Context):
        self.queue.skip()
        return await ctx.send("Audio Skipped!")

    @commands.command(aliases=['back', 'b'])
    async def _back(self, ctx: commands.Context):
        self.queue.back()
        return await ctx.send("Audio returned backwards")

    @commands.command(aliases=['lq', 'loopqueue'])
    async def _loopqueue(self, ctx: commands.Context):
        self.queue.loop = not self.queue.loop
        if self.queue.loop:
            return await ctx.send("Queue looped")
        await ctx.send("Cancelled Queue loop")


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if int(member.id) == int(os.environ.get("BOT_ID")):
            if after.channel is None:
                self.queue.vc = None
                self.queue = None

    @_pause.before_invoke
    @_resume.before_invoke
    @_now_playing.before_invoke
    @_loop.before_invoke
    @_queue.before_invoke
    @_clear.before_invoke
    @_delete.before_invoke
    @_shuffle.before_invoke
    @_loopqueue.before_invoke
    async def ensure_state(self, ctx):
        if self.queue is None or self.queue.vc and not self.queue.vc.is_playing() and not self.queue.vc.is_paused():
            await ctx.send("Bot is not playing anything!")
            raise NotPlayingAnything("Bot is not playing anything yet!")
        if not ctx.author.voice or ctx.author.voice.channel is not self.queue.vc.channel:
            await ctx.send("You must be on the same channel as the bot!")
            raise NotPlayingAnything("You must be on the same channel as the bot!")



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