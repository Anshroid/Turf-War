from content import GameMap

m = GameMap()

for region in m.regions:
    with open("test.png", "wb") as f:
        f.write(m.render(0, 0, highlight_1=[region], highlight_2=region.adjacent))
        
    input("press enter to continue")