import asyncio
from typing import List

import validators

import discord
import yt_dlp as ytdl
from discord.ext import commands
import datetime as dt
import random
import spotipy
from spotipy import SpotifyClientCredentials

ytdl.utils.bug_reports_message = lambda: ''

YTDL_OPS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'playlistend': 25
}

FFMPEG_BEFORE_OPTS = {
    "before_options": '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    "options": '-vn'
}


class YTDLSource:

    def __init__(self):
        self.videos = None
        self._results = []
        self.spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

    async def extract_info(self, search: str, ctx: commands.Context, loop=None):
        async with ctx.typing():
            loop = loop or asyncio.get_event_loop()
            requester = ctx.author
            embed = discord.Embed(
                description="Unable to fetch URL",
                color=discord.Color.from_rgb(0, 0, 0))
            if search.startswith(tuple(['https://open.spotify.com/track/', 'https://open.spotify.com/playlist/',
                                        'https://open.spotify.com/album/', "https://open.spotify.com/artist/"])):
                await self._extract_spotify(search, ctx, requester, loop)
            elif search.startswith('https://www.youtube.com/') or not validators.url(search):
                if not validators.url(search):
                    YTDL_OPS["match_title"] = search
                await self._extract_yt(search, ctx, requester, loop)
            else:
                return await ctx.send(embed=embed)
            if len(self._results) == 0:
                return await ctx.send(embed=embed)
            return self._results

    async def _extract_yt(self, search: str, ctx: commands.Context, requester, loop):
        with ytdl.YoutubeDL(YTDL_OPS) as ydl:
            try:
                info = await loop.run_in_executor(None, ydl.extract_info, search, False, False, None, False, False)
            except Exception:
                return
            videos = []
            if '_type' in info and info["_type"] == "playlist":
                await ctx.send(embed=self._detectedSen("Playlist"))
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

    async def _extract_spotify(self, search: str, ctx: commands.Context, requester, loop):
        tracks = []
        if search.startswith('https://open.spotify.com/track/'):
            result = self.spotify.track(search)
            tracks.append(result['name'] + result['artists'][0]['name'])
        elif search.startswith('https://open.spotify.com/playlist/'):
            await ctx.send(embed=self._detectedSen("Playlist"))
            results = self.spotify.playlist(search)
            for result in results['tracks']['items']:
                tracks.append(result['track']['name'] + " - " + result['track']['artists'][0]['name'] + " (Lyrics)")
        elif search.startswith('https://open.spotify.com/album/'):
            await ctx.send(embed=self._detectedSen("Album"))
            results = self.spotify.album(search)
            for result in results['tracks']['items']:
                tracks.append(result['name'] + " - " + result['artists'][0]['name'] + " (Lyrics)")

        elif search.startswith('https://open.spotify.com/artist/'):
            await ctx.send(embed=self._detectedSen("Artists"))
            results = self.spotify.artist_top_tracks(search)
            for result in results['tracks']:
                tracks.append(result['name'] + " - " + result['artists'][0]['name'] + " (Lyrics)")
        entries = await loop.run_in_executor(None, self._searchTracks, tracks)
        for entry in entries:
            self._results.append(Song(entry["entries"][0], requester))

    @staticmethod
    def _searchTracks(tracks: List[str]):
        count = 0
        entries = []
        for track in tracks:
            YTDL_OPS["match_title"] = track
            with ytdl.YoutubeDL(YTDL_OPS) as ydl:
                count += 1
                entry = ydl.extract_info(track, download=False)
                entries.append(entry)
        return entries

    @staticmethod
    def _detectedSen(keyword: str):
        return discord.Embed(
            description=f"{keyword} Detected, gathering will take longer than usual",
            color=discord.Color.blurple()
        )

    @property
    def results(self):
        return self._results


class Song:

    def __init__(self, video, requester):
        video_format = video["formats"]
        for fmt in video_format:
            if fmt['format_id'] == '251':
                self.stream_url = fmt['url']
        for fmt in video_format:
            if fmt['acodec'] != 'none':
                self.stream_url = fmt['url']
        self.video_url = video["webpage_url"]
        self.title = video["title"]
        self.uploader = video["uploader"] if "uploader" in video else ""
        self.thumbnail = video["thumbnail"] if "thumbnail" in video else None
        self.requester = requester
        self._duration = video["duration"]
        self._convertedDur = dt.timedelta(seconds=self._duration)
        self._source = None
        self._loop = False
        self._seek = 0

    @property
    def seek(self):
        return self._seek

    @seek.setter
    def seek(self, value):
        self._seek = value

    @property
    def convertedDur(self):
        return self._convertedDur

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        self._source = value

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value):
        self._loop = value

    def createSongEmbed(self):
        return (discord.Embed(
            title="Now Playing",
            description=f"``{self.title}``",
            color=discord.Color.blurple()
        )
                 .add_field(name="Duration", value=self._convertedDur)
                 .add_field(name="Requested By", value=self.requester.display_name)
                 .set_thumbnail(url=self.thumbnail))


class UnableToFetchException(Exception):
    pass
