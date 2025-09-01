"""
Sand command for logging spice sand harvests and calculating melange conversion.
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': [],  # formerly named 'harvest'
    'description': "Log spice sand harvests and calculate melange conversion",
    'params': {'amount': "Amount of spice sand harvested"}
}

import time
from utils.database_utils import timed_database_operation, validate_user_exists, get_user_stats
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.decorators import handle_interaction_expiration
from utils.helpers import get_database, get_sand_per_melange, send_response


@handle_interaction_expiration
async def sand(interaction, amount: int, use_followup: bool = True):
    """Log spice sand harvests and calculate melange conversion"""
    command_start = time.time()
    
    # Validate amount
    if not 1 <= amount <= 10000:
        await send_response(interaction, "❌ Amount must be between 1 and 10,000 spice sand.", use_followup=use_followup, ephemeral=True)
        return
    
    # Get conversion rate and add deposit
    sand_per_melange = get_sand_per_melange()
    
    # Database operations with timing using utility functions
    
    # Add deposit with timing
    _, add_deposit_time = await timed_database_operation(
        "add_deposit",
        get_database().add_deposit,
        str(interaction.user.id), interaction.user.display_name, amount
    )
    
    # Get user data and calculate totals
    user_stats = await get_user_stats(get_database(), str(interaction.user.id))
    
    # Ensure user exists and has valid data
    user = await validate_user_exists(get_database(), str(interaction.user.id), interaction.user.display_name)
    
    # Convert sand directly to melange
    new_melange = amount // sand_per_melange
    current_melange = user_stats['total_melange']
    
    # Only update melange if we have new melange to add
    update_melange_time = 0
    if new_melange > 0:
        _, update_melange_time = await timed_database_operation(
            "update_user_melange",
            get_database().update_user_melange,
            str(interaction.user.id), new_melange
        )
    
    # Build information-dense response focused on melange
    leftover_sand = amount % sand_per_melange
    description = f"🎉 **+{new_melange:,} melange produced!**" if new_melange > 0 else f"📦 **{amount:,} sand processed**"
    
    # Show only melange information - sand is just temporary input
    fields = {
        "💎 Melange Status": f"**Total:** {(current_melange + new_melange):,} | **New:** +{new_melange:,}",
        "⚙️ Conversion": f"**Processed:** {amount:,} sand → {new_melange:,} melange" + (f" ({leftover_sand} sand unused)" if leftover_sand > 0 else "")
    }
    
    embed = build_status_embed(
        title="🏜️ Harvest Complete",
        description=description,
        color=0xE67E22,
        fields=fields,
        timestamp=interaction.created_at
    )
    
    # Send response using helper function
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
    response_time = time.time() - response_start
    
    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Harvest",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        amount=amount,
        add_deposit_time=f"{add_deposit_time:.3f}s",
        update_melange_time=f"{update_melange_time:.3f}s",
        **user_stats['timing'],
        response_time=f"{response_time:.3f}s",
        new_melange=new_melange
    )
