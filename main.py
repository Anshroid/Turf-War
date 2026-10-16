import pathlib

from jloxgame import JLOXBot

from game import TurfWar

with open("TOKEN", "r") as f:
    TOKEN = f.read()

bot = JLOXBot(TurfWar, pathlib.Path() / "save", member_hostable=False, joinable=False)

@bot.event
async def on_ready():
    bot.logger.info(f"{bot.user} is online!")

bot.run(TOKEN)