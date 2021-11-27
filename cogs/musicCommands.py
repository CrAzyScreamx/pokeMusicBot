import os
from typing import Dict

from importentFiles.songClasses import *
from discord.ext import commands


class musicCommands(commands.Cog):

    def __init__(self, client):
        self.client: discord.Client = client
        self.music: Dict[int, Queue] = None

    @commands.command(aliases=['join', 'j', 'summon'])
    async def _join(self, ctx: commands.Context, activate_reaction=True):
        message: discord.Message = ctx.message
        if not ctx.author.voice:
            await ctx.send(
                embed=self._embedSentence("You must be connected to a channel", discord.Color.from_rgb(0, 0, 0)))
            raise NotPlayingAnything("User not connected to the channel")
        if activate_reaction:
            await message.add_reaction("👌")
        vc = await ctx.author.voice.channel.connect()
        self.music = self.music or dict()
        self.music[int(ctx.message.guild.id)] = Queue(self.client, vc, ctx)

    @commands.command(aliases=['leave', 'dc', 'disconnect'])
    async def _leave(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel is self.music[int(ctx.message.guild.id)].vc.channel:
            return await ctx.send(embed=self._embedSentence("You must be connected ot the same channel as the bot",
                                                            discord.Color.from_rgb(0, 0, 0)))
        await ctx.message.add_reaction('👋')
        await self.music[int(ctx.message.guild.id)].vc.disconnect()

    @commands.command(aliases=['play', 'p'])
    async def _stream(self, ctx: commands.Context, *, search: str = None):
        activate = False
        if search is None:
            return await ctx.send(
                embed=self._embedSentence("You must provide a url or a search", discord.Color.from_rgb(0, 0, 0)))
        if not ctx.author.voice:
            await ctx.send(
                embed=self._embedSentence("You must be connected to a channel", discord.Color.from_rgb(0, 0, 0)))
            raise NotPlayingAnything("User not connected to the channel")
        if self.music is None or not int(ctx.message.guild.id) in list(self.music.keys()) or self.music[
            int(ctx.message.guild.id)] is None:
            activate = True
        message: discord.Message = ctx.message
        await message.add_reaction("☝")
        ytdlSource = YTDLSource()
        if search.startswith(tuple(['https://open.spotify.com/track/', 'https://open.spotify.com/playlist/',
                                    'https://open.spotify.com/album/', "https://open.spotify.com/artist/"])):
            await ytdlSource.extract_spotify_videos(search, ctx.author, ctx, self.client.loop)
        elif search.startswith('https://www.youtube.com/') or not validators.url(search):
            await ytdlSource.extract_videos(search, ctx.author, ctx, self.client.loop)
        else:
            return await ctx.send(
                embed=self._embedSentence(f"Unable to fetch URL Data",
                                          discord.Color.from_rgb(0, 0, 0)))
        if activate or self.music[int(ctx.message.guild.id)] is None:
            await ctx.invoke(self._join, activate_reaction=False)
        self.music[int(ctx.message.guild.id)].addSongs(ytdlSource.results)
        if len(ytdlSource.results) == 1:
            return await ctx.send(
                embed=self._embedSentence(f"Enqueued ``{ytdlSource.results[0].title}``", discord.Color.blurple()))
        else:
            return await ctx.send(
                embed=self._embedSentence(f"Enqueued ``{len(ytdlSource.results)}`` songs", discord.Color.blurple()))

    @commands.command(aliases=['pause'])
    async def _pause(self, ctx: commands.Context):
        if self.music[int(ctx.message.guild.id)].vc.is_paused():
            return await ctx.send(embed=self._embedSentence("Audio is paused", discord.Color.from_rgb(0, 0, 0)))
        message: discord.Message = ctx.message
        await message.add_reaction('⏸')
        self.music[int(ctx.message.guild.id)].pause()

    @commands.command(aliases=['resume'])
    async def _resume(self, ctx: commands.Context):
        if not self.music[int(ctx.message.guild.id)].vc.is_paused():
            return await ctx.send(embed=self._embedSentence("Audio is not paused", discord.Color.from_rgb(0, 0, 0)))

        message: discord.Message = ctx.message
        await message.add_reaction('▶')
        self.music[int(ctx.message.guild.id)].resume()

    @commands.command(aliases=['np', 'nowplaying', 'currentsong', 'current'])
    async def _now_playing(self, ctx: commands.Context):
        currentSong: Song = self.music[int(ctx.message.guild.id)].current
        await ctx.send(embed=currentSong.create_embed())

    @commands.command(aliases=['loopsong', 'ls', 'loop'])
    async def _loopSong(self, ctx: commands.Context):
        self.music[int(ctx.message.guild.id)].current.loop = not self.music[int(ctx.message.guild.id)].current.loop
        if self.music[int(ctx.message.guild.id)].current.loop:
            return await ctx.send("Looping Song 🔂")
        else:
            return await ctx.send("Cancelled Song Loop ❌")

    @commands.command(aliases=['queue', 'q'])
    async def _queue(self, ctx: commands.Context):
        if self.music is None or self.music[int(ctx.message.guild.id)] is None:
            return await ctx.send(
                embed=self._embedSentence("Bot is not playing anything", discord.Color.from_rgb(0, 0, 0)))
        if len(self.music[int(ctx.message.guild.id)].queue) == 0:
            return await ctx.send(f"```{self.client.user.display_name} Queue\n```")
        self.music[int(ctx.message.guild.id)].page = 1
        sen = f"```{self.client.user.display_name} Queue - Page {self.music[int(ctx.message.guild.id)].page}\n-------------------\n"
        for i in range(min(25, len(self.music[int(ctx.message.guild.id)].queue))):
            sen += str(i + 1) + ". " + self.music[int(ctx.message.guild.id)].queue[i].title
            sen += "\n"
        loopstate = " Song is Looped" if self.music[int(ctx.message.guild.id)].current.loop else " Song is not Looped"
        queueLoop = "Queue is Looped" if self.music[int(ctx.message.guild.id)].loop else "Queue is not Looped"
        currentSong = self.music[
                          int(ctx.message.guild.id)].current.title + f"(#{self.music[int(ctx.message.guild.id)].currentIndex + 1})"
        nextSong = "\nNext Song -> "
        if self.music[int(ctx.message.guild.id)].next is not None and self.music[
            int(ctx.message.guild.id)].currentIndex != len(self.music[int(ctx.message.guild.id)].queue):
            nextSong += self.music[
                            int(ctx.message.guild.id)].next.title + f"(#{self.music[int(ctx.message.guild.id)].currentIndex + 2})"
        else:
            nextSong += "None"
        sen += f"-----------------------------------------------\n{loopstate}\t\t{queueLoop}\n-------------------\nCurrent Song -> {currentSong}{nextSong}```"
        self.music[int(ctx.message.guild.id)].msg = await ctx.send(sen)
        if self.music[int(ctx.message.guild.id)].countPage() > 1:
            await self.music[int(ctx.message.guild.id)].msg.add_reaction('⏭')

    @commands.command(aliases=['clearqueue', 'clearq', 'clear'])
    async def _clear(self, ctx):
        self.music[int(ctx.message.guild.id)].clear()
        await ctx.message.add_reaction('👌')

    @commands.command(aliases=['delete', 'del', 'remove'])
    async def _delete(self, ctx: commands.Context, index):
        try:
            index = int(index)
        except ValueError:
            return await ctx.send(embed=self._embedSentence("Index must be a number!", discord.Color.from_rgb(0, 0, 0)))
        index = int(index)
        if 1 < index <= len(self.music[int(ctx.message.guild.id)].queue):
            await ctx.send(embed=self._embedSentence(
                f"Song ``{self.music[int(ctx.message.guild.id)].queue[index - 1].title}`` has been deleted",
                discord.Color.blurple()))
            self.music[int(ctx.message.guild.id)].deleteSong(index)
        else:
            if len(self.music[int(ctx.message.guild.id)].queue) == 1 and index == 1:
                return await ctx.send(
                    embed=self._embedSentence("Cannot delete the only song", discord.Color.from_rgb(0, 0, 0)))
            else:
                return await ctx.send(embed=self._embedSentence(
                    f"Index must be between 2 and {len(self.music[int(ctx.message.guild.id)].queue)}",
                    discord.Color.from_rgb(0, 0, 0)))

    @commands.command(aliases=['shuffle'])
    async def _shuffle(self, ctx: commands.Context):
        self.music[int(ctx.message.guild.id)].shuffle()
        await ctx.message.add_reaction('🔀')

    @commands.command(aliases=['skip', 's'])
    async def _skip(self, ctx: commands.Context):
        self.music[int(ctx.message.guild.id)].skip()
        await ctx.message.add_reaction('⏭')

    @commands.command(aliases=['back', 'b'])
    async def _back(self, ctx: commands.Context):
        self.music[int(ctx.message.guild.id)].back()
        await ctx.message.add_reaction('⏮')

    @commands.command(aliases=['lq', 'loopqueue'])
    async def _loopqueue(self, ctx: commands.Context):
        self.music[int(ctx.message.guild.id)].loop = not self.music[int(ctx.message.guild.id)].loop
        if self.music[int(ctx.message.guild.id)].loop:
            return await ctx.send("Looping Queue 🔂")
        await ctx.send("Cancelled Queue Loop ❌")

    @commands.command(aliases=['removedupes'])
    async def _removeDupes(self, ctx: commands.Context):
        self.music[int(ctx.message.guild.id)].removeDupes()
        await ctx.message.add_reaction('👍')

    @commands.command(aliases=['jumpto'])
    async def _jumpTo(self, ctx: commands.Context, index):
        try:
            index = int(index)
        except ValueError:
            return await ctx.send(
                embed=self._embedSentence("Number must be an integer!", discord.Color.from_rgb(0, 0, 0)))
        if not 0 < index <= len(self.music[int(ctx.message.guild.id)].queue):
            return await ctx.send(embed=self._embedSentence(
                f"Number must be between 1 and {len(self.music[int(ctx.message.guild.id)].queue)}",
                discord.Color.from_rgb(0, 0, 0)))
        self.music[int(ctx.message.guild.id)].jumpTo(index)

    @_pause.before_invoke
    @_resume.before_invoke
    @_now_playing.before_invoke
    @_loopSong.before_invoke
    @_clear.before_invoke
    @_delete.before_invoke
    @_shuffle.before_invoke
    @_loopqueue.before_invoke
    @_removeDupes.before_invoke
    @_jumpTo.before_invoke
    async def ensure_state(self, ctx):
        if self.music[int(ctx.message.guild.id)] is None or self.music[int(ctx.message.guild.id)].vc and not \
                self.music[int(ctx.message.guild.id)].vc.is_playing() and not self.music[
            int(ctx.message.guild.id)].vc.is_paused():
            await ctx.send(embed=self._embedSentence("Bot is not playing anything!", discord.Color.from_rgb(0, 0, 0)))
            raise NotPlayingAnything("Bot is not playing anything yet!")
        if not ctx.author.voice or ctx.author.voice.channel is not self.music[int(ctx.message.guild.id)].vc.channel:
            await ctx.send(embed=self._embedSentence("You must be on the same channel as the bot!",
                                                     discord.Color.from_rgb(0, 0, 0)))
            raise NotPlayingAnything("You must be on the same channel as the bot!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        if int(member.id) == int(os.environ.get("BOT_ID")):
            if after.channel is None:
                self.music[int(member.guild.id)].currentIndex = len(self.music[int(member.guild.id)].queue)
                self.music[int(member.guild.id)] = None

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        if not user.bot and self.music[int(reaction.message.guild.id)].msg == reaction.message:
            if str(reaction.emoji) == str('⏭'):
                self.music[int(reaction.message.guild.id)].page += 1
            elif str(reaction.emoji) == str('⏮'):
                self.music[int(reaction.message.guild.id)].page -= 1
            firstTrack = (self.music[int(reaction.message.guild.id)].page - 1) * 25
            trackList = list()
            for i in range(firstTrack, min(firstTrack + 25, len(self.music[int(reaction.message.guild.id)].queue))):
                trackList.append(self.music[int(reaction.message.guild.id)].queue[i])
            await self.editQueue(reaction.message, trackList)
            msg: discord.Message = reaction.message
            for r in msg.reactions:
                await msg.clear_reaction(r)
            if self.music[int(reaction.message.guild.id)].page == 1:
                await msg.add_reaction('⏭')
            elif 1 < self.music[int(reaction.message.guild.id)].page < self.music[
                int(reaction.message.guild.id)].countPage():
                await msg.add_reaction('⏭')
                await msg.add_reaction('⏮')
            elif self.music[int(reaction.message.guild.id)].countPage() == self.music[
                int(reaction.message.guild.id)].page:
                await msg.add_reaction('⏮')

    async def editQueue(self, msg: discord.Message, trackList: List[Song]):
        sen = f"```{self.client.user.display_name} Queue - Page {self.music[int(msg.guild.id)].page}\n-------------------\n"
        for i in range(len(trackList)):
            sen += str((i + 1) + ((self.music[int(msg.guild.id)].page - 1) * 25)) + ". " + trackList[i].title
            sen += "\n"
        loopstate = " Song is Looped" if self.music[int(msg.guild.id)].current.loop else " Song is not Looped"
        queueLoop = "Queue is Looped" if self.music[int(msg.guild.id)].loop else "Queue is not Looped"
        currentSong = self.music[
                          int(msg.guild.id)].current.title + f"(#{self.music[int(msg.guild.id)].currentIndex + 1})"
        nextSong = f"\nNext Song -> {self.music[int(msg.guild.id)].next.title}(#{self.music[int(msg.guild.id)].currentIndex + 2})" if \
            self.music[int(msg.guild.id)].currentIndex != len(
                self.music[int(msg.guild.id)].queue) else None
        sen += f"-----------------------------------------------\n{loopstate}\t\t{queueLoop}\n-------------------\nCurrent Song -> {currentSong}{nextSong}```"
        await msg.edit(content=sen)

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
