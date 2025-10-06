"""
Help command for showing all available spice tracking commands.
"""

# Command metadata
COMMAND_METADATA = {
    'aliases': [],  # ['commands'] - removed for simplicity
    'description': "Show all available spice tracking commands",
    'permission_level': 'any'
}

import os
from utils.embed_utils import build_status_embed
from utils.base_command import command
from utils.helpers import send_response


@command('help')
async def help(interaction, command_start, use_followup: bool = True):
    """Show all available commands and their descriptions"""

    # Use utility function for embed building
    fields = {
        "**`General Commands`**":
            "**`/help`**: Show this list of commands\n"
            "**`/perms`**: Check your current permission level\n"
            "**`/calc [amount]`**: Estimate melange from sand without saving",

        "**`Harvester Commands`**":
            "**`/sand [amount]`**: Convert your sand into melange\n"
            "**`/refinery`**: View your melange production and payment status\n"
            "**`/ledger`**: View your personal conversion history\n"
            "**`/leaderboard [limit]`**: See the top melange producers\n"
            "**`/split [sand] [users]`**: Split sand with others and convert it to melange\n"
            "**`/expedition [id]`**: View the details of a specific split/expedition\n"
            "**`/water [destination]`**: Request a water delivery",

        "**`Admin & Officer Commands`**":
            "**`--- User & Payroll Management ---`**\n"
            "**`/pending`**: View all users with pending (unpaid) melange.\n"
            "**`/pay [user] [amount]`**: Pay a user their pending melange.\n"
            "**`/payroll confirm:True`**: Pay all users with pending melange at once.\n\n"
            "**`--- Guild Management ---`**\n"
            "**`/guild treasury`**: View the guild's treasury balance.\n"
            "**`/guild withdraw [user] [amount]`**: Withdraw melange from the treasury to a user.\n"
            "**`/guild transactions`**: View the guild's transaction history.\n"
            "**`/guild payouts`**: View the guild's melange payout history.\n\n"
            "**`--- Bot Settings ---`**\n"
            "**`/settings [subcommand]`**: View a setting by calling it without options (e.g., `/settings admin_roles`).\n"
            "**`/settings [admin_roles|officer_roles|user_roles] [roles]`**: Set or clear permission roles.\n"
            "**`/settings landsraad [action]`**: Manage the Landsraad conversion bonus (`status`, `enable`, `disable`).\n"
            "**`/settings [user_cut|guild_cut] [value]`**: Set default percentages for `/split`.\n"
            "**`/settings region [region]`**: Set the guild's primary operational region.\n\n"
            "**`--- System Commands ---`**\n"
            "**`/reset confirm:True`**: Reset all data (Admin Only).\n"
            "**`/sync`**: Sync commands with Discord (Bot Owner Only).",
    }

    embed = build_status_embed(
        title="🏜️ Spice Tracker Commands",
        description="A bot for tracking sand-to-melange conversions and guild payroll.",
        color=0xF39C12,
        fields=fields,
        timestamp=interaction.created_at
    )

    await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
