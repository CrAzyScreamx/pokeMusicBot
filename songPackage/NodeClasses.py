import asyncio
import random
from typing import List

import discord
from discord.ext import commands

from songPackage.SourceExtractor import FFMPEG_BEFORE_OPTS


class SongNode:

    def __init__(self, data):
        self.data = data
        self.next = None
        self.prev = None
        self._loop = False

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value):
        self._loop = value


class SongQueue:

    def __init__(self, client: discord.Client, vc: discord.VoiceClient, ctx: commands.Context):
        self.head = None
        self.last = None

        self.client = client
        self.vc = vc
        self.ctx = ctx
        self._curr = None
        self._skip = False
        self._back = False
        self._passed = list()
        self.loopedTask = None
        self._loop = False

        self._msg: discord.Message = None
        self._page = 0

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, value):
        self._page = value

    @property
    def msg(self):
        return self._msg

    @msg.setter
    def msg(self, value: discord.Message):
        self._msg: discord.Message = value

    @property
    def curr(self):
        return self._curr

    @property
    def loop(self):
        return self._loop

    @property
    def passed(self):
        return self._passed

    def skip(self):
        self._skip = True

    def back(self):
        self._back = True

    def loop(self):
        self._loop = True

    def pause(self):
        self.vc.pause()

    def resume(self):
        self.vc.resume()

    def enqueue(self, data):
        if self.last is None:
            self.head = SongNode(data)
            self.last = self.head
            if not self.loopedTask in asyncio.all_tasks(self.client.loop) or self.loopedTask is None:
                self.loopedTask = self.client.loop.create_task(self.create_loop_task())
        else:
            self.last.next = SongNode(data)
            self.last.next.prev = self.last
            self.last = self.last.next

    def enqueueList(self, datas: List):
        for data in datas:
            self.enqueue(data)

    def dequeue(self):
        if self.head is None:
            return None
        else:
            temp = self.head.data
            self.head = self.head.next
            if self.head:
                self.head.prev = None
            else:
                self.last = None
            self._passed.append(temp)
            return temp

    def VIPAccess(self, data):
        if self.last is None:
            self.enqueue(data)
        else:
            self.head.prev = SongNode(data)
            self.head.prev.next = self.head
            self.head = self.head.prev

    def clear(self):
        self.head = None
        self.last = None

    def first(self):
        return self.head.data or None

    def __sizeof__(self):
        temp = self.head
        count = 0
        while temp:
            count = count + 1
            temp = temp.next
        return count

    def isEmpty(self):
        return self.head is None

    def __str__(self):
        queue = list()
        curr = f"1. {self._curr.title} - ({self._curr.convertedDur})\n"
        count = 2
        temp: SongNode = self.head
        while temp is not None:
            curr += f"{count}. {temp.data.title} - ({temp.data.convertedDur})\n"
            if count % 20 == 0 or temp.next is None:
                queue.append(curr)
                curr = ""
            count += 1
            temp = temp.next
        if len(queue) == 0:
            queue.append(curr)
        return queue

    def removeSong(self, index):
        if self.last is None:
            return None
        else:
            temp = self.head
            for i in range(index):
                temp = temp.next
            nodeData = temp.data
            prevSong = temp.prev
            nextSong = temp.next
            temp.prev.next = nextSong
            temp.next.prev = prevSong
            return nodeData

    def toList(self):
        if self.last is None:
            return list()
        nodeList = list()
        temp = self.head
        while temp:
            nodeList.append(temp.data)
            temp = temp.next
        print(nodeList)
        return nodeList

    def shuffle(self, fromPointer=0):
        nodeList: List = self.toList()
        currList: List = list()
        for i in range(fromPointer):
            currList.append(nodeList.pop(i))
        random.shuffle(nodeList)
        nodeList += currList
        self.clear()
        for data in nodeList:
            self.enqueue(data)

    def removeDupes(self):
        self.VIPAccess(self._curr)
        current = self.head
        # This is require to keep track of the prev Node
        prev = None
        duplicate_dict = dict()
        while current:
            if current.data.title not in duplicate_dict:
                duplicate_dict[current.data.title] = None
                # Track the prev Node
                prev = current
            else:
                # When a duplicate is found assign prev Node's next to current's next
                prev.next = current.next

            current = current.next
        self.dequeue()

    def __index__(self, data):
        try:
            return self.toList().index(data)
        except ValueError:
            return -1

    async def create_loop_task(self):
        while True:
            if self.isEmpty():
                self._curr = None
                break

            async with self.ctx.typing():
                if self._curr is None:
                    self._curr = self.dequeue()
                elif self._skip:
                    self._skip = False
                    self._curr = self.dequeue()
                elif len(self._passed) > 0 and self._back:
                    self._back = False
                    self.VIPAccess(self._passed.pop())
                    self._curr = self.dequeue()
                elif not self._curr.loop:
                    self._curr = self.dequeue()

            self._curr.source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(self._curr.stream_url, before_options=FFMPEG_BEFORE_OPTS["before_options"],
                                       options=FFMPEG_BEFORE_OPTS["options"]), volume=0.5)

            await self.ctx.send(embed=self._curr.createSongEmbed())
            self.vc.play(self._curr.source)
            while self.vc.is_playing() or self.vc.is_paused():
                if self._skip or self._back:
                    if self._back:
                        self.VIPAccess(self._passed.pop())
                    self.vc.stop()
                    break
                await asyncio.sleep(1)
        if self._loop:
            for data in self._passed:
                self.enqueue(data)
            self._passed.clear()
            self.loopedTask = self.client.loop.create_task(self.create_loop_task())
        else:
            asyncio.run_coroutine_threadsafe(self.vc.disconnect(),
                                             self.client.loop)
