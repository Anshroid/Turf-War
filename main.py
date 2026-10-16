from typing import Iterable, cast
import pathlib

from jloxgame import JLOXBot

from game import TurfWar
from util import generate_new_map, choices, OwnedBy

from discord import ApplicationContext, File, option, AutocompleteContext, OptionChoice, Member # pyright: ignore[reportUnknownVariableType]

from views import ConfirmClaimView

with open("TOKEN", "r") as f:
    TOKEN = f.read()

bot = JLOXBot(TurfWar, pathlib.Path() / "save", member_hostable=False, joinable=False)

@bot.event
async def on_ready():
    bot.logger.info(f"{bot.user} is online!")

@bot.command()
async def hi(dctx: ApplicationContext, p: str):
    pass

@bot.game_command()
async def map(dctx: ApplicationContext, gctx: TurfWar):
    """Get the current game map!"""
    embed, map_png_path = generate_new_map(gctx)
    await dctx.respond(embed=embed, file=File(map_png_path, filename="map.png"))

def region_autocomplete(ctx: AutocompleteContext) -> Iterable[OptionChoice]:
    assert isinstance(ctx.interaction.user, Member)
    bot = cast(JLOXBot[TurfWar], ctx.bot)
    gctx = bot.get_game_ctx(ctx)
    if gctx is None:
        return []
    return choices([(region.name, region.idx) for region in gctx.map.regions if not region.home], ctx.value)

@bot.game_command()
@option("region", autocomplete=region_autocomplete, parameter_name="region_id")
async def claim(dctx: ApplicationContext, gctx: TurfWar, region_id: int):
    """Claim a region!"""
    
    assert isinstance(dctx.user, Member)
    team = gctx.get_user_team(dctx.user)
    if team is None:
        await dctx.respond("You have not joined this game!", ephemeral=True)
        return
    
    msg = "Is this the region you want to claim?"
    failed = False
    
    region = gctx.map.regions[region_id]
    if region.home:
        msg = f"{region.name} is a team's base and cannot be claimed!"
        failed = True
    
    own = [OwnedBy.RED, OwnedBy.YELLOW][team.team_id]
    if not failed and region.claim == own:
        msg = f"Your team already owns {region.name}!"
        failed = True
    
    if not failed and not any(neighbour.claim == own for neighbour in region.adjacent):
        msg = f"{region.name} is not adjacent to any of your team's owned regions. Ask a referee if you think this is incorrect."
        failed = True
    
    embed, map_png_path = generate_new_map(gctx, highlight=region_id)
    await dctx.respond(msg, embed=embed, file=File(map_png_path, filename="map.png"), view=ConfirmClaimView(team, gctx, region_id) if not failed else None, ephemeral=True)

bot.run(TOKEN)