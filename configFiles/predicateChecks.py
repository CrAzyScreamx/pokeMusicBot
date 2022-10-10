import discord
from discord.commands.context import ApplicationContext
from discord.ext import commands
from discord.ext.commands import Context, BadArgument, CommandError


def isAuthorConnected():
    """
    Checks if the author is connected to any voice channel
    :return: True if author is connected, false otherwise
    """

    async def predicate(ctx: ApplicationContext):
        if ctx.author.voice is None:
            await ctx.respond(embed=createErrorEmbed("You Must be connected to the voice channel"),
                              ephemeral=True)
            return False
        return True

    return commands.check(predicate)


def canBotConnect():
    """
    Checks if the bot can be connected to a voice channel
    :return: False if it's already connected, True otherwise
    """

    async def predicate(ctx: ApplicationContext):
        if ctx.guild.voice_client is not None:
            await ctx.respond(embed=createErrorEmbed("The bot is already connected to a voice channel"),
                              ephemeral=True)
            return False
        return True

    return commands.check(predicate)


def canBotDisconnect():
    """
    Checks if the bot can be disconnected from a voice channel
    :return: False if it's already disconnected, True otherwise
    """

    async def predicate(ctx: ApplicationContext):
        if ctx.guild.voice_client is None:
            await ctx.respond(embed=createErrorEmbed("The bot is not connected to any channel"),
                              ephemeral=True)
            return False
        return True

    return commands.check(predicate)


def isSameChannel():
    """
    Checks if the author and the bot are connected to the same channel

    NOTE: this function relies on 'isAuthorConnected' and 'canBotDisconnect' before checking this
    :return: True if the bot and the user in the same channel, False otherwise
    """

    async def predicate(ctx: ApplicationContext):
        if ctx.voice_client and ctx.author.voice.channel != ctx.voice_client.channel:
            await ctx.respond(embed=createErrorEmbed("You must be connected to the same channel as the bot"),
                              ephemeral=True)
            return False
        return True

    return commands.check(predicate)


class seekConverter(commands.Converter):
    async def convert(self, ctx, argument: str):
        message = "You must use format: hh:mm:ss"
        if argument.count(":") != 2:
            raise CommandError(message=message)
        split = argument.split(":")
        if not (split[0].isdigit() or split[1].isdigit() or split[2].isdigit()):
            raise CommandError(message)
        return int((int(split[0]) * 3600) + (int(split[1]) * 60) + int(split[2]))


def createErrorEmbed(message):
    return discord.Embed(
        title=f"❌ {message}",
        colour=discord.Colour.from_rgb(0, 0, 0)
    )
