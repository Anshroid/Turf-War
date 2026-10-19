from discord import ApplicationContext, File

from content import GameMap, ChallengeDeck
from util import Status, OwnedBy, claimable, colour_convert, generate_new_map
from config import GAME_DURATION_MINUTES, MAP_COLOURS, CYCLE_INTERVAL_MINUTES

from jloxgame import GameContext, Team, event

class TurfWar(GameContext):
    def __init__(self) -> None:
        super().__init__()
        
        self.status = Status.INIT
        
        self.teams = [Team("Red Team", colour_convert(MAP_COLOURS[OwnedBy.RED])), Team("Yellow Team", colour_convert(MAP_COLOURS[OwnedBy.YELLOW]))]
        
        self.challenge_deck = ChallengeDeck()
        self.map = GameMap()
        
        self.region_counts: dict[OwnedBy, int] = {OwnedBy.RED: 1, OwnedBy.YELLOW: 1, OwnedBy.UNOWNED: len(self.map.regions) - 2}
    
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
        region = self.map.regions[region_id]
        own = OwnedBy(team_id)
        
        if not claimable(own, region):
            self.logger.info("invalid claim!")
            return False
    
        self.region_counts[region.claim] -= 1
        region.claim = own
        region.locked = True
        self.region_counts[region.claim] += 1
        
        return True
    
    async def cycle_announce(self) -> None:
        embed, map_png_path = generate_new_map(self)
        if self.thread: await self.thread.send("Challenges have been refreshed! Here is the current state of the map.", embed=embed, file=File(map_png_path, filename="map.png"))
    
    @event(callback=cycle_announce)
    def end_cycle(self) -> None:
        if self.status != Status.RUNNING:
            self.logger.info("game is not running, cancelling cycles")
            return
        
        self.challenge_deck.shuffle(self.rng)
        for region, challenge in zip(self.map.regions, self.challenge_deck.challenges):
            region.locked = False
            region.challenge = challenge
        
        self.schedule_event(0, CYCLE_INTERVAL_MINUTES, 0, self.end_cycle)
    
    async def win_announce(self) -> None:    
        red = self.region_counts[OwnedBy.RED]
        yellow = self.region_counts[OwnedBy.YELLOW]
        win_message = "It was a draw!" if red == yellow else f"{self.teams[red < yellow].name} has won!"
        
        if self.thread: await self.thread.send(f"# The game has ended! {win_message}")
    
    @event(callback=win_announce)
    def end_game(self) -> None:
        self.status = Status.END
    
    # ============================================== referee events ==============================================
    
    @event()
    def force_claim(self, team_id: int, region_id: int, locked: bool = True) -> None:
        region = self.map.regions[region_id]
        
        self.region_counts[region.claim] -= 1
        region.claim = OwnedBy(team_id)
        region.locked = locked
        self.region_counts[region.claim] += 1
        
    
    @event()
    def force_connect(self, region_1_id: int, region_2_id: int) -> None:
        region_1 = self.map.regions[region_1_id]
        region_2 = self.map.regions[region_2_id]
        
        region_1.adjacent.add(region_2)
        region_2.adjacent.add(region_1)