import asyncio
import math
from typing import List
import validators

import discord
import youtube_dl as ytdl
from discord.ext import commands
import datetime as dt
import random
import re

ytdl.utils.bug_reports_message = lambda: ''

YTDL_OPS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

FFMPEG_BEFORE_OPTS = {
    "before_options": '-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 2',
    "options": '-vn'
}


class YTDLSource:

    def __init__(self):
        self.videos = None
        self._results = list()

    async def extract_videos(self, search, requester, ctx: commands.Context, loop=None):
        loop = loop or asyncio.get_event_loop()
        if not validators.url(search):
            YTDL_OPS["match_title"] = search
        with ytdl.YoutubeDL(YTDL_OPS) as ydl:
            async with ctx.typing():
                try:
                    info = await loop.run_in_executor(None, ydl.extract_info, search, False, None, {}, False)
                except Exception:
                    info = -1
                videos = list()
                if info == -1:
                    self.results.append(-1)
                else:
                    if '_type' in info and info["_type"] == "playlist":
                        await ctx.send(embed=discord.Embed(
                            description="Playlist detected, gathering will take longer than usual",
                            color=discord.Color.blurple()
                        ))
                    info = await loop.run_in_executor(None, ydl.extract_info, search, False)

                    if 'entries' not in info:
                        single_page = info['webpage_url']
                        entry = ydl.extract_info(single_page, download=False)
                        videos.append(entry)
                    else:
                        for entry in info["entries"]:
                            videos.append(entry)

                    for video in videos:
                        self._results.append(Song(video, requester))

    @property
    def results(self):
        return self._results


class Song:

    def __init__(self, video, requested_by):
        video_format = video["formats"][0]
        self.stream_url = video_format["url"]
        self.video_url = video["webpage_url"]
        self.title = video["title"]
        self.uploader = video["uploader"] if "uploader" in video else ""
        self.thumbnail = video["thumbnail"] if "thumbnail" in video else None
        self.requested = requested_by
        self._duration = video["duration"]
        self._source = None
        self._loop = False

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value: discord.PCMVolumeTransformer):
        self._source = value

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    def create_embed(self):
        embed = (discord.Embed(
            title="Now Playing",
            description=f"``{self.title}``",
            color=discord.Color.blurple()
        )
                 .add_field(name="Duration", value=dt.timedelta(seconds=self._duration))
                 .add_field(name="Requested By", value=self.requested.display_name)
                 .set_thumbnail(url=self.thumbnail))
        return embed


class Queue:
    def __init__(self, client: discord.Client, vc: discord.VoiceClient, ctx: commands.Context):
        self._client = client
        self._queue: List[Song] = list()
        self._vc = vc
        self._ctx = ctx
        self._current: Song = None
        self._next: Song = None
        self._currentIndex = 0
        self.loopedTask = None

        self._skipping = False
        self._backing = False
        self._loop = False
        self._msg: discord.Message = None
        self._page = 1

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, value: int):
        self._page = value

    def countPage(self):
        return math.ceil(len(self.queue) / 25)

    def _addSong(self, song: Song):
        self._queue.append(song)
        if len(self._queue) == 1:
            self.loopedTask = self._client.loop.create_task(self.create_loop_task())

    def addSongs(self, songs: List[Song]):
        for song in songs:
            if len(self._queue) == 1:
                self.next = song
            self._addSong(song)

    def deleteSong(self, index):
        self._queue.pop(index - 1)

    def shuffle(self):
        passedSongs = list()
        for i in range(self.currentIndex + 1):
            passedSongs.append(self.queue[0])
            self.deleteSong(1)
        passedSongs = reversed(passedSongs)
        random.shuffle(self._queue)
        for song in passedSongs:
            self._queue.insert(0, song)
        if self.currentIndex + 1 < len(self._queue):
            self._next = self._queue[self.currentIndex + 1]

    def clear(self):
        self._queue.clear()
        self._queue.append(self.current)

    def skip(self):
        self._skipping = True

    def back(self):
        self._backing = True

    @property
    def msg(self):
        return self._msg

    @msg.setter
    def msg(self, value: discord.Message):
        self._msg = value

    @property
    def queue(self):
        return self._queue

    @queue.setter
    def queue(self, value: List[Song]):
        self._queue = value

    @property
    def vc(self):
        return self._vc

    @vc.setter
    def vc(self, value: discord.VoiceClient):
        self._vc = value

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, value: Song):
        self._current = value

    @property
    def next(self):
        return self._next

    @next.setter
    def next(self, value: Song):
        self._next = value

    @property
    def currentIndex(self):
        return self._currentIndex

    @currentIndex.setter
    def currentIndex(self, value: int):
        self._currentIndex = value

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    def pause(self):
        self._vc.pause()

    def resume(self):
        self._vc.resume()

    def removeDupes(self):
        queue_set = set()
        queue_add = queue_set.add
        self.queue = [x for x in self.queue if not (x.title in queue_set or queue_add(x.title))]
        for song in self.queue:
            if song.title == self.current.title:
                self.currentIndex = self.queue.index(song)
                self.current = song
        if self.currentIndex + 1 < len(self._queue):
            self._next = self._queue[self.currentIndex + 1]

    async def create_loop_task(self):
        while True:
            if len(self._queue) == self.currentIndex:
                self.currentIndex = 0
                break

            async with self._ctx.typing():
                self.current = self.queue[self._currentIndex]
                self.current.source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(self.current.stream_url, before_options=FFMPEG_BEFORE_OPTS["before_options"],
                                           options=FFMPEG_BEFORE_OPTS["options"]), volume=0.5)

                await self._ctx.send(embed=self.current.create_embed())

            if len(self._queue) > 1 and self.currentIndex + 1 < len(self._queue):
                self._next = self._queue[self.currentIndex + 1]

            self._vc.play(self.current.source)
            while self._vc.is_playing() or self._vc.is_paused():
                if self._skipping or self._backing:
                    self._vc.stop()
                    break
                await asyncio.sleep(1)
            if not self.current.loop or self._skipping:
                self._skipping = False
                self.currentIndex += 1
            if self._backing:
                if self.currentIndex > 0:
                    self._backing = False
                    self.currentIndex -= 2

        if self._loop:
            self.currentIndex = 0
            self.loopedTask = self._client.loop.create_task(self.create_loop_task())
        if not self._vc is None and not self._loop:
            asyncio.run_coroutine_threadsafe(self._vc.disconnect(),
                                             self._client.loop)
            self._vc = None
