import asyncio
from typing import List

import discord
from discord.commands.context import ApplicationContext
import spotipy
from spotipy import SpotifyClientCredentials
import yt_dlp as ytdl
import validators

from configFiles.songManagers.Song import Song

YTDL_OPS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'restrictfilenames': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'playlistend': 25,
}


class SongExtractor:

    def __init__(self, loop=None):
        self._loop = loop or asyncio.get_running_loop()
        self.spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

    async def searchOnWeb(self, search: str, ctx: ApplicationContext) -> List[Song]:
        if search.startswith(('https://open.spotify.com/track/', 'https://open.spotify.com/playlist/',
                              'https://open.spotify.com/album/', "https://open.spotify.com/artist/")):
            return await self._spotify_search(search, ctx)
        elif search.startswith('https://www.youtube.com/') or not validators.url(search):
            if not validators.url(search):
                YTDL_OPS["match_title"] = search
            return await self._youtube_search(search, ctx)

    async def _spotify_search(self, search: str, ctx: ApplicationContext):
        tracks = []
        if search.startswith("https://open.spotify.com/track/"):
            result = self.spotify.track(search)
            song_name = result["name"]
            artist = result["artists"][1]["name"] if type(result["artists"]) is list else result["artists"]["name"]
            tracks.append(f'{song_name} by {artist} - lyric')

        elif search.startswith('https://open.spotify.com/album/'):
            await self.sendDetected(ctx, "Album")
            result = self.spotify.album_tracks(search)
            song_array = result["items"]
            tracks.extend(self._getListedTracks(song_array))

        elif search.startswith('https://open.spotify.com/artist/'):
            await self.sendDetected(ctx, "Artist")
            result = self.spotify.artist_top_tracks(search)
            song_array = result["tracks"]
            tracks.extend(self._getListedTracks(song_array))

        elif search.startswith('https://open.spotify.com/playlist/'):
            await self.sendDetected(ctx, "Playlist")
            result = self.spotify.playlist(search)
            song_array = result["tracks"]["items"]
            for i in range(len(song_array)):
                song = song_array[i]["track"]["name"]
                artists = song_array[i]["track"]["artists"][1]["name"] \
                    if type(song_array[i]["artists"]) is list else song_array[i]["artists"]["name"]
                tracks.append(f"{song} by {artists} - Lyrics")

        return self._searchList(tracks, ctx)

    @staticmethod
    def _searchList(tracks, ctx: ApplicationContext):
        with ytdl.YoutubeDL(YTDL_OPS) as ydl:
            return [Song(ydl.extract_info(track, download=False), ctx.author.display_name) for track in tracks]

    async def _youtube_search(self, search: str, ctx: ApplicationContext):
        with ytdl.YoutubeDL(YTDL_OPS) as ydl:
            try:
                info = await self._loop.run_in_executor(None, ydl.extract_info, search, False, False, None, False,
                                                        False)
            except Exception:
                return
            if '_type' in info and info["_type"] == "playlist":
                await self.sendDetected(ctx, "Playlist")
            info = await self._loop.run_in_executor(None, ydl.extract_info, search, False)
            tracks = []
            if 'entries' not in info:
                single_page = info['webpage_url']
                entry = ydl.extract_info(single_page, download=False)
                tracks.append(entry)
            else:
                tracks.extend(iter(info['entries']))
            return [Song(track, ctx.author.display_name) for track in tracks]

    @staticmethod
    def _getListedTracks(song_array):
        tracks = []
        for i in range(len(song_array)):
            song = song_array[i]["name"]
            artist = song_array[i]["artists"][1]["name"] \
                if type(song_array[i]["artists"]) is list else song_array[i]["artists"]["name"]
            tracks.append(f'{song} by {artist} - lyric')
        return tracks

    @staticmethod
    async def sendDetected(ctx, message):
        await ctx.followup.send(embed=discord.Embed(
            title=f"‼{message} detected, gathering will be longer than usual",
            colour=discord.Colour.blurple()
        ), ephemeral=True)
