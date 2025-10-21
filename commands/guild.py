"""
Guild command group for managing guild-related commands.
"""

import time
import discord
from discord import app_commands

# Import utility modules
from utils.database_utils import timed_database_operation
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.helpers import get_database, format_melange
from utils.logger import logger
from utils.permissions import check_permission
from utils.pagination_utils import PaginatedView, build_paginated_embed


def format_transaction_item(transaction: dict) -> str:
    """Formats a single guild transaction item for display."""
    date_str = f"<t:{int(transaction['created_at'].timestamp())}:R>"

    if transaction["melange_amount"] > 0:
        amount_str = f"**{format_melange(transaction['melange_amount'])} melange**"
    else:
        amount_str = f"**{transaction['sand_amount']:,} sand**"

    type_str = transaction["transaction_type"].replace("_", " ").title()

    description = ""
    if transaction["transaction_type"] == "guild_cut":
        description = f"from expedition `{transaction['expedition_id']}`"
    elif transaction["transaction_type"] == "guild_withdraw":
        description = f"to **{transaction['target_username']}** by **{transaction['admin_username']}**"
    else:
        description = f"by **{transaction['admin_username']}**"

    return f"**{type_str}**: {amount_str} {description} - {date_str}"


async def build_transactions_embed(
    interaction: discord.Interaction,
    data: list[dict],
    current_page: int,
    total_pages: int,
    extra_data: dict | None = None,
) -> discord.Embed:
    """Builds the embed for guild transactions."""
    return await build_paginated_embed(
        interaction=interaction,
        data=data,
        current_page=current_page,
        total_pages=total_pages,
        title="🏛️ Guild Transaction History",
        no_results_message="No guild transactions found.",
        format_item_func=format_transaction_item,
        color=0x2ECC71,
    )


def format_payout_item(payout: dict) -> str:
    """Formats a single melange payout item for display."""
    date_str = f"<t:{int(payout['created_at'].timestamp())}:R>"
    amount_str = f"**{format_melange(payout['melange_amount'])} melange**"

    description = f"to **{payout['username']}**"
    if payout.get("admin_username"):
        description += f" by **{payout['admin_username']}**"

    return f"**Payout**: {amount_str} {description} - {date_str}"


async def build_payouts_embed(
    interaction: discord.Interaction,
    data: list[dict],
    current_page: int,
    total_pages: int,
    extra_data: dict | None = None,
) -> discord.Embed:
    """Builds the embed for melange payouts."""
    return await build_paginated_embed(
        interaction=interaction,
        data=data,
        current_page=current_page,
        total_pages=total_pages,
        title="💸 Melange Payout History",
        no_results_message="No melange payouts found.",
        format_item_func=format_payout_item,
        color=0xE67E22,
    )


class Guild(app_commands.Group):
    """A command group for all guild-related commands."""

    def __init__(self, bot):
        super().__init__(name="guild", description="Manage guild settings and treasury")
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user has the required permissions for any command in this group."""
        if not check_permission(interaction, "admin_or_officer"):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.", ephemeral=True
            )
            return False
        return True

    async def send_response(self, interaction, *args, **kwargs):
        """Helper to handle response sending."""
        if not interaction.response.is_done():
            await interaction.response.send_message(*args, **kwargs)
        else:
            await interaction.followup.send(*args, **kwargs)

    @app_commands.command(
        name="withdraw",
        description="Withdraw melange from guild treasury to give to a user.",
    )
    @app_commands.describe(
        user="The user whose ledger to credit melange",
        amount="Amount of melange to credit from guild treasury",
    )
    async def withdraw(
        self, interaction: discord.Interaction, user: discord.Member, amount: int
    ):
        """Withdraw melange from guild treasury and give to a user."""
        command_start = time.time()
        await interaction.response.defer()

        try:
            # Validate amount
            if amount < 1:
                await self.send_response(
                    interaction,
                    "❌ Withdrawal amount must be at least 1 melange.",
                    ephemeral=True,
                )
                return

            db = get_database()

            # Get current guild treasury balance
            treasury_data, get_treasury_time = await timed_database_operation(
                "get_guild_treasury", db.get_guild_treasury
            )

            current_melange = treasury_data.get("total_melange", 0)
            if current_melange < amount:
                await self.send_response(
                    interaction,
                    f"❌ Insufficient guild treasury funds.\n\n"
                    f"**Available:** {format_melange(current_melange)} melange\n"
                    f"**Requested:** {format_melange(amount)} melange\n"
                    f"**Shortfall:** {format_melange(amount - current_melange)} melange",
                    ephemeral=True,
                )
                return

            # Perform withdrawal and get new balance
            new_balance, withdraw_time = await timed_database_operation(
                "guild_withdraw",
                db.guild_withdraw,
                str(interaction.user.id),
                interaction.user.display_name,
                str(user.id),
                user.display_name,
                amount,
            )

            # Build response embed
            fields = {
                "💸 Transaction": f"**Recipient:** {user.display_name} | **Amount:** {format_melange(amount)} melange | **Admin:** {interaction.user.display_name}",
                "🏛️ Treasury": f"**Previous:** {format_melange(current_melange)} | **New:** {format_melange(new_balance)}",
            }

            embed = build_status_embed(
                title="✅ Guild Withdrawal Completed",
                description=f"💰 **{format_melange(amount)} melange** transferred from guild treasury to **{user.display_name}**",
                color=0x00FF00,
                fields=fields,
                timestamp=interaction.created_at,
            )

            # Send response
            response_start = time.time()
            await self.send_response(interaction, embed=embed.build())
            response_time = time.time() - response_start

            # Log metrics
            total_time = time.time() - command_start
            log_command_metrics(
                "Guild Withdraw",
                str(interaction.user.id),
                interaction.user.display_name,
                total_time,
                target_user_id=str(user.id),
                target_username=user.display_name,
                get_treasury_time=f"{get_treasury_time:.3f}s",
                withdraw_time=f"{withdraw_time:.3f}s",
                response_time=f"{response_time:.3f}s",
                withdrawal_amount=amount,
                previous_balance=current_melange,
                new_balance=new_balance,
            )

            # Log the withdrawal for audit
            logger.info(
                f"Guild withdrawal: {format_melange(amount)} melange from treasury to {user.display_name} ({user.id}) by {interaction.user.display_name} ({interaction.user.id})"
            )

        except ValueError as ve:
            # Handle insufficient funds or other validation errors
            await self.send_response(interaction, f"❌ {str(ve)}", ephemeral=True)

        except Exception as error:
            total_time = time.time() - command_start
            logger.error(
                f"Error in guild withdraw command: {error}",
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                target_user_id=str(user.id),
                target_username=user.display_name,
                amount=amount,
                total_time=f"{total_time:.3f}s",
            )
            await self.send_response(
                interaction,
                "❌ An error occurred while processing the withdrawal.",
                ephemeral=True,
            )

    @app_commands.command(
        name="treasury", description="View guild treasury balance and statistics."
    )
    async def treasury(self, interaction: discord.Interaction):
        """View guild treasury balance and statistics."""
        command_start = time.time()
        await interaction.response.defer()

        try:
            db = get_database()
            # Get guild treasury data
            treasury_data, get_treasury_time = await timed_database_operation(
                "get_guild_treasury", db.get_guild_treasury
            )

            # Get treasury melange (primary currency)
            total_melange = treasury_data.get("total_melange", 0)

            # Format timestamps
            last_updated = treasury_data.get("last_updated")
            updated_str = (
                last_updated.strftime("%Y-%m-%d %H:%M UTC") if last_updated else "Never"
            )

            # Determine color based on melange (primary currency)
            if total_melange >= 200:
                color = 0xFFD700  # Gold - very wealthy
            elif total_melange >= 100:
                color = 0x00FF00  # Green - healthy
            elif total_melange >= 50:
                color = 0xFFA500  # Orange - moderate
            else:
                color = 0xFF4500  # Red - low funds

            embed = build_status_embed(
                title="🏛️ Guild Treasury",
                description=f"The guild treasury currently holds **{total_melange:,} melange**.",
                color=color,
                fields={"📊 Last Updated": updated_str},
                timestamp=interaction.created_at,
            )

            # Send response
            response_start = time.time()
            await self.send_response(interaction, embed=embed.build())
            response_time = time.time() - response_start

            # Log metrics
            total_time = time.time() - command_start
            log_command_metrics(
                "Guild Treasury",
                str(interaction.user.id),
                interaction.user.display_name,
                total_time,
                get_treasury_time=f"{get_treasury_time:.3f}s",
                response_time=f"{response_time:.3f}s",
                total_melange=total_melange,
            )

        except Exception as error:
            total_time = time.time() - command_start
            logger.error(
                f"Error in guild treasury command: {error}",
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                total_time=f"{total_time:.3f}s",
            )
            await self.send_response(
                interaction,
                "❌ An error occurred while fetching guild treasury data.",
                ephemeral=True,
            )

    @app_commands.command(
        name="transactions", description="View the guild's transaction history."
    )
    async def transactions(self, interaction: discord.Interaction):
        """View the guild's transaction history."""
        command_start = time.time()
        await interaction.response.defer(ephemeral=True)

        db = get_database()

        try:
            total_transactions, count_time = await timed_database_operation(
                "get_guild_transactions_count", db.get_guild_transactions_count
            )

            if total_transactions == 0:
                embed = await build_transactions_embed(interaction, [], 1, 1)
                await self.send_response(interaction, embed=embed, ephemeral=True)
                return

            view = PaginatedView(
                interaction=interaction,
                total_items=total_transactions,
                fetch_data_func=db.get_guild_transactions_paginated,
                format_embed_func=build_transactions_embed,
            )

            initial_data, fetch_time = await timed_database_operation(
                "get_guild_transactions_paginated",
                db.get_guild_transactions_paginated,
                page=1,
            )

            embed = await build_transactions_embed(
                interaction, initial_data, 1, view.total_pages
            )
            await self.send_response(
                interaction, embed=embed, view=view, ephemeral=True
            )

            total_time = time.time() - command_start
            log_command_metrics(
                "Guild Transactions",
                str(interaction.user.id),
                interaction.user.display_name,
                total_time,
                count_time=f"{count_time:.3f}s",
                fetch_time=f"{fetch_time:.3f}s",
                result_count=total_transactions,
            )

        except Exception as error:
            total_time = time.time() - command_start
            logger.error(
                f"Error in guild transactions command: {error}",
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                total_time=f"{total_time:.3f}s",
            )
            await self.send_response(
                interaction,
                "❌ An error occurred while fetching guild transactions.",
                ephemeral=True,
            )

    @app_commands.command(
        name="payouts", description="View the guild's melange payout history."
    )
    async def payouts(self, interaction: discord.Interaction):
        """View the guild's melange payout history."""
        command_start = time.time()
        await interaction.response.defer(ephemeral=True)

        db = get_database()

        try:
            total_payouts, count_time = await timed_database_operation(
                "get_melange_payouts_count", db.get_melange_payouts_count
            )

            if total_payouts == 0:
                embed = await build_payouts_embed(interaction, [], 1, 1)
                await self.send_response(interaction, embed=embed, ephemeral=True)
                return

            view = PaginatedView(
                interaction=interaction,
                total_items=total_payouts,
                fetch_data_func=db.get_melange_payouts,
                format_embed_func=build_payouts_embed,
            )

            initial_data, fetch_time = await timed_database_operation(
                "get_melange_payouts", db.get_melange_payouts, page=1
            )

            embed = await build_payouts_embed(
                interaction, initial_data, 1, view.total_pages
            )
            await self.send_response(
                interaction, embed=embed, view=view, ephemeral=True
            )

            total_time = time.time() - command_start
            log_command_metrics(
                "Guild Payouts",
                str(interaction.user.id),
                interaction.user.display_name,
                total_time,
                count_time=f"{count_time:.3f}s",
                fetch_time=f"{fetch_time:.3f}s",
                result_count=total_payouts,
            )

        except Exception as error:
            total_time = time.time() - command_start
            logger.error(
                f"Error in guild payouts command: {error}",
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                total_time=f"{total_time:.3f}s",
            )
            await self.send_response(
                interaction,
                "❌ An error occurred while fetching melange payouts.",
                ephemeral=True,
            )
