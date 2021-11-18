import pprint

import spotipy
from discord.ext import commands
from spotipy import SpotifyClientCredentials


class SpotiTest(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

    @commands.command()
    async def SpotiTestAlbum(self, ctx, search):
        artist = self.spotify.artist_top_tracks(search)
        print(artist['tracks'][0]['artists'][0]['name'])
        print(artist['tracks'][0]['name'])



def setup(client):
    client.add_cog(SpotiTest(client))
