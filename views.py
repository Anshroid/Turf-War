import asyncio
from typing import TYPE_CHECKING

from discord import ButtonStyle, File, Interaction
from discord.ui import View, Button, button

from jloxgame.state import Team
from util import generate_new_map, disable_view

if TYPE_CHECKING:
    from game import TurfWar

class ConfirmClaimView(View):
    instances: dict[Team, ConfirmClaimView] = {}
    
    def __init__(self, team: Team, gctx: TurfWar, region_id: int):
        super().__init__(timeout=None)
        
        if team in ConfirmClaimView.instances:
            view = ConfirmClaimView.instances[team]
            asyncio.create_task(disable_view(view))
        ConfirmClaimView.instances[team] = self
        
        self.team = team
        self.gctx = gctx
        self.region_id = region_id
        
    @button(label="Confirm!", style=ButtonStyle.green, emoji="🎯")
    async def confirm(self, button: Button[ConfirmClaimView], interaction: Interaction):
        success = self.gctx.claim_region(self.team.team_id, self.region_id)
        
        if success:
            region = self.gctx.map.regions[self.region_id]
            await interaction.respond(f"Claimed {region.name}!", ephemeral=True)
            
            await disable_view(self)
            
            embed, map_png_path = generate_new_map(self.gctx, highlight=self.region_id)
            if self.gctx.thread: await self.gctx.thread.send(f"{self.team.name} has claimed {region.name}!", embed=embed, file=File(map_png_path, filename="map.png"))
        
        else:
            await interaction.respond(f"Something went wrong - the claim is no longer valid!", ephemeral=True)
    
    @button(label="Cancel!", style=ButtonStyle.red, emoji="✖️")
    async def cancel(self, button: Button[ConfirmClaimView], interaction: Interaction):
        await interaction.respond("Cancelled the interaction.", ephemeral=True)
        
        await disable_view(self)
