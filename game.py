from discord import ApplicationContext, File

from content import GameMap, ChallengeDeck, MapRegion
from util import Status, OwnedBy, colour_convert, disable_view, generate_new_map
from config import GAME_DURATION_MINUTES, MAP_COLOURS, CYCLE_INTERVAL_MINUTES

from jloxgame import GameContext, Team, event
from views import ClaimView

class TurfWar(GameContext):
    def __init__(self) -> None:
        super().__init__()
        
        self.status = Status.INIT
        
        self.teams = [Team("Red Team", colour_convert(MAP_COLOURS[OwnedBy.RED])), Team("Yellow Team", colour_convert(MAP_COLOURS[OwnedBy.YELLOW]))]
        
        self.challenge_deck = ChallengeDeck()
        self.map = GameMap()
        
        self.cycle = 0
        self.get_challenge_views: list[ClaimView] = []
        
        self.claimable_regions: dict[OwnedBy, set[MapRegion]] = {OwnedBy.RED: set(), OwnedBy.YELLOW: set()}
        self.owned_regions: dict[OwnedBy, set[MapRegion]] = {OwnedBy.RED: set(), OwnedBy.YELLOW: set(), OwnedBy.UNOWNED: set()}
        
        for region in self.map.get_regions():
            self.owned_regions[region.claim].add(region)
            
        self.recalculate_claimable()
    
    def recalculate_claimable(self):
        for owned_by in OwnedBy:
            self.claimable_regions[owned_by] = {region for region in self.map.get_regions() if region.claimable_by(owned_by)}
    
    # ============================================== meta state management ==============================================
    
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
        self.schedule_event(0, GAME_DURATION_MINUTES, 0, self.end_game)
        self.unpause()
    
    # ============================================== game actions ==============================================
    
    @event()
    def claim_region(self, team_id: int, region_id: int) -> bool:        
        region = self.map.get_region(region_id)
        own = OwnedBy(team_id)
        
        if not region.claimable_by(own):
            self.logger.info("invalid claim!")
            return False
    
        self.owned_regions[region.claim].remove(region)
        region.claim = own
        region.locked = True
        self.owned_regions[region.claim].add(region)
        
        self.recalculate_claimable()
        
        return True
    
    async def cycle_announce(self) -> None:
        for view in self.get_challenge_views:
            await disable_view(view)
            
        embed, map_png_path = generate_new_map(self)
        if self.thread: await self.thread.send("Challenges have been refreshed! Here is the current state of the map.", embed=embed, file=File(map_png_path, filename="map.png"))
    
    @event(callback=cycle_announce)
    def end_cycle(self) -> None:
        if self.status != Status.RUNNING:
            self.logger.info("game is not running, cancelling cycles")
            return
        
        self.challenge_deck.shuffle(self.rng)
        for region, challenge in zip(self.map.get_regions(), self.challenge_deck.challenges):
            region.locked = False
            region.challenge = challenge
        
        self.recalculate_claimable()
        
        self.cycle += 1
        
        self.schedule_event(0, CYCLE_INTERVAL_MINUTES, 0, self.end_cycle)
    
    async def win_announce(self) -> None:    
        red = len(self.owned_regions[OwnedBy.RED])
        yellow = len(self.owned_regions[OwnedBy.YELLOW])
        win_message = "It was a draw!" if red == yellow else f"{self.teams[red < yellow].name} has won!"
        
        if self.thread: await self.thread.send(f"# The game has ended! {win_message}")
    
    @event(callback=win_announce)
    def end_game(self) -> None:
        self.status = Status.END
    
    # ============================================== referee events ==============================================
    
    @event()
    def force_claim(self, team_id: int, region_id: int, locked: bool = True) -> None:
        region = self.map.get_region(region_id)
        
        self.owned_regions[region.claim].remove(region)
        region.claim = OwnedBy(team_id)
        region.locked = locked
        self.owned_regions[region.claim].add(region)
        
        self.recalculate_claimable()
        
    
    @event()
    def force_connect(self, region_1_id: int, region_2_id: int) -> None:
        region_1 = self.map.get_region(region_1_id)
        region_2 = self.map.get_region(region_2_id)
        
        region_1.adjacent.add(region_2)
        region_2.adjacent.add(region_1)
        
        self.recalculate_claimable()
        
    
    @event()
    def force_disconnect(self, region_1_id: int, region_2_id: int) -> None:
        region_1 = self.map.get_region(region_1_id)
        region_2 = self.map.get_region(region_2_id)
        
        region_1.adjacent.remove(region_2)
        region_2.adjacent.remove(region_1)
        
        self.recalculate_claimable()
        