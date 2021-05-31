# Discord-bot-attack-defence
Be alerted when your Discord server is under attack from spam bots and ban them all with 1 command

## Dependencies

- Python 3.7 or higher
- discordpy: [Pypi](https://pypi.org/project/discord.py/), [Github](https://github.com/Rapptz/discord.py), [Docs](https://discordpy.readthedocs.io/en/latest/)

## Setup

1) Edit the bot.py file and fill DISCORD_TOKEN with your Discord bot token string from the [discord developer portal](https://discord.com/developers/applications)
2) Edit the bot.py file and fill client.LOG_CHANNEL_ID with the Discord channel ID that you want moderators of your server to be alerted in when an attack is detected
3) Enable privileged intents for your bot application on the [discord developer portal](https://discord.com/developers/applications)
![image](https://user-images.githubusercontent.com/63066020/120230205-c1cf0000-c246-11eb-8f58-36895f6583e6.png)
4) Run the bot by running the bot.py file, the bot will print when it is ready to go

## Features:

1) Alert when mass joins occur at a threshhold of your choice (default >= 11) 
![image](https://user-images.githubusercontent.com/63066020/120230446-3609a380-c247-11eb-8a40-e35800418eda.png)
2) Commands that can: 
   - Ban all members with the same name
   - Ban all members that joined at the same time
   - Ban all members with the same profile picture
   - Ban all members with a name that match the same regex pattern
   - Ban all members with the same account creation date
3) Offline protection to auto-ban all members in an alert message if more than 20 joined and UTC time is between 1am and 8am  
