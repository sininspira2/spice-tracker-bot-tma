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
from utils.helpers import get_database, send_response, format_melange
from utils.logger import logger
from utils.permissions import check_permission


class Guild(app_commands.Group):
    """A command group for all guild-related commands."""
    def __init__(self, bot):
        super().__init__(name="guild", description="Manage guild settings and treasury")
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user has the required permissions for any command in this group."""
        if not check_permission(interaction, 'admin_or_officer'):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return False
        return True

    async def send_response(self, interaction, *args, **kwargs):
        """Helper to handle response sending."""
        if not interaction.response.is_done():
            await interaction.response.send_message(*args, **kwargs)
        else:
            await interaction.followup.send(*args, **kwargs)

    @app_commands.command(name="withdraw", description="Withdraw melange from guild treasury to give to a user.")
    @app_commands.describe(
        user="The user whose ledger to credit melange",
        amount="Amount of melange to credit from guild treasury"
    )
    async def withdraw(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Withdraw melange from guild treasury and give to a user."""
        command_start = time.time()
        await interaction.response.defer()

        try:
            # Validate amount
            if amount < 1:
                await self.send_response(interaction, "❌ Withdrawal amount must be at least 1 melange.", ephemeral=True)
                return

            db = get_database()

            # Get current guild treasury balance
            treasury_data, get_treasury_time = await timed_database_operation(
                "get_guild_treasury",
                db.get_guild_treasury
            )

            current_melange = treasury_data.get('total_melange', 0)
            if current_melange < amount:
                await self.send_response(interaction,
                    f"❌ Insufficient guild treasury funds.\n\n"
                    f"**Available:** {format_melange(current_melange)} melange\n"
                    f"**Requested:** {format_melange(amount)} melange\n"
                    f"**Shortfall:** {format_melange(amount - current_melange)} melange",
                    ephemeral=True)
                return

            # Perform withdrawal
            _, withdraw_time = await timed_database_operation(
                "guild_withdraw",
                db.guild_withdraw,
                str(interaction.user.id), interaction.user.display_name,
                str(user.id), user.display_name, amount
            )

            # Get updated treasury balance
            updated_treasury, _ = await timed_database_operation(
                "get_guild_treasury",
                db.get_guild_treasury
            )

            # Build response embed
            fields = {
                "💸 Transaction": f"**Recipient:** {user.display_name} | **Amount:** {format_melange(amount)} melange | **Admin:** {interaction.user.display_name}",
                "🏛️ Treasury": f"**Previous:** {format_melange(current_melange)} | **New:** {format_melange(updated_treasury.get('total_melange', 0))} | **Available:** {format_melange(updated_treasury.get('total_melange', 0))}"
            }

            embed = build_status_embed(
                title="✅ Guild Withdrawal Completed",
                description=f"💰 **{format_melange(amount)} melange** transferred from guild treasury to **{user.display_name}**",
                color=0x00FF00,
                fields=fields,
                timestamp=interaction.created_at
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
                admin_id=str(interaction.user.id),
                admin_username=interaction.user.display_name,
                target_user_id=str(user.id),
                target_username=user.display_name,
                get_treasury_time=f"{get_treasury_time:.3f}s",
                withdraw_time=f"{withdraw_time:.3f}s",
                response_time=f"{response_time:.3f}s",
                withdrawal_amount=amount,
                previous_balance=current_melange,
                new_balance=updated_treasury.get('total_melange', 0)
            )

            # Log the withdrawal for audit
            logger.info(f"Guild withdrawal: {format_melange(amount)} melange from treasury to {user.display_name} ({user.id}) by {interaction.user.display_name} ({interaction.user.id})")

        except ValueError as ve:
            # Handle insufficient funds or other validation errors
            await self.send_response(interaction, f"❌ {str(ve)}", ephemeral=True)

        except Exception as error:
            total_time = time.time() - command_start
            logger.error(f"Error in guild withdraw command: {error}",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        target_user_id=str(user.id),
                        target_username=user.display_name,
                        amount=amount,
                        total_time=f"{total_time:.3f}s")
            await self.send_response(interaction, "❌ An error occurred while processing the withdrawal.", ephemeral=True)

    @app_commands.command(name="treasury", description="View guild treasury balance and statistics.")
    async def treasury(self, interaction: discord.Interaction):
        """View guild treasury balance and statistics."""
        command_start = time.time()
        await interaction.response.defer()

        try:
            db = get_database()
            # Get guild treasury data
            treasury_data, get_treasury_time = await timed_database_operation(
                "get_guild_treasury",
                db.get_guild_treasury
            )

            # Get treasury melange (primary currency)
            total_melange = treasury_data.get('total_melange', 0)

            # Format timestamps
            last_updated = treasury_data.get('last_updated')
            updated_str = last_updated.strftime('%Y-%m-%d %H:%M UTC') if last_updated else 'Never'

            fields = {
                "💎 Melange": f"**{total_melange:,}** available",
                "📊 Updated": updated_str
            }

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
                title="🏛️ Treasury",
                description=f"💎 **{total_melange:,} melange** in treasury",
                color=color,
                fields=fields,
                timestamp=interaction.created_at
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
                total_melange=total_melange
            )

        except Exception as error:
            total_time = time.time() - command_start
            logger.error(f"Error in guild treasury command: {error}",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        total_time=f"{total_time:.3f}s")
            await self.send_response(interaction, "❌ An error occurred while fetching guild treasury data.", ephemeral=True)