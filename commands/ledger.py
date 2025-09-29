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
import discord
from functools import partial
from utils.database_utils import timed_database_operation, validate_user_exists
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.base_command import command
from utils.helpers import get_database, send_response, format_melange
from utils.pagination_utils import PaginatedView, build_paginated_embed, ITEMS_PER_PAGE

def format_deposit_item(deposit: dict) -> str:
    """Formats a single deposit item for display."""
    date_str = f"<t:{int(deposit['created_at'].timestamp())}:R>" if deposit['created_at'] else "Unknown date"
    melange_amount = deposit.get('melange_amount')

    if melange_amount is not None:
        melange_str = f"**{format_melange(melange_amount)} melange**"
    else:
        melange_str = "(legacy)"

    type_map = {
        'expedition': "🚀 Expedition",
        'group': "👥 Group",
        'Guild': "🏛️ Guild",
    }
    deposit_type = type_map.get(deposit['type'], "🏜️ Solo")

    if deposit['type'] == 'Guild':
        return f"{melange_str} {deposit_type} - {date_str}"
    else:
        return f"**{deposit['sand_amount']:,} sand** -> {melange_str} {deposit_type} - {date_str}"

async def build_ledger_embed(
    interaction: discord.Interaction,
    data: list[dict],
    current_page: int,
    total_pages: int,
    extra_data: dict | None = None,
) -> discord.Embed:
    """Builds the embed for the user's ledger."""
    user = extra_data.get("user")
    total_melange = user.get('total_melange', 0) if user else 0
    paid_melange = user.get('paid_melange', 0) if user else 0
    pending_melange = total_melange - paid_melange

    fields = {
        "💎 Melange": f"**{format_melange(total_melange)}** total | **{format_melange(paid_melange)}** paid | **{format_melange(pending_melange)}** pending",
    }

    return await build_paginated_embed(
        interaction=interaction,
        data=data,
        current_page=current_page,
        total_pages=total_pages,
        title="📋 Conversion History",
        no_results_message="No conversion history found for this page.",
        format_item_func=format_deposit_item,
        extra_embed_data={"fields": fields},
        color=0x3498DB
    )

@command('ledger')
async def ledger(interaction, command_start, use_followup: bool = True):
    """View your sand conversion history and melange status"""
    user_id = str(interaction.user.id)
    db = get_database()
    user = await validate_user_exists(db, user_id, interaction.user.display_name, create_if_missing=True)

    total_deposits, get_count_time = await timed_database_operation(
        "get_user_deposits_count", db.get_user_deposits_count, user_id
    )

    total_melange = user.get('total_melange', 0)
    if total_deposits == 0:
        embed = build_status_embed(
            title="📋 Spice Deposit Ledger",
            description="💎 You haven't made any melange yet! Use `/sand` to convert spice sand into melange.",
            color=0x95A5A6,
            timestamp=interaction.created_at
        ).build()
        await send_response(interaction, embed=embed, use_followup=use_followup, ephemeral=True)
        log_command_metrics(
            "Ledger", user_id, interaction.user.display_name, time.time() - command_start, result_count=0, total_melange=total_melange
        )
        return

    fetch_func = partial(db.get_user_deposits, user_id)

    view = PaginatedView(
        interaction=interaction,
        total_items=total_deposits,
        fetch_data_func=fetch_func,
        format_embed_func=build_ledger_embed,
        extra_embed_data={"user": user}
    )

    initial_deposits, get_deposits_time = await timed_database_operation(
        "get_user_deposits", db.get_user_deposits, user_id, page=1, per_page=ITEMS_PER_PAGE
    )

    embed = await build_ledger_embed(interaction, initial_deposits, 1, view.total_pages, extra_data={"user": user})

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