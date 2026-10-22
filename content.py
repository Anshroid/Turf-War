from logging import getLogger
from pathlib import Path
from shutil import which
from subprocess import Popen, PIPE
import time
from typing import TYPE_CHECKING, Iterable, TypedDict
from xml.etree import ElementTree
from copy import deepcopy
from dataclasses import dataclass, field
from random import Random

import json

RSVG_PATH = which("rsvg-convert")
if RSVG_PATH is None or TYPE_CHECKING:
    print("WARNING: librsvg could not be found, falling back to resvg (8x slower)")
    import resvg_py

from util import OwnedBy
from config import BACKGROUND_COLOUR, HIGHLIGHT_1_COLOUR, HIGHLIGHT_2_COLOUR, MAP_COLOURS, MAP_COLOURS_DARK

ChallengeDict = TypedDict("ChallengeDict", {"title": str, "description": str})
@dataclass
class Challenge:
    title: str
    description: str

MapRegionDict = TypedDict("MapRegionDict", {"name": str, "svg_id": str, "default_state": int, "adjacent": list[int]})
@dataclass
class MapRegion:
    id: int
    name: str
    svg_id: str
    claim: OwnedBy
    adjacent: set[MapRegion] = field(repr=False)
    home: bool
    locked: bool = False
    challenge: Challenge | None = None
    
    def __hash__(self) -> int:
        return hash(self.id)

class ChallengeDeck:
    def __init__(self, challenges_path: Path = Path() / "content" / "challenges.json") -> None:
        with open(challenges_path, "r") as f:
            challenge_dicts: list[ChallengeDict] = json.load(f)
        
        self.challenges = [Challenge(c["title"], c["description"]) for c in challenge_dicts]
    
    def shuffle(self, rng: Random):
        rng.shuffle(self.challenges)

class GameMap:
    def __init__(self, map_path: Path = Path() / "content" / "maps" / "oxford_city_centre") -> None:
        with open(map_path / "map.svg", "r") as f:
            self._svg = ElementTree.parse(f)
        
        for team in [OwnedBy.RED, OwnedBy.YELLOW]:
            stop = self._svg.find(f"./{{*}}defs/{{*}}linearGradient[@id='{team.name}']/{{*}}stop")
            if stop is not None: stop.set("stop-color", MAP_COLOURS[team])
            
            stop = self._svg.find(f"./{{*}}defs/{{*}}linearGradient[@id='{team.name}-dark']/{{*}}stop")
            if stop is not None: stop.set("stop-color", MAP_COLOURS_DARK[team])
            
            locked_stops = self._svg.findall(f"./{{*}}defs/{{*}}linearGradient[@id='{team.name}-locked']/{{*}}stop")
            
            locked_stops[0].set("stop-color", MAP_COLOURS[team])
            locked_stops[1].set("stop-color", MAP_COLOURS[team])
            locked_stops[2].set("stop-color", MAP_COLOURS_DARK[team])
            locked_stops[3].set("stop-color", MAP_COLOURS_DARK[team])
            
        with open(map_path / "map.json", "r") as f:
            region_dicts: list[MapRegionDict] = json.load(f)
            
        self._regions = [MapRegion(i+1, r["name"], r["svg_id"], OwnedBy(r["default_state"]), set(), r["default_state"] != 2) for i, r in enumerate(region_dicts)]
        for region, region_dict in zip(self._regions, region_dicts):
            region.adjacent = {self.get_region(i) for i in region_dict["adjacent"]}
        
        self.region_count = len(self._regions)
            
        # assert edge relation symmetry
        for region in self._regions:
            for neighbour in region.adjacent:
                if region not in neighbour.adjacent:
                    raise ValueError(f"{region.name} should be adjacent to {neighbour.name}")
        
        # assert edge relation irreflexivity (for typos)
        for region in self._regions:
            if region in region.adjacent:
                raise ValueError(f"{region.name} should not be adjacent to itself")
        
        # assert all zones exist
        for region in self._regions:
            assert self._svg.find(f".//*[@id='{region.svg_id}']") is not None
    
    def is_valid_region(self, region_id: int) -> bool:
        return 0 < region_id <= len(self._regions) # region_id is 1-indexed
    
    def get_region(self, region_id: int) -> MapRegion:
        return self._regions[region_id-1] # region_id is 1-indexed
    
    def get_regions(self) -> Iterable[MapRegion]:
        return (region for region in self._regions) # access only as iterable
        
    def render(self, red: float, yellow: float, *, highlight_1: Iterable[MapRegion], highlight_2: Iterable[MapRegion]) -> bytes:
        start_time = time.time()
        svg = deepcopy(self._svg)
        root = svg.getroot()
        for region in self._regions:
            element = root.find(f"./{{*}}g/{{*}}g[@id='{region.svg_id}']")
            assert element is not None
            
            highlighted_1 = region in highlight_1
            highlighted_2 = region in highlight_2
            
            claim = region.claim
            colour = (claim.name + region.locked*"-locked") if not region.home else f"{claim.name}-dark"
            
            if highlighted_1:
                style = f"stroke-width: 1.5px; stroke: {HIGHLIGHT_1_COLOUR};"
            elif highlighted_2:
                style = f"stroke-width: 1.2px; stroke: {HIGHLIGHT_2_COLOUR};"
            else:
                style = ""
                
            style += f'fill: url(#{colour});'
            
            element.set("style", style)
            
            # fix to display highlight border over other elements (z-index in SVGs is by document order, so effectively duplicate the element at the bottom)
            if highlighted_1 or highlighted_2: 
                highlight_container = root.find(f"./{{*}}g/{{*}}g[@id='highlight-{1 + highlighted_2}-container']")
                assert highlight_container is not None
                highlight_container.append(ElementTree.Element("use", {"href": "#" + region.svg_id}))
        
        win_bars = root.findall("./{*}g[@id='win-bar']/{*}rect")
        x_str = win_bars[0].get("x")
        width_str = win_bars[0].get("width")
        assert x_str is not None and width_str is not None
        right = (int(width_str[:-1]) + int(x_str[:-1])) / 100
        
        win_bars[1].set("width", f"{red*90:.01f}%")
        win_bars[1].set("style", f"fill: url('#RED')")
        win_bars[2].set("x", f"{right*100 - yellow*90:.01f}%")
        win_bars[2].set("width", f"{yellow*90:.01f}%")
        win_bars[2].set("style", f"fill: url('#YELLOW')")
        
        if RSVG_PATH is not None:
            with Popen([RSVG_PATH, "-w", "2000", "-f", "png", "--background-color", BACKGROUND_COLOUR], stdout=PIPE, stdin=PIPE) as p:
                output = p.communicate(ElementTree.tostring(root))[0]
        else:
            output = resvg_py.svg_to_bytes(ElementTree.tostring(root, encoding="unicode"), width=2000, background=BACKGROUND_COLOUR)
        
        getLogger(f"jloxgame.game").info(f"map generation took {time.time()-start_time:.02f}s")
            
        return output
        