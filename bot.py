import discord
from discord.ext import commands
import os
import time
import datetime
from dotenv import load_dotenv
from database import Database
from utils.embed_builder import EmbedBuilder
from utils.logger import logger

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
# For slash commands, we don't need message_content intent
intents.message_content = False
intents.reactions = True
intents.guilds = True
intents.guild_messages = True
# Note: command_prefix is set but not used since we're using slash commands
# The prefix commands are kept for potential future use or debugging
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database (lazy initialization)
database = None

def get_database():
    """Get or create database instance"""
    global database
    if database is None:
        database = Database()
    return database

def get_sand_per_melange() -> int:
    """Get the spice sand to melange conversion rate from environment variables"""
    return int(os.getenv('SAND_PER_MELANGE', '50'))

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
            'description': "View the current spice sand to melange conversion rate",
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
        # Create a closure to capture the current command_data and command_name
        def create_command_wrapper(cmd_data, cmd_name):
            if 'params' in cmd_data:
                # Command with parameters - we need to create specific parameter types
                if cmd_name == 'harvest':
                    @bot.tree.command(name=command_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction, amount: int):
                        await cmd_data['function'](interaction, amount)
                elif cmd_name == 'leaderboard':
                    @bot.tree.command(name=command_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction, limit: int = 10):
                        await cmd_data['function'](interaction, limit)
                elif cmd_name == 'conversion':
                    @bot.tree.command(name=command_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction):
                        await cmd_data['function'](interaction)
                elif cmd_name == 'split':
                    @bot.tree.command(name=command_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction, total_sand: int, participants: int, harvester_percentage: float = None):
                        await cmd_data['function'](interaction, total_sand, participants, harvester_percentage)
                elif cmd_name == 'reset':
                    @bot.tree.command(name=command_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction, confirm: bool):
                        await cmd_data['function'](interaction, confirm)
                elif cmd_name == 'payment':
                    @bot.tree.command(name=command_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction, user: discord.Member):
                        await cmd_data['function'](interaction, user)
                else:
                    # Generic fallback for other commands
                    @bot.tree.command(name=command_name, description=cmd_data['description'])
                    async def wrapper(interaction: discord.Interaction):
                        await cmd_data['function'](interaction)
                
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
        main_cmd = create_command_wrapper(command_data, command_name)
        print(f"Registered command: {command_name}")
        
        # Register aliases
        for alias in command_data['aliases']:
            def create_alias_wrapper(cmd_data, alias_name):
                if 'params' in cmd_data:
                    # Alias with parameters - we need to create specific parameter types
                    if 'amount' in cmd_data['params']:  # harvest/sand
                        @bot.tree.command(name=alias_name, description=cmd_data['description'])
                        async def wrapper(interaction: discord.Interaction, amount: int):
                            await cmd_data['function'](interaction, amount)
                    elif 'limit' in cmd_data['params']:  # leaderboard/top
                        @bot.tree.command(name=alias_name, description=cmd_data['description'])
                        async def wrapper(interaction: discord.Interaction, limit: int = 10):
                            await cmd_data['function'](interaction, limit)
                    elif 'sand_per_melange' in cmd_data['params']:  # conversion/rate
                        @bot.tree.command(name=alias_name, description=cmd_data['description'])
                        async def wrapper(interaction: discord.Interaction):
                            await cmd_data['function'](interaction)
                    elif 'total_sand' in cmd_data['params']:  # split
                        @bot.tree.command(name=alias_name, description=cmd_data['description'])
                        async def wrapper(interaction: discord.Interaction, total_sand: int, participants: int, harvester_percentage: float = None):
                            await cmd_data['function'](interaction, total_sand, participants, harvester_percentage)
                    elif 'confirm' in cmd_data['params']:  # reset
                        @bot.tree.command(name=alias_name, description=cmd_data['description'])
                        async def wrapper(interaction: discord.Interaction, confirm: bool):
                            await cmd_data['function'](interaction, confirm)
                    elif 'user' in cmd_data['params']:  # payment/pay
                        @bot.tree.command(name=alias_name, description=cmd_data['description'])
                        async def wrapper(interaction: discord.Interaction, user: discord.Member):
                            await cmd_data['function'](interaction, user)
                    else:
                        # Generic fallback for other commands
                        @bot.tree.command(name=alias_name, description=cmd_data['description'])
                        async def wrapper(interaction: discord.Interaction):
                            await cmd_data['function'](interaction)
                    
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
    try:
        if bot.user:
            logger.bot_event(f"Bot started - {bot.user.name} ({bot.user.id}) in {len(bot.guilds)} guilds")
            print(f'{bot.user.name}#{bot.user.discriminator} is online!')
        else:
            logger.bot_event("Bot started - Unknown")
            print('Bot is online!')
        
        print("🔄 Starting bot initialization...")
        
        # Initialize database
        try:
            print("🗄️ Initializing database...")
            await get_database().initialize()
            logger.bot_event("Database initialized successfully")
            print('✅ Database initialized successfully.')
            
            # Clean up old deposits (older than 30 days)
            try:
                print("🧹 Cleaning up old deposits...")
                cleaned_count = await get_database().cleanup_old_deposits(30)
                if cleaned_count > 0:
                    logger.bot_event(f"Cleaned up {cleaned_count} old paid deposits")
                    print(f'✅ Cleaned up {cleaned_count} old paid deposits.')
                else:
                    print("✅ No old deposits to clean up.")
            except Exception as cleanup_error:
                logger.bot_event(f"Failed to clean up old deposits: {cleanup_error}")
                print(f'⚠️ Failed to clean up old deposits: {cleanup_error}')
                
        except Exception as error:
            logger.bot_event(f"Failed to initialize database: {error}")
            print(f'❌ Failed to initialize database: {error}')
            print(f'❌ Error type: {type(error).__name__}')
            import traceback
            print(f'❌ Full traceback: {traceback.format_exc()}')
            return
        
        # Sync slash commands
        try:
            print("🔄 Syncing slash commands...")
            # Sync to guilds for immediate availability
            for guild in bot.guilds:
                try:
                    guild_synced = await bot.tree.sync(guild=guild)
                    print(f'✅ Synced {len(guild_synced)} commands to guild: {guild.name}')
                except Exception as guild_error:
                    print(f'⚠️ Failed to sync to guild {guild.name}: {guild_error}')
            
            # Sync globally (takes up to 1 hour to propagate)
            synced = await bot.tree.sync()
            logger.bot_event(f"Synced {len(synced)} commands")
            print(f'✅ Synced {len(synced)} commands.')
            print("🎉 Bot is fully ready!")
        except Exception as error:
            logger.bot_event(f"Command sync failed: {error}")
            print(f'❌ Failed to sync commands: {error}')
            print(f'❌ Error type: {type(error).__name__}')
            import traceback
            print(f'❌ Full traceback: {traceback.format_exc()}')
            
    except Exception as error:
        print(f'❌ CRITICAL ERROR in on_ready: {error}')
        print(f'❌ Error type: {type(error).__name__}')
        import traceback
        print(f'❌ Full traceback: {traceback.format_exc()}')
        logger.error(f"Critical error in on_ready: {error}")

async def harvest(interaction: discord.Interaction, amount: int):
    """Log spice sand harvests and calculate melange conversion"""
    # Validate amount
    if not 1 <= amount <= 10000:
        await interaction.response.send_message("❌ Amount must be between 1 and 10,000 spice sand.", ephemeral=True)
        return
    
    try:
        # Try to defer the response, but handle expired interactions gracefully
        try:
            await interaction.response.defer(thinking=True)
            use_followup = True
        except Exception as defer_error:
            if "Unknown interaction" in str(defer_error) or "NotFound" in str(defer_error):
                # Interaction expired, we'll need to send a new message
                use_followup = False
                logger.warning(f"Interaction expired for harvest command, user: {interaction.user.id}")
            else:
                # Re-raise if it's a different error
                raise defer_error
        
        # Get conversion rate and add deposit
        sand_per_melange = get_sand_per_melange()
        await get_database().add_deposit(str(interaction.user.id), interaction.user.display_name, amount)
        
        # Get user data and calculate totals
        user = await get_database().get_user(str(interaction.user.id))
        total_sand = await get_database().get_user_total_sand(str(interaction.user.id))
        
        # Debug logging
        logger.bot_event(f"Harvest debug - User: {user}, Total sand: {total_sand}, User ID: {interaction.user.id}")
        
        # Calculate melange conversion
        total_melange_earned = total_sand // sand_per_melange
        current_melange = user['total_melange'] if user and user['total_melange'] is not None else 0
        new_melange = total_melange_earned - current_melange
        
        if new_melange > 0:
            await get_database().update_user_melange(str(interaction.user.id), new_melange)
        
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
        
        # Send response based on whether defer was successful
        if use_followup:
            await interaction.followup.send(embed=embed.build())
        else:
            await interaction.channel.send(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in harvest command: {error}")
        logger.error(f"Error type: {type(error).__name__}")
        logger.error(f"Error details: {str(error)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        try:
            # Send error response based on whether defer was successful
            if use_followup:
                await interaction.followup.send("❌ An error occurred while processing your harvest.", ephemeral=True)
            else:
                await interaction.channel.send("❌ An error occurred while processing your harvest.")
        except Exception as response_error:
            logger.error(f"Error sending error response: {response_error}")
            # If all else fails, try to send to the channel
            try:
                await interaction.channel.send("❌ An error occurred while processing your harvest.")
            except:
                pass  # Last resort - just log the error

async def refinery(interaction: discord.Interaction):
    """Show your total sand and melange statistics"""
    try:
        # Try to defer the response, but handle expired interactions gracefully
        try:
            await interaction.response.defer(thinking=True)
            use_followup = True
        except Exception as defer_error:
            if "Unknown interaction" in str(defer_error) or "NotFound" in str(defer_error):
                # Interaction expired, we'll need to send a new message
                use_followup = False
                logger.warning(f"Interaction expired for refinery command, user: {interaction.user.id}")
            else:
                # Re-raise if it's a different error
                raise defer_error
        
        user = await get_database().get_user(str(interaction.user.id))
        total_sand = await get_database().get_user_total_sand(str(interaction.user.id))
        paid_sand = await get_database().get_user_paid_sand(str(interaction.user.id))
        
        if not user and total_sand == 0:
            embed = (EmbedBuilder("🏭 Spice Refinery Status", color=0x95A5A6, timestamp=interaction.created_at)
                     .set_description("🏜️ You haven't harvested any spice sand yet! Use `/harvest` to start tracking your harvests.")
                     .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
            await interaction.followup.send(embed=embed.build(), ephemeral=True)
            return
        
        # Calculate progress
        sand_per_melange = get_sand_per_melange()
        remaining_sand = total_sand % sand_per_melange
        sand_needed = sand_per_melange - remaining_sand if total_sand > 0 else sand_per_melange
        progress_percent = int((remaining_sand / sand_per_melange) * 100) if total_sand > 0 else 0
        
        # Create progress bar
        progress_bar_length = 10
        filled_bars = int((remaining_sand / sand_per_melange) * progress_bar_length) if total_sand > 0 else 0
        progress_bar = '▓' * filled_bars + '░' * (progress_bar_length - filled_bars)
        
        embed = (EmbedBuilder("🏭 Spice Refinery Status", color=0x3498DB, timestamp=interaction.created_at)
                 .set_thumbnail(interaction.user.display_avatar.url)
                 .add_field("🏜️ Harvest Summary", f"**Unpaid Harvest:** {total_sand:,}\n**Paid Harvest:** {paid_sand:,}")
                 .add_field("✨ Melange Production", f"**Total Melange:** {user['total_melange'] if user else 0:,}")
                 .add_field("⚙️ Refinement Rate", f"{sand_per_melange} sand = 1 melange")
                 .add_field("🎯 Refinement Progress", f"{progress_bar} {progress_percent}%\n**Sand Needed:** {sand_needed:,}", inline=False)
                 .add_field("📅 Last Activity", f"<t:{int(user['last_updated'].timestamp()) if user else interaction.created_at.timestamp()}:F>", inline=False)
                 .set_footer(f"Spice Refinery • {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        # Send response based on whether defer was successful
        if use_followup:
            await interaction.followup.send(embed=embed.build())
        else:
            await interaction.channel.send(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in refinery command: {error}")
        try:
            # Send error response based on whether defer was successful
            if use_followup:
                await interaction.followup.send("❌ An error occurred while fetching your refinery status.", ephemeral=True)
            else:
                await interaction.channel.send("❌ An error occurred while fetching your refinery status.")
        except Exception as response_error:
            logger.error(f"Error sending error response: {response_error}")
            # If all else fails, try to send to the channel
            try:
                await interaction.channel.send("❌ An error occurred while fetching your refinery status.")
            except:
                pass  # Last resort - just log the error

async def leaderboard(interaction: discord.Interaction, limit: int = 10):
    """Display top refiners by melange earned"""
    try:
        # Try to defer the response, but handle expired interactions gracefully
        try:
            await interaction.response.defer(thinking=True)
            use_followup = True
        except Exception as defer_error:
            if "Unknown interaction" in str(defer_error) or "NotFound" in str(defer_error):
                # Interaction expired, we'll need to send a new message
                use_followup = False
                logger.warning(f"Interaction expired for leaderboard command, user: {interaction.user.id}")
            else:
                # Re-raise if it's a different error
                raise defer_error
        
        # Validate limit
        if not 5 <= limit <= 25:
            if use_followup:
                await interaction.followup.send("❌ Limit must be between 5 and 25.", ephemeral=True)
            else:
                await interaction.channel.send("❌ Limit must be between 5 and 25.")
            return
        
        leaderboard_data = await get_database().get_leaderboard(limit)
        
        if not leaderboard_data:
            embed = EmbedBuilder("🏆 Spice Refinery Rankings", color=0x95A5A6, timestamp=interaction.created_at)
            embed.set_description("🏜️ No refiners found yet! Be the first to start harvesting spice sand with `/harvest`.")
            if use_followup:
                await interaction.followup.send(embed=embed.build())
            else:
                await interaction.channel.send(embed=embed.build())
            return
        
        # Get conversion rate and build leaderboard
        sand_per_melange = get_sand_per_melange()
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
        
        # Send response based on whether defer was successful
        if use_followup:
            await interaction.followup.send(embed=embed.build())
        else:
            await interaction.channel.send(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in leaderboard command: {error}")
        try:
            # Send error response based on whether defer was successful
            if use_followup:
                await interaction.followup.send("❌ An error occurred while fetching the leaderboard.", ephemeral=True)
            else:
                await interaction.channel.send("❌ An error occurred while fetching the leaderboard.")
        except Exception as response_error:
            logger.error(f"Error sending error response: {response_error}")
            # If all else fails, try to send to the channel
            try:
                await interaction.channel.send("❌ An error occurred while fetching the leaderboard.")
            except:
                pass  # Last resort - just log the error

async def conversion(interaction: discord.Interaction):
    """View the current spice sand to melange conversion rate"""
    try:
        
        # Get current rate from environment
        current_rate = get_sand_per_melange()
        
        embed = (EmbedBuilder("⚙️ Refinement Rate Information", color=0x3498DB, timestamp=interaction.created_at)
                 .add_field("📊 Current Rate", f"**{current_rate} sand = 1 melange**", inline=False)
                 .add_field("⚠️ Important Note", "The conversion rate is set via environment variables and cannot be changed through commands. Contact an administrator to modify the SAND_PER_MELANGE environment variable.", inline=False)
                 .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.response.send_message(embed=embed.build())
        print(f'Refinement rate info requested by {interaction.user.display_name} ({interaction.user.id}) - Current rate: {current_rate}')
        
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
        sand_per_melange = get_sand_per_melange()
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
        sand_per_melange = get_sand_per_melange()
        
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
                           "**`/conversion`**\nView the current refinement rate.\n\n"
                           "**`/payment [user]`**\nProcess payment for a harvester's deposits.\n\n"
                           "**`/payroll`**\nProcess payments for all unpaid harvesters.\n\n"
                           "**`/reset confirm:True`**\nReset all refinery statistics (requires confirmation).", inline=False)
                 .add_field("📋 Current Settings", f"**Refinement Rate:** {sand_per_melange} sand = 1 melange (set via SAND_PER_MELANGE env var)\n**Default Harvester %:** {os.getenv('DEFAULT_HARVESTER_PERCENTAGE', '25.0')}%", inline=False)
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
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while displaying help.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while displaying help.", ephemeral=True)
        except Exception as followup_error:
            logger.error(f"Error sending followup message: {followup_error}")
            # If all else fails, try to send to the channel
            try:
                await interaction.channel.send("❌ An error occurred while displaying help.")
            except:
                pass  # Last resort - just log the error

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
        deleted_rows = await get_database().reset_all_stats()
        
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
        # Try to defer the response, but handle expired interactions gracefully
        try:
            await interaction.response.defer(thinking=True)
            use_followup = True
        except Exception as defer_error:
            if "Unknown interaction" in str(defer_error) or "NotFound" in str(defer_error):
                # Interaction expired, we'll need to send a new message
                use_followup = False
                logger.warning(f"Interaction expired for ledger command, user: {interaction.user.id}")
            else:
                # Re-raise if it's a different error
                raise defer_error
        
        deposits_data = await get_database().get_user_deposits(str(interaction.user.id))
        
        if not deposits_data:
            embed = (EmbedBuilder("📋 Spice Harvest Ledger", color=0x95A5A6, timestamp=interaction.created_at)
                     .set_description("🏜️ You haven't harvested any spice sand yet! Use `/harvest` to start tracking your harvests.")
                     .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
            if use_followup:
                await interaction.followup.send(embed=embed.build(), ephemeral=True)
            else:
                await interaction.channel.send(embed=embed.build())
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
                 .set_thumbnail(interaction.user.display_avatar.url)
                 .add_field("💰 Payment Summary", f"**Unpaid Harvest:** {total_unpaid:,} sand\n**Paid Harvest:** {total_paid:,} sand\n**Total Harvests:** {len(deposits_data)}", inline=False)
                 .set_footer(f"Spice Refinery • {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        # Send response based on whether defer was successful
        if use_followup:
            await interaction.followup.send(embed=embed.build())
        else:
            await interaction.channel.send(embed=embed.build())
        
    except Exception as error:
        logger.error(f"Error in ledger command: {error}")
        try:
            # Send error response based on whether defer was successful
            if use_followup:
                await interaction.followup.send("❌ An error occurred while fetching your harvest ledger.", ephemeral=True)
            else:
                await interaction.channel.send("❌ An error occurred while fetching your harvest ledger.")
        except Exception as response_error:
            logger.error(f"Error sending error response: {response_error}")
            # If all else fails, try to send to the channel
            try:
                await interaction.channel.send("❌ An error occurred while fetching your harvest ledger.")
            except:
                pass  # Last resort - just log the error

async def payment(interaction: discord.Interaction, user: discord.Member):
    """Process payment for a harvester's deposits (Admin only)"""
    try:
        # Defer the response to prevent interaction timeout
        await interaction.response.defer(thinking=True)
        
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        # Get user's unpaid deposits
        unpaid_deposits = await get_database().get_user_deposits(str(user.id), include_paid=False)
        
        if not unpaid_deposits:
            embed = (EmbedBuilder("💰 Payment Status", color=0x95A5A6, timestamp=interaction.created_at)
                     .set_description(f"🏜️ **{user.display_name}** has no unpaid harvests to process.")
                     .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
            await interaction.followup.send(embed=embed.build())
            return
        
        # Mark all deposits as paid
        await get_database().mark_all_user_deposits_paid(str(user.id))
        
        total_paid = sum(deposit['sand_amount'] for deposit in unpaid_deposits)
        
        embed = (EmbedBuilder("💰 Payment Processed", color=0x27AE60, timestamp=interaction.created_at)
                 .set_description(f"✅ **{user.display_name}** has been paid for all harvests!")
                 .add_field("📊 Payment Summary", f"**Total Spice Sand Paid:** {total_paid:,}\n**Harvests Processed:** {len(unpaid_deposits)}", inline=False)
                 .set_footer(f"Payment processed by {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.followup.send(embed=embed.build())
        print(f'Harvester {user.display_name} ({user.id}) paid {total_paid:,} spice sand by {interaction.user.display_name} ({interaction.user.id})')
        
    except Exception as error:
        logger.error(f"Error in payment command: {error}")
        try:
            # Since we deferred, always use followup.send
            await interaction.followup.send("❌ An error occurred while processing the payment.", ephemeral=True)
        except Exception as followup_error:
            logger.error(f"Error sending followup message: {followup_error}")
            # If followup fails, try to send to the channel
            try:
                await interaction.channel.send("❌ An error occurred while processing the payment.")
            except:
                pass  # Last resort - just log the error

async def payroll(interaction: discord.Interaction):
    """Process payments for all unpaid harvesters (Admin only)"""
    try:
        # Defer the response to prevent interaction timeout
        await interaction.response.defer(thinking=True)
        
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        # Get all unpaid deposits
        unpaid_deposits = await get_database().get_all_unpaid_deposits()
        
        if not unpaid_deposits:
            embed = (EmbedBuilder("💰 Payroll Status", color=0x95A5A6, timestamp=interaction.created_at)
                     .set_description("🏜️ There are no unpaid harvests to process.")
                     .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
            await interaction.followup.send(embed=embed.build())
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
            await get_database().mark_all_user_deposits_paid(user_id)
            user_total = sum(deposit['sand_amount'] for deposit in deposits_list)
            total_paid += user_total
            users_paid += 1
        
        embed = (EmbedBuilder("💰 Guild Payroll Complete", color=0x27AE60, timestamp=interaction.created_at)
                 .set_description("✅ **All harvesters have been paid for their harvests!**")
                 .add_field("📊 Payroll Summary", f"**Total Spice Sand Paid:** {total_paid:,}\n**Harvesters Paid:** {users_paid}\n**Total Harvests:** {len(unpaid_deposits)}", inline=False)
                 .set_footer(f"Guild payroll processed by {interaction.user.display_name}", interaction.user.display_avatar.url))
        
        await interaction.followup.send(embed=embed.build())
        print(f'Guild payroll of {total_paid:,} spice sand to {users_paid} harvesters by {interaction.user.display_name} ({interaction.user.id})')
        
    except Exception as error:
        logger.error(f"Error in payroll command: {error}")
        try:
            # Since we deferred, always use followup.send
            await interaction.followup.send("❌ An error occurred while processing the guild payroll.", ephemeral=True)
        except Exception as followup_error:
            logger.error(f"Error sending followup message: {followup_error}")
            # If followup fails, try to send to the channel
            try:
                await interaction.channel.send("❌ An error occurred while processing the guild payroll.")
            except:
                pass  # Last resort - just log the error

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

# Fly.io health check endpoint
import http.server
import socketserver
import threading

def start_health_server():
    """Start a robust HTTP server for Fly.io health checks with keep-alive"""
    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()
                
                # Return bot status information
                status = {
                    'status': 'healthy',
                    'bot_ready': bot.is_ready(),
                    'guild_count': len(bot.guilds),
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }
                self.wfile.write(str(status).encode())
            elif self.path == '/ping':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'pong')
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass  # Suppress HTTP server logs
    
    try:
        port = int(os.getenv('PORT', 8080))
        with socketserver.TCPServer(("", port), HealthHandler) as httpd:
            logger.bot_event(f"Health server started on port {port}")
            print(f"Health check server started on port {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Health server failed to start: {e}")
        print(f"Health server failed to start: {e}")

# Run the bot
if __name__ == '__main__':
    # Start health check server in a separate thread for Fly.io
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Start a keep-alive thread to prevent machine from going idle
    def keep_alive():
        """Send periodic pings to keep the machine alive"""
        import requests
        import time
        while True:
            try:
                time.sleep(300)  # Every 5 minutes
                requests.get('http://localhost:8080/ping', timeout=5)
            except:
                pass  # Ignore errors, just keep trying
    
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set")
        print("❌ ERROR: DISCORD_TOKEN environment variable is not set!")
        print("Please set the DISCORD_TOKEN environment variable in Fly.io or your .env file")
        exit(1)
    
    logger.bot_event(f"Bot starting - Token present: {bool(token)}")
    print("Starting Discord bot...")
    bot.run(token)