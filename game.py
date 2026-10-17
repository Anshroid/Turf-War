import itertools

from discord import ApplicationContext, File

from content import GameMap, ChallengeDeck
from util import Status, OwnedBy, colour_convert, generate_new_map
from config import GAME_DURATION_MINUTES, MAP_COLOURS, CYCLE_INTERVAL_MINUTES

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
    
    # ============================================== meta state management ==============================================
    
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
        self.schedule_event(0, GAME_DURATION_MINUTES, 0, self.end_game)
        self.unpause()
    
    # ============================================== game actions ==============================================
    
    @event()
    def claim_region(self, team_id: int, region_id: int) -> bool:        
        region = self.map.regions[region_id]
        own = [OwnedBy.RED, OwnedBy.YELLOW][team_id]
        
        if region.locked or region.home or region.claim == own:
            self.logger.info("invalid claim!")
            return False
        
        if not any(neighbour.claim == own for neighbour in region.adjacent):
            self.logger.info("claim fails adjacency!")
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
    
    async def win_announce(self) -> None:
        grouped = itertools.groupby(self.map.regions, lambda region: region.claim)
        counted = {k: len(list(v)) for k, v in grouped}
        
        red = counted[OwnedBy.RED]
        yellow = counted[OwnedBy.YELLOW]
        
        win_message = "It was a draw!" if red == yellow else f"{self.teams[red < yellow].name} has won!"
        
        if self.thread: await self.thread.send(f"# The game has ended! {win_message}")
    
    @event(callback=win_announce)
    def end_game(self) -> None:
        self.status = Status.END
    
    # ============================================== referee events ==============================================
    
    @event()
    def force_claim(self, team_id: int, region_id: int, locked: bool = True) -> None:
        region = self.map.regions[region_id]
        region.claim = [OwnedBy.RED, OwnedBy.YELLOW][team_id]
        region.locked = locked
    
    @event()
    def force_connect(self, region_1_id: int, region_2_id: int) -> None:
        region_1 = self.map.regions[region_1_id]
        region_2 = self.map.regions[region_2_id]
        
        region_1.adjacent.add(region_2)
        region_2.adjacent.add(region_1)