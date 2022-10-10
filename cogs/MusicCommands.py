from typing import Dict, Union

from discord.commands import Option
from discord.ext.pages import Paginator

from configFiles.predicateChecks import *
from configFiles.songManagers import Song
from configFiles.songManagers.QueueManager import QueueManager
from configFiles.songManagers.QueuePages import getQueueBook
from configFiles.songManagers.SongExtractor import SongExtractor

guild_ids = []


class MusicCommands(commands.Cog):

    def __init__(self, client: discord.Bot):
        self.client: discord.Bot = client
        self.songExtractor = SongExtractor(client.loop)
        self.queues: Dict[int, QueueManager] = {}  # guild_id : QueueHolder

    @commands.slash_command(name="join",
                            description="Connects the bot to a channel",)
    @isAuthorConnected()
    @canBotConnect()
    async def _join(self, ctx: ApplicationContext):
        voice_client = await ctx.author.voice.channel.connect()
        await ctx.respond(embed=self.createEmbed(f"👋 Successfully joined {ctx.author.voice.channel.name}, "
                                                 f"type /play to start playing songs!"), ephemeral=True)
        self.queues[ctx.guild.id] = QueueManager(voice_client=voice_client, ctx=ctx)

    @commands.slash_command(name="leave",
                            description="Disconnects the bot from a channel")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _leave(self, ctx: ApplicationContext):
        await ctx.voice_client.disconnect(force=True)
        await ctx.respond(embed=self.createEmbed(f"🤙 Successfully left {ctx.author.voice.channel.name}, Cya!"),
                          ephemeral=True)
        self.queues[ctx.guild.id].player.cancel()

    @commands.slash_command(name="play",
                            description="Plays a song depends on the search (Spotify and YT)")
    @isAuthorConnected()
    @isSameChannel()
    async def _stream(self, ctx: ApplicationContext, search: Option(str, "paste YT/Spotify link or just type whatever "
                                                                         "you want")):
        await ctx.respond(embed=self.createEmbed(f"🎶 Searching ``{search}`` on the web!"), ephemeral=True)
        if ctx.guild.voice_client is None:
            voice_client = await ctx.author.voice.channel.connect()
            self.queues[ctx.guild.id] = QueueManager(voice_client=voice_client, ctx=ctx)
        async with ctx.typing():
            searchResult = await self.songExtractor.searchOnWeb(search=search, ctx=ctx)
        send_msg = self.queues[ctx.guild.id].player.is_running()
        self.queues[ctx.guild.id].addSongs(searchResult)
        if send_msg:
            await ctx.respond(embed=self.createEmbed(f"✅ Enqueued result for ``{search}``"), ephemeral=True)

    @commands.slash_command(name="pause",
                            description="Pauses the current playing music")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _pause(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        if self.queues[ctx.guild.id].voice_client.is_paused():
            await ctx.respond(embed=createErrorEmbed("Music is already paused"), ephemeral=True)
            return
        await ctx.respond(embed=self.createEmbed(f"⏸ Paused ``{self.queues[ctx.guild.id].currSong.title}``"),
                          ephemeral=True)
        self.queues[ctx.guild.id].pauseAudio()

    @commands.slash_command(name="resume",
                            description="Resume the current playing music")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _resume(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        if not self.queues[ctx.guild.id].voice_client.is_paused():
            await ctx.respond(embed=createErrorEmbed("Music is already playing"), ephemeral=True)
            return
        await ctx.respond(embed=self.createEmbed(f"▶️Resumed ``{self.queues[ctx.guild.id].currSong.title}``"),
                          ephemeral=True)
        self.queues[ctx.guild.id].resumeAudio()

    @commands.slash_command(name="nowplaying",
                            description="Sends details about the current playing song")
    @canBotDisconnect()
    async def _nowplaying(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        await ctx.respond(embed=self.queues[ctx.guild.id].currSong.createEmbed(), ephemeral=True)

    @commands.slash_command(name="loopsong",
                            description="Sets weather current song should be looped")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _loopsong(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        self.queues[ctx.guild.id].loopSong()
        if self.queues[ctx.guild.id].currSong.shouldLoop:
            await ctx.respond(embed=self.createEmbed(f"🔁 Looping ``{self.queues[ctx.guild.id].currSong.title}``"),
                              ephemeral=True)
        else:
            await ctx.respond(embed=self.createEmbed(f"🔁❌ Cancelled Looping "
                                                     f"``{self.queues[ctx.guild.id].currSong.title}``"), ephemeral=True)

    @commands.slash_command(name="clear",
                            description="Clears all songs from the queue")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _clear(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        if self.queues[ctx.guild.id].qsize() == 0:
            await ctx.respond(embed=createErrorEmbed("Queue's already empty"), ephemeral=True)
            return
        self.queues[ctx.guild.id].clearQueue()
        await ctx.respond(embed=self.createEmbed("🙀 Emptied queue"), ephemeral=True)

    @commands.slash_command(name="delete",
                            description="Deletes a song from the queue")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _delete(self, ctx: ApplicationContext, value: Option(int, "The number of the song you want to delete")):
        if not await self.isBotRunning(ctx):
            return
        item: Union[None, Song] = self.queues[ctx.guild.id].deleteSong(value)
        if item is None:
            return await ctx.respond(embed=createErrorEmbed("Couldn't delete Song from queue, "
                                                            "type /queue to find which song you want to delete"),
                                     ephemeral=True)
        return await ctx.respond(embed=self.createEmbed(f"✍ ``{item.title}`` has been deleted"), ephemeral=True)

    @commands.slash_command(name="shuffle",
                            description="Shuffles the queue",)
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _shuffle(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        self.queues[ctx.guild.id].shuffleQueue()
        return await ctx.respond(embed=self.createEmbed("🔀 Shuffled queue"), ephemeral=True)

    @commands.slash_command(name="skip",
                            description="Skips the current song",)
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _skip(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        song: Song = self.queues[ctx.guild.id].skipSong()
        return await ctx.respond(embed=self.createEmbed(f"⏭ Skipped ``{song.title}``"), ephemeral=True)

    @commands.slash_command(name="back",
                            description="Goes back to previous song")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _back(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        song: Song = self.queues[ctx.guild.id].returnSong()
        return await ctx.respond(embed=self.createEmbed(f"⏮ Stopped ``{song.title}`` returning to previous"),
                                 ephemeral=True)

    @commands.slash_command(name="loopqueue",
                            description="Loops the whole queue")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _loopqueue(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        self.queues[ctx.guild.id].loopQueue()
        if self.queues[ctx.guild.id].loop:
            await ctx.respond(embed=self.createEmbed("🔁 Looping Queue"), ephemeral=True)
        else:
            await ctx.respond(embed=self.createEmbed("🔁❌ Cancelled Queue Looping"), ephemeral=True)

    @commands.slash_command(name="removedupes",
                            description="Remove all song duplicates")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _removedupes(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        self.queues[ctx.guild.id].removeDupes()
        await ctx.respond(embed=self.createEmbed("❌ Removed all song duplicates"), ephemeral=True)

    @commands.slash_command(name="seek",
                            description="Seeks to a specific time in the video")
    @isAuthorConnected()
    @canBotDisconnect()
    @isSameChannel()
    async def _seek(self, ctx: ApplicationContext,
                    seek: Option(seekConverter, "Seek through the video (format: hh:mm:ss)")):
        if not await self.isBotRunning(ctx):
            return
        await ctx.respond(embed=self.createEmbed(f"⏲ Seeking to ``{seek}`` in "
                                                 f"``{self.queues[ctx.guild.id].currSong.title}``"), ephemeral=True)
        self.queues[ctx.guild.id].seekTo(seek)

    @_seek.error
    async def _seek_error(self, ctx: ApplicationContext, error: CommandError):
        await ctx.respond(embed=createErrorEmbed("Use format hh:mm:ss (ex. 00:00:05)"), ephemeral=True)

    @commands.slash_command(name="queue",
                            description="Presents the current playing queue")
    @isAuthorConnected()
    @canBotDisconnect()
    async def _queue(self, ctx: ApplicationContext):
        if not await self.isBotRunning(ctx):
            return
        queuePages = getQueueBook(self.queues[ctx.guild.id].queue, self.queues[ctx.guild.id].currSong)
        paginator = Paginator(pages=queuePages)
        await paginator.respond(ctx.interaction, ephemeral=True)

    async def isBotRunning(self, ctx: ApplicationContext):
        if not self.queues[ctx.guild.id].isBotPlaying():
            await ctx.respond(embed=createErrorEmbed("Bot is not playing anything at the moment"), ephemeral=True)
            return False
        return True

    @staticmethod
    def createEmbed(message):
        return discord.Embed(
            title=f" {message}",
            colour=discord.Colour.blurple()
        )


def setup(client):
    client.add_cog(MusicCommands(client))
