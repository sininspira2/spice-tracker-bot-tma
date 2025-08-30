import discord
from discord.ext import commands
import os
import time
import datetime
import asyncio
import http.server
import socketserver
import threading
import requests
from dotenv import load_dotenv
from database import Database
from utils.embed_builder import EmbedBuilder
from utils.logger import logger
from utils.command_utils import create_command_function, log_command_metrics
from utils.database_utils import timed_database_operation, validate_user_exists, get_user_stats
from utils.embed_utils import (
    build_status_embed, 
    build_info_embed, 
    build_progress_embed, 
    build_leaderboard_embed, 
    build_warning_embed, 
    build_success_embed
)

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

async def send_response(interaction: discord.Interaction, content=None, embed=None, ephemeral=False, use_followup=True):
    """Helper function to send responses using the appropriate method based on use_followup"""
    start_time = time.time()
    
    # Validate inputs with better error logging
    if not interaction:
        logger.error("send_response called with None interaction")
        return
    
    # Check if interaction has required attributes
    if not hasattr(interaction, 'channel') or not interaction.channel:
        logger.error(f"send_response called with invalid channel - interaction type: {type(interaction)}, channel: {getattr(interaction, 'channel', 'NO_CHANNEL_ATTR')}")
        return
    
    # Guild can be None for DMs, so we don't require it
    # But we do need to check if we're in a guild context for certain operations
    is_guild_context = hasattr(interaction, 'guild') and interaction.guild is not None
    
    try:
        if use_followup:
            if content:
                await interaction.followup.send(content, ephemeral=ephemeral)
            elif embed:
                await interaction.followup.send(embed=embed)
        else:
            if content:
                await interaction.channel.send(content)
            elif embed:
                await interaction.channel.send(embed=embed)
        
        response_time = time.time() - start_time
        logger.info(f"Response sent successfully", 
                   response_time=f"{response_time:.3f}s", 
                   use_followup=use_followup, 
                   has_content=content is not None, 
                   has_embed=embed is not None)
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Error sending response: {e}", 
                    response_time=f"{response_time:.3f}s", 
                    use_followup=use_followup, 
                    error=str(e))
        # Fallback to channel if followup fails
        try:
            if content:
                await interaction.channel.send(content)
            elif embed:
                await interaction.channel.send(embed=embed)
            
            fallback_time = time.time() - start_time
            logger.info(f"Fallback response sent successfully", 
                       total_time=f"{fallback_time:.3f}s", 
                       fallback_time=f"{fallback_time - response_time:.3f}s")
            
        except Exception as fallback_error:
            total_time = time.time() - start_time
            logger.error(f"Fallback response also failed: {fallback_error}", 
                        total_time=f"{total_time:.3f}s", 
                        original_error=str(e), 
                        fallback_error=str(fallback_error))
            # Last resort - just log the error, don't raise

def handle_interaction_expiration(func):
    """Decorator to handle interaction expiration gracefully"""
    async def wrapper(interaction: discord.Interaction, *args, **kwargs):
        command_start_time = time.time()
        use_followup = True
        
        # Check if this command requires guild context
        if not hasattr(interaction, 'guild') or not interaction.guild:
            try:
                await send_response(interaction, "❌ This command can only be used in a Discord server, not in direct messages.", use_followup=False, ephemeral=True)
            except:
                # If we can't send a response, just log it
                logger.warning(f"Command {func.__name__} called in DM context, cannot proceed")
            return
        
        try:
            # Validate interaction before attempting defer
            if not hasattr(interaction, 'response') or not hasattr(interaction, 'user'):
                logger.warning(f"Invalid interaction object for {func.__name__}, falling back to channel messages")
                use_followup = False
                return
            
            # Try to defer the response with a timeout
            import asyncio
            defer_start = time.time()
            await asyncio.wait_for(interaction.response.defer(thinking=True), timeout=5.0)
            defer_time = time.time() - defer_start
            logger.info(f"Interaction deferred successfully", 
                       command=func.__name__, 
                       defer_time=f"{defer_time:.3f}s")
            
        except asyncio.TimeoutError:
            # Defer timed out, fall back to channel messages
            use_followup = False
            defer_time = time.time() - defer_start
            logger.warning(f"Defer timeout for {func.__name__} command", 
                          user=interaction.user.display_name, 
                          user_id=interaction.user.id, 
                          defer_time=f"{defer_time:.3f}s")
        except Exception as defer_error:
            if "Unknown interaction" in str(defer_error) or "NotFound" in str(defer_error):
                # Interaction expired, we'll need to send channel messages
                use_followup = False
                defer_time = time.time() - defer_start
                logger.warning(f"Interaction expired for {func.__name__} command", 
                              user=interaction.user.display_name, 
                              user_id=interaction.user.id, 
                              defer_time=f"{defer_time:.3f}s")
            else:
                # Re-raise if it's a different error
                raise defer_error
        
        # Add use_followup to kwargs so the function can use it
        kwargs['use_followup'] = use_followup
        
        try:
            function_start = time.time()
            result = await func(interaction, *args, **kwargs)
            function_time = time.time() - function_start
            total_time = time.time() - command_start_time
            
            logger.command_success(
                command=func.__name__,
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                execution_time=function_time,
                total_time=total_time,
                guild_id=str(interaction.guild.id) if interaction.guild else None,
                guild_name=interaction.guild.name if interaction.guild else None
            )
            
            return result
        except Exception as func_error:
            function_time = time.time() - function_start
            total_time = time.time() - command_start_time
            
            # Log the error but don't re-raise it
            logger.command_error(
                command=func.__name__,
                user_id=str(interaction.user.id),
                username=interaction.user.display_name,
                error=str(func_error),
                execution_time=function_time,
                total_time=total_time,
                guild_id=str(interaction.guild.id) if interaction.guild else None,
                guild_name=interaction.guild.name if interaction.guild else None
            )
            
            # Try to send error response, but don't let it fail the decorator
            try:
                # Check if interaction is still valid before trying to send response
                # Guild can be None for DMs, so we only require channel
                if hasattr(interaction, 'channel') and interaction.channel:
                    await send_response(interaction, "❌ An error occurred while processing your command.", use_followup=use_followup, ephemeral=True)
                else:
                    logger.warning(f"Interaction invalid for {func.__name__}, skipping error response")
            except Exception as response_error:
                logger.error(f"Failed to send error response for {func.__name__}: {response_error}")
                # Don't re-raise - just log the failure
            
            # Return None to indicate error occurred
            return None
    
    return wrapper

def monitor_performance(operation_name: str = None):
    """Decorator to monitor performance of database operations and other timed operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            operation = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log performance metrics
                logger.info(f"{operation} completed successfully", 
                           execution_time=f"{execution_time:.3f}s",
                           operation=operation)
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{operation} failed", 
                           execution_time=f"{execution_time:.3f}s",
                           operation=operation,
                           error=str(e))
                raise
        
        return wrapper
    return decorator

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
                'harvester_percentage': "Percentage for primary harvester (default: 10%)"
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
        'expedition': {
            'aliases': ['exp'],
            'description': "View details of a specific expedition",
            'params': {'expedition_id': "ID of the expedition to view"},
            'function': expedition_details
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
    for command_name, command_data in commands.items():
        # Register main command
        main_cmd = create_command_function(command_data, command_name, bot)
        print(f"Registered command: {command_name}")
        
        # Register aliases
        for alias in command_data['aliases']:
            alias_cmd = create_command_function(command_data, alias, bot)

@bot.event
async def on_ready():
    bot_start_time = time.time()
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
            db_init_start = time.time()
            await get_database().initialize()
            db_init_time = time.time() - db_init_start
            logger.bot_event("Database initialized successfully", db_init_time=f"{db_init_time:.3f}s")
            print(f'✅ Database initialized successfully in {db_init_time:.3f}s.')
            
            # Clean up old deposits (older than 30 days)
            try:
                print("🧹 Cleaning up old deposits...")
                cleanup_start = time.time()
                cleaned_count = await get_database().cleanup_old_deposits(30)
                cleanup_time = time.time() - cleanup_start
                if cleaned_count > 0:
                    logger.bot_event(f"Cleaned up {cleaned_count} old paid deposits", cleanup_time=f"{cleanup_time:.3f}s")
                    print(f'✅ Cleaned up {cleaned_count} old paid deposits in {cleanup_time:.3f}s.')
                else:
                    logger.bot_event("No old deposits to clean up", cleanup_time=f"{cleanup_time:.3f}s")
                    print(f"✅ No old deposits to clean up in {cleanup_time:.3f}s.")
            except Exception as cleanup_error:
                cleanup_time = time.time() - cleanup_start
                logger.bot_event(f"Failed to clean up old deposits: {cleanup_error}", cleanup_time=f"{cleanup_time:.3f}s")
                print(f'⚠️ Failed to clean up old deposits in {cleanup_time:.3f}s: {cleanup_error}')
                
        except Exception as error:
            db_init_time = time.time() - db_init_start
            logger.bot_event(f"Failed to initialize database: {error}", db_init_time=f"{db_init_time:.3f}s")
            print(f'❌ Failed to initialize database in {db_init_time:.3f}s: {error}')
            print(f'❌ Error type: {type(error).__name__}')
            import traceback
            print(f'❌ Full traceback: {traceback.format_exc()}')
            return
        
        # Sync slash commands
        try:
            print("🔄 Syncing slash commands...")
            sync_start = time.time()
            
            # Sync to guilds for immediate availability
            guild_sync_start = time.time()
            guild_sync_success = 0
            guild_sync_failed = 0
            for guild in bot.guilds:
                try:
                    guild_synced = await bot.tree.sync(guild=guild)
                    print(f'✅ Synced {len(guild_synced)} commands to guild: {guild.name}')
                    guild_sync_success += 1
                except Exception as guild_error:
                    print(f'⚠️ Failed to sync to guild {guild.name}: {guild_error}')
                    guild_sync_failed += 1
            
            guild_sync_time = time.time() - guild_sync_start
            logger.bot_event(f"Guild command sync completed", 
                           guild_sync_time=f"{guild_sync_time:.3f}s",
                           guilds_success=guild_sync_success,
                           guilds_failed=guild_sync_failed)
            
            # Sync globally (takes up to 1 hour to propagate)
            global_sync_start = time.time()
            synced = await bot.tree.sync()
            global_sync_time = time.time() - global_sync_start
            
            total_sync_time = time.time() - sync_start
            logger.bot_event(f"Command sync completed", 
                           total_sync_time=f"{total_sync_time:.3f}s",
                           guild_sync_time=f"{guild_sync_time:.3f}s",
                           global_sync_time=f"{global_sync_time:.3f}s",
                           commands_synced=len(synced))
            print(f'✅ Synced {len(synced)} commands in {total_sync_time:.3f}s.')
            print("🎉 Bot is fully ready!")
            
        except Exception as error:
            sync_time = time.time() - sync_start
            logger.bot_event(f"Command sync failed: {error}", sync_time=f"{sync_time:.3f}s")
            print(f'❌ Failed to sync commands in {sync_time:.3f}s: {error}')
            print(f'❌ Error type: {type(error).__name__}')
            import traceback
            print(f'❌ Full traceback: {traceback.format_exc()}')
        
        # Log total bot startup time
        total_startup_time = time.time() - bot_start_time
        logger.bot_event(f"Bot startup completed", 
                        total_startup_time=f"{total_startup_time:.3f}s",
                        db_init_time=f"{db_init_time:.3f}s",
                        guild_count=len(bot.guilds))
        print(f"🚀 Bot startup completed in {total_startup_time:.3f}s")
            
    except Exception as error:
        total_startup_time = time.time() - bot_start_time
        print(f'❌ CRITICAL ERROR in on_ready: {error}')
        print(f'❌ Error type: {type(error).__name__}')
        print(f'❌ Startup time: {total_startup_time:.3f}s')
        import traceback
        print(f'❌ Full traceback: {traceback.format_exc()}')
        logger.error(f"Critical error in on_ready: {error}", startup_time=f"{total_startup_time:.3f}s")

@handle_interaction_expiration
async def harvest(interaction: discord.Interaction, amount: int, use_followup: bool):
    """Log spice sand harvests and calculate melange conversion"""
    command_start = time.time()
    
    # Validate amount
    if not 1 <= amount <= 10000:
        await send_response(interaction, "❌ Amount must be between 1 and 10,000 spice sand.", use_followup=use_followup, ephemeral=True)
        return
    
    # Get conversion rate and add deposit
    sand_per_melange = get_sand_per_melange()
    
    # Database operations with timing using utility functions
    
    # Add deposit with timing
    add_deposit_time = await timed_database_operation(
        "add_deposit",
        get_database().add_deposit,
        str(interaction.user.id), interaction.user.display_name, amount
    )
    
    # Get user data and calculate totals
    user_stats = await get_user_stats(get_database(), str(interaction.user.id))
    
    # Ensure user exists and has valid data
    user = await validate_user_exists(get_database(), str(interaction.user.id), interaction.user.display_name)
    
    # Calculate melange conversion
    total_melange_earned = user_stats['total_sand'] // sand_per_melange
    current_melange = user['total_melange'] if user and user['total_melange'] is not None else 0
    new_melange = max(0, total_melange_earned - current_melange)  # Ensure new_melange is never negative
    
    # Only update melange if we have new melange to add
    if new_melange > 0:
        update_melange_time = await timed_database_operation(
            "update_user_melange",
            get_database().update_user_melange,
            str(interaction.user.id), new_melange
        )
    
    # Build response
    remaining_sand = user_stats['total_sand'] % sand_per_melange
    sand_needed = max(0, sand_per_melange - remaining_sand)  # Ensure sand_needed is never negative
    
    # Use utility function for embed building
    fields = {
        "📊 Harvest Summary": f"**Spice Sand Harvested:** {amount:,}\n**Total Unpaid Harvest:** {user_stats['total_sand']:,}",
        "✨ Melange Production": f"**Total Melange:** {(current_melange + new_melange):,}\n**Conversion Rate:** {sand_per_melange} sand = 1 melange",
        "🎯 Next Refinement": f"**Sand Until Next Melange:** {sand_needed:,}"
    }
    
    embed = build_status_embed(
        title="🏜️ Spice Harvest Logged",
        color=0xE67E22,
        fields=fields,
        footer=f"Harvested by {interaction.user.display_name}",
        timestamp=interaction.created_at
    )
    
    if new_melange and new_melange > 0:
        embed.set_description(f"🎉 **You produced {new_melange:,} melange from this harvest!**")
    
    # Send response using helper function
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
    response_time = time.time() - response_start
    
    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Harvest",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        amount=amount,
        add_deposit_time=f"{add_deposit_time:.3f}s",
        **user_stats['timing'],
        response_time=f"{response_time:.3f}s",
        new_melange=new_melange
    )
        


@handle_interaction_expiration
async def refinery(interaction: discord.Interaction, use_followup: bool):
    """Show your total sand and melange statistics"""
    command_start = time.time()
    
    # Use utility function for database operations
    user_stats = await get_user_stats(get_database(), str(interaction.user.id))
    
    if not user_stats['user'] and user_stats['total_sand'] == 0:
        embed = build_info_embed(
            title="🏭 Spice Refinery Status",
            info_message="🏜️ You haven't harvested any spice sand yet! Use `/harvest` to start tracking your harvests.",
            color=0x95A5A6,
            footer=f"Requested by {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
        return
    
    # Calculate progress
    sand_per_melange = get_sand_per_melange()
    remaining_sand = user_stats['total_sand'] % sand_per_melange
    sand_needed = sand_per_melange - remaining_sand if user_stats['total_sand'] > 0 else sand_per_melange
    
    # Build progress fields
    progress_fields = {
        "🏜️ Harvest Summary": f"**Unpaid Harvest:** {user_stats['total_sand']:,}\n**Paid Harvest:** {user_stats['paid_sand']:,}",
        "✨ Melange Production": f"**Total Melange:** {user_stats['user']['total_melange'] if user_stats['user'] else 0:,}",
        "⚙️ Refinement Rate": f"{sand_per_melange} sand = 1 melange",
        "📅 Last Activity": f"<t:{int(user_stats['user']['last_updated'].timestamp()) if user_stats['user'] else interaction.created_at.timestamp()}:F>"
    }
    
    # Use utility function for progress embed
    embed = build_progress_embed(
        title="🏭 Spice Refinery Status",
        current=remaining_sand,
        total=sand_per_melange,
        progress_fields=progress_fields,
        footer=f"Spice Refinery • {interaction.user.display_name}",
        thumbnail=interaction.user.display_avatar.url,
        timestamp=interaction.created_at
    )
    
    # Send response using helper function
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
    response_time = time.time() - response_start
    
    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Refinery",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        **user_stats['timing'],
        response_time=f"{response_time:.3f}s",
        total_sand=user_stats['total_sand'],
        paid_sand=user_stats['paid_sand']
    )

@handle_interaction_expiration
async def leaderboard(interaction: discord.Interaction, limit: int = 10, use_followup: bool = True):
    """Display top refiners by melange earned"""
    command_start = time.time()
    
    # Validate limit
    if not 5 <= limit <= 25:
        await send_response(interaction, "❌ Limit must be between 5 and 25.", use_followup=use_followup, ephemeral=True)
        return
    
    # Database operation with timing using utility function
    leaderboard_data, get_leaderboard_time = await timed_database_operation(
        "get_leaderboard", 
        get_database().get_leaderboard, 
        limit
    )
    
    if not leaderboard_data:
        embed = build_info_embed(
            title="🏆 Spice Refinery Rankings",
            info_message="🏜️ No refiners found yet! Be the first to start harvesting spice sand with `/harvest`.",
            color=0x95A5A6,
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup)
        return
    
    # Calculate totals
    total_melange = sum(user['total_melange'] for user in leaderboard_data)
    total_sand = sum(user['total_sand'] for user in leaderboard_data)
    
    # Use utility function for leaderboard embed
    total_stats = {
        'total_refiners': len(leaderboard_data),
        'total_melange': total_melange,
        'total_sand': total_sand,
        'sand_per_melange': get_sand_per_melange()
    }
    
    embed = build_leaderboard_embed(
        title="🏆 Spice Refinery Rankings",
        leaderboard_data=leaderboard_data,
        total_stats=total_stats,
        footer=f"Showing top {len(leaderboard_data)} refiners • Updated",
        timestamp=interaction.created_at
    )
    
    # Send response using helper function
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
    response_time = time.time() - response_start
    
    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Leaderboard",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        limit=limit,
        get_leaderboard_time=f"{get_leaderboard_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        result_count=len(leaderboard_data),
        total_melange=total_melange,
        total_sand=total_sand
    )

@handle_interaction_expiration
async def conversion(interaction: discord.Interaction, use_followup: bool = True):
    """View the current spice sand to melange conversion rate"""
    try:
        # Get current rate from environment
        current_rate = get_sand_per_melange()
        
        # Use utility function for embed building
        fields = {
            "📊 Current Rate": f"**{current_rate} sand = 1 melange**",
            "⚠️ Important Note": "The conversion rate is set via environment variables and cannot be changed through commands. Contact an administrator to modify the SAND_PER_MELANGE environment variable."
        }
        
        embed = build_info_embed(
            title="⚙️ Refinement Rate Information",
            info_message="Current spice sand to melange conversion rate",
            fields=fields,
            footer=f"Requested by {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        
        await send_response(interaction, embed=embed.build(), use_followup=use_followup)
        print(f'Refinement rate info requested by {interaction.user.display_name} ({interaction.user.id}) - Current rate: {current_rate}')
        
    except Exception as error:
        logger.error(f"Error in conversion command: {error}")
        await send_response(interaction, "❌ An error occurred while fetching the refinement rate.", use_followup=use_followup, ephemeral=True)

@handle_interaction_expiration
async def split(interaction: discord.Interaction, total_sand: int, harvester_percentage: float = None, use_followup: bool = True):
    """Split harvested spice sand among expedition members"""
    try:
        # Use environment variable if no harvester_percentage provided
        if harvester_percentage is None:
            harvester_percentage = float(os.getenv('DEFAULT_HARVESTER_PERCENTAGE', 10.0))  # Default to 10%
        
        # Validate inputs
        if total_sand < 1:
            await send_response(interaction, "❌ Total spice sand must be at least 1.", use_followup=use_followup, ephemeral=True)
            return
        if not 0 <= harvester_percentage <= 100:
            await send_response(interaction, "❌ Primary harvester percentage must be between 0 and 100.", use_followup=use_followup, ephemeral=True)
            return
        
        # Create a modal to collect participant information
        class ExpeditionModal(discord.ui.Modal, title="🏜️ Expedition Participants"):
            participants_input = discord.ui.TextInput(
                label="Participant Discord IDs (one per line)",
                placeholder="Enter Discord user IDs, one per line\nExample:\n123456789012345678\n987654321098765432",
                style=discord.TextStyle.paragraph,
                required=True,
                min_length=1,
                max_length=1000
            )
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    # Parse participant IDs
                    participant_ids = [pid.strip() for pid in self.participants_input.value.split('\n') if pid.strip()]
                    
                    if not participant_ids:
                        await modal_interaction.response.send_message("❌ No valid participant IDs provided.", ephemeral=True)
                        return
                    
                    # Defer response to prevent timeout
                    await modal_interaction.response.defer(thinking=True)
                    
                    # Get conversion rate
                    sand_per_melange = get_sand_per_melange()
                    
                    # Create expedition record
                    expedition_id = await get_database().create_expedition(
                        str(interaction.user.id),
                        interaction.user.display_name,
                        total_sand,
                        harvester_percentage,
                        sand_per_melange
                    )
                    
                    if not expedition_id:
                        await modal_interaction.followup.send("❌ Failed to create expedition record.", ephemeral=True)
                        return
                    
                    # Calculate harvester share
                    harvester_sand = int(total_sand * (harvester_percentage / 100))
                    remaining_sand = total_sand - harvester_sand
                    
                    # Calculate remaining share per participant (excluding harvester)
                    remaining_participants = len(participant_ids) + 1  # +1 for harvester
                    share_per_participant = remaining_sand // remaining_participants if remaining_participants > 0 else 0
                    leftover_sand = remaining_sand % remaining_participants if remaining_participants > 0 else remaining_sand
                    
                    # Add harvester (initiator) as primary harvester
                    harvester_melange = harvester_sand // sand_per_melange
                    harvester_leftover = harvester_sand % sand_per_melange
                    
                    await get_database().add_expedition_participant(
                        expedition_id,
                        str(interaction.user.id),
                        interaction.user.display_name,
                        harvester_sand,
                        harvester_melange,
                        harvester_leftover,
                        is_harvester=True
                    )
                    
                    # Create expedition deposit for harvester
                    await get_database().add_expedition_deposit(
                        str(interaction.user.id),
                        interaction.user.display_name,
                        harvester_sand,
                        expedition_id
                    )
                    
                    # Add remaining participants
                    participant_details = []
                    total_melange = harvester_melange
                    
                    for participant_id in participant_ids:
                        # Try to get user info from Discord
                        try:
                            if modal_interaction.guild:
                                user = await modal_interaction.guild.fetch_member(int(participant_id))
                                username = user.display_name
                            else:
                                # No guild context (DM), use participant ID as username
                                username = f"User_{participant_id}"
                        except:
                            username = f"User_{participant_id}"
                        
                        # Calculate participant share
                        participant_sand = share_per_participant
                        participant_melange = participant_sand // sand_per_melange
                        participant_leftover = participant_sand % sand_per_melange
                        
                        # Add to database
                        await get_database().add_expedition_participant(
                            expedition_id,
                            participant_id,
                            username,
                            participant_sand,
                            participant_melange,
                            participant_leftover,
                            is_harvester=False
                        )
                        
                        # Create expedition deposit for participant
                        await get_database().add_expedition_deposit(
                            participant_id,
                            username,
                            participant_sand,
                            expedition_id
                        )
                        
                        participant_details.append(f"**{username}**: {participant_sand:,} sand ({participant_melange:,} melange)")
                        total_melange += participant_melange
                    
                    # Add leftover to harvester if any
                    if leftover_sand > 0:
                        leftover_melange = leftover_sand // sand_per_melange
                        leftover_remaining = leftover_sand % sand_per_melange
                        
                        # Update harvester's share
                        await get_database().add_expedition_participant(
                            expedition_id,
                            str(interaction.user.id),
                            interaction.user.display_name,
                            leftover_sand,
                            leftover_melange,
                            leftover_remaining,
                            is_harvester=False
                        )
                        
                        # Create expedition deposit for leftover
                        await get_database().add_expedition_deposit(
                            str(interaction.user.id),
                            interaction.user.display_name,
                            leftover_sand,
                            expedition_id
                        )
                        
                        harvester_sand += leftover_sand
                        harvester_melange += leftover_melange
                        harvester_leftover += leftover_remaining
                    
                    # Build response embed
                    embed = (EmbedBuilder("🏜️ Expedition Created", 
                                          description=f"**Expedition #{expedition_id}** has been created and recorded in the database!",
                                          color=0xF39C12, timestamp=modal_interaction.created_at)
                             .add_field("📊 Expedition Summary", 
                                       f"**Total Sand:** {total_sand:,}\n"
                                       f"**Primary Harvester:** {interaction.user.display_name}\n"
                                       f"**Harvester Share:** {harvester_sand:,} sand ({harvester_percentage}%)\n"
                                       f"**Participants:** {len(participant_ids) + 1}", inline=False)
                             .add_field("💰 Melange Distribution", 
                                       f"**Harvester Melange:** {harvester_melange:,}\n"
                                       f"**Total Melange:** {total_melange:,}", inline=False)
                             .add_field("📋 Participants", 
                                       f"**Primary Harvester:** {interaction.user.display_name} - {harvester_sand:,} sand\n" +
                                       "\n".join(participant_details), inline=False)
                             .add_field("📋 Database Status", 
                                       f"✅ Expedition record created\n"
                                       f"✅ Participant shares recorded\n"
                                       f"✅ Deposits logged for payout tracking\n"
                                       f"🔗 Use `/expedition {expedition_id}` to view details", inline=False)
                             .set_footer(f"Expedition initiated by {interaction.user.display_name}", interaction.user.display_avatar.url))
                    
                    await modal_interaction.followup.send(embed=embed.build())
                    
                    # Log the expedition creation
                    logger.bot_event(f"Expedition {expedition_id} created by {interaction.user.display_name} ({interaction.user.id}) - {total_sand} sand, {harvester_percentage}% harvester share, {len(participant_ids)} participants")
                    
                except Exception as error:
                    logger.error(f"Error in expedition modal: {error}")
                    try:
                        await modal_interaction.followup.send("❌ An error occurred while creating the expedition.", ephemeral=True)
                    except:
                        await modal_interaction.channel.send("❌ An error occurred while creating the expedition.")
        
        # Show the modal
        modal = ExpeditionModal()
        await interaction.response.send_modal(modal)
        
    except Exception as error:
        logger.error(f"Error in split command: {error}")
        await send_response(interaction, "❌ An error occurred while setting up the expedition.", use_followup=use_followup, ephemeral=True)

@handle_interaction_expiration
async def help_command(interaction: discord.Interaction, use_followup: bool = True):
    """Show all available commands and their descriptions"""
    sand_per_melange = get_sand_per_melange()
    
    # Use utility function for embed building
    fields = {
        "📊 Harvester Commands": "**`/harvest [amount]`**\nLog spice sand harvests (1-10,000). Automatically converts to melange.\n\n"
                                 "**`/refinery`**\nView your refinery statistics and melange production progress.\n\n"
                                 "**`/ledger`**\nView your complete harvest ledger with payment status.\n\n"
                                 "**`/expedition [id]`**\nView details of a specific expedition.\n\n"
                                 "**`/leaderboard [limit]`**\nShow top refiners by melange production (5-25 users).\n\n"
                                 "**`/split [total_sand] [harvester_%]`**\nSplit harvested spice among expedition members. Enter participant Discord IDs in the modal. Creates expedition records and tracks melange owed for payout. Harvester % is optional (default: 10%).\n\n"
                                 "**`/help`**\nDisplay this help message with all commands.",
        "⚙️ Guild Admin Commands": "**`/conversion`**\nView the current refinement rate.\n\n"
                                   "**`/payment [user]`**\nProcess payment for a harvester's deposits.\n\n"
                                   "**`/payroll`**\nProcess payments for all unpaid harvesters.\n\n"
                                   "**`/reset confirm:True`**\nReset all refinery statistics (requires confirmation).",
        "📋 Current Settings": f"**Refinement Rate:** {sand_per_melange} sand = 1 melange (set via SAND_PER_MELANGE env var)\n**Default Harvester %:** {os.getenv('DEFAULT_HARVESTER_PERCENTAGE', '10.0')}%",
        "💡 Example Usage": "• `/harvest 250` or `/sand 250` - Harvest 250 spice sand\n"
                           "• `/refinery` or `/status` - Check your refinery status\n"
                           "• `/ledger` or `/deposits` - View your harvest ledger\n"
                           "• `/leaderboard 15` or `/top 15` - Show top 15 refiners\n"
                           "• `/payment @username` or `/pay @username` - Pay a specific harvester\n"
                           "• `/payroll` or `/payall` - Pay all harvesters at once\n"
                           "• `/split 1000 30` - Split 1000 sand, 30% to primary harvester\n"
                           "• `/split 1000` - Split 1000 sand using default harvester % (10%)\n"
                           "• **Note:** You'll be prompted to enter participant Discord IDs in a modal",
        "🔄 Command Aliases": "**Harvest:** `/harvest` = `/sand`\n"
                             "**Status:** `/refinery` = `/status`\n"
                             "**Ledger:** `/ledger` = `/deposits`\n"
                             "**Leaderboard:** `/leaderboard` = `/top`\n"
                             "**Expedition:** `/expedition` = `/exp`\n"
                             "**Help:** `/help` = `/commands`\n"
                             "**Conversion:** `/conversion` = `/rate`\n"
                             "**Payment:** `/payment` = `/pay`\n"
                             "**Payroll:** `/payroll` = `/payall`"
    }
    
    embed = build_info_embed(
        title="🏜️ Spice Refinery Commands",
        info_message="Track your spice sand harvests and melange production in the Dune: Awakening universe!",
        color=0xF39C12,
        fields=fields,
        footer="Spice Refinery Bot - Dune: Awakening Guild Resource Tracker",
        timestamp=interaction.created_at
    )
    
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)

@handle_interaction_expiration
async def reset(interaction: discord.Interaction, confirm: bool, use_followup: bool = True):
    """Reset all spice refinery statistics (Admin only - USE WITH CAUTION)"""
    command_start = time.time()
    
    try:
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await send_response(interaction, "❌ You need administrator permissions to use this command.", use_followup=use_followup, ephemeral=True)
            return
        
        if not confirm:
            embed = build_warning_embed(
                title="⚠️ Reset Cancelled",
                warning_message="You must set the `confirm` parameter to `True` to proceed with the reset.",
                fields={"🔄 How to Reset": "Use `/reset confirm:True` to confirm the reset."},
                timestamp=interaction.created_at
            )
            await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
            return
        
        # Reset all refinery statistics using utility function
        deleted_rows, reset_time = await timed_database_operation(
            "reset_all_stats",
            get_database().reset_all_stats
        )
        
        # Use utility function for embed building
        fields = {
            "📊 Reset Summary": f"**Users Affected:** {deleted_rows}\n**Data Cleared:** All harvest records and melange production",
            "✅ What Remains": "Refinement rates and bot settings are preserved."
        }
        
        embed = build_warning_embed(
            title="🔄 Refinery Reset Complete",
            warning_message="**All refinery statistics have been permanently deleted!**",
            fields=fields,
            footer=f"Reset performed by {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        
        # Send response using helper function
        response_start = time.time()
        await send_response(interaction, embed=embed.build(), use_followup=use_followup)
        response_time = time.time() - response_start
        
        # Log performance metrics using utility function
        total_time = time.time() - command_start
        log_command_metrics(
            "Reset",
            str(interaction.user.id),
            interaction.user.display_name,
            total_time,
            admin_id=str(interaction.user.id),
            admin_username=interaction.user.display_name,
            reset_time=f"{reset_time:.3f}s",
            response_time=f"{response_time:.3f}s",
            deleted_rows=deleted_rows
        )
        
        print(f'All refinery statistics reset by {interaction.user.display_name} ({interaction.user.id}) - {deleted_rows} records deleted')
        
    except Exception as error:
        total_time = time.time() - command_start
        logger.error(f"Error in reset command: {error}", 
                    admin_id=str(interaction.user.id),
                    admin_username=interaction.user.display_name,
                    total_time=f"{total_time:.3f}s")
        await send_response(interaction, "❌ An error occurred while resetting refinery statistics.", use_followup=use_followup, ephemeral=True)

@handle_interaction_expiration
async def ledger(interaction: discord.Interaction, use_followup: bool = True):
    """View your complete spice harvest ledger"""
    command_start = time.time()
    
    # Database operation with timing using utility function
    deposits_data, get_deposits_time = await timed_database_operation(
        "get_user_deposits",
        get_database().get_user_deposits,
        str(interaction.user.id)
    )
    
    if not deposits_data:
        embed = build_info_embed(
            title="📋 Spice Harvest Ledger",
            info_message="🏜️ You haven't harvested any spice sand yet! Use `/harvest` to start tracking your harvests.",
            color=0x95A5A6,
            footer=f"Requested by {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup, ephemeral=True)
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
    
    # Use utility function for embed building
    fields = {
        "💰 Payment Summary": f"**Unpaid Harvest:** {total_unpaid:,} sand\n**Paid Harvest:** {total_paid:,} sand\n**Total Harvests:** {len(deposits_data)}"
    }
    
    embed = build_status_embed(
        title="📋 Spice Harvest Ledger",
        description=ledger_text,
        color=0x3498DB,
        fields=fields,
        footer=f"Spice Refinery • {interaction.user.display_name}",
        thumbnail=interaction.user.display_avatar.url,
        timestamp=interaction.created_at
    )
    
    # Send response using helper function
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
    response_time = time.time() - response_start
    
    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Ledger",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        get_deposits_time=f"{get_deposits_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        result_count=len(deposits_data),
        total_unpaid=total_unpaid,
        total_paid=total_paid
    )

@handle_interaction_expiration
async def expedition_details(interaction: discord.Interaction, expedition_id: int, use_followup: bool = True):
    """View details of a specific expedition"""
    command_start = time.time()
    
    try:
        # Get expedition details using utility function
        expedition_participants, get_participants_time = await timed_database_operation(
            "get_expedition_participants",
            get_database().get_expedition_participants,
            expedition_id
        )
        
        if not expedition_participants:
            await send_response(interaction, "❌ Expedition not found or you don't have access to it.", use_followup=use_followup, ephemeral=True)
            return
        
        # Build participant list
        participant_details = []
        total_sand = 0
        
        for participant in expedition_participants:
            role = "🏭 Primary Harvester" if participant['is_harvester'] else "👥 Expedition Member"
            status = "✅ Paid" if participant['sand_amount'] == 0 else "⏳ Unpaid"
            participant_details.append(f"{role}: **{participant['username']}**\n"
                                    f"   Sand: {participant['sand_amount']:,} | Melange: {participant['melange_amount']:,} | Leftover: {participant['leftover_sand']:,} - {status}")
            total_sand += participant['sand_amount']
        
        # Use utility function for embed building
        fields = {
            "📋 Expedition Participants": "\n\n".join(participant_details)
        }
        
        embed = build_status_embed(
            title=f"🏜️ Expedition #{expedition_id}",
            description=f"**Total Sand Distributed:** {total_sand:,}\n**Participants:** {len(expedition_participants)}",
            color=0xF39C12,
            fields=fields,
            footer=f"Requested by {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        
        # Send response using helper function
        response_start = time.time()
        await send_response(interaction, embed=embed.build(), use_followup=use_followup)
        response_time = time.time() - response_start
        
        # Log performance metrics using utility function
        total_time = time.time() - command_start
        log_command_metrics(
            "Expedition Details",
            str(interaction.user.id),
            interaction.user.display_name,
            total_time,
            expedition_id=expedition_id,
            get_participants_time=f"{get_participants_time:.3f}s",
            response_time=f"{response_time:.3f}s",
            participant_count=len(expedition_participants),
            total_sand=total_sand
        )
        
    except Exception as error:
        total_time = time.time() - command_start
        logger.error(f"Error in expedition_details command: {error}", 
                    user_id=str(interaction.user.id),
                    username=interaction.user.display_name,
                    expedition_id=expedition_id,
                    total_time=f"{total_time:.3f}s")
        await send_response(interaction, "❌ An error occurred while fetching expedition details.", use_followup=use_followup, ephemeral=True)

@handle_interaction_expiration
async def payment(interaction: discord.Interaction, user: discord.Member, use_followup: bool = True):
    """Process payment for a harvester's deposits (Admin only)"""
    command_start = time.time()
    
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await send_response(interaction, "❌ You need administrator permissions to use this command.", use_followup=use_followup, ephemeral=True)
        return
    
    # Get user's unpaid deposits using utility function
    unpaid_deposits, get_deposits_time = await timed_database_operation(
        "get_user_deposits",
        get_database().get_user_deposits,
        str(user.id), False
    )
    
    if not unpaid_deposits:
        embed = build_info_embed(
            title="💰 Payment Status",
            info_message=f"🏜️ **{user.display_name}** has no unpaid harvests to process.",
            color=0x95A5A6,
            footer=f"Requested by {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup)
        return
    
    # Mark all deposits as paid using utility function
    _, update_time = await timed_database_operation(
        "mark_all_user_deposits_paid",
        get_database().mark_all_user_deposits_paid,
        str(user.id)
    )
    
    total_paid = sum(deposit['sand_amount'] for deposit in unpaid_deposits)
    
    # Use utility function for embed building
    fields = {
        "📊 Payment Summary": f"**Total Spice Sand Paid:** {total_paid:,}\n**Harvests Processed:** {len(unpaid_deposits)}"
    }
    
    embed = build_success_embed(
        title="💰 Payment Processed",
        success_message=f"**{user.display_name}** has been paid for all harvests!",
        fields=fields,
        footer=f"Payment processed by {interaction.user.display_name}",
        timestamp=interaction.created_at
    )
    
    # Send response using helper function
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
    response_time = time.time() - response_start
    
    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Payment",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        admin_id=str(interaction.user.id),
        admin_username=interaction.user.display_name,
        target_user_id=str(user.id),
        target_username=user.display_name,
        get_deposits_time=f"{get_deposits_time:.3f}s",
        update_time=f"{update_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        total_paid=total_paid,
        harvests_processed=len(unpaid_deposits)
    )
    
    print(f'Harvester {user.display_name} ({user.id}) paid {total_paid:,} spice sand by {interaction.user.display_name} ({interaction.user.id})')

@handle_interaction_expiration
async def payroll(interaction: discord.Interaction, use_followup: bool = True):
    """Process payments for all unpaid harvesters (Admin only)"""
    command_start = time.time()
    
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await send_response(interaction, "❌ You need administrator permissions to use this command.", use_followup=use_followup, ephemeral=True)
        return
    
    # Get all unpaid deposits using utility function
    unpaid_deposits, get_deposits_time = await timed_database_operation(
        "get_all_unpaid_deposits",
        get_database().get_all_unpaid_deposits
    )
    
    if not unpaid_deposits:
        embed = build_info_embed(
            title="💰 Payroll Status",
            info_message="🏜️ There are no unpaid harvests to process.",
            color=0x95A5A6,
            footer=f"Requested by {interaction.user.display_name}",
            timestamp=interaction.created_at
        )
        await send_response(interaction, embed=embed.build(), use_followup=use_followup)
        return
    
    # Group deposits by user
    user_deposits = {}
    for deposit in unpaid_deposits:
        user_id = deposit['user_id']
        if user_id not in user_deposits:
            user_deposits[user_id] = []
        user_deposits[user_id].append(deposit)
    
    # Mark all deposits as paid using utility function
    total_paid = 0
    users_paid = 0
    
    for user_id, deposits_list in user_deposits.items():
        _, update_time = await timed_database_operation(
            "mark_all_user_deposits_paid",
            get_database().mark_all_user_deposits_paid,
            user_id
        )
        user_total = sum(deposit['sand_amount'] for deposit in deposits_list)
        total_paid += user_total
        users_paid += 1
    
    # Use utility function for embed building
    fields = {
        "📊 Payroll Summary": f"**Total Spice Sand Paid:** {total_paid:,}\n**Harvesters Paid:** {users_paid}\n**Total Harvests:** {len(unpaid_deposits)}"
    }
    
    embed = build_success_embed(
        title="💰 Guild Payroll Complete",
        success_message="**All harvesters have been paid for their harvests!**",
        fields=fields,
        footer=f"Guild payroll processed by {interaction.user.display_name}",
        timestamp=interaction.created_at
    )
    
    # Send response using helper function
    response_start = time.time()
    await send_response(interaction, embed=embed.build(), use_followup=use_followup)
    response_time = time.time() - response_start
    
    # Log performance metrics using utility function
    total_time = time.time() - command_start
    log_command_metrics(
        "Payroll",
        str(interaction.user.id),
        interaction.user.display_name,
        total_time,
        admin_id=str(interaction.user.id),
        admin_username=interaction.user.display_name,
        get_deposits_time=f"{get_deposits_time:.3f}s",
        response_time=f"{response_time:.3f}s",
        total_paid=total_paid,
        users_paid=users_paid,
        total_harvests=len(unpaid_deposits)
    )
    
    print(f'Guild payroll of {total_paid:,} spice sand to {interaction.user.display_name} ({interaction.user.id})')

# Register all commands with the bot's command tree
register_commands()

# Error handling
@bot.event
async def on_command_error(ctx, error):
    error_start = time.time()
    logger.error(f"Command error: {error}", event_type="command_error", 
                 command=ctx.command.name if ctx.command else "unknown",
                 user_id=str(ctx.author.id) if ctx.author else "unknown",
                 username=ctx.author.display_name if ctx.author else "unknown",
                 error=str(error))
    print(f'Command error: {error}')

@bot.event
async def on_error(event, *args, **kwargs):
    error_start = time.time()
    logger.error(f"Discord event error: {event}", event_type="discord_error",
                 event=event, args=str(args), kwargs=str(kwargs))
    print(f'Discord event error: {event}')

# Fly.io health check endpoint
def start_health_server():
    """Start a robust HTTP server for Fly.io health checks with keep-alive"""
    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            request_start = time.time()
            
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
                
                request_time = time.time() - request_start
                logger.info(f"Health check request completed", 
                           request_time=f"{request_time:.3f}s",
                           bot_ready=bot.is_ready(),
                           guild_count=len(bot.guilds))
                
            elif self.path == '/ping':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'pong')
                
                request_time = time.time() - request_start
                logger.info(f"Ping request completed", request_time=f"{request_time:.3f}s")
                
            else:
                self.send_response(404)
                self.end_headers()
                
                request_time = time.time() - request_start
                logger.warning(f"Invalid health check request", 
                              path=self.path, 
                              request_time=f"{request_time:.3f}s")
        
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
        ping_count = 0
        while True:
            try:
                time.sleep(300)  # Every 5 minutes
                ping_start = time.time()
                response = requests.get('http://localhost:8080/ping', timeout=5)
                ping_time = time.time() - ping_start
                ping_count += 1
                
                logger.info(f"Keep-alive ping completed", 
                           ping_count=ping_count,
                           ping_time=f"{ping_time:.3f}s",
                           status_code=response.status_code)
                
            except Exception as e:
                ping_count += 1
                logger.warning(f"Keep-alive ping failed", 
                              ping_count=ping_count,
                              error=str(e))
                pass  # Ignore errors, just keep trying
    
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set")
        print("❌ ERROR: DISCORD_TOKEN environment variable is not set!")
        print("Please set the DISCORD_TOKEN environment variable in Fly.io or your .env file")
        exit(1)
    
    startup_start = time.time()
    logger.bot_event(f"Bot starting - Token present: {bool(token)}")
    print("Starting Discord bot...")
    
    try:
        bot.run(token)
    except Exception as e:
        startup_time = time.time() - startup_start
        logger.error(f"Bot startup failed", 
                    startup_time=f"{startup_time:.3f}s",
                    error=str(e))
        raise e