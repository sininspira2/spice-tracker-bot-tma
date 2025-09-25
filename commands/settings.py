"""
Settings command group for managing bot settings.
"""
import time
import discord
from discord import app_commands
from typing import Literal

# Import utility modules
from utils.database_utils import timed_database_operation
from utils.embed_utils import build_status_embed
from utils.command_utils import log_command_metrics
from utils.helpers import (
    get_database, get_sand_per_melange_with_bonus,
    send_response as original_send_response,
    update_landsraad_bonus_status,
    update_user_cut, get_user_cut,
    update_guild_cut, get_guild_cut,
    update_region, get_region
)
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
    async def landsraad(self, interaction: discord.Interaction, action: Literal['status', 'enable', 'disable'], confirm: bool = False):
        """Manage the landsraad bonus for melange conversion"""
        command_start = time.time()
        await interaction.response.defer(ephemeral=True)

        if not check_permission(interaction, 'admin_or_officer'):
            await self.send_response(interaction, "❌ You do not have permission to use this command.", ephemeral=True)
            return

        try:
            db = get_database()
            if action == 'status':
                landsraad_status_str, get_status_time = await timed_database_operation(
                    "get_global_setting",
                    db.get_global_setting,
                    'landsraad_bonus_active'
                )
                is_active = landsraad_status_str and landsraad_status_str.lower() == 'true'

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
                    "set_global_setting",
                    db.set_global_setting,
                    'landsraad_bonus_active',
                    str(new_status).lower(),
                    'Whether the landsraad bonus is active (37.5 sand = 1 melange instead of 50)'
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

    @app_commands.command(name="user_cut", description="Set or view the default user cut percentage for /split.")
    @app_commands.describe(value="The default percentage for each user in a split (0 to unset).")
    async def user_cut(self, interaction: discord.Interaction, value: app_commands.Range[int, 0, 100] = None):
        """Set or view the default user cut for /split."""
        command_start = time.time()
        await interaction.response.defer(ephemeral=True)

        if not check_permission(interaction, 'admin_or_officer'):
            await self.send_response(interaction, "❌ You do not have permission to use this command.", ephemeral=True)
            return

        db = get_database()

        if value is None:
            # View current setting
            current_value = get_user_cut()
            status_text = f"{current_value}%" if current_value is not None else "Not set (optional in /split)"
            embed = build_status_embed(
                title="⚙️ Default User Cut",
                description=f"Current default user cut is **{status_text}**.",
                color=0x3498DB
            )
            await self.send_response(interaction, embed=embed.build())
        else:
            # Set new value
            try:
                setting_value = str(value) if value != 0 else ""
                await db.set_global_setting('user_cut', setting_value, 'Default user cut for /split command')
                update_user_cut(value)

                status_text = f"{value}%" if value != 0 else "Unset"
                embed = build_status_embed(
                    title="✅ Default User Cut Updated",
                    description=f"Default user cut has been set to **{status_text}**.",
                    color=0x00FF00
                )
                await self.send_response(interaction, embed=embed.build())
                log_command_metrics("Settings UserCut", str(interaction.user.id), interaction.user.display_name, time.time() - command_start, new_value=value)
            except Exception as e:
                logger.error(f"Error setting user_cut: {e}", user_id=str(interaction.user.id))
                await self.send_response(interaction, f"❌ An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="guild_cut", description="Set or view the default guild cut percentage for /split.")
    @app_commands.describe(value="The default percentage for the guild in a split (0 for default 10%).")
    async def guild_cut(self, interaction: discord.Interaction, value: app_commands.Range[int, 0, 100] = None):
        """Set or view the default guild cut for /split."""
        command_start = time.time()
        await interaction.response.defer(ephemeral=True)

        if not check_permission(interaction, 'admin_or_officer'):
            await self.send_response(interaction, "❌ You do not have permission to use this command.", ephemeral=True)
            return

        db = get_database()

        if value is None:
            # View current setting
            current_value = get_guild_cut()
            embed = build_status_embed(
                title="⚙️ Default Guild Cut",
                description=f"Current default guild cut is **{current_value}%**.",
                color=0x3498DB
            )
            await self.send_response(interaction, embed=embed.build())
        else:
            # Set new value
            try:
                setting_value = str(value) if value != 0 else ""
                await db.set_global_setting('guild_cut', setting_value, 'Default guild cut for /split command')
                update_guild_cut(value)

                new_val_display = value if value != 0 else 10
                description = f"Default guild cut has been set to **{new_val_display}%**."
                fields = None
                if value == 0:
                    fields = {"ℹ️ Note": "A value of 0 unsets the global default, reverting to the bot's default of 10%."}

                embed = build_status_embed(
                    title="✅ Default Guild Cut Updated",
                    description=description,
                    color=0x00FF00,
                    fields=fields
                )
                await self.send_response(interaction, embed=embed.build())
                log_command_metrics("Settings GuildCut", str(interaction.user.id), interaction.user.display_name, time.time() - command_start, new_value=new_val_display)
            except Exception as e:
                logger.error(f"Error setting guild_cut: {e}", user_id=str(interaction.user.id))
                await self.send_response(interaction, f"❌ An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="region", description="Set or view the guild's primary region.")
    @app_commands.describe(region="The primary operational region.")
    @app_commands.choices(region=[
        app_commands.Choice(name="North America", value="na"),
        app_commands.Choice(name="Europe", value="eu"),
        app_commands.Choice(name="South America", value="sa"),
        app_commands.Choice(name="Asia", value="as"),
        app_commands.Choice(name="Oceania", value="oc"),
    ])
    async def region(self, interaction: discord.Interaction, region: app_commands.Choice[str] = None):
        """Set or view the guild's region."""
        command_start = time.time()
        await interaction.response.defer(ephemeral=True)

        if not check_permission(interaction, 'admin_or_officer'):
            await self.send_response(interaction, "❌ You do not have permission to use this command.", ephemeral=True)
            return

        db = get_database()

        # Mapping for display
        region_map = {
            "na": "North America", "eu": "Europe", "sa": "South America",
            "as": "Asia", "oc": "Oceania"
        }

        if region is None:
            # View current setting
            current_value_code = get_region()
            current_value_name = region_map.get(current_value_code, "Not set")
            embed = build_status_embed(
                title="🌍 Guild Region",
                description=f"Current guild region is **{current_value_name}**.",
                color=0x3498DB
            )
            await self.send_response(interaction, embed=embed.build())
        else:
            # Set new value
            try:
                await db.set_global_setting('region', region.value, 'Primary guild region')
                update_region(region.value)

                embed = build_status_embed(
                    title="✅ Guild Region Updated",
                    description=f"Guild region has been set to **{region.name}**.",
                    color=0x00FF00
                )
                await self.send_response(interaction, embed=embed.build())
                log_command_metrics("Settings Region", str(interaction.user.id), interaction.user.display_name, time.time() - command_start, new_value=region.value)
            except Exception as e:
                logger.error(f"Error setting region: {e}", user_id=str(interaction.user.id))
                await self.send_response(interaction, f"❌ An error occurred: {e}", ephemeral=True)