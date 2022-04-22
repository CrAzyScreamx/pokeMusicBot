from typing import Dict
import re

import discord
from discord.ext import commands
from discord.utils import get
from songPackage.SourceExtractor import YTDLSource, Song
from songPackage.NodeClasses import SongQueue
from discord.ui import Button, View

emojis = ['✅', '❌']


class MusicCommands(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.music: Dict[int, SongQueue] = {}

    @commands.command(aliases=['join', 'j', 'summon'])
    async def _join(self, ctx: commands.Context, activate=True):
        if self.is_connected(ctx):
            return
        if activate is not True and activate is not False:
            activate = True
        msg, gid = self.getGuild(ctx)
        if not ctx.author.voice:
            return await ctx.send(
                embed=discord.Embed(
                    description=f"{emojis[1]} You must be connected to a channel",
                    color=discord.Color.from_rgb(0, 0, 0)))
        if self.is_connected(ctx) and activate:
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Bot is already connected to a channel"))
        if activate:
            await msg.add_reaction("👌")
        if gid not in self.music.keys() and not self.is_connected(ctx):
            vc = await ctx.author.voice.channel.connect()
            self.music = self.music or dict()
            self.music[gid] = SongQueue(self.client, vc, ctx)


    @commands.command(aliases=['l', 'dc', 'leave'])
    async def _leave(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        if (
            not ctx.author.voice
            or gid not in self.music.keys()
            or ctx.author.voice.channel is not self.music[gid].vc.channel
        ):
            return await ctx.send(embed=discord.Embed(
                description="You must be connected to the same channel as the bot",
                color=discord.Color.from_rgb(0, 0, 0)))
        if self.music[gid].loopedTask is not None:
            self.music[gid].loopedTask.cancel()
        await ctx.message.add_reaction('👋')
        self.music[gid].vc.cleanup()
        await self.music[gid].vc.disconnect()
        self.music.pop(gid)

    @commands.command(aliases=['play', 'p', 'stream'])
    async def _stream(self, ctx: commands.Context, *, search: str = None):
        msg, gid = self.getGuild(ctx)
        if search is None:
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} You must provide a URL or a search string",
                color=discord.Color.from_rgb(0, 0, 0)))
        if not ctx.author.voice:
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} You must connected to a channel",
                color=discord.Color.from_rgb(0, 0, 0)))
        if not self.is_connected(ctx):
            if gid in self.music.keys():
                self.music.pop(gid)
            await ctx.invoke(self._join, False)
        await msg.add_reaction("☝")
        ytdlSource = YTDLSource()
        results = await ytdlSource.extract_info(search, ctx, self.client.loop)
        if not isinstance(results, discord.Message):
            if len(results) == 1:
                await ctx.send(embed=discord.Embed(
                    description=f"{emojis[0]} Enqueued ``{results[0].title}``",
                    color=discord.Color.blurple()))
            else:
                await ctx.send(embed=discord.Embed(
                    description=f"{emojis[0]} Enqueued ``{len(results)}`` songs",
                    color=discord.Color.blurple()))
            self.music[gid].enqueueList(results)

    @commands.command(aliases=['pause'])
    async def _pause(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        if not self.music[gid].vc.is_playing():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} No Audio is being played",
                color=discord.Color.from_rgb(0, 0, 0)))
        elif self.music[gid].vc.is_paused():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Audio is already paused, type ``+resume`` to unpause the audio",
                color=discord.Color.from_rgb(0, 0, 0)))
        await msg.add_reaction('⏸')
        self.music[gid].pause()

    @commands.command(aliases=['resume'])
    async def _resume(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        if not self.music[gid].vc.is_playing() and not self.music[gid].vc.is_paused():
            print(self.music[gid].vc.is_paused())
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} No Audio is being played",
                color=discord.Color.from_rgb(0, 0, 0)))
        elif not self.music[gid].vc.is_paused():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Audio is already playing, type ``+pause`` to pause the audio",
                color=discord.Color.from_rgb(0, 0, 0)))
        await msg.add_reaction('▶')
        self.music[gid].resume()

    @commands.command(aliases=['np', 'nowplaying', 'current', 'currentsong'])
    async def _nowPlaying(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        if not self.music[gid].vc.is_playing():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} No Audio is being played",
                color=discord.Color.from_rgb(0, 0, 0)))
        await ctx.send(embed=self.music[gid].curr.createSongEmbed())

    @commands.command(aliases=['loopsong', 'ls', 'loop'])
    async def _loopSong(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        if not self.music[gid].vc.is_playing():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} No Audio is being played",
                color=discord.Color.from_rgb(0, 0, 0)))
        self.music[gid].curr.loop = not self.music[gid].curr.loop
        if self.music[gid].curr.loop:
            return await ctx.send("Looping Song 🔂")
        else:
            return await ctx.send("Cancelled Song Loop ❌")

    @commands.command(aliases=['queue', 'q'])
    async def _queue(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        startOfPage = f"```{self.client.user.display_name}'s Queue - Page 1\n-------------------\n"
        if gid not in self.music.keys() or not self.is_connected(ctx) or \
                not self.music[gid].vc.is_playing() and not self.music[gid].vc.is_paused():
            return await ctx.send(startOfPage + "\n```")
        elif self.music[gid].__sizeof__() == 0:
            startOfPage += f"1. {self.music[gid].curr.title} - ({self.music[gid].curr.convertedDur})" \
                           f"\n-------------------\n** Current Song: {self.music[gid].curr.title}" \
                           f" - ({self.music[gid].curr.convertedDur})\n** Next Song: None - " \
                           f"(None)\n```"
        else:
            startOfPage += f"{self.music[gid].__str__()[0]}-------------------\n** Current Song: {self.music[gid].curr.title}" \
                           f" - ({self.music[gid].curr.convertedDur})\n** Next Song: {self.music[gid].first().title or None} - " \
                           f"({self.music[gid].first().convertedDur or None})\n```"
        btnAfter = Button(style=discord.ButtonStyle.grey, emoji="⏭")
        btnBefore = Button(style=discord.ButtonStyle.grey, emoji="⏮")
        self.music[gid].page = 0

        btnAfter.callback = lambda inter: self.btn_after_callback(inter, ctx)
        btnBefore.callback = lambda inter: self.btn_before_callback(inter, ctx)
        view = View()

        view.add_item(btnAfter)
        view.add_item(btnBefore)
        if self.music[gid].msg:
            # This try checks if the message is already deleted
            try:
                await self.music[gid].msg.delete()
            except Exception:
                pass
        self.music[gid].msg = await ctx.send(startOfPage, view=view)

    @commands.command(aliases=['clearqueue', 'clearq', 'clear'])
    async def _clear(self, ctx):
        msg, gid = self.getGuild(ctx)
        self.music[gid].clear()
        await msg.add_reaction('👌')

    @commands.command(aliases=['delete', 'del', 'remove'])
    async def _delete(self, ctx: commands.Context, index: int):
        msg, gid = self.getGuild(ctx)
        if not self.is_connected(ctx) or not self.music[gid].vc.is_playing():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} No Audio is being played"
            ))
        if index == 1:
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} You can't delete the current song"
            ))
        if index > self.music[gid].__sizeof__()+1 or index < 2:
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} You must choose an index between 2 and {self.music[gid].__sizeof__()+1}"
            ))
        await msg.add_reaction('👌')
        removedSong: Song = self.music[gid].__delete__(index-2)
        await ctx.send(embed=discord.Embed(
            description=f"{emojis[1]} Song ``{removedSong.title}`` has been deleted"
        ))



    @commands.command(aliases=['shuffle'])
    async def _shuffle(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        if not self.music[gid].vc.is_playing() and not self.music[gid].vc.is_paused():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Bot must be playing something",
                color=discord.Color.from_rgb(0, 0, 0)))
        self.music[gid].shuffle()
        await msg.add_reaction('🔀')

    @commands.command(aliases=['skip', 's'])
    async def _skip(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        self.music[gid].skip()
        await msg.add_reaction('⏭')

    @commands.command(aliases=['back', 'b'])
    async def _back(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        print(len(self.music[gid].passed))
        if len(self.music[gid].passed) > 1:
            self.music[gid].back()
        await msg.add_reaction('⏮')

    @commands.command(aliases=['lq', 'loopqueue'])
    async def _loopqueue(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        if not self.music[gid].vc.is_playing() and not self.music[gid].vc.is_paused():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Bot must be playing something",
                color=discord.Color.from_rgb(0, 0, 0)))
        self.music[gid].loop()
        if self.music[gid].loop:
            return await ctx.send("Looping Queue 🔂")
        await ctx.send("Cancelled Queue Loop ❌")

    @commands.command(aliases=['removedupes'])
    async def _removeDupes(self, ctx: commands.Context):
        msg, gid = self.getGuild(ctx)
        if not self.music[gid].vc.is_playing() and not self.music[gid].vc.is_paused():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Bot must be playing something",
                color=discord.Color.from_rgb(0, 0, 0)))
        self.music[gid].removeDupes()
        await msg.add_reaction('👍')

    @commands.command(aliases=['seek', 'seekTo'])
    async def _seek(self, ctx: commands.Context, time: str):
        msg, gid = self.getGuild(ctx)
        if not self.music[gid].vc.is_playing() and not self.music[gid].vc.is_paused():
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Bot must be playing something",
                color=discord.Color.from_rgb(0, 0, 0)))
        # Check if string time matches hh:mm:ss or hh:mm format
        if time.count(':') == 2:
            time = time.split(':')
            time = int(time[0]) * 3600 + int(time[1]) * 60 + int(time[2])
        elif time.count(':') == 1:
            time = time.split(':')
            time = int(time[0]) * 60 + int(time[1]) + 1
        else:
            return await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Invalid time format",
                color=discord.Color.from_rgb(0, 0, 0)))
        time = 1 if time == 0 else time
        self.music[gid].seek(time)
        await msg.add_reaction('⏱')



    @_removeDupes.before_invoke
    @_loopqueue.before_invoke
    @_clear.before_invoke
    @_back.before_invoke
    @_skip.before_invoke
    @_delete.before_invoke
    @_shuffle.before_invoke
    @_loopSong.before_invoke
    @_resume.before_invoke
    @_leave.before_invoke
    @_pause.before_invoke
    @_pause.before_invoke
    @_seek.before_invoke
    async def ensure_state(self, ctx):
        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} You must be connected to a channel",
                color=discord.Color.from_rgb(0, 0, 0)))
        if not self.is_connected(ctx):
            await ctx.send(embed=discord.Embed(
                description=f"{emojis[1]} Bot must be connected to a voice channel",
                color=discord.Color.from_rgb(0, 0, 0)))
            raise EnsureStateFailed

    @staticmethod
    def getGuild(ctx: commands.Context):
        message = ctx.message
        guild: discord.Guild = ctx.guild
        return message, int(guild.id)

    @staticmethod
    def is_connected(ctx: commands.Context):
        vc: discord.VoiceClient = get(ctx.bot.voice_clients, guild=ctx.guild)
        return vc and vc.is_connected()

    async def btn_after_callback(self, interaction, ctx):
        msg, gid = self.getGuild(ctx)
        if self.music[gid].page + 1 < len(self.music[gid].__str__()):
            self.music[gid].page += 1
            await self.music[gid].msg.edit(content=self.getPageMethod(gid))

    async def btn_before_callback(self, interaction, ctx):
        msg, gid = self.getGuild(ctx)
        if self.music[gid].page > 0:
            self.music[gid].page -= 1
            await self.music[gid].msg.edit(content=self.getPageMethod(gid))

    def getPageMethod(self, gid):
        startOfPage = f"```{self.client.user.display_name}'s Queue - Page {self.music[gid].page + 1}\n-------------------\n"
        startOfPage += f"{self.music[gid].__str__()[self.music[gid].page]}-------------------\n** Current Song: {self.music[gid].curr.title}" \
                       f" - ({self.music[gid].curr.convertedDur})\n** Next Song: {self.music[gid].first().title} - " \
                       f"({self.music[gid].first().convertedDur})\n```"
        return startOfPage


def setup(client):
    client.add_cog(MusicCommands(client))


class EnsureStateFailed(Exception):
    pass
