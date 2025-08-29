import discord
from discord.ext import commands
import os
import time
from dotenv import load_dotenv
from database import Database
from utils.embed_builder import EmbedBuilder
from utils.logger import logger

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = False
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database
database = Database()

# Register commands with the bot's command tree
def register_commands():
    """Register all decorated commands with the bot's command tree"""
    
    # Command definitions with aliases
    # Structure: 'command_name': {
    #     'aliases': ['alias1', 'alias2'],  # List of alternative names
    #     'description': "Command description",
    #     'params': {'param_name': "Parameter description"},  # Optional - only if command has parameters
    #     'function': function_name  # The actual function to call
    # }
    commands = {
        'harvest': {
            'aliases': ['sand'],
            'description': "Log spice sand harvests and calculate melange conversion",
            'params': {'amount': "Amount of spice sand harvested"},
            'function': harvest
        },
        'refinery': {
            'aliases': ['status'],
            'description': "View your spice refinery statistics and progress",
            'function': refinery
        },
        'leaderboard': {
            'aliases': ['top'],
            'description': "Display top spice refiners by melange production",
            'params': {'limit': "Number of top refiners to display (default: 10)"},
            'function': leaderboard
        },
        'conversion': {
            'aliases': ['rate'],
            'description': "Set the spice sand to melange conversion rate (Admin only)",
            'params': {'sand_per_melange': "Amount of spice sand required for 1 melange"},
            'function': conversion
        },
        'split': {
            'aliases': [],
            'description': "Split harvested spice sand among expedition members",
            'params': {
                'total_sand': "Total spice sand collected to split",
                'participants': "Number of expedition members participating",
                'harvester_percentage': "Percentage for primary harvester (default: uses environment variable)"
            },
            'function': split
        },
        'help': {
            'aliases': ['commands'],
            'description': "Show all available spice tracking commands",
            'function': help_command
        },
        'reset': {
            'aliases': [],
            'description': "Reset all spice refinery statistics (Admin only - USE WITH CAUTION)",
            'params': {'confirm': "Confirm that you want to delete all refinery data"},
            'function': reset
        },
        'ledger': {
            'aliases': ['deposits'],
            'description': "View your complete spice harvest ledger",
            'function': ledger
        },
        'payment': {
            'aliases': ['pay'],
            'description': "Process payment for a harvester's deposits (Admin only)",
            'params': {'user': "Harvester to pay"},
            'function': payment
        },
        'payroll': {
            'aliases': ['payall'],
            'description': "Process payments for all unpaid harvesters (Admin only)",
            'function': payroll
        }
    }
    
    # Register all commands and their aliases
    # This loop automatically creates slash commands for both main names and aliases
    # Each command points to the same underlying function, so behavior is identical
    for command_name, command_data in commands.items():
        # Create a closure to capture the current command_data
        def create_command_wrapper(cmd_data):
            if 'params' in cmd_data:
                # Command with parameters
                @bot.tree.command(name=command_name, description=cmd_data['description'])
                async def wrapper(interaction: discord.Interaction, **kwargs):
                    await cmd_data['function'](interaction, **kwargs)
                
                # Add parameter descriptions
                for param_name, param_desc in cmd_data['params'].items():
                    wrapper = discord.app_commands.describe(**{param_name: param_desc})(wrapper)
                return wrapper
            else:
                # Command without parameters
                @bot.tree.command(name=command_name, description=cmd_data['description'])
                async def wrapper(interaction: discord.Interaction):
                    await cmd_data['function'](interaction)
                return wrapper
        
        # Register main command
        main_cmd = create_command_wrapper(command_data)
        
        # Register aliases
        for alias in command_data['aliases']:
            def create_alias_wrapper(cmd_data, alias_name):
                if 'params' in cmd_data:
                    # Alias with parameters
                    @bot.tree.command(name=alias_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction, **kwargs):
                        await cmd_data['function'](interaction, **kwargs)
                    
                    # Add parameter descriptions
                    for param_name, param_desc in cmd_data['params'].items():
                        wrapper = discord.app_commands.describe(**{param_name: param_desc})(wrapper)
                    return wrapper
                else:
                    # Alias without parameters
                    @bot.tree.command(name=alias_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction):
                        await cmd_data['function'](interaction)
                    return wrapper
            
            alias_cmd = create_alias_wrapper(command_data, alias)

@bot.event
async def on_ready():
    if bot.user:
        logger.bot_event("Bot started", bot_name=bot.user.name, bot_id=str(bot.user.id), guild_count=len(bot.guilds))
        print(f'{bot.user.name}#{bot.user.discriminator} is online!')
    else:
        logger.bot_event("Bot started", bot_name="Unknown")
        print('Bot is online!')
    
    # Initialize database
    try:
        await database.initialize()
        logger.bot_event("initialize", "database", True)
        print('Database initialized successfully.')
        
        # Clean up old deposits (older than 30 days)
        try:
            cleaned_count = await database.cleanup_old_deposits(30)
            if cleaned_count > 0:
                logger.bot_event("cleanup", "old_deposits", True, cleaned_count=cleaned_count)
                print(f'Cleaned up {cleaned_count} old paid deposits.')
        except Exception as cleanup_error:
            logger.bot_event("cleanup", "old_deposits", False, error=str(cleanup_error))
            print(f'Failed to clean up old deposits: {cleanup_error}')
            
    except Exception as error:
        logger.bot_event("initialize", "database", False, error=str(error))
        print(f'Failed to initialize database: {error}')
        return
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.bot_event("Commands synced", synced_count=len(synced))
        print(f'Synced {len(synced)} commands.')
    except Exception as error:
        logger.bot_event("Command sync failed", error=str(error))
        print(f'Failed to sync commands: {error}')

async def harvest(interaction: discord.Interaction, amount: int):
    """Log spice sand harvests and calculate melange conversion"""
    # Validate amount
    if not 1 <= amount <= 10000:
        await interaction.response.send_message("❌ Amount must be between 1 and 10,000 spice sand.", ephemeral=True)
        return
    
    try:
        # Get conversion rate and add deposit
        sand_per_melange = int(await database.get_setting('sand_per_melange') or 50)
        await database.add_deposit(str(interaction.user.id), interaction.user.display_name, amount)
        
        # Get user data and calculate totals
        user = await database.get_user(str(interaction.user.id))
        total_sand = await database.get_user_total_sand(str(interaction.user.id))
        
        # Calculate melange conversion
        total_melange_earned = total_sand // sand_per_melange
        current_melange = user['total_melange'] or 0
        new_melange = total_melange_earned - current_melange
        
        if new_melange > 0:
            await database.update_user_melange(str(interaction.user.id), new_melange)
        
        # Build response
        remaining_sand = total_sand % sand_per_melange
        sand_needed = sand_per_melange - remaining_sand
        
        embed = (EmbedBuilder("🏜️ Spice Harvest Logged", color=0xE67E22, timestamp=interaction.created_at)
                 .add_field("📊 Harvest Summary", f"**Spice Sand Harvested:** {amount:,}\n**Total Unpaid Harvest:** {total_sand:,}")
                 .add_field("✨ Melange Production", f"**Total Melange:** {(current_melange + new_melange):,}\n**Conversion Rate:** {sand_per_melange} sand = 1 melange")
                 .add_field("🎯 Next Refinement", f"**Sand Until Next Melange:** {sand_needed:,}", inline=False)
                 .set_footer(f"Harvested by {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        if new_melange > 0:
            embed.set_description(f"🎉 **You produced {new_melange:,} melange from this harvest!**")
        
        await interaction.response.send_message(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in harvest command: {error}")
        await interaction.response.send_message("❌ An error occurred while processing your harvest.", ephemeral=True)

async def refinery(interaction: discord.Interaction):
    """Show your total sand and melange statistics"""
    try:
        user = await database.get_user(str(interaction.user.id))
        total_sand = await database.get_user_total_sand(str(interaction.user.id))
        paid_sand = await database.get_user_paid_sand(str(interaction.user.id))
        
        if not user and total_sand == 0:
            embed = (EmbedBuilder("🏭 Spice Refinery Status", color=0x95A5A6, timestamp=interaction.created_at)
                     .set_description("🏜️ You haven't harvested any spice sand yet! Use `/harvest` to start tracking your harvests.")
                     .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return
        
        # Calculate progress
        sand_per_melange = int(await database.get_setting('sand_per_melange') or 50)
        remaining_sand = total_sand % sand_per_melange
        sand_needed = sand_per_melange - remaining_sand if total_sand > 0 else sand_per_melange
        progress_percent = int((remaining_sand / sand_per_melange) * 100) if total_sand > 0 else 0
        
        # Create progress bar
        progress_bar_length = 10
        filled_bars = int((remaining_sand / sand_per_melange) * progress_bar_length) if total_sand > 0 else 0
        progress_bar = '▓' * filled_bars + '░' * (progress_bar_length - filled_bars)
        
        embed = (EmbedBuilder("🏭 Spice Refinery Status", color=0x3498DB, timestamp=interaction.created_at)
                 .add_thumbnail(interaction.user.display_avatar.url)
                 .add_field("🏜️ Harvest Summary", f"**Unpaid Harvest:** {total_sand:,}\n**Paid Harvest:** {paid_sand:,}")
                 .add_field("✨ Melange Production", f"**Total Melange:** {user['total_melange'] if user else 0:,}")
                 .add_field("⚙️ Refinement Rate", f"{sand_per_melange} sand = 1 melange")
                 .add_field("🎯 Refinement Progress", f"{progress_bar} {progress_percent}%\n**Sand Needed:** {sand_needed:,}", inline=False)
                 .add_field("📅 Last Activity", f"<t:{int(user['last_updated'].timestamp()) if user else interaction.created_at.timestamp()}:F>", inline=False)
                 .set_footer(f"Spice Refinery • {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.response.send_message(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in refinery command: {error}")
        await interaction.response.send_message("❌ An error occurred while fetching your refinery status.", ephemeral=True)

async def leaderboard(interaction: discord.Interaction, limit: int = 10):
    """Display top refiners by melange earned"""
    try:
        # Validate limit
        if not 5 <= limit <= 25:
            await interaction.response.send_message("❌ Limit must be between 5 and 25.", ephemeral=True)
            return
        
        leaderboard_data = await database.get_leaderboard(limit)
        
        if not leaderboard_data:
            embed = EmbedBuilder("🏆 Spice Refinery Rankings", color=0x95A5A6, timestamp=interaction.created_at)
            embed.set_description("🏜️ No refiners found yet! Be the first to start harvesting spice sand with `/harvest`.")
            await interaction.response.send_message(embed=embed.build())
            return
        
        # Get conversion rate and build leaderboard
        sand_per_melange = int(await database.get_setting('sand_per_melange') or 50)
        medals = ['🥇', '🥈', '🥉']
        
        leaderboard_text = ""
        for index, user in enumerate(leaderboard_data):
            position = index + 1
            medal = medals[index] if index < 3 else f"**{position}.**"
            leaderboard_text += f"{medal} **{user['username']}**\n"
            leaderboard_text += f"├ Melange: {user['total_melange']:,}\n"
            leaderboard_text += f"└ Sand: {user['total_sand']:,}\n\n"
        
        # Calculate totals
        total_melange = sum(user['total_melange'] for user in leaderboard_data)
        total_sand = sum(user['total_sand'] for user in leaderboard_data)
        
        embed = (EmbedBuilder("🏆 Spice Refinery Rankings", description=leaderboard_text, color=0xF39C12, timestamp=interaction.created_at)
                 .add_field("📊 Guild Statistics", f"**Total Refiners:** {len(leaderboard_data)}\n**Total Melange:** {total_melange:,}\n**Total Harvest:** {total_sand:,}")
                 .add_field("⚙️ Refinement Rate", f"{sand_per_melange} sand = 1 melange")
                 .set_footer(f"Showing top {len(leaderboard_data)} refiners • Updated", bot.user.display_avatar.url if bot.user else None))
        
        await interaction.response.send_message(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in leaderboard command: {error}")
        await interaction.response.send_message("❌ An error occurred while fetching the leaderboard.", ephemeral=True)

async def conversion(interaction: discord.Interaction, sand_per_melange: int):
    """Set the spice sand to melange conversion rate (Admin only)"""
    try:
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        # Validate input
        if not 1 <= sand_per_melange <= 1000:
            await interaction.response.send_message("❌ Conversion rate must be between 1 and 1,000.", ephemeral=True)
            return
        
        # Get current rate and update
        current_rate = int(await database.get_setting('sand_per_melange') or 50)
        await database.set_setting('sand_per_melange', str(sand_per_melange))
        
        embed = (EmbedBuilder("⚙️ Refinement Rate Updated", color=0x27AE60, timestamp=interaction.created_at)
                 .add_field("📊 Rate Change", f"**Previous Rate:** {current_rate} sand = 1 melange\n**New Rate:** {sand_per_melange} sand = 1 melange", inline=False)
                 .add_field("⚠️ Important Note", "This change affects future calculations only. Existing refinery data remains unchanged.", inline=False)
                 .set_footer(f"Changed by {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.response.send_message(embed=embed.build())
        print(f'Refinement rate changed from {current_rate} to {sand_per_melange} by {interaction.user.display_name} ({interaction.user.id})')
        
    except Exception as error:
        logger.error(f"Error in conversion command: {error}")
        await interaction.response.send_message("❌ An error occurred while updating the refinement rate.", ephemeral=True)

async def split(interaction: discord.Interaction, total_sand: int, participants: int, harvester_percentage: float = None):
    """Split harvested spice sand among expedition members"""
    try:
        # Use environment variable if no harvester_percentage provided
        if harvester_percentage is None:
            harvester_percentage = float(os.getenv('DEFAULT_HARVESTER_PERCENTAGE', 25.0))
        
        # Validate inputs
        if total_sand < 1:
            await interaction.response.send_message("❌ Total spice sand must be at least 1.", ephemeral=True)
            return
        if participants < 1:
            await interaction.response.send_message("❌ Number of expedition members must be at least 1.", ephemeral=True)
            return
        if not 0 <= harvester_percentage <= 100:
            await interaction.response.send_message("❌ Primary harvester percentage must be between 0 and 100.", ephemeral=True)
            return
        
        # Calculate splits
        sand_per_melange = int(await database.get_setting('sand_per_melange') or 50)
        harvester_sand = int(total_sand * (harvester_percentage / 100))
        remaining_sand = total_sand - harvester_sand
        
        harvester_melange = harvester_sand // sand_per_melange
        harvester_leftover_sand = harvester_sand % sand_per_melange
        
        sand_per_participant = remaining_sand // participants
        melange_per_participant = sand_per_participant // sand_per_melange
        leftover_sand_per_participant = sand_per_participant % sand_per_melange
        
        total_distributed = sand_per_participant * participants
        remainder_sand = remaining_sand - total_distributed
        
        embed = (EmbedBuilder("🏜️ Expedition Split Operation", 
                              description=f"**Total Spice Sand:** {total_sand:,}\n**Expedition Members:** {participants}\n**Primary Harvester Cut:** {harvester_percentage}%",
                              color=0xF39C12, timestamp=interaction.created_at)
                 .add_field("🏭 Primary Harvester Share", f"**Sand:** {harvester_sand:,}\n**Melange:** {harvester_melange:,}\n**Leftover Sand:** {harvester_leftover_sand:,}")
                 .add_field("👥 Each Expedition Member Gets", f"**Sand:** {sand_per_participant:,}\n**Melange:** {melange_per_participant:,}\n**Leftover Sand:** {leftover_sand_per_participant:,}")
                 .add_field("📊 Split Summary", f"**Expedition Pool:** {remaining_sand:,} sand\n**Total Distributed:** {total_distributed:,} sand\n**Remainder:** {remainder_sand:,} sand", inline=False)
                 .set_footer(f"Split initiated by {interaction.user.display_name} • Refinement: {sand_per_melange} sand = 1 melange", interaction.user.display_avatar.url))
        
        await interaction.response.send_message(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in split command: {error}")
        await interaction.response.send_message("❌ An error occurred while calculating the expedition split.", ephemeral=True)

async def help_command(interaction: discord.Interaction):
    """Show all available commands and their descriptions"""
    try:
        sand_per_melange = int(await database.get_setting('sand_per_melange') or 50)
        
        embed = (EmbedBuilder("🏜️ Spice Refinery Commands", 
                              description="Track your spice sand harvests and melange production in the Dune: Awakening universe!",
                              color=0xF39C12, timestamp=interaction.created_at)
                 .add_field("📊 Harvester Commands", 
                           "**`/harvest [amount]`**\nLog spice sand harvests (1-10,000). Automatically converts to melange.\n\n"
                           "**`/refinery`**\nView your refinery statistics and melange production progress.\n\n"
                           "**`/ledger`**\nView your complete harvest ledger with payment status.\n\n"
                           "**`/leaderboard [limit]`**\nShow top refiners by melange production (5-25 users).\n\n"
                           "**`/split [total_sand] [harvester_%]`**\nSplit harvested spice among expedition members. Harvester % is optional.\n\n"
                           "**`/help`**\nDisplay this help message with all commands.", inline=False)
                 .add_field("⚙️ Guild Admin Commands", 
                           "**`/conversion [sand_per_melange]`**\nSet refinement rate (1-1,000 sand per melange).\n\n"
                           "**`/payment [user]`**\nProcess payment for a harvester's deposits.\n\n"
                           "**`/payroll`**\nProcess payments for all unpaid harvesters.\n\n"
                           "**`/reset confirm:True`**\nReset all refinery statistics (requires confirmation).", inline=False)
                 .add_field("📋 Current Settings", f"**Refinement Rate:** {sand_per_melange} sand = 1 melange\n**Default Harvester %:** {os.getenv('DEFAULT_HARVESTER_PERCENTAGE', '25.0')}%", inline=False)
                 .add_field("💡 Example Usage", 
                           "• `/harvest 250` or `/sand 250` - Harvest 250 spice sand\n"
                           "• `/refinery` or `/status` - Check your refinery status\n"
                           "• `/ledger` or `/deposits` - View your harvest ledger\n"
                           "• `/leaderboard 15` or `/top 15` - Show top 15 refiners\n"
                           "• `/payment @username` or `/pay @username` - Pay a specific harvester\n"
                           "• `/payroll` or `/payall` - Pay all harvesters at once\n"
                           "• `/split 1000 30` - Split 1000 sand, 30% to primary harvester\n"
                           "• `/split 1000` - Split 1000 sand using default harvester %", inline=False)
                 .add_field("🔄 Command Aliases", 
                           "**Harvest:** `/harvest` = `/sand`\n"
                           "**Status:** `/refinery` = `/status`\n"
                           "**Ledger:** `/ledger` = `/deposits`\n"
                           "**Leaderboard:** `/leaderboard` = `/top`\n"
                           "**Help:** `/help` = `/commands`\n"
                           "**Conversion:** `/conversion` = `/rate`\n"
                           "**Payment:** `/payment` = `/pay`\n"
                           "**Payroll:** `/payroll` = `/payall`", inline=False)
                 .set_footer("Spice Refinery Bot - Dune: Awakening Guild Resource Tracker", bot.user.display_avatar.url if bot.user else None))
        
        await interaction.response.send_message(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in help command: {error}")
        await interaction.response.send_message("❌ An error occurred while displaying help.", ephemeral=True)

async def reset(interaction: discord.Interaction, confirm: bool):
    """Reset all spice refinery statistics (Admin only - USE WITH CAUTION)"""
    try:
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        if not confirm:
            embed = (EmbedBuilder("⚠️ Reset Cancelled", color=0xE74C3C)
                     .set_description("You must set the `confirm` parameter to `True` to proceed with the reset.")
                     .add_field("🔄 How to Reset", "Use `/reset confirm:True` to confirm the reset.", inline=False))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return
        
        # Reset all refinery statistics
        deleted_rows = await database.reset_all_stats()
        
        embed = (EmbedBuilder("🔄 Refinery Reset Complete", 
                              description="⚠️ **All refinery statistics have been permanently deleted!**",
                              color=0xE74C3C, timestamp=interaction.created_at)
                 .add_field("📊 Reset Summary", f"**Users Affected:** {deleted_rows}\n**Data Cleared:** All harvest records and melange production", inline=False)
                 .add_field("✅ What Remains", "Refinement rates and bot settings are preserved.", inline=False)
                 .set_footer(f"Reset performed by {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.response.send_message(embed=embed.build())
        print(f'All refinery statistics reset by {interaction.user.display_name} ({interaction.user.id}) - {deleted_rows} records deleted')
        
    except Exception as error:
        logger.error(f"Error in reset command: {error}")
        await interaction.response.send_message("❌ An error occurred while resetting refinery statistics.", ephemeral=True)

async def ledger(interaction: discord.Interaction):
    """View your complete spice harvest ledger"""
    try:
        deposits_data = await database.get_user_deposits(str(interaction.user.id))
        
        if not deposits_data:
            embed = (EmbedBuilder("📋 Spice Harvest Ledger", color=0x95A5A6, timestamp=interaction.created_at)
                     .set_description("🏜️ You haven't harvested any spice sand yet! Use `/harvest` to start tracking your harvests.")
                     .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
            await interaction.response.send_message(embed=embed.build(), ephemeral=True)
            return
        
        # Build harvest ledger
        ledger_text = ""
        total_unpaid = 0
        total_paid = 0
        
        for deposit in deposits_data:
            status = "✅ Paid" if deposit['paid'] else "⏳ Unpaid"
            date_str = f"<t:{int(deposit['created_at'].timestamp())}:R>"
            ledger_text += f"**{deposit['sand_amount']:,} spice sand** - {status} - {date_str}\n"
            
            if deposit['paid']:
                total_paid += deposit['sand_amount']
            else:
                total_unpaid += deposit['sand_amount']
        
        embed = (EmbedBuilder("📋 Spice Harvest Ledger", description=ledger_text, color=0x3498DB, timestamp=interaction.created_at)
                 .add_thumbnail(interaction.user.display_avatar.url)
                 .add_field("💰 Payment Summary", f"**Unpaid Harvest:** {total_unpaid:,} sand\n**Paid Harvest:** {total_paid:,} sand\n**Total Harvests:** {len(deposits_data)}", inline=False)
                 .set_footer(f"Spice Refinery • {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.response.send_message(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in ledger command: {error}")
        await interaction.response.send_message("❌ An error occurred while fetching your harvest ledger.", ephemeral=True)

async def payment(interaction: discord.Interaction, user: discord.Member):
    """Process payment for a harvester's deposits (Admin only)"""
    try:
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        # Get user's unpaid deposits
        unpaid_deposits = await database.get_user_deposits(str(user.id), include_paid=False)
        
        if not unpaid_deposits:
            embed = (EmbedBuilder("💰 Payment Status", color=0x95A5A6, timestamp=interaction.created_at)
                     .set_description(f"🏜️ **{user.display_name}** has no unpaid harvests to process.")
                     .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
            await interaction.response.send_message(embed=embed.build())
            return
        
        # Mark all deposits as paid
        await database.mark_all_user_deposits_paid(str(user.id))
        
        total_paid = sum(deposit['sand_amount'] for deposit in unpaid_deposits)
        
        embed = (EmbedBuilder("💰 Payment Processed", color=0x27AE60, timestamp=interaction.created_at)
                 .set_description(f"✅ **{user.display_name}** has been paid for all harvests!")
                 .add_field("📊 Payment Summary", f"**Total Spice Sand Paid:** {total_paid:,}\n**Harvests Processed:** {len(unpaid_deposits)}", inline=False)
                 .set_footer(f"Payment processed by {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.response.send_message(embed=embed.build())
        print(f'Harvester {user.display_name} ({user.id}) paid {total_paid:,} spice sand by {interaction.user.display_name} ({interaction.user.id})')
        
    except Exception as error:
        logger.error(f"Error in payment command: {error}")
        await interaction.response.send_message("❌ An error occurred while processing the payment.", ephemeral=True)

async def payroll(interaction: discord.Interaction):
    """Process payments for all unpaid harvesters (Admin only)"""
    try:
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        # Get all unpaid deposits
        unpaid_deposits = await database.get_all_unpaid_deposits()
        
        if not unpaid_deposits:
            embed = (EmbedBuilder("💰 Payroll Status", color=0x95A5A6, timestamp=interaction.created_at)
                     .set_description("🏜️ There are no unpaid harvests to process.")
                     .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
            await interaction.response.send_message(embed=embed.build())
            return
        
        # Group deposits by user
        user_deposits = {}
        for deposit in unpaid_deposits:
            user_id = deposit['user_id']
            if user_id not in user_deposits:
                user_deposits[user_id] = []
            user_deposits[user_id].append(deposit)
        
        # Mark all deposits as paid
        total_paid = 0
        users_paid = 0
        
        for user_id, deposits_list in user_deposits.items():
            await database.mark_all_user_deposits_paid(user_id)
            user_total = sum(deposit['sand_amount'] for deposit in deposits_list)
            total_paid += user_total
            users_paid += 1
        
        embed = (EmbedBuilder("💰 Guild Payroll Complete", color=0x27AE60, timestamp=interaction.created_at)
                 .set_description("✅ **All harvesters have been paid for their harvests!**")
                 .add_field("📊 Payroll Summary", f"**Total Spice Sand Paid:** {total_paid:,}\n**Harvesters Paid:** {users_paid}\n**Total Harvests:** {len(unpaid_deposits)}", inline=False)
                 .set_footer(f"Guild payroll processed by {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.response.send_message(embed=embed.build())
        print(f'Guild payroll of {total_paid:,} spice sand to {users_paid} harvesters by {interaction.user.display_name} ({interaction.user.id})')
        
    except Exception as error:
        logger.error(f"Error in payroll command: {error}")
        await interaction.response.send_message("❌ An error occurred while processing the guild payroll.", ephemeral=True)

# Register all commands with the bot's command tree
register_commands()

# Error handling
@bot.event
async def on_command_error(ctx, error):
    logger.error(f"Command error: {error}", event_type="command_error", 
                 command=ctx.command.name if ctx.command else "unknown",
                 user_id=str(ctx.author.id) if ctx.author else "unknown",
                 username=ctx.author.display_name if ctx.author else "unknown",
                 error=str(error))
    print(f'Command error: {error}')

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Discord event error: {event}", event_type="discord_error",
                 event=event, args=str(args), kwargs=str(kwargs))
    print(f'Discord event error: {event}')

# Railway health check endpoint
import http.server
import socketserver
import threading

def start_health_server():
    """Start a simple HTTP server for Railway health checks"""
    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass  # Suppress HTTP server logs
    
    try:
        port = int(os.getenv('PORT', 8080))
        with socketserver.TCPServer(("", port), HealthHandler) as httpd:
            logger.bot_event("Health server started", port=port)
            print(f"Health check server started on port {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.error("Health server failed to start", error=str(e))
        print(f"Health server failed to start: {e}")

# Run the bot
if __name__ == '__main__':
    # Start health check server in a separate thread for Railway
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set")
        print("❌ ERROR: DISCORD_TOKEN environment variable is not set!")
        print("Please set the DISCORD_TOKEN environment variable in Railway or your .env file")
        exit(1)
    
    logger.bot_event("Bot starting", has_token=bool(token))
    print("Starting Discord bot...")
    bot.run(token)