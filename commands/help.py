"""
Help command for showing all available spice tracking commands.
"""

import discord
from utils.embed_utils import build_status_embed
from utils.base_command import command
from utils.pagination_utils import StaticPaginatedView

# Command metadata
COMMAND_METADATA = {
    'aliases': [],
    'description': "Show all available spice tracking commands",
    'permission_level': 'any'
}

# Define the content for each page
PAGES_CONTENT = [
    {
        "title": "General Commands",
        "description": "Commands available to everyone.",
        "color": 0x3498DB,
        "fields": {
            "**`/help`**": "Show this list of commands.",
            "**`/perms`**": "Check your current permission level.",
            "**`/calc [amount]`**": "Estimate melange from sand without saving.",
        },
    },
    {
        "title": "Harvester Commands",
        "description": "Commands for tracking sand and melange.",
        "color": 0x2ECC71,
        "fields": {
            "**`/sand [amount]`**": "Convert your sand into melange.",
            "**`/refinery`**": "View your melange production and payment status.",
            "**`/ledger`**": "View your personal conversion history.",
            "**`/leaderboard [limit]`**": "See the top melange producers.",
            "**`/split [sand] [users]`**": "Split sand with others and convert it to melange.",
            "**`/expedition [id]`**": "View the details of a specific split/expedition.",
            "**`/water [destination]`**": "Request a water delivery.",
        },
    },
    {
        "title": "Admin & Officer Commands (1/2)",
        "description": "Management commands for officers and admins.",
        "color": 0xE74C3C,
        "fields": {
            "**`--- User & Payroll Management ---`**": "\u200b",
            "**`/pending`**": "View all users with pending (unpaid) melange.",
            "**`/pay [user] [amount]`**": "Pay a user their pending melange.",
            "**`/payroll confirm:True`**": "Pay all users with pending melange at once.",
            "**`--- Guild Management ---`**": "\u200b",
            "**`/guild treasury`**": "View the guild's treasury balance.",
            "**`/guild withdraw [user] [amount]`**": "Withdraw melange from the treasury to a user.",
            "**`/guild transactions`**": "View the guild's transaction history.",
            "**`/guild payouts`**": "View the guild's melange payout history.",
        },
    },
    {
        "title": "Admin & Officer Commands (2/2)",
        "description": "Configuration and system commands for admins.",
        "color": 0xE74C3C,
        "fields": {
            "**`--- Bot Settings ---`**": "\u200b",
            "**`/settings [subcommand]`**": "View a setting by calling it without options.",
            "**`/settings [roles]`**": "Set or clear permission roles (e.g., `admin_roles`).",
            "**`/settings landsraad [action]`**": "Manage the Landsraad conversion bonus.",
            "**`/settings [cuts]`**": "Set default percentages for `/split` (e.g., `user_cut`).",
            "**`/settings region [region]`**": "Set the guild's primary operational region.",
            "**`--- System Commands ---`**": "\u200b",
            "**`/reset confirm:True`**": "Reset all data (Admin Only).",
            "**`/sync`**": "Sync commands with Discord (Bot Owner Only).",
        },
    },
]

def build_help_pages(interaction: discord.Interaction) -> list[discord.Embed]:
    """Builds a list of embed pages for the help command."""
    pages = []
    total_pages = len(PAGES_CONTENT)
    for i, page_content in enumerate(PAGES_CONTENT):
        # Create a dictionary of fields where the value is the description
        fields_dict = {name: desc for name, desc in page_content["fields"].items()}

        embed = build_status_embed(
            title=f"🏜️ Help: {page_content['title']}",
            description=page_content['description'],
            color=page_content['color'],
            fields=fields_dict,
            timestamp=interaction.created_at
        )
        embed.set_footer(text=f"Page {i + 1}/{total_pages} • Use the buttons to navigate.")
        pages.append(embed.build())
    return pages


@command('help')
async def help(interaction: discord.Interaction, command_start, **kwargs):
    """Show all available commands and their descriptions using a paginated view."""
    pages = build_help_pages(interaction)
    view = StaticPaginatedView(interaction=interaction, pages=pages)

    # The decorator already defers the response, so we use a followup.
    await interaction.followup.send(
        embed=pages[0],
        view=view,
        ephemeral=True
    )
