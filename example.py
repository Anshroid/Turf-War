import pathlib
import random

from jloxgame.offline import JLOXBotOffline

from game import TurfWar

with open("TOKEN", "r") as f:
    TOKEN = f.read()

bot = JLOXBotOffline(TurfWar, pathlib.Path() / "save", logging_enabled=False)

game = bot.create()

for i in range(10):
    game.end_cycle()
    # with open("out.png", "wb") as f:
    #     f.write(game.map.render())
    # input("press enter to continue...")
    
    for i in range(1000):
        game.claim_region(random.random() > 0.5, random.randint(0, len(game.map._regions)-1))
    
    
    # input("press enter to continue...")

with open("generated_maps/out.png", "wb") as f:
    f.write(game.map.render())