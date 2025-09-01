"""
Ledger command for viewing spice deposit history and melange status.
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': [],  # ['deposits'] - removed for simplicity
    'description': "View your spice deposit history and melange status"
}

import time
from utils.database_utils import timed_database_operation, get_user_stats
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.decorators import handle_interaction_expiration
from utils.helpers import get_database, get_sand_per_melange, send_response


@handle_interaction_expiration
async def ledger(interaction, use_followup: bool = True):
    """View your spice deposit history and melange status"""
    command_start = time.time()
    
    # Get user stats for melange information
    user_stats, get_stats_time = await timed_database_operation(
        "get_user_stats",
        get_user_stats,
        get_database(), str(interaction.user.id)
    )
    
    # Get deposit history
    deposits_data, get_deposits_time = await timed_database_operation(
        "get_user_deposits",
        get_database().get_user_deposits,
        str(interaction.user.id)
    )
    
    if not deposits_data:
        embed = build_status_embed(
            title="📋 Spice Deposit Ledger",
            description="🏜️ You haven't made any spice deposits yet! Use `/sand` to start tracking your harvests.",
            color=0x95A5A6,
            footer=f"/ledger • {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
        return
    
    # Build deposit history (just a log, no payment status per deposit)
    ledger_text = ""
    total_sand_deposited = 0
    sand_per_melange = get_sand_per_melange()
    
    for deposit in deposits_data:
        # Handle null created_at timestamps
        if deposit['created_at'] and hasattr(deposit['created_at'], 'timestamp'):
            date_str = f"<t:{int(deposit['created_at'].timestamp())}:R>"
        else:
            date_str = "Unknown date"
        
        # Show deposit type
        deposit_type = "🚀 Expedition" if deposit['type'] == 'expedition' else "🏜️ Solo"
        
        ledger_text += f"**{deposit['sand_amount']:,} sand** {deposit_type} - {date_str}\n"
        total_sand_deposited += deposit['sand_amount']
    
    # Calculate total melange earned from all deposits
    total_melange_earned = total_sand_deposited // sand_per_melange
    
    # Use utility function for embed building
    fields = {
        "💎 Melange Status": f"**Total Earned:** {user_stats['total_melange']:,} | **Paid:** {user_stats['paid_melange']:,} | **Pending:** {user_stats['pending_melange']:,}",
        "📊 Deposit Summary": f"**Total Deposits:** {len(deposits_data)} | **Total Sand:** {total_sand_deposited:,} | **Melange Value:** {total_melange_earned:,}"
    }
    
    embed = build_status_embed(
        title="📋 Spice Deposit Ledger",
        description=ledger_text,
        color=0x3498DB,
        fields=fields,
        footer=f"/ledger • {interaction.user.display_name}",
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
        "Ledger",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        get_deposits_time=f"{get_deposits_time:.3f}s",
        get_stats_time=f"{get_stats_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        result_count=len(deposits_data),
        total_sand_deposited=total_sand_deposited,
        total_melange_earned=total_melange_earned
    )