from discord import ApplicationContext, File

from content import GameMap, ChallengeDeck
from util import Status, OwnedBy, colour_convert, generate_new_map
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
        self.configuration()
        return True
    
    @event()
    def configuration(self) -> None:
        self.status = Status.SETUP
    
    @event()
    def start(self) -> None:
        if self.status != Status.SETUP:
            self.logger.warning("event called during non-setup phase!")
            return
        
        self.status = Status.RUNNING
        
        self.schedule_event(0, 0, 0, self.end_cycle)
        self.unpause()
    
    @event()
    def claim_region(self, team_id: int, region_id: int) -> bool:        
        region = self.map.regions[region_id]
        own = [OwnedBy.RED, OwnedBy.YELLOW][team_id]
        
        if region.locked or region.home or region.claim == own:
            self.logger.warning("invalid claim!")
            return False
        
        if not any(neighbour.claim == own for neighbour in region.adjacent):
            self.logger.warning("claim fails adjacency!")
            return False
    
        region.claim = own
        region.locked = True
        
        return True
    
    async def cycle_announce(self) -> None:
        embed, map_png_path = generate_new_map(self)
        if self.thread: await self.thread.send("Challenges have been refreshed! Here is the current state of the map.", embed=embed, file=File(map_png_path, filename="map.png"))
    
    @event(callback=cycle_announce)
    def end_cycle(self) -> None:
        self.challenge_deck.shuffle(self.rng)
        for region, challenge in zip(self.map.regions, self.challenge_deck.challenges):
            region.locked = False
            region.challenge = challenge
        
        self.schedule_event(0, CYCLE_INTERVAL_MINUTES, 0, self.end_cycle)