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
        "base_description": "Commands available to everyone.",
        "color": 0x3498DB,
        "sections": [
            {
                "title": "",
                "commands": [
                    {"name": "/help", "desc": "Show this list of commands."},
                    {"name": "/perms", "desc": "Check your current permission level."},
                    {"name": "/calc [amount]", "desc": "Estimate melange from sand without saving."},
                ]
            }
        ]
    },
    {
        "title": "Harvester Commands",
        "base_description": "Commands for tracking sand and melange.",
        "color": 0x2ECC71,
        "sections": [
            {
                "title": "",
                "commands": [
                    {"name": "/sand [amount]", "desc": "Convert your sand into melange."},
                    {"name": "/refinery", "desc": "View your melange production and payment status."},
                    {"name": "/ledger", "desc": "View your personal conversion history."},
                    {"name": "/leaderboard [limit]", "desc": "See the top melange producers."},
                    {"name": "/split [sand] [users]", "desc": "Split sand with others and convert it to melange."},
                    {"name": "/expedition [id]", "desc": "View the details of a specific split/expedition."},
                    {"name": "/water [destination]", "desc": "Request a water delivery."},
                ]
            }
        ]
    },
    {
        "title": "Admin & Officer Commands (1/2)",
        "base_description": "Management commands for officers and admins.",
        "color": 0xE74C3C,
        "sections": [
            {
                "title": "User & Payroll Management",
                "commands": [
                    {"name": "/pending", "desc": "View all users with pending (unpaid) melange."},
                    {"name": "/pay [user] [amount]", "desc": "Pay a user their pending melange."},
                    {"name": "/payroll [confirm]", "desc": "Pay all users with pending melange at once."},
                ]
            },
            {
                "title": "Guild Management",
                "commands": [
                    {"name": "/guild treasury", "desc": "View the guild's treasury balance."},
                    {"name": "/guild withdraw [user] [amount]", "desc": "Withdraw melange from the treasury to a user."},
                    {"name": "/guild transactions", "desc": "View the guild's transaction history."},
                    {"name": "/guild payouts", "desc": "View the guild's melange payout history."},
                ]
            }
        ]
    },
    {
        "title": "Admin & Officer Commands (2/2)",
        "base_description": "Configuration and system commands for admins.",
        "color": 0xE74C3C,
        "sections": [
            {
                "title": "Bot Settings",
                "commands": [
                    {"name": "/settings [subcommand]", "desc": "View a setting by calling it without options."},
                    {"name": "/settings [admin_roles|officer_roles|user_roles] [roles]", "desc": "Set or clear permission roles."},
                    {"name": "/settings landsraad [action]", "desc": "Manage the Landsraad conversion bonus."},
                    {"name": "/settings [user_cut|guild_cut] [value]", "desc": "Set default percentages for `/split`."},
                    {"name": "/settings region [region]", "desc": "Set the guild's primary operational region."},
                ]
            },
            {
                "title": "System Commands",
                "commands": [
                    {"name": "/reset [confirm]", "desc": "Reset all data (Admin Only)."},
                    {"name": "/sync", "desc": "Sync commands with Discord (Bot Owner Only)."},
                ]
            }
        ]
    }
]

def build_help_pages(interaction: discord.Interaction) -> list[discord.Embed]:
    """Builds a list of embed pages for the help command."""
    pages = []
    total_pages = len(PAGES_CONTENT)
    for i, page_content in enumerate(PAGES_CONTENT):
        # Combine all sections into a single description string
        description = page_content['base_description']

        for section in page_content['sections']:
            if section['title']:
                description += f"\n\n**__{section['title']}__**"

            command_list = []
            for command in section['commands']:
                command_list.append(f"**`{command['name']}`** - {command['desc']}")
            description += "\n" + "\n".join(command_list)

        embed = build_status_embed(
            title=f"🏜️ Help: {page_content['title']}",
            description=description,
            color=page_content['color'],
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
