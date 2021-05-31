import asyncio
import inspect
from io import BytesIO
import typing
import re

import discord
from discord.ext import commands
from datetime import timedelta, datetime

from utils import *


class AttackCheck(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.joined_dic = {}
        self.last_member = {}
        self.loop = self.client.loop.create_task(self.joined_check())
        self.client.ban_exceptions = {}  # holds user IDs under a guild ID that will not be banned when +banbytime command is run

    @commands.Cog.listener()
    async def on_guild_available(self, guild):
        print(f"'{guild}' became available")
        if guild.id not in self.joined_dic:
            self.joined_dic[guild.id] = 0
        if guild.id not in self.last_member:
            self.last_member[guild.id] = None

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if guild.id not in self.joined_dic:
            self.joined_dic[guild.id] = 0
        if guild.id not in self.last_member:
            self.last_member[guild.id] = None

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if guild.id in self.joined_dic:
            self.joined_dic.pop(guild.id)
        if guild.id in self.last_member:
            self.last_member.pop(guild.id)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.joined_dic[member.guild.id] += 1
        self.last_member[member.guild.id] = member

    @commands.command(
        usage="+toggle",
        description="Toggles whether the attack check alert should trigger"
    )
    async def toggle(self, ctx):
        if self.client.alerts_enabled:
            self.client.alerts_enabled = 0
            await ctx.send("Disabled attack check alerts")
        else:
            self.client.alerts_enabled = 1
            await ctx.send("Enabled attack check alerts")

    async def auto_ban(self, guild_id, ban_time):
        log_channel = get_log_channel(self.client)
        if not log_channel:
            return
        msg = await log_channel.send(":warning: Auto-ban criteria satisfied, preparing to ban all members in the "
                                     "above alert\nREACT WITH :x: IN THE NEXT 90 SECONDS TO CANCEL AUTO-BANNING")
        def check(reaction, user):
            return (reaction.message == msg) and (str(reaction.emoji) == "❌")

        try:
            reaction, user = await self.client.wait_for("reaction_add", timeout=90, check=check)

        except asyncio.TimeoutError:  # No one cancelled the auto-ban within 90 seconds

            ban_time = ban_time.replace(second=0, microsecond=0)
            guild = self.client.get_guild(guild_id)
            collected_members = [m for m in guild.members if m.joined_at.replace(second=0, microsecond=0) == ban_time]
            await log_channel.send(f"Preparing to ban {len(collected_members)} members...")
            for member in collected_members:
                try:
                    await guild.ban(discord.Object(member.id),
                                reason=f"Auto-banned at {frmtd_utcnow()} during late-night attack")
                except Exception:
                    continue
            await log_channel.send(f"{len(collected_members)} members have been auto-banned.")

        else:
            await log_channel.send(f"{user.mention} banning cancelled!")

    async def joined_check(self):
        await self.client.wait_until_ready()
        while not self.client.is_closed():
            for guild_id in self.joined_dic:
                # if no member has joined this guild since starting the bot
                if self.last_member[guild_id] is None:
                    self.joined_dic[guild_id] = 0
                    continue
                     # CHANGE 11 TO THE THRESHOLD OF MEMBERS TO JOIN IN A SINGLE CLOCK MINUTE FOR THE ALERT TO TRIGGER
                if self.joined_dic[guild_id] >= 11 and self.client.alerts_enabled:
                    bbt = (datetime.utcnow() - timedelta(minutes=1))
                    await post_log_embed(
                        client=self.client,
                        guild_id=guild_id,
                        title=f"{self.joined_dic[guild_id]} accounts have joined within the last 60 seconds!",
                        desc=f"`+banbytime {bbt.strftime('%H:%M %d/%m/%y')}`",
                        color=0xed2140,
                        author="Potential bot attack!",
                        author_url="https://media.discordapp.net/attachments/560128634984202258/652220624600563752/wip.gif",
                        thumbnail="https://cdn.discordapp.com/emojis/588814117305843714.png?v=1",
                        message="@here"
                    )
                    # auto ban accounts joined in the last minute if more than 20 and between 01:00 and 08:00 UTC
                    if (self.joined_dic[guild_id] >= 20) and (1 < datetime.utcnow().hour < 8):
                        asyncio.create_task(self.auto_ban(guild_id, bbt))

                self.joined_dic[guild_id] = 0
            sleep_time = (datetime.utcnow() + timedelta(minutes=1)).replace(second=0)
            await discord.utils.sleep_until(sleep_time)

    async def ban_base(self, ctx: commands.Context, condition: typing.Callable[[discord.Member], bool]):
        """
        Base function for all mass ban commands, pass ctx and a boolean check function and then the magic happens
        """
        called_by = inspect.getframeinfo(inspect.currentframe().f_back)[2]
        async with ctx.channel.typing():
            collected_members = [m for m in ctx.guild.members if condition(m)]
            with BytesIO(
                str.encode('\n'.join(
                    [f"{m.name}#{m.discriminator}\tID: {m.id}\tJ: {date_str(m.joined_at)}\tC: {date_str(m.created_at)}"
                        for m in collected_members]))) as byt_f:

                await ctx.send(f"It is currently {frmtd_utcnow()} UTC.\nThe following {len(collected_members)} members"
                               f" will be banned, do you want to continue, Y/N?",
                               file=discord.File(fp=byt_f, filename="members_to_ban.txt"))

        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        try:
            msg = await self.client.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send(f"{ctx.author.mention} Timed out! No banning will take place :(")

        if msg.content.lower() not in ("y", "yes"):
            return await ctx.send(f"{ctx.author.mention} banning cancelled!")
        await ctx.send("Banning continuing, stand by...")

        async with ctx.channel.typing():
            ban_fails = []
            for member in collected_members:
                try:
                    await ctx.guild.ban(
                        discord.Object(member.id),
                        reason=f"Banned by {ctx.author.id} using {called_by} at {frmtd_utcnow()} UTC")
                except discord.HTTPException:
                    ban_fails.append(member)

            if ban_fails:
                with BytesIO(str.encode(
                        '\n'.join([f"{m.name}#{m.discriminator}\tID: {m.id}" for m in ban_fails]))) as byt_f:
                    await ctx.send(f"The following {len(ban_fails)} members failed to be banned",
                                   file=discord.File(fp=byt_f, filename="members_to_ban.txt"))
            await ctx.send(f"{ctx.author.mention} bans complete!")

    @commands.bot_has_permissions(ban_members=True)
    @commands.command(
        name="banbyname",
        usage="+banbyname [name]",
        description="Bans all members with that exact name. Case insensitive.",
        aliases=("banname",)
    )
    @commands.has_permissions(ban_members=True)
    async def ban_by_name(self, ctx, *, name):
        def condition(m: discord.Member):
            return m.name.lower() == name.lower()
        await self.ban_base(ctx, condition)

    @commands.command(
        name="bantimeexceptions",
        usage="+bantimeexception [ID, ID, ID]",
        description="Creates a list of user IDs that won't be banned when +banbytime is run.",
        aliases=("bantimeexception", "banexceptions")
    )
    @commands.has_permissions(ban_members=True)
    async def ban_by_time_exceptions(self, ctx, *, exceptions):
        ban_exceptions = exceptions.split(", ")
        self.client.ban_exceptions[ctx.guild.id] = ban_exceptions
        await ctx.send(f"Exception list created with users: {ban_exceptions}")

    @commands.bot_has_permissions(ban_members=True)
    @commands.command(
        name="banbytime",
        usage="+banbytime [HH:MM] <dd/mm/yyyy>",
        description="Bans all members that joined at that time. In UTC.",
        aliases=("bantime",)
    )
    @commands.has_permissions(ban_members=True)
    async def ban_by_time(self, ctx, *, ban_date: TimeString):
        ban_exceptions = [] if ctx.guild.id not in self.client.ban_exceptions \
            else self.client.ban_exceptions[ctx.guild.id]

        if ban_date > datetime.utcnow():
            return await ctx.send("You're trying to ban all join dates in the future, check UTC time...")

        def condition(m: discord.Member):
            return m.joined_at.replace(second=0, microsecond=0) == ban_date \
                   and m.id not in ban_exceptions  # self.client.ban_exceptions[ctx.guild.id]

        await self.ban_base(ctx, condition)

    @commands.bot_has_permissions(ban_members=True)
    @commands.command(
        name="banbyregex",
        usage="+banbyregex [pattern string]",
        description="Bans all members that joined at that time. In UTC.",
        aliases=("banregex",)
    )
    # THIS IS RESTRICTED TO ADMINISTRATORS AS IT CAN BE DANGEROUS  -  POTENTIAL TO BAN ALL MEMBERS WITH +banregex .*
    @commands.bot_has_permissions(administrator=True)
    async def ban_by_regex(self, ctx, *, regex_pattern: str):
        compiled = re.compile(regex_pattern)

        def condition(m: discord.Member):
            return compiled.match(m.name) is not None

        await self.ban_base(ctx, condition)

    @commands.bot_has_permissions(ban_members=True)
    @commands.command(
        name="banbypfp",
        usage="+banbypfp [member/user/hash]",
        description="Bans all members that have the same avatar hash.",
        aliases=("banpfp", "banbyavatar")
    )
    @commands.has_permissions(ban_members=True)
    async def ban_by_pfp(self, ctx, item: typing.Union[BMC, UserID, str]):
        pfp_hash = item.avatar if not isinstance(item, str) else item

        def condition(m: discord.Member):
            return m.avatar == pfp_hash

        await self.ban_base(ctx, condition)

    @commands.bot_has_permissions(ban_members=True)
    @commands.command(
        name="banbycreation",
        usage="+banbycreation [member/user]",
        description="Bans all members that have the same creation date.",
        aliases=("bancreation",)
    )
    @commands.has_permissions(ban_members=True)
    async def ban_by_creation(self, ctx, *, item: typing.Union[BMC, UserID, TimeString]):
        member_creation = item if isinstance(item, datetime) else item.created_at.replace(second=0, microsecond=0)

        def condition(m: discord.Member):
            return m.created_at.replace(second=0, microsecond=0) == member_creation

        await self.ban_base(ctx, condition)

    def cog_unload(self):
        self.loop.cancel()


def setup(client):
    client.add_cog(AttackCheck(client))
