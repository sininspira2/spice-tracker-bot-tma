"""
Reusable pagination utilities for Discord views.
"""
import math
import discord
from typing import Callable, Coroutine, List, Dict, Any, Optional

from utils.embed_utils import build_status_embed
from utils.database_utils import timed_database_operation

ITEMS_PER_PAGE = 10

class PaginatedView(discord.ui.View):
    """
    A generic paginated view for displaying lists of items.
    """
    def __init__(
        self,
        interaction: discord.Interaction,
        total_items: int,
        fetch_data_func: Callable[[int, int], Coroutine[Any, Any, List[Dict[str, Any]]]],
        format_embed_func: Callable[[discord.Interaction, List[Dict[str, Any]], int, int, Optional[Dict[str, Any]]], Coroutine[Any, Any, discord.Embed]],
        extra_embed_data: Optional[Dict[str, Any]] = None,
        timeout: float = 180.0
    ):
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.total_items = total_items
        self.fetch_data_func = fetch_data_func
        self.format_embed_func = format_embed_func
        self.extra_embed_data = extra_embed_data
        self.current_page = 1
        self.total_pages = math.ceil(total_items / ITEMS_PER_PAGE)

        if self.total_pages <= 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True

    async def update_view(self, interaction: discord.Interaction):
        """Update the view with the new page content."""
        self.previous_button.disabled = self.current_page == 1
        self.next_button.disabled = self.current_page == self.total_pages

        data, _ = await timed_database_operation(
            f"fetch_paginated_data_page_{self.current_page}",
            self.fetch_data_func,
            page=self.current_page,
            per_page=ITEMS_PER_PAGE
        )

        embed = await self.format_embed_func(
            interaction, data, self.current_page, self.total_pages, self.extra_embed_data
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.grey)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 1:
            self.current_page -= 1
            await self.update_view(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages:
            self.current_page += 1
            await self.update_view(interaction)

    async def on_timeout(self):
        """Disable buttons on timeout."""
        self.previous_button.disabled = True
        self.next_button.disabled = True
        try:
            message = await self.interaction.original_response()
            await message.edit(view=self)
        except discord.NotFound:
            pass

async def build_paginated_embed(
    interaction: discord.Interaction,
    data: List[Dict[str, Any]],
    current_page: int,
    total_pages: int,
    title: str,
    no_results_message: str,
    format_item_func: Callable[[Dict[str, Any]], str],
    extra_embed_data: Optional[Dict[str, Any]] = None,
    color: int = 0x3498DB
) -> discord.Embed:
    """
    Builds a generic paginated embed.
    """
    description_text = ""
    if not data:
        description_text = no_results_message
    else:
        description_text = "\n".join(format_item_func(item) for item in data)

    fields = extra_embed_data.get("fields", {}) if extra_embed_data else {}

    embed = build_status_embed(
        title=title,
        description=description_text,
        color=color,
        fields=fields,
        thumbnail=interaction.user.display_avatar.url,
        timestamp=interaction.created_at
    )
    embed.set_footer(text=f"Page {current_page}/{total_pages}")
    return embed.build()