from discord import ApplicationContext

from content import GameMap, ChallengeDeck
from util import Status, OwnedBy, colour_convert
from config import MAP_COLOURS, CYCLE_INTERVAL_MINUTES

from jloxgame import GameContext, Team, event

class TurfWar(GameContext):
    def __init__(self) -> None:
        super().__init__()
        
        self.status = Status.INIT
        
        self.teams = [Team("Red Team", colour_convert(MAP_COLOURS[OwnedBy.RED])), Team("Yellow Team", colour_convert(MAP_COLOURS[OwnedBy.YELLOW]))]
        
        self.challenge_deck = ChallengeDeck()
        self.map = GameMap()
    
    async def configure(self, dctx: ApplicationContext) -> bool:
        return True
    
    @event()
    def claim_region(self, team_id: int, region_id: int) -> None:        
        region = self.map.regions[region_id]
        own = [OwnedBy.RED, OwnedBy.YELLOW][team_id]
        
        if region.locked or region.claim in [OwnedBy.YELLOW_HOME, OwnedBy.RED_HOME, own]:
            return
        
        # note: do not enforce neighbour checks! these should purposefully be overrideable.
        # if not any(neighbour.claim == own for neighbour in region.adjacent):
        #     return
    
        region.claim = own
        region.locked = True
        
    @event()
    def end_cycle(self) -> None:
        self.challenge_deck.shuffle(self.rng)
        for region, challenge in zip(self.map.regions, self.challenge_deck.challenges):
            region.locked = False
            region.challenge = challenge
        
        self.schedule_event(0, CYCLE_INTERVAL_MINUTES, 0, self.end_cycle)