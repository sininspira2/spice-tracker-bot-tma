"""
Payment command for processing payment for a harvester's deposits (Admin only).
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': ['pay'],
    'description': "Process payment for a harvester's deposits (Admin only)",
    'params': {'user': "Harvester to pay"}
}

import time
from utils.database_utils import timed_database_operation
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.decorators import handle_interaction_expiration
from utils.helpers import get_database, send_response
from utils.permissions import is_admin


@handle_interaction_expiration
async def payment(interaction, user, use_followup: bool = True):
    """Process payment for a harvester's deposits (Admin only)"""
    command_start = time.time()
    
    # Check if user has admin permissions
    if not is_admin(interaction):
        await send_response(interaction, "❌ You need an admin role to use this command. Contact a server administrator.", use_followup=use_followup, ephemeral=True)
        return
    
    # Get user's pending melange
    pending_data, get_pending_time = await timed_database_operation(
        "get_user_pending_melange",
        get_database().get_user_pending_melange,
        str(user.id)
    )
    
    pending_melange = pending_data.get('pending_melange', 0)
    total_melange = pending_data.get('total_melange', 0)
    paid_melange = pending_data.get('paid_melange', 0)
    
    if pending_melange <= 0:
        embed = build_status_embed(
            title="💰 No Payment Due",
            description=f"**{user.display_name}** has no pending melange.",
            color=0x95A5A6,
            fields={"📊 Status": f"**Total:** {total_melange:,} | **Paid:** {paid_melange:,} | **Pending:** {pending_melange:,}"},
            footer=f"/payment @{user.display_name} • {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup)
        return
    
    # Pay the user's pending melange
    paid_amount, pay_melange_time = await timed_database_operation(
        "pay_user_melange",
        get_database().pay_user_melange,
        str(user.id), user.display_name, pending_melange,
        str(interaction.user.id), interaction.user.display_name
    )
    
    # Build information-dense response
    fields = {
        "💰 Payment Processed": f"**Amount:** {paid_amount:,} melange | **Admin:** {interaction.user.display_name}",
        "📊 User Status": f"**Total:** {total_melange:,} | **Paid:** {paid_melange + paid_amount:,} | **Pending:** 0"
    }
    
    embed = build_status_embed(
        title="💰 Payment Processed",
        description=f"**{user.display_name}** has been paid {paid_amount:,} melange!",
        color=0x27AE60,
        fields=fields,
        footer=f"/payment @{user.display_name} • {interaction.user.display_name}",
        timestamp=interaction.created_at
    )
    
    # Send response using helper function
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
    response_time = time.time() - response_start
    
    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Melange Payment",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        admin_id=str(interaction.user.id),
        admin_username=interaction.user.display_name,
        target_user_id=str(user.id),
        target_username=user.display_name,
        get_pending_time=f"{get_pending_time:.3f}s",
        pay_melange_time=f"{pay_melange_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        melange_paid=paid_amount,
        total_melange=total_melange
    )
    
    print(f'User {user.display_name} ({user.id}) paid {paid_amount:,} melange by {interaction.user.display_name} ({interaction.user.id})')
