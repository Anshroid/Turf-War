from typing import TYPE_CHECKING, Iterable
from enum import Enum
from time import time
from pathlib import Path
from datetime import timedelta
import os

from discord.ui import View

if TYPE_CHECKING:
    from game import TurfWar
    
from discord import Embed, OptionChoice

Status = Enum("STATUS", "INIT SETUP RUNNING END")
OwnedBy = Enum("OwnedBy", "YELLOW RED UNOWNED", start=0)

def colour_convert(c: str) -> int:
    return int(c[1:], 16)

map_dir = Path() / "generated_maps"
if not map_dir.exists():
    os.mkdir(map_dir)

map_embed = Embed()
map_embed.set_image(url="attachment://map.png")

def generate_new_map(gctx: TurfWar, *, highlight: int | None = None, highlight_neighbours: bool = True):
    map_png_path = map_dir / f"{int(time())}.{gctx.thread_id}.png"
    map_png_path.write_bytes(gctx.map.render(highlight=highlight, highlight_neighbours=highlight_neighbours))

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