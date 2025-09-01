"""
Ledger command for viewing complete spice harvest ledger.
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': [],  # ['deposits'] - removed for simplicity
    'description': "View your complete spice harvest ledger"
}

import time
from utils.database_utils import timed_database_operation
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.decorators import handle_interaction_expiration
from utils.helpers import get_database, get_sand_per_melange, send_response


@handle_interaction_expiration
async def ledger(interaction, use_followup: bool = True):
    """View your complete spice harvest ledger"""
    command_start = time.time()
    
    # Database operation with timing using utility function
    deposits_data, get_deposits_time = await timed_database_operation(
        "get_user_deposits",
        get_database().get_user_deposits,
        str(interaction.user.id)
    )
    
    if not deposits_data:
        embed = build_status_embed(
            title="📋 Spice Harvest Ledger",
            description="🏜️ You haven't harvested any spice sand yet! Use `/sand` to start tracking your harvests.",
            color=0x95A5A6,
            footer=f"Requested by {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
        return
    
    # Build melange ledger - convert sand to melange equivalents
    ledger_text = ""
    total_unpaid_melange = 0
    total_paid_melange = 0
    sand_per_melange = get_sand_per_melange()
    
    for deposit in deposits_data:
        status = "✅ Paid" if deposit['paid'] else "⏳ Unpaid"
        melange_amount = deposit['sand_amount'] // sand_per_melange
        
        # Handle null created_at timestamps
        if deposit['created_at'] and hasattr(deposit['created_at'], 'timestamp'):
            date_str = f"<t:{int(deposit['created_at'].timestamp())}:R>"
        else:
            date_str = "Unknown date"
            
        ledger_text += f"**{melange_amount:,} melange** - {status} - {date_str}\n"
        
        if deposit['paid']:
            total_paid_melange += melange_amount
        else:
            total_unpaid_melange += melange_amount
    
    # Use utility function for embed building
    fields = {
        "💎 Melange Summary": f"**Pending:** {total_unpaid_melange:,} | **Paid:** {total_paid_melange:,} | **Deposits:** {len(deposits_data)}"
    }
    
    embed = build_status_embed(
        title="📋 Spice Harvest Ledger",
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
        response_time=f"{response_time:.3f}s",
        result_count=len(deposits_data),
        total_unpaid_melange=total_unpaid_melange,
        total_paid_melange=total_paid_melange
    )
