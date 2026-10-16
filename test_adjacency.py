from util import OwnedBy
from content import GameMap

m = GameMap()

for region in m.regions:
    for r in m.regions:
        r.claim = OwnedBy.UNOWNED
    
    region.claim = OwnedBy.RED
    
    for neighbour in region.adjacent:
        neighbour.claim = OwnedBy.YELLOW
    
    m.render()
    input("press enter to continue")