import math
import queue
from typing import List, Deque

import discord
from discord.ext.pages import Page
from queue import Queue
from configFiles.songManagers.Song import Song
from collections import deque


def getQueueBook(currQueue: deque, currPlaying: Song):
    currSongs: Deque[Song] = currQueue.copy()
    currSongs.appendleft(currPlaying)
    embedPages: List[List[discord.Embed]] = _createTitleList(currSongs)
    return [Page(embeds=embeds) for embeds in embedPages]


def _createTitleList(currSongs) -> List[List[discord.Embed]]:
    my_titles: List[List[discord.Embed]] = []

    curr_list = []
    PAGE_BREAK = 5
    for counter, item in enumerate(currSongs):
        if (counter+1) % PAGE_BREAK == 0 and counter != 0:
            breakSongEmbed = item.createEmbed()
            breakSongEmbed.set_footer(text="")
            curr_list.append(breakSongEmbed)
            my_titles.append(curr_list.copy())
            curr_list.clear()
        else:
            songEmbed = item.createEmbed()
            songEmbed.set_footer(text="")
            curr_list.append(songEmbed)
    if curr_list:
        my_titles.append(curr_list.copy())
        curr_list.clear()
    my_titles[0][0].set_footer(text="▪ Now Playing ▪")
    if len(my_titles[0]) > 1:
        my_titles[0][1].set_footer(text="▪ Next Song ▪")
    return my_titles
