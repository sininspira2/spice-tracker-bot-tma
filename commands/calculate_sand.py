"""
/calculate_sand command for calculating melange conversion without database interaction.
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': [],
    'description': "Calculates melange conversion from spice sand without depositing.",
    'params': {
        'amount': "Amount of spice sand to calculate conversion for",
        'landsraad_bonus': "Whether or not to apply the 25% Landsraad crafting reduction (default: false)."
    }
}

import math
from utils.embed_utils import build_status_embed
from utils.decorators import handle_interaction_expiration
from utils.helpers import get_sand_per_melange, send_response
from utils.permissions import is_allowed_user

@handle_interaction_expiration
async def calculate_sand(interaction, amount: int, landsraad_bonus: bool = False, use_followup: bool = True):
    """Calculates melange conversion from spice sand."""

    # Check if user is allowed to use the command
    if not is_allowed_user(interaction):
        await send_response(interaction, "❌ You are not authorized to use this command.", use_followup=use_followup, ephemeral=True)
        return

    # Validate amount
    if not 1 <= amount <= 10000:
        await send_response(interaction, "❌ Amount must be between 1 and 10,000 spice sand.", use_followup=use_followup, ephemeral=True)
        return

    # Get conversion rate
    sand_per_melange = get_sand_per_melange(landsraad_bonus=landsraad_bonus)

    # Calculate melange
    calculated_melange = math.ceil(amount / sand_per_melange) if sand_per_melange > 0 else 0

    # Build response
    description = f"🎉 **{calculated_melange:,} melange** would be generated from **{amount:,} sand**."

    fields = {
        "⚙️ Conversion Rate": f"1 melange = {sand_per_melange} sand",
        "🎁 Landsraad Bonus": "✅ Active" if landsraad_bonus else "❌ Inactive"
    }

    embed = build_status_embed(
        title="🧮 Sand Conversion Calculation",
        description=description,
        color=0x3498DB, # A nice blue color
        fields=fields,
        timestamp=interaction.created_at
    )

    # Send response
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
