"""
Settings command group for managing bot settings.
"""
import time
import discord
from discord import app_commands

# Import utility modules
from utils.database_utils import timed_database_operation
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.helpers import get_database, get_sand_per_melange_with_bonus, send_response as original_send_response, update_landsraad_bonus_status
from utils.logger import logger
from utils.permissions import check_permission

class Settings(app_commands.Group):
    """A command group for all settings-related commands."""
    def __init__(self, bot):
        super().__init__(name="settings", description="Manage bot settings")
        self.bot = bot

    async def send_response(self, interaction, *args, **kwargs):
        """Helper to handle response sending, since we are not using the @command decorator."""
        if not interaction.response.is_done():
            await interaction.response.send_message(*args, **kwargs)
        else:
            await interaction.followup.send(*args, **kwargs)

    @app_commands.command(name="landsraad", description="Manage the landsraad bonus for melange conversion")
    @app_commands.describe(
        action="Action to perform: 'status', 'enable', 'disable'",
        confirm="Confirmation required for enable/disable actions"
    )
    async def landsraad(self, interaction: discord.Interaction, action: str, confirm: bool = False):
        """Manage the landsraad bonus for melange conversion"""
        command_start = time.time()
        await interaction.response.defer(ephemeral=True)

        if not check_permission(interaction, 'admin_or_officer'):
            await self.send_response(interaction, "❌ You do not have permission to use this command.", ephemeral=True)
            return

        valid_actions = ['status', 'enable', 'disable']
        if action not in valid_actions:
            await self.send_response(interaction, f"❌ Invalid action. Use one of: {', '.join(valid_actions)}", ephemeral=True)
            return

        try:
            if action == 'status':
                is_active, get_status_time = await timed_database_operation(
                    "get_landsraad_bonus_status",
                    get_database().get_landsraad_bonus_status
                )
                conversion_rate = await get_sand_per_melange_with_bonus()
                status_text = "🟢 **ACTIVE**" if is_active else "🔴 **INACTIVE**"
                rate_text = f"{conversion_rate} sand = 1 melange"
                fields = {
                    "📊 Status": status_text,
                    "⚙️ Conversion Rate": rate_text,
                    "💡 Effect": "37.5 sand = 1 melange" if is_active else "50 sand = 1 melange"
                }
                color = 0x00FF00 if is_active else 0xFF4500
                embed = build_status_embed(
                    title="🏛️ Landsraad Bonus Status",
                    description=f"Current melange conversion rate: **{rate_text}**",
                    color=color,
                    fields=fields,
                    timestamp=interaction.created_at
                )
                await self.send_response(interaction, embed=embed.build())
                log_command_metrics(
                    "Landsraad Status", str(interaction.user.id), interaction.user.display_name, time.time() - command_start,
                    get_status_time=f"{get_status_time:.3f}s", is_active=is_active, conversion_rate=conversion_rate
                )

            elif action in ['enable', 'disable']:
                if not confirm:
                    action_text = "enable" if action == 'enable' else "disable"
                    await self.send_response(
                        interaction,
                        f"⚠️ **Confirmation required!**\n\n"
                        f"Use `/settings landsraad {action} confirm:true` to {action_text} the landsraad bonus.\n\n"
                        f"**Effect:** This will change the conversion rate.",
                        ephemeral=True
                    )
                    return

                new_status = action == 'enable'
                _, set_status_time = await timed_database_operation(
                    "set_landsraad_bonus_status",
                    get_database().set_landsraad_bonus_status,
                    new_status
                )
                update_landsraad_bonus_status(new_status)
                conversion_rate = await get_sand_per_melange_with_bonus()
                action_text = "enabled" if new_status else "disabled"
                status_text = "🟢 **ACTIVE**" if new_status else "🔴 **INACTIVE**"
                rate_text = f"{conversion_rate} sand = 1 melange"
                fields = {
                    "📊 Status": status_text,
                    "⚙️ Conversion Rate": rate_text,
                    "💡 Effect": "37.5 sand = 1 melange" if new_status else "50 sand = 1 melange"
                }
                color = 0x00FF00 if new_status else 0xFF4500
                embed = build_status_embed(
                    title=f"🏛️ Landsraad Bonus {action_text.title()}",
                    description=f"Melange conversion rate updated to: **{rate_text}**",
                    color=color,
                    fields=fields,
                    timestamp=interaction.created_at
                )
                await self.send_response(interaction, embed=embed.build())
                log_command_metrics(
                    f"Landsraad {action.title()}", str(interaction.user.id), interaction.user.display_name, time.time() - command_start,
                    set_status_time=f"{set_status_time:.3f}s", new_status=new_status, conversion_rate=conversion_rate
                )

        except Exception as error:
            logger.error(f"Error in settings landsraad command: {error}",
                        user_id=str(interaction.user.id),
                        username=interaction.user.display_name,
                        action=action,
                        total_time=f"{time.time() - command_start:.3f}s")
            await self.send_response(interaction, f"❌ An error occurred while managing landsraad bonus: {error}", ephemeral=True)