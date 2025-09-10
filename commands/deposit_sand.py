"""
/deposit_sand command for logging spice sand harvests and calculating melange conversion.
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': [],  # The old command name was 'sand'. Slash commands don't support aliases.
    'description': "Deposits spice sand and converts it into melange (primary currency)",
    'params': {
        'amount': "Amount of spice sand to convert",
        'landsraad_bonus': "Whether or not to apply the 25% Landsraad crafting reduction (default: false)."
    }
}

import time
import math
from utils.database_utils import timed_database_operation, validate_user_exists
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.decorators import handle_interaction_expiration
from utils.helpers import get_database, get_sand_per_melange, send_response
from utils.permissions import is_officer


@handle_interaction_expiration
async def deposit_sand(interaction, amount: int, landsraad_bonus: bool = False, use_followup: bool = True):
    """Convert spice sand into melange (primary currency)"""
    command_start = time.time()

    # Check if user has officer permissions
    if not is_officer(interaction):
        await send_response(interaction, "❌ You need to be an officer to use this command.", use_followup=use_followup, ephemeral=True)
        return

    # Validate amount
    if not 1 <= amount <= 10000:
        await send_response(interaction, "❌ Amount must be between 1 and 10,000 spice sand.", use_followup=use_followup, ephemeral=True)
        return

    # Get conversion rate and add deposit
    sand_per_melange = get_sand_per_melange(landsraad_bonus=landsraad_bonus)

    # Ensure user exists and get their data before the transaction
    user = await validate_user_exists(get_database(), str(interaction.user.id), interaction.user.display_name)
    current_melange = user.get('total_melange', 0)

    # Convert sand directly to melange
    new_melange = math.ceil(amount / sand_per_melange) if sand_per_melange > 0 else 0

    # Perform atomic deposit and melange update
    _, process_deposit_time = await timed_database_operation(
        "process_deposit",
        get_database().process_deposit,
        str(interaction.user.id),
        interaction.user.display_name,
        amount,
        new_melange
    )

    # Build concise response
    description = f"🎉 **+{new_melange:,} melange**" if new_melange > 0 else f"📦 **{amount:,} sand processed**"

    fields = {
        "💎 Total": f"{(current_melange + new_melange):,} melange",
        "⚙️ Converted": f"{amount:,} sand → {new_melange:,} melange"
    }

    embed = build_status_embed(
        title="🏜️ Conversion Complete",
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
        "Deposit Sand",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        amount=amount,
        process_deposit_time=f"{process_deposit_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        new_melange=new_melange
    )
