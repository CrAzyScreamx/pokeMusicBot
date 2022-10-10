from queue import Queue, LifoQueue
from typing import List, Union, Dict

from discord.commands.context import ApplicationContext
import discord
from discord.ext import tasks
from configFiles.songManagers.Song import Song
import random
from collections import deque
from configFiles.predicateChecks import seekConverter

FFMPEG_OPTS = {
    "before_options": '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    "options": '-vn'
}


class QueueManager(Queue):

    def __init__(self, voice_client: discord.VoiceClient, ctx: ApplicationContext):
        super().__init__()
        self._loop = False
        self._voice_client: discord.VoiceClient = voice_client
        self._ctx: ApplicationContext = ctx
        self._currSong = None
        self._currSource = None
        self.cacheQueue = LifoQueue()

        self.deletedIndexes = []
        self.goToPrev = False

    @tasks.loop()
    async def player(self):
        if not self._voice_client.is_playing() and not self._voice_client.is_paused():
            self.player.stop()

    @player.before_loop
    async def before_player(self):
        if self._currSong is None or not self._currSong.shouldLoop:
            if self.goToPrev:
                print([item.title for item in self.cacheQueue.queue])
                cachedSong = self.cacheQueue.get()
                self.queue.appendleft(self._currSong)
                self._currSong = self.cacheQueue.get()
                self.cacheQueue.put(self._currSong)
                print([item.title for item in self.cacheQueue.queue])
                self.goToPrev = False
            elif self._currSong is None or self._currSong.startSong == 0:
                self._currSong: Song = self.get()
                self.cacheQueue.put(self._currSong)  # Puts the new song inside the cachedQueue
        self.createSource()  # Takes the last Song
        if self._currSong.startSong == 0:
            await self._ctx.followup.send(embed=self._currSong.createEmbed(), ephemeral=True)
        self._currSong.startSong = 0
        self._voice_client.play(self._currSource)  # Starts playing the song

    @player.after_loop
    async def after_loop(self):
        if not self.voice_client.is_connected():
            return
        if self._currSong.shouldLoop or self._currSong.startSong > 0:
            self.player.restart()
            return
        if self.empty() and not self.goToPrev:  # Checks if current Queue is empty
            if self._loop:
                self.cacheQueue.queue.reverse()
                while not self.cacheQueue.empty():  # Puts all the same songs
                    self.put(self.cacheQueue.get())
                self.player.restart()
                return
            else:
                self.voice_client.cleanup()
                await self.voice_client.disconnect()
        else:  # The queue is not empty
            self.player.restart()
            return

    @property
    def loop(self):
        return self._loop

    @property
    def voice_client(self):
        return self._voice_client

    @property
    def currSong(self):
        return self._currSong

    @loop.setter
    def loop(self, loop: bool):
        self._loop = loop

    def getQueue(self):
        return self.queue

    def isBotPlaying(self):
        return self._voice_client.is_playing() or self._voice_client.is_paused()

    def createSource(self):
        FFMPEG_OPTS["options"] = f"-vn -ss {self._currSong.startSong}"
        self._currSource = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(self._currSong.stream_url, before_options=FFMPEG_OPTS["before_options"],
                                   options=FFMPEG_OPTS["options"]), volume=0.5)

    def addSongs(self, song: List[Song]):
        for s in song:
            self.put(s)
        if self.qsize() >= 1 and not self.player.is_running():
            self.player.start()

    def pauseAudio(self):
        self._voice_client.pause()

    def resumeAudio(self):
        self._voice_client.resume()

    def loopSong(self):
        self._currSong.shouldLoop = not self._currSong.shouldLoop

    def clearQueue(self):
        self.queue.clear()
        self.cacheQueue.queue.clear()

    def deleteSong(self, item_number: int) -> Union[None, Song]:
        """
        Deletes an item from the song if it's allowed to do so
        :param item_number: the number of the item ( condition: must be between 1 and the size of the queue
        :return: None if song hasn't been deleted, the Song otherwise
        """
        if item_number < 2 or item_number - 2 > len(self.queue):
            return None
        item_number -= 2
        item = self.queue[item_number]
        del self.queue[item_number]
        return item

    def shuffleQueue(self):
        if self.empty():
            return
        random.shuffle(self.queue)

    def skipSong(self):
        self._currSong.shouldLoop = False
        item = self._currSong
        self.voice_client.stop()
        return item

    def returnSong(self):
        self.goToPrev = True
        self._currSong.shouldLoop = False
        item = self._currSong
        self.voice_client.stop()
        return item

    def loopQueue(self):
        self._loop = not self._loop

    def removeDupes(self):
        dequeHolder = deque()
        songTitles = deque()
        for song in self.queue:
            if song.title not in songTitles:
                dequeHolder.append(song)
                songTitles.append(song.title)
        self.queue = dequeHolder

        dequeHolder = deque()
        songTitles = deque()
        for song in self.cacheQueue.queue:
            if song.title not in songTitles:
                dequeHolder.append(song)
                songTitles.append(song.title)
        self.cacheQueue.queue = dequeHolder

    def seekTo(self, seek: int):
        self.currSong.startSong = seek
        self.voice_client.stop()
