"""
Help command for showing all available spice tracking commands.
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': [],  # ['commands'] - removed for simplicity
    'description': "Show all available spice tracking commands"
}

import os
from utils.embed_utils import build_status_embed
from utils.decorators import handle_interaction_expiration
from utils.helpers import send_response


@handle_interaction_expiration
async def help(interaction, use_followup: bool = True):
    """Show all available commands and their descriptions"""
    
    # Use utility function for embed building
    fields = {
        "📊 Harvester Commands": "**`/sand [amount]`**\nLog spice sand harvests (1-10,000). Automatically converts to melange.\n\n"
                                 "**`/refinery`**\nView your refinery statistics and melange production progress.\n\n"
                                 "**`/ledger`**\nView your complete deposit history and melange status.\n\n"
                                 "**`/expedition [id]`**\nView details of a specific expedition.\n\n"
                                 "**`/leaderboard [limit]`**\nShow top refiners by melange production (5-25 users).\n\n"
                                 "**`/split [total_sand] [@users]`**\nSplit harvested spice equally among mentioned users. Mention users with @ symbol. Include @yourself if you want to be part of the split. Creates expedition records and tracks melange owed for payout.\n\n"
                                 "**`/help`**\nDisplay this help message with all commands.",
        "⚙️ Guild Admin Commands": "**`/pending`**\nView all users with pending melange payments and amounts owed.\n\n"
                                   "**`/payment [user]`**\nProcess payment for a harvester's deposits.\n\n"
                                   "**`/payroll`**\nProcess payments for all unpaid harvesters.\n\n"
                                   "**`/treasury`**\nView guild treasury balance and melange reserves.\n\n"
                                   "**`/guild_withdraw [user] [amount]`**\nWithdraw sand from guild treasury to give to a user.\n\n"
                                   "**`/sync`**\nSync slash commands (Bot Owner Only).\n\n"
                                   "**`/reset confirm:True`**\nReset all refinery statistics (requires confirmation).",

        "💡 Example Usage": "• `/sand 250` - Harvest 250 spice sand\n"
                            "• `/refinery` - Check your refinery status\n"
                            "• `/ledger` - View your harvest ledger\n"
                            "• `/leaderboard 15` - Show top 15 refiners\n"
                            "• `/payment @username` - Pay a specific harvester\n"
                            "• `/payroll` - Pay all harvesters at once\n"
                            "• `/split 1000 @shon @theycall @ricky` - Split 1000 sand equally among 3 people\n"
                            "• `/split 500 @username @yourself` - Split 500 sand equally between 2 people (including yourself)\n"
                            "• **Note:** Users must be mentioned with @ symbol. Include @yourself if you want to be part of the split."
    }
    
    embed = build_status_embed(
        title="🏜️ Spice Refinery Commands",
        description="Track your spice sand harvests and melange production in the Dune: Awakening universe!",
        color=0xF39C12,
        fields=fields,
        timestamp=interaction.created_at
    )
    
    await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
