"""
Backfill command for data migration tasks.
"""

# Command metadata
COMMAND_METADATA = {
    "aliases": [],
    "description": "Perform data backfill operations (admin only)",
    "permission_level": "admin",
}

import time
from utils.database_utils import timed_database_operation
from utils.embed_utils import build_status_embed
from utils.base_command import command
from utils.helpers import get_database, send_response
from sqlalchemy import select, update
from database_orm import Deposit


@command("backfill")
async def backfill(interaction, command_start, use_followup: bool = True):
    """Perform data backfill operations."""

    db = get_database()
    async with db._get_session() as session:
        # Find deposits that need backfill
        stmt = select(Deposit).where(Deposit.melange_amount.is_(None))
        result = await session.execute(stmt)
        deposits_to_update = result.scalars().all()

        if not deposits_to_update:
            await send_response(
                interaction,
                "✅ No deposits to backfill.",
                use_followup=use_followup,
                ephemeral=True,
            )
            return

        updated_count = 0
        default_conversion_rate = 50.0
        for deposit in deposits_to_update:
            melange_amount = deposit.sand_amount / default_conversion_rate
            update_stmt = (
                update(Deposit)
                .where(Deposit.id == deposit.id)
                .values(
                    melange_amount=melange_amount,
                    conversion_rate=default_conversion_rate,
                )
            )
            await session.execute(update_stmt)
            updated_count += 1

        await session.commit()

    embed = build_status_embed(
        title="📈 Backfill Complete",
        description=f"Updated **{updated_count}** deposit records with calculated melange amounts.",
        color=0x2ECC71,
    )
    await send_response(
        interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True
    )
