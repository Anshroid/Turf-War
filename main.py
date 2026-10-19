from typing import Iterable, cast
import pathlib

from config import MAX_PAGE_SIZE
from jloxgame import JLOXBot

from game import TurfWar
from util import Status, claimable, generate_new_map, choices, owned_by

from discord import ApplicationContext, Embed, File, Interaction, option, AutocompleteContext, OptionChoice, Member # pyright: ignore[reportUnknownVariableType]
from discord.ext.pages import Page, Paginator # pyright: ignore[reportMissingTypeStubs]

from views import ClaimView, ChallengeListView

with open("TOKEN", "r") as f:
    TOKEN = f.read()

bot = JLOXBot(TurfWar, pathlib.Path() / "save", member_hostable=False, joinable=True)

@bot.event
async def on_ready():
    bot.logger.info(f"{bot.user} is online!")

@bot.game_command()
async def map(dctx: ApplicationContext, gctx: TurfWar):
    """Get the current game map!"""
    embed, map_png_path = generate_new_map(gctx)
    await dctx.respond(embed=embed, file=File(map_png_path, filename="map.png"))

@bot.game_management_group.game_command()
async def start(dctx: ApplicationContext, gctx: TurfWar):
    """Start the game."""
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
        regions = [region for region in regions if claimable(owned_by(team), region)]
    return choices([(region.name, region.idx) for region in regions], ctx.value)

def owned_region_autocomplete(ctx: AutocompleteContext) -> Iterable[OptionChoice]:
    assert isinstance(ctx.interaction.user, Member)
    bot = cast(JLOXBot[TurfWar], ctx.bot)
    gctx = bot.get_game_ctx(ctx)
    if gctx is None:
        return []
    team = gctx.get_user_team(ctx.interaction.user)
    regions = gctx.map.regions
    if team is not None:
        regions = [region for region in regions if region.claim == owned_by(team)]
    return choices([(region.name, region.idx) for region in regions], ctx.value)

challenge_group = bot.create_group("challenge")

@challenge_group.game_command()
@option("region", autocomplete=region_autocomplete, parameter_name="region_id")
async def get(dctx: ApplicationContext | Interaction, gctx: TurfWar, region_id: int):
    """Get the challenge for a region!"""
    
    assert isinstance(dctx.user, Member)
    team = gctx.get_user_team(dctx.user)
    
    if not (0 <= region_id < len(gctx.map.regions)):
        await dctx.respond("Invalid region entered!", ephemeral=True)
        return
        
    region = gctx.map.regions[region_id]
    if region.home:
        await dctx.respond(f"{region.name} is a team's base!", ephemeral=True)
        return
    
    msg = "If you want to claim this region, make sure it's the right one!"
    
    if team is None:
        msg = f"You are not in this game!"
    
    else:
        own = owned_by(team)
        
        if gctx.status != Status.RUNNING:
            msg = f"The game has ended!"
        
        elif region.claim == own:
            msg = f"Your team already owns {region.name}!"
        
        elif region.locked:
            msg = f"That region is locked for this cycle!"
            
        elif not any(neighbour.claim == own for neighbour in region.adjacent):
            msg = f"{region.name} is not adjacent to any of your team's owned regions. Ask a referee if you think this is incorrect."
        
    
    if region.challenge is None:
        await dctx.respond("Challenges have not been generated yet!", ephemeral=True)
        return
    
    challenge_embed = Embed(title=region.challenge.title, description=region.challenge.description)
    
    map_embed, map_png_path = generate_new_map(gctx, highlight_1=[region])
    await dctx.respond(
        f"Here is the challenge for {region.name}!\n-# {msg}",
        embeds=[challenge_embed, map_embed], 
        file=File(map_png_path, filename="map.png"), 
        view=ClaimView(team, gctx, region_id, disabled=not claimable(owned_by(team), region)), # pyright: ignore[reportArgumentType]
        ephemeral=True
    )
    
@challenge_group.game_command(name="near")
@option("region", autocomplete=owned_region_autocomplete, parameter_name="region_id")
async def list_challenges_near(dctx: ApplicationContext, gctx: TurfWar, region_id: int):
    """List the challenges for all neighbours of a region!"""
    
    assert isinstance(dctx.user, Member)
    team = gctx.get_user_team(dctx.user)
    
    selected_region = gctx.map.regions[region_id]
    
    regions = [region for region in selected_region.adjacent if not region.home]
    
    if team is not None:
        regions = (region for region in regions if claimable(owned_by(team), region))
    
    challenges_embed = Embed()
    challenges_embed.title = f"Challenges near {selected_region.name}"
    
    for region in regions:
        if region.home: continue
        
        if region.challenge is None:
            await dctx.respond("Challenges have not been generated yet!", ephemeral=True)
            return
        
        ownership_msg = f"({region.claim.name})" if team is None else ""
        challenges_embed.add_field(name=f"{region.name} {ownership_msg}- {region.challenge.title}", value=region.challenge.description, inline=False)
        
    if len(challenges_embed.fields) == 0:
        challenges_embed.description = "There are no claimable neighbours!"
    
    map_embed, map_png_path = generate_new_map(gctx, highlight_1=[selected_region], highlight_2=selected_region.adjacent)
    await dctx.respond(embeds=[challenges_embed, map_embed], file=File(map_png_path, filename="map.png"), ephemeral=True)

@challenge_group.game_command(name="list")
async def list_challenges(dctx: ApplicationContext, gctx: TurfWar):
    """List the challenges for all claimable regions!"""
    
    pages: list[Page] = []
    
    assert isinstance(dctx.user, Member)
    team = gctx.get_user_team(dctx.user)
    
    regions = [region for region in gctx.map.regions if not region.home]
    
    if team is not None:
        regions = [region for region in regions if claimable(owned_by(team), region)]
    
    offset = 0
    while offset < len(regions):
        embed = Embed()
        
        for region in regions[offset:offset+MAX_PAGE_SIZE]:
            if region.home: continue
            
            if region.challenge is None:
                await dctx.respond("Challenges have not been generated yet!", ephemeral=True)
                return
            
            ownership_msg = f"({region.claim.name})" if team is None else ""
            embed.add_field(name=f"{region.name} {ownership_msg}- {region.challenge.title}", value=region.challenge.description, inline=False)
        
        pages.append(Page(embeds=[embed], custom_view=ChallengeListView(regions[offset:offset+MAX_PAGE_SIZE], get), content="Here are all the challenges!"))
        
        offset += MAX_PAGE_SIZE
    
    if len(pages) == 0:
        await dctx.respond("There are no valid regions for you to claim!", ephemeral=True)
        return
    
    paginator = Paginator(pages)
    
    await paginator.respond(dctx.interaction, ephemeral=True) # pyright: ignore[reportUnknownMemberType]

@bot.referee_group.game_command()
@option("team", autocomplete=bot.team_autocomplete, parameter_name="team_id")
@option("region", autocomplete=region_autocomplete, parameter_name="region_id")
async def claim(dctx: ApplicationContext, gctx: TurfWar, team_id: int, region_id: int, locked: bool = True):
    """Forcefully set the claimed and locked state of a regions."""
    
    team = gctx.get_team(team_id)
    if team is None:
        await dctx.respond("Invalid team entered!", ephemeral=True)
        return
        
    gctx.force_claim(team_id, region_id, locked)
    await dctx.respond(f"Force claimed {gctx.map.regions[region_id].name} for {team.name}, {(not locked) * "un"}locked successfully!", ephemeral=True)

@bot.referee_group.game_command()
@option("region-1", autocomplete=region_autocomplete, parameter_name="region_1_id")
@option("region-2", autocomplete=region_autocomplete, parameter_name="region_2_id")
async def connect(dctx: ApplicationContext, gctx: TurfWar, region_1_id: int, region_2_id: int):
    """Forcefully connect two regions in the map."""
    
    if not (0 <= region_1_id < len(gctx.map.regions)):
        await dctx.respond("Invalid region 1 entered!", ephemeral=True)
        return
    
    if not (0 <= region_2_id < len(gctx.map.regions)):
        await dctx.respond("Invalid region 2 entered!", ephemeral=True)
        return
    
    gctx.force_connect(region_1_id, region_2_id)
    await dctx.respond(f"Connected {gctx.map.regions[region_1_id].name} to {gctx.map.regions[region_2_id].name} successfully!", ephemeral=True)

bot.run(TOKEN)