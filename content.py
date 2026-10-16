from pathlib import Path
from typing import TypedDict
import xml.etree.ElementTree as ET
from copy import deepcopy
from dataclasses import dataclass
from random import Random

import json

import resvg_py

from util import OwnedBy
from config import MAP_COLOURS

ChallengeDict = TypedDict("ChallengeDict", {"title": str, "description": str})
@dataclass
class Challenge:
    title: str
    description: str

MapRegionDict = TypedDict("MapRegionDict", {"name": str, "svg_id": str, "default_state": int, "adjacent": list[int]})
@dataclass
class MapRegion:
    name: str
    svg_id: str
    claim: OwnedBy
    adjacent: list[MapRegion]
    locked: bool = False
    challenge: Challenge | None = None

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
            self._svg = ET.parse(f)
        
        for team, team_home in [(OwnedBy.RED, OwnedBy.RED_HOME), (OwnedBy.YELLOW, OwnedBy.YELLOW_HOME)]:
            gradient = self._svg.find(f".//*[@id='{team.name}-locked']")
            assert gradient is not None
            stops = gradient.findall(".//*")
            
            stops[0].set("stop-color", MAP_COLOURS[team])
            stops[1].set("stop-color", MAP_COLOURS[team_home])
        
        with open(map_path / "map.json", "r") as f:
            region_dicts: list[MapRegionDict] = json.load(f)
            
        self.regions = [MapRegion(r["name"], r["svg_id"], OwnedBy(r["default_state"]), []) for r in region_dicts]
        for region, region_dict in zip(self.regions, region_dicts):
            region.adjacent = [self.regions[i] for i in region_dict["adjacent"]]
        
        # assert edge relation symmetry
        # for region in self._regions:
        #     for neighbour in region.adjacent:
        #         assert region in neighbour.adjacent
        
        # assert all zones exist
        for region in self.regions:
            assert self._svg.find(f".//*[@id='{region.svg_id}']") is not None
        
    def render(self) -> bytes:
        svg = deepcopy(self._svg)
        root = svg.getroot()
        for region in self.regions:
            element = root.find(f".//*[@id='{region.svg_id}']")
            assert element is not None
            
            colour = MAP_COLOURS[region.claim]
            style = "stroke: #000; stroke-width: 0.2px;"
            style += f'fill: {f'url(#{region.claim.name}-locked)' if region.locked else colour};'
            
            element.set("style", style)
            
        return resvg_py.svg_to_bytes(ET.tostring(root, encoding="unicode"), width=2000, height=2000)
        