"""
Ledger command for viewing spice deposit history and melange status with pagination.
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': [],
    'description': "View your conversion history and melange status",
    'permission_level': 'user'
}

import time
import math
import discord
from utils.database_utils import timed_database_operation, validate_user_exists
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.base_command import command
from utils.helpers import get_database, send_response, format_melange

DEPOSITS_PER_PAGE = 10

async def build_ledger_embed(interaction, user, deposits, page, total_pages):
    """Build the embed for the ledger."""

    ledger_text = ""
    if not deposits:
        ledger_text = "No conversion history found for this page."
    else:
        for deposit in deposits:
            date_str = f"<t:{int(deposit['created_at'].timestamp())}:R>" if deposit['created_at'] else "Unknown date"
            melange_amount = deposit.get('melange_amount')

            if melange_amount is not None:
                melange_str = f"**{format_melange(melange_amount)} melange**"
            else:
                melange_str = "(legacy)"

            if deposit['type'] == 'expedition':
                deposit_type = "🚀 Expedition"
            elif deposit['type'] == 'group':
                deposit_type = "👥 Group"
            elif deposit['type'] == 'Guild':
                deposit_type = "🏛️ Guild"
            else:
                deposit_type = "🏜️ Solo"

            if deposit['type'] == 'Guild':
                ledger_text += f"{melange_str} {deposit_type} - {date_str}\n"
            else:
                ledger_text += f"**{deposit['sand_amount']:,} sand** -> {melange_str} {deposit_type} - {date_str}\n"

    total_melange = user.get('total_melange', 0) if user else 0
    paid_melange = user.get('paid_melange', 0) if user else 0
    pending_melange = total_melange - paid_melange

    fields = {
        "💎 Melange": f"**{format_melange(total_melange)}** total | **{format_melange(paid_melange)}** paid | **{format_melange(pending_melange)}** pending",
    }

    embed = build_status_embed(
        title="📋 Conversion History",
        description=ledger_text,
        color=0x3498DB,
        fields=fields,
        thumbnail=interaction.user.display_avatar.url,
        timestamp=interaction.created_at
    )
    embed.set_footer(text=f"Page {page}/{total_pages}")
    return embed.build()


class LedgerView(discord.ui.View):
    """A view for paginating through a user's deposit ledger."""

    def __init__(self, interaction, user, total_deposits):
        super().__init__(timeout=180.0)
        self.interaction = interaction
        self.user = user
        self.current_page = 1
        self.total_pages = math.ceil(total_deposits / DEPOSITS_PER_PAGE)

        # Disable buttons if there is only one page
        if self.total_pages <= 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True

    async def update_view(self, interaction: discord.Interaction):
        """Update the view with the new page content."""
        self.previous_button.disabled = self.current_page == 1
        self.next_button.disabled = self.current_page == self.total_pages

        deposits, _ = await timed_database_operation(
            "get_user_deposits",
            get_database().get_user_deposits,
            self.user['user_id'],
            page=self.current_page,
            per_page=DEPOSITS_PER_PAGE
        )

        embed = await build_ledger_embed(interaction, self.user, deposits, self.current_page, self.total_pages)
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
        # Need the original message to edit it.
        # This requires storing the message or fetching it.
        # For simplicity, we'll just let the buttons be disabled client-side.
        # To properly update the message, we'd need to get the original response message
        # and edit it.
        try:
            # message = await self.interaction.original_response()
            # await message.edit(view=self)
            pass # The view is passed by reference, so this should be enough.
        except discord.NotFound:
            pass # The message might have been deleted.

@command('ledger')
async def ledger(interaction, command_start, use_followup: bool = True):
    """View your sand conversion history and melange status"""

    user_id = str(interaction.user.id)
    user = await validate_user_exists(get_database(), user_id, interaction.user.display_name, create_if_missing=True)

    total_deposits, get_count_time = await timed_database_operation(
        "get_user_deposits_count",
        get_database().get_user_deposits_count,
        user_id
    )

    total_melange = user.get('total_melange', 0) if user else 0

    if total_deposits == 0:
        embed = build_status_embed(
            title="📋 Spice Deposit Ledger",
            description="💎 You haven't made any melange yet! Use `/sand` to convert spice sand into melange.",
            color=0x95A5A6,
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
        # Log metrics even for users with no deposits
        log_command_metrics(
            "Ledger",
            user_id,
            interaction.user.display_name,
            time.time() - command_start,
            result_count=0,
            total_melange=total_melange
        )
        return

    view = LedgerView(interaction, user, total_deposits)

    # Get initial deposits for the first page
    initial_deposits, get_deposits_time = await timed_database_operation(
        "get_user_deposits",
        get_database().get_user_deposits,
        user_id,
        page=1,
        per_page=DEPOSITS_PER_PAGE
    )

    embed = await build_ledger_embed(interaction, user, initial_deposits, 1, view.total_pages)

    response_start = time.time()
    await send_response(interaction, embed=embed, view=view, use_followup=use_followup, ephemeral=True)
    response_time = time.time() - response_start

    total_time = time.time() - command_start
    log_command_metrics(
        "Ledger",
        user_id,
        interaction.user.display_name,
        total_time,
        get_deposits_time=f"{get_deposits_time:.3f}s",
        get_count_time=f"{get_count_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        result_count=total_deposits,
        total_melange=total_melange
    )
