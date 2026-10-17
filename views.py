from typing import TYPE_CHECKING

from discord import ButtonStyle, File, Interaction, SelectOption
from discord.ui import Select, View, Button, button

from content import MapRegion
from jloxgame.abc import AsyncCallable
from jloxgame.state import Team
from util import generate_new_map, disable_view

if TYPE_CHECKING:
    from game import TurfWar

class ClaimView(View):
    def __init__(self, team: Team, gctx: TurfWar, region_id: int, disabled: bool = False):
        super().__init__(timeout=None)
        
        self.team = team
        self.gctx = gctx
        self.region_id = region_id
        
        if disabled: self.disable_all_items()
        
    @button(label="Claim!", style=ButtonStyle.green, emoji="🎯")
    async def confirm(self, button: Button[ClaimView], interaction: Interaction):
        success = self.gctx.claim_region(self.team.team_id, self.region_id)
        
        if success:
            region = self.gctx.map.regions[self.region_id]
            await interaction.respond(f"Claimed {region.name}!", ephemeral=True)
            
            await disable_view(self)
            
            embed, map_png_path = generate_new_map(self.gctx, highlight=self.region_id)
            if self.gctx.thread: await self.gctx.thread.send(f"{self.team.name} has claimed {region.name}!", embed=embed, file=File(map_png_path, filename="map.png"))
        
        else:
            await interaction.respond(f"Something went wrong - the claim is no longer valid!", ephemeral=True)

class ChallengeListView(View):
    def __init__(self, regions: list[MapRegion], get_challenge_fn: AsyncCallable[[Interaction, int], None]):
        super().__init__(timeout=None)
        
        class ChallengeListSelect(Select):
            async def callback(self, interaction: Interaction):
                if not self.values: return
                
                region_id = int(self.values[0])
                
                await get_challenge_fn(interaction, region_id)
            
        self.add_item(ChallengeListSelect(options = [SelectOption(label=region.name, value=str(region.idx)) for region in regions], placeholder = "Select a region to claim..."))
        