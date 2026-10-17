from typing import Iterable, cast
import pathlib

from config import MAX_PAGE_SIZE
from jloxgame import JLOXBot

from game import TurfWar
from util import generate_new_map, choices, OwnedBy

from discord import ApplicationContext, Embed, File, Interaction, option, AutocompleteContext, OptionChoice, Member # pyright: ignore[reportUnknownVariableType]
from discord.ext.pages import Page, Paginator # pyright: ignore[reportMissingTypeStubs]

from views import ClaimView, ChallengeListView

with open("TOKEN", "r") as f:
    TOKEN = f.read()

bot = JLOXBot(TurfWar, pathlib.Path() / "save", member_hostable=False, joinable=True)

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

@bot.game_management_group.game_command()
async def start(dctx: ApplicationContext, gctx: TurfWar):
    gctx.start()
    await dctx.respond("Game started!")

def region_autocomplete(ctx: AutocompleteContext) -> Iterable[OptionChoice]:
    assert isinstance(ctx.interaction.user, Member)
    bot = cast(JLOXBot[TurfWar], ctx.bot)
    gctx = bot.get_game_ctx(ctx)
    if gctx is None:
        return []
    team = gctx.get_user_team(ctx.interaction.user)
    regions = [region for region in gctx.map.regions if not region.home]
    if team is not None:
        own = [OwnedBy.RED, OwnedBy.YELLOW][team.team_id]
        regions = [region for region in regions if region.claim != own and any(neighbour.claim == own for neighbour in region.adjacent)]
    return choices([(region.name, region.idx) for region in regions], ctx.value)

challenge_group = bot.create_group("challenge")

@challenge_group.game_command()
@option("region", autocomplete=region_autocomplete, parameter_name="region_id")
async def get(dctx: ApplicationContext | Interaction, gctx: TurfWar, region_id: int):
    """Get the challenge for a region you are currently in!"""
    
    assert isinstance(dctx.user, Member)
    team = gctx.get_user_team(dctx.user)
    region = gctx.map.regions[region_id]
    
    msg = "If you want to claim this region, make sure it's the right one!"
    claimable = True
    
    if team is None:
        msg = f"You are not in any team in this game!"
        claimable = False
    else:
        own = [OwnedBy.RED, OwnedBy.YELLOW][team.team_id]
        
        if region.home:
            msg = f"{region.name} is a team's base and cannot be claimed!"
            claimable = False
            
        elif region.claim == own:
            msg = f"Your team already owns {region.name}!"
            claimable = False
            
        elif not any(neighbour.claim == own for neighbour in region.adjacent):
            msg = f"{region.name} is not adjacent to any of your team's owned regions. Ask a referee if you think this is incorrect."
            claimable = False
    
    if region.challenge is None:
        await dctx.respond("Something went wrong - challenges have not been generated yet!", ephemeral=True)
        return
    
    challenge_embed = Embed(title=region.challenge.title, description=region.challenge.description)
    
    map_embed, map_png_path = generate_new_map(gctx, highlight=region_id, highlight_neighbours=True)
    await dctx.respond(
        f"Here is the challenge for {region.name}!\n-# {msg}",
        embeds=[challenge_embed, map_embed], 
        file=File(map_png_path, filename="map.png"), 
        view=ClaimView(team, gctx, region_id, disabled=not claimable), # pyright: ignore[reportArgumentType]
        ephemeral=True
    )

@challenge_group.game_command(name="list")
async def list_challenges(dctx: ApplicationContext, gctx: TurfWar, show_all: bool = False):
    """List the challenges for all regions!"""
    
    pages: list[Page] = []
    
    assert isinstance(dctx.user, Member)
    team = gctx.get_user_team(dctx.user)
    
    regions = [region for region in gctx.map.regions if not region.home]
    
    if team is not None:
        own = [OwnedBy.RED, OwnedBy.YELLOW][team.team_id]
        regions = [region for region in regions if region.claim != own and any(neighbour.claim == own for neighbour in region.adjacent)]
    
    if len(regions) == 0:
        await dctx.respond("There are no valid regions for you to claim!", ephemeral=True)
        return
    
    offset = 0
    while offset < len(regions):
        embed = Embed()
        
        for region in regions[offset:offset+MAX_PAGE_SIZE]:
            if region.home: continue
            
            if region.challenge is None:
                await dctx.respond("Something went wrong - challenges have not been generated yet!", ephemeral=True)
                return
            
            embed.add_field(name=f"{region.name} - {region.challenge.title}", value=region.challenge.description, inline=False)
        
        pages.append(Page(embeds=[embed], custom_view=ChallengeListView(regions[offset:offset+MAX_PAGE_SIZE], get), content="Here are all the challenges!"))
        
        offset += MAX_PAGE_SIZE
    
    paginator = Paginator(pages)
    
    await paginator.respond(dctx.interaction, ephemeral=True) # pyright: ignore[reportUnknownMemberType]

@bot.referee_group.game_command()
@option("team", autocomplete=bot.team_autocomplete, parameter_name="team_id")
@option("region", autocomplete=region_autocomplete, parameter_name="region_id")
async def claim(dctx: ApplicationContext, gctx: TurfWar, team_id: int, region_id: int, locked: bool = True):
    team = gctx.get_team(team_id)
    if team is None:
        await dctx.respond("Invalid team entered!", ephemeral=True)
        return
        
    gctx.force_claim(team_id, region_id, locked)
    await dctx.respond(f"Force claimed {gctx.map.regions[region_id].name} for {team.name}, {not locked * "un"}locked successfully!", ephemeral=True)

@bot.referee_group.game_command()
@option("region-1", autocomplete=region_autocomplete, parameter_name="region_1_id")
@option("region-2", autocomplete=region_autocomplete, parameter_name="region_2_id")
async def connect(dctx: ApplicationContext, gctx: TurfWar, region_1_id: int, region_2_id: int):
    gctx.force_connect(region_1_id, region_2_id)
    await dctx.respond(f"Connected {gctx.map.regions[region_1_id]} to {gctx.map.regions[region_2_id]} successfully!", ephemeral=True)

bot.run(TOKEN)