import discord
from discord.ext import commands


# PUT YOUR DISCORD BOT TOKEN HERE FROM THE DISCORD DEVELOPER PORTAL
DISCORD_TOKEN = ""
# YOU MUST ENABLE BOTH INTENTS TICK BOXES ON THE DISCORD DEVELOPER PORTAL
client = commands.Bot(command_prefix="+", fetch_offline_members=True, intents=discord.Intents.all())

# set this to the integer of the log channel you want alerts to be posted in
# make this a private moderator channel where @here won't be problematic
client.LOG_CHANNEL_ID = 0

# allows you to toggle the alert system, by default is on
client.alerts_enabled = 1

if __name__ == "__main__":
    client.load_extension("attack_check")


@client.event
async def on_ready():
    print("I am ready to go!")


client.run(DISCORD_TOKEN)
