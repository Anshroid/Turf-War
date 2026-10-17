from pathlib import Path
from shutil import which
import subprocess
from typing import TYPE_CHECKING, TypedDict
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
from config import HIGHLIGHT_1_COLOUR, HIGHLIGHT_2_COLOUR, MAP_COLOURS, MAP_COLOURS_DARK

ChallengeDict = TypedDict("ChallengeDict", {"title": str, "description": str})
@dataclass
class Challenge:
    title: str
    description: str

MapRegionDict = TypedDict("MapRegionDict", {"name": str, "svg_id": str, "default_state": int, "adjacent": list[int]})
@dataclass
class MapRegion:
    idx: int
    name: str
    svg_id: str
    claim: OwnedBy
    adjacent: set[MapRegion] = field(repr=False)
    home: bool
    locked: bool = False
    challenge: Challenge | None = None
    
    def __hash__(self) -> int:
        return hash(self.idx)

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
            gradient = self._svg.find(f".//*[@id='{team.name}-locked']")
            assert gradient is not None
            stops = gradient.findall(".//*")
            
            stops[0].set("stop-color", MAP_COLOURS[team])
            stops[1].set("stop-color", MAP_COLOURS_DARK[team])
        
        with open(map_path / "map.json", "r") as f:
            region_dicts: list[MapRegionDict] = json.load(f)
            
        self.regions = [MapRegion(i, r["name"], r["svg_id"], OwnedBy(r["default_state"]), set(), r["default_state"] != 2) for i, r in enumerate(region_dicts)]
        for region, region_dict in zip(self.regions, region_dicts):
            region.adjacent = {self.regions[i] for i in region_dict["adjacent"]}
        
        # assert edge relation symmetry
        # for region in self._regions:
        #     for neighbour in region.adjacent:
        #         assert region in neighbour.adjacent
        
        # assert all zones exist
        for region in self.regions:
            assert self._svg.find(f".//*[@id='{region.svg_id}']") is not None
        
    def render(self, *, highlight: int | None = None, highlight_neighbours: bool = False) -> bytes:
        svg = deepcopy(self._svg)
        root = svg.getroot()
        for region in self.regions:
            element = root.find(f".//*[@id='{region.svg_id}']")
            assert element is not None
            
            highlighted_1 = highlight == region.idx
            highlighted_2 = highlight is not None and highlight_neighbours and region in self.regions[highlight].adjacent
            
            claim = region.claim
            colour = MAP_COLOURS[claim] if not region.home else MAP_COLOURS_DARK[claim]
            
            if highlighted_1:
                style = f"stroke-width: 1.5px; stroke: {HIGHLIGHT_1_COLOUR};"
            elif highlighted_2:
                style = f"stroke-width: 0.8px; stroke: {HIGHLIGHT_2_COLOUR};"
            else:
                style = "stroke-width: 0.2px; stroke: #000;"
            style += f'fill: {f'url(#{claim.name}-locked)' if region.locked else colour};'
            
            element.set("style", style)
            
            # fix to display highlight border over other elements (z-index in SVGs is by document order, so effectively duplicate the element at the bottom)
            if highlighted_1 or highlighted_2: 
                highlight_container = root.find(f".//*[@id='highlight-{1 + highlighted_2}-container']")
                assert highlight_container is not None
                highlight_container.append(ElementTree.Element("use", {"href": "#" + region.svg_id}))
        
        if RSVG_PATH is not None:
            return subprocess.run([RSVG_PATH, "-w", "2000", "-f", "png", "-", ElementTree.tostring(root, encoding="unicode")], stdout=subprocess.PIPE).stdout
        else:
            return resvg_py.svg_to_bytes(ElementTree.tostring(root, encoding="unicode"), width=2000)
        