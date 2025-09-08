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
        "📊 Harvester Commands": "**`/deposit_sand [amount]`** Convert sand→melange (1-10k, 50:1 ratio)\n"
                                 "**`/refinery`** View melange status & payments\n"
                                 "**`/ledger`** View conversion history & status\n"
                                 "**`/expedition [id]`** View expedition details\n"
                                 "**`/leaderboard [limit]`** Top refiners (5-25 users)\n"
                                 "**`/split [sand] [@users]`** Split sand→melange with guild cut\n"
                                 "**`/help`** Show all commands",
        "⚙️ Admin Commands": "**`/pending`** View pending melange payments\n"
                                   "**`/pay [user] [amount]`** Process user payment (full or partial)\n"
                                   "**`/payroll`** Pay all users\n"
                                   "**`/treasury`** View guild treasury\n"
                                   "**`/guild_withdraw [user] [amount]`** Treasury withdrawal\n"
                                   "**`/sync`** Sync commands (Owner)\n"
                                   "**`/reset confirm:True`** Reset all data",

        "💡 Examples": "• `/deposit_sand 250` → 5 melange\n"
                            "• `/split 1000 @user1 @user2` → 500 each\n"
                            "• `/pay @user` → pay pending melange\n"
                            "• `/payroll` → pay all users"
    }
    
    embed = build_status_embed(
        title="🏜️ Spice Refinery Commands",
        description="Sand→melange conversion & production tracking",
        color=0xF39C12,
        fields=fields,
        timestamp=interaction.created_at
    )
    
    await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
