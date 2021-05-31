from datetime import datetime
import discord
from discord.ext import commands
import re
import typing


def frmtd_utcnow():
    # returns the current UTC time in an HH:MM dd/mm/yy format
    return datetime.strftime(datetime.utcnow(), '%H:%M %d/%m/%y')


def date_str(datetime_object):
    # returns the inputted datetime in an HH:MM dd/mm/yy format
    # None check primarily used for Discord Object joined_at attributes that optionally return
    return "Unavailable" if datetime_object is None else datetime_object.strftime('%H:%M %d/%m/%y') + " UTC"


def get_log_channel(client):
    return client.get_channel(client.LOG_CHANNEL_ID)


async def post_log_embed(client, guild_id, title="", desc="", color=0xed2140, author="Bot", author_url="",
                         author_icon_url="", thumbnail="", footer="", fields: typing.List[dict] = None, message=""):
    fields = [] if fields is None else fields

    log_embed = discord.Embed(title=title, description=desc, color=color)
    log_embed.set_author(name=author, icon_url=author_icon_url, url=author_url)
    log_embed.set_thumbnail(url=thumbnail)
    log_embed.set_footer(text=footer)
    if fields:
        for field in fields:
            log_embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])

    channel = get_log_channel(client)
    if channel:
        try:
            await channel.send(message, embed=log_embed)
        except discord.Forbidden:
            await channel.send("There was a log to post but I do not have permissions to post it in this channel!\n"
                               "Please ensure I have the 'embed links' permission.")


class BMC(commands.Converter):
    """Better Member Converter"""
    def __init__(self):
        self.id_regex = re.compile(r'([0-9]{15,21})$')
        self.mention_regex = re.compile(r'<@!?([0-9]+)>$')
        super().__init__()

    def __repr__(self):
        return "member"

    async def convert(self, ctx, argument):
        """
        Lookup via ID extracted using regex pattern from raw ID inputting or inside a mention.
        First, check bot's internal cache of members for the ctx.guild but if they are not found there then try fetching
        the member directly using an API call (fetch_member) - sometimes members are not in the cache in large guilds
        when the member is appearing offline; this can result in confusion to whether they're in the discord still and
        fetching resolves this.
        This converter does not lookup users by name. Looking up by name only caused problems.
        """
        result = None
        match = self.id_regex.match(argument) or self.mention_regex.match(argument)

        if match:
            member_id = int(match.group(1))
            result = ctx.guild.get_member(member_id)
            if not result:
                try:
                    result = await ctx.guild.fetch_member(member_id)
                except discord.NotFound:
                    result = None

        if not result:
            raise commands.BadArgument(f"ID {argument} not found")

        return result


class UserID(commands.Converter):
    """
    Verifies if it's a discord user ID and returns a user object
    """
    def __init__(self):
        self.id_regex = re.compile(r'([0-9]{15,21})$')
        super().__init__()

    def __repr__(self):
        return "user"

    async def convert(self, ctx, argument):
        result = None
        match = self.id_regex.match(argument)

        if match:
            try:
                result = await ctx.bot.fetch_user(int(argument))
            except discord.NotFound:
                result = None
            except discord.HTTPException:
                return await ctx.send("HTTPException occurred whilst trying to fetch a user with this ID!")

        if not result:
            raise commands.BadArgument(f"UserID {argument} not found")

        return result


class TimeString(commands.Converter):
    """
    -Formats HH:MM (dd/mm(/yy(yy)?)?)? into a datetime object, if not all fields are provided then it will replace
    elements from datetime.utcnow()
    -Does not verify if this date is in the future or past, implementations of the converter should do this
    """
    def __init__(self):
        self.date_re = re.compile(r'^\d{2}:\d{2}(\s\d{1,2}/\d{1,2}(?:/((\d{4})|(?:\d{2})))?)?$')
        super().__init__()

    async def convert(self, ctx, argument):
        result = None
        match = self.date_re.match(argument)

        if match:
            abs_groups = len([g for g in match.groups() if g is not None])
            try:
                input_date = datetime.strptime(
                    argument,
                    "%H:%M" if abs_groups == 0 else "%H:%M %d/%m" if abs_groups == 1 else "%H:%M %d/%m/%y"
                    if abs_groups == 2 else "%H:%M %d/%m/%Y"
                )
            except ValueError:
                result = None
            else:
                result = datetime.utcnow().replace(
                    year=input_date.year if abs_groups > 1 else datetime.utcnow().year,
                    month=input_date.month if abs_groups > 0 else datetime.utcnow().month,
                    day=input_date.day if abs_groups > 0 else datetime.utcnow().day,
                    hour=input_date.hour,
                    minute=input_date.minute,
                    second=0,
                    microsecond=0
                )
        if result is None:
            return commands.BadArgument(f"Time {argument} could not convert using TimeStringConverter\nWrong datetime "
                                        f"format provided, use HH:MM dd/mm/yyyy, optional date but required time.")
        return result
