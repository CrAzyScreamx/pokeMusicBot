import pprint

import spotipy
from discord.ext import commands
from spotipy import SpotifyClientCredentials


class SpotiTest(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())



def setup(client):
    client.add_cog(SpotiTest(client))
