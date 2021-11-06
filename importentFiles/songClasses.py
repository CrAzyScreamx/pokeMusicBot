import asyncio
from typing import List
import validators

import discord
import youtube_dl as ytdl
from discord.ext import commands
import datetime as dt
import random

ytdl.utils.bug_reports_message = lambda: ''

YTDL_OPS = {
    "ignoreerrors": True,
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "extract_audio": True,
    "audio_format": "mp3",
    "quiet": True,
    "audio_quality": 9,
}

FFMPEG_BEFORE_OPTS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'


class YTDLSource:

    def __init__(self, search, requester):
        videos = self._extract_videos(self, search=search)
        self._results = list()
        for video in videos:
            self._results.append(Song(video, requester))

    @staticmethod
    def _extract_videos(self, search):
        if not validators.url(search):
            YTDL_OPS["match_title"] = search
        with ytdl.YoutubeDL(YTDL_OPS) as ydl:
            info = ydl.extract_info(search, download=False)
            video = list()

            if 'entries' not in info:
                single_page = info['webpage_url']
                entry = ydl.extract_info(single_page, download=False)
                video.append(entry)
            else:
                for entry in info["entries"]:
                    video.append(entry)

            return video

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
        self.duration = video["duration"]
        self._source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(video_format["url"], before_options=FFMPEG_BEFORE_OPTS), volume=1.0)
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
                 .add_field(name="Duration", value=dt.timedelta(seconds=self.duration))
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

    def _addSong(self, song: Song):
        self._queue.append(song)
        if len(self._queue) == 1:
            self.loopedTask = self._client.loop.create_task(self.create_loop_task())

    def addSongs(self, songs: List[Song]):
        for song in songs:
            self._addSong(song)

    def deleteSong(self, index):
        self._queue.pop(index - 1)

    def shuffle(self):
        self.deleteSong(1)
        random.shuffle(self._queue)
        self.queue.insert(0, self.current)

    def clear(self):
        self._queue.clear()
        self._queue.append(self.current)

    @property
    def queue(self):
        return self._queue

    @property
    def vc(self):
        return self._vc

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

    def pause(self):
        self._vc.pause()

    def resume(self):
        self._vc.resume()

    async def create_loop_task(self):
        while True:
            if len(self._queue) == self.currentIndex:
                self.currentIndex = 0
                break

            async with self._ctx.typing():
                self.current = self.queue[self._currentIndex]
                self.current.source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(self.current.stream_url, before_options=FFMPEG_BEFORE_OPTS), volume=1.0)
                await self._ctx.send(embed=self.current.create_embed())

            if len(self._queue) > 1:
                self._next = self._queue[1]

            self._vc.play(self.current.source)
            while self._vc.is_playing() or self._vc.is_paused():
                await asyncio.sleep(1)
            await asyncio.sleep(1)
            if not self.current.loop:
                self.currentIndex += 1

        if not self._vc is None:
            asyncio.run_coroutine_threadsafe(self._vc.disconnect(),
                                             self._client.loop)
            self._vc = None
