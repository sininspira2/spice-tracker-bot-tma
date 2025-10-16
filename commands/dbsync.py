"""
Admin command to manually resynchronize database primary key sequences.
"""

from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.helpers import get_database, send_response
from utils.base_command import admin_command
from utils.logger import logger

COMMAND_METADATA = {
    'aliases': [],
    'description': "Manually resynchronizes all database primary key sequences.",
    'params': {},
    'permission_level': 'any'
}

@admin_command('dbsync')
async def dbsync(interaction, command_start, **kwargs):
    """
    Admin command to manually resynchronize all database primary key sequences.
    This is a maintenance command to fix sequences that are out of sync.
    """
    import os
    if interaction.user.id != int(os.getenv('BOT_OWNER_ID', '0')):
        await send_response(interaction, "❌ Only the bot owner can use this command.", ephemeral=True)
        return
    db = get_database()

    # This command is PostgreSQL-specific
    if db.is_sqlite:
        embed = build_status_embed(
            title="⚙️ Database Sync",
            description="This command is only applicable for PostgreSQL databases.",
            color=0x95A5A6
        )
        await send_response(interaction, embed=embed.build(), ephemeral=True)
        return

    try:
        resynced_sequences = await db.resync_sequences()

        if not resynced_sequences:
            description = "No sequences needed resynchronization or no tables found."
        else:
            description = "**The following sequences have been successfully resynchronized:**\n"
            for seq, next_id in resynced_sequences.items():
                description += f"- `{seq}` restarted at **{next_id}**\n"

        embed = build_status_embed(
            title="✅ Database Sync Complete",
            description=description,
            color=0x27AE60
        )
        await send_response(interaction, embed=embed.build(), ephemeral=True)

        logger.info(f"Database sequences resynced by {interaction.user.display_name} ({interaction.user.id}).")

    except Exception as e:
        logger.error(f"An error occurred during database sequence resynchronization: {e}", exc_info=True)
        embed = build_status_embed(
            title="❌ Database Sync Failed",
            description=f"An unexpected error occurred. Please check the logs.\n`{e}`",
            color=0xE74C3C
        )
        await send_response(interaction, embed=embed.build(), ephemeral=True)