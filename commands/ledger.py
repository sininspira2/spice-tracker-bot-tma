"""
Ledger command for viewing spice deposit history and melange status with pagination.
"""
import math
import time
import discord
from utils.database_utils import timed_database_operation, validate_user_exists
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.decorators import handle_interaction_expiration
from utils.helpers import get_database, send_response

# Command metadata
COMMAND_METADATA = {
    'aliases': [],
    'description': "View your conversion history and melange status"
}

PAGE_SIZE = 10

async def build_ledger_embed(interaction, user, total_deposits, page=1):
    """Builds the embed for the ledger command."""
    db = get_database()

if user and total_deposits > 0:
        deposits_data, get_deposits_time = await timed_database_operation(
            "get_user_deposits_paginated",
            db.get_user_deposits_paginated,
            user['user_id'],
            page=page,
            page_size=PAGE_SIZE
        )
    else:
        deposits_data = []
        get_deposits_time = 0.0

    total_pages = math.ceil(total_deposits / PAGE_SIZE) if total_deposits > 0 else 1
    total_melange = user.get('total_melange', 0) if user else 0

    if not deposits_data:
        embed = build_status_embed(
            title="📋 Spice Deposit Ledger",
            description="💎 You haven't made any melange yet! Use `/sand` to convert spice sand into melange.",
            color=0x95A5A6,
            timestamp=interaction.created_at
        )
        return embed, total_pages, total_melange, get_deposits_time

    ledger_text = ""
    for deposit in deposits_data:
        date_str = f"<t:{int(deposit['created_at'].timestamp())}:R>" if deposit['created_at'] else "Unknown date"
        deposit_type = "🚀 Expedition" if deposit['type'] == 'expedition' else "🏜️ Solo"
        ledger_text += f"**{deposit['sand_amount']:,} sand** ({deposit['melange_amount']:,} melange) {deposit_type} - {date_str}\n"

    paid_melange = user.get('paid_melange', 0) if user else 0
    pending_melange = total_melange - paid_melange

    fields = {
        "💎 Melange": f"**{total_melange:,}** total | **{paid_melange:,}** paid | **{pending_melange:,}** pending",
        "📊 Activity": f"{total_deposits} conversions"
    }

    embed = build_status_embed(
        title="📋 Conversion History",
        description=ledger_text,
        color=0x3498DB,
        fields=fields,
        thumbnail=interaction.user.display_avatar.url,
        timestamp=interaction.created_at
    )
    embed.set_footer(text=f"Page {page} of {total_pages}")
    return embed, total_pages, total_melange, get_deposits_time

class LedgerView(discord.ui.View):
    """A view for paginating through the ledger."""
    def __init__(self, interaction, user, total_deposits, total_pages, initial_page=1):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.user = user
        self.total_deposits = total_deposits
        self.current_page = initial_page
        self.total_pages = total_pages
        self.update_buttons()

    def update_buttons(self):
        """Enable or disable buttons based on the current page."""
        self.previous_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages

    async def update_message(self, interaction: discord.Interaction):
        """Update the message with the new page."""
        embed, self.total_pages, _, _ = await build_ledger_embed(self.interaction, self.user, self.total_deposits, self.current_page)
        self.update_buttons()
        await interaction.edit_original_response(embed=embed.build(), view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.grey)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.current_page > 1:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.current_page < self.total_pages:
            self.current_page += 1
            await self.update_message(interaction)

@handle_interaction_expiration
async def ledger(interaction, use_followup: bool = True):
    """View your sand conversion history and melange status"""
    command_start = time.time()
    user_id = str(interaction.user.id)
    db = get_database()

    user = await validate_user_exists(db, user_id, interaction.user.display_name, create_if_missing=False)
    total_deposits = await db.get_user_deposits_count(user_id)

    embed, total_pages, total_melange, get_deposits_time = await build_ledger_embed(interaction, user, total_deposits, page=1)

    view = LedgerView(interaction, user, total_deposits, total_pages) if total_pages > 1 else None

    response_start = time.time()
    await send_response(interaction, embed=embed.build(), view=view, use_followup=use_followup, ephemeral=True)
    response_time = time.time() - response_start

    total_time = time.time() - command_start
    log_command_metrics(
        "Ledger",
        user_id,
        interaction.user.display_name,
        total_time,
        get_deposits_time=f"{get_deposits_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        result_count=total_deposits,
        total_melange=total_melange
    )
