import datetime as dt

import discord


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

        self.shouldLoop = False
        self.startSong = 0

    def createEmbed(self):
        embed = discord.Embed(
            title=f"{self.title}",
            description=f"Uploaded by {self.uploader}",
            colour=discord.Colour.blurple())
        embed.set_thumbnail(url=self.thumbnail)
        embed.add_field(name="Duration", value=str(self._convertedDur))
        embed.add_field(name="Requested By", value=self.requester)
        embed.set_footer(text="▪ Now Playing ▪")
        return embed

    @property
    def convertedDur(self):
        return self._convertedDur
