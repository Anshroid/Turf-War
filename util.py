from typing import TYPE_CHECKING, Iterable
from enum import Enum
from time import time
from pathlib import Path
from datetime import timedelta
import os

from discord.ui import View

from jloxgame.state import Team

if TYPE_CHECKING:
    from content import MapRegion
    from game import TurfWar
    
from discord import Embed, OptionChoice

Status = Enum("STATUS", "INIT SETUP RUNNING END")
OwnedBy = Enum("OwnedBy", "RED YELLOW UNOWNED", start=0)

def colour_convert(c: str) -> int:
    return int(c[1:], 16)

map_dir = Path() / "generated_maps"
if not map_dir.exists():
    os.mkdir(map_dir)

map_embed = Embed()
map_embed.set_image(url="attachment://map.png")

def generate_new_map(gctx: TurfWar, *, highlight_1: Iterable[MapRegion] = [], highlight_2: Iterable[MapRegion] = []):
    map_png_path = map_dir / f"{int(time())}.{gctx.thread_id}.png"
    
    red = len(gctx.owned_regions[OwnedBy.RED])
    yellow = len(gctx.owned_regions[OwnedBy.YELLOW])
    total = red + yellow + len(gctx.owned_regions[OwnedBy.UNOWNED])
        
    map_png_path.write_bytes(gctx.map.render(red / total, yellow / total, highlight_1=highlight_1, highlight_2=highlight_2))

    # Maintain the most recent 10 generated map files
    files = sorted(os.listdir(map_dir), reverse=True)
    while len(files) > 10:
        os.unlink(map_dir / files.pop())

    embed = map_embed.copy()
    embed.set_footer(text=f"Time elapsed: {timedelta(seconds=gctx.game_time_now() // 1000)}")

    return embed, map_png_path

def choices(options: Iterable[tuple[str, str | int]], typed: str) -> list[OptionChoice]:
    typed = typed.lower()
    return [OptionChoice(shown, key) for shown, key in sorted(options) if typed in shown.lower() or typed in str(key).lower()]

async def disable_view(view: View):
    view.disable_all_items()
    if view.parent: await view.parent.edit_original_response(view=view)

def owned_by(team: Team) -> OwnedBy: return OwnedBy(team.team_id)