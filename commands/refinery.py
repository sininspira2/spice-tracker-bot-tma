"""
Refinery command for viewing spice refinery statistics and progress.
"""

import time
from utils.database_utils import validate_user_exists
from utils.embed_utils import build_info_embed, build_status_embed
from utils.command_utils import log_command_metrics
from utils.decorators import handle_interaction_expiration
from utils.helpers import send_response

# Command metadata
COMMAND_METADATA = {
    'aliases': [],  # ['status'] - removed for simplicity
    'description': "View your spice refinery statistics and progress"
}


@handle_interaction_expiration
async def refinery(interaction, use_followup: bool = True):
    """Show your total sand and melange statistics"""
    command_start = time.time()

    # Get user data directly from database
    user = await validate_user_exists(get_database(), str(interaction.user.id), interaction.user.display_name, create_if_missing=False)

    if not user or user.get('total_melange', 0) == 0:
        embed = build_info_embed(
            title="🏭 Spice Refinery Status",
            info_message="🏜️ You haven't harvested any spice sand yet! Use `/sand` to start tracking your harvests.",
            color=0x95A5A6,
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
        return

    # Build melange status fields - no sand information needed
    last_activity_timestamp = (
        user['last_updated'].timestamp()
        if user and user.get('last_updated') else interaction.created_at.timestamp()
    )

    # Calculate pending melange
    total_melange = user.get('total_melange', 0)
    paid_melange = user.get('paid_melange', 0)
    pending_melange = total_melange - paid_melange

    # Focus purely on melange - the primary currency
    fields = {
        "💎 Melange Status": f"**Total:** {total_melange:,} | **Pending:** {pending_melange:,} | **Paid:** {paid_melange:,}",
        "💰 Last Activity": f"<t:{int(last_activity_timestamp)}:R>"
    }

    # Use utility function for status embed (no progress bar needed)
    embed = build_status_embed(
        title="🏭 Spice Refinery Status",
        description=f"💎 **{total_melange:,} total melange** in your refinery",
        color=0xF39C12,
        fields=fields,
        thumbnail=interaction.user.display_avatar.url,
        timestamp=interaction.created_at
    )

    # Send response using helper function (ephemeral for privacy)
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
    response_time = time.time() - response_start

    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Refinery",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        response_time=f"{response_time:.3f}s",
        total_melange=total_melange,
        pending_melange=pending_melange,
        paid_melange=paid_melange
    )
