import discord
from discord.ext import commands
import os
import time
from dotenv import load_dotenv
from database import Database
from utils.decorators import command_handler
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
        logger.database_operation("initialize", "database", True)
        print('Database initialized successfully.')
    except Exception as error:
        logger.database_operation("initialize", "database", False, error=str(error))
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

@command_handler("logsolo", rate_limit=True)
async def logsolo(interaction: discord.Interaction, amount: int):
    """Log sand deposits and calculate melange conversion"""
    # Validate amount
    if not 1 <= amount <= 10000:
        raise ValueError("Amount must be between 1 and 10,000 sand.")
    
    # Get conversion rate and update user
    sand_per_melange = int(await database.get_setting('sand_per_melange') or 50)
    await database.upsert_user(str(interaction.user.id), interaction.user.display_name, amount)
    user = await database.get_user(str(interaction.user.id))
    
    # Calculate melange conversion
    total_melange_earned = user['total_sand'] // sand_per_melange
    current_melange = user['total_melange'] or 0
    new_melange = total_melange_earned - current_melange
    
    if new_melange > 0:
        await database.update_user_melange(str(interaction.user.id), new_melange)
    
    # Build response
    remaining_sand = user['total_sand'] % sand_per_melange
    sand_needed = sand_per_melange - remaining_sand
    
    embed = (EmbedBuilder("🏜️ Sand Deposit Logged", color=0xE67E22, timestamp=interaction.created_at)
             .add_field("📊 Deposit Summary", f"**Sand Deposited:** {amount:,}\n**Total Sand:** {user['total_sand']:,}")
             .add_field("✨ Melange Status", f"**Total Melange:** {(current_melange + new_melange):,}\n**Conversion Rate:** {sand_per_melange} sand = 1 melange")
             .add_field("🎯 Next Conversion", f"**Sand Until Next Melange:** {sand_needed:,}", inline=False)
             .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
    
    if new_melange > 0:
        embed.set_description(f"🎉 **You earned {new_melange:,} melange from this deposit!**")
    
    await interaction.response.send_message(embed.build())
    
    return {
        'amount': amount,
        'total_sand': user['total_sand'],
        'total_melange': current_melange + new_melange,
        'new_melange': new_melange,
        'sand_per_melange': sand_per_melange
    }

@command_handler("myrefines", rate_limit=True)
async def myrefines(interaction: discord.Interaction):
    """Show your total sand and melange statistics"""
    user = await database.get_user(str(interaction.user.id))
    
    if not user:
        embed = (EmbedBuilder("📊 Your Refining Statistics", color=0x95A5A6, timestamp=interaction.created_at)
                 .set_description("🏜️ You haven't deposited any sand yet! Use `/logsolo` to start tracking your deposits.")
                 .set_footer(f"Requested by {interaction.user.display_name}", interaction.user.display_avatar.url))
        await interaction.response.send_message(embed.build(), ephemeral=True)
        return
    
    # Calculate progress
    sand_per_melange = int(await database.get_setting('sand_per_melange') or 50)
    remaining_sand = user['total_sand'] % sand_per_melange
    sand_needed = sand_per_melange - remaining_sand
    progress_percent = int((remaining_sand / sand_per_melange) * 100)
    
    # Create progress bar
    progress_bar_length = 10
    filled_bars = int((remaining_sand / sand_per_melange) * progress_bar_length)
    progress_bar = '▓' * filled_bars + '░' * (progress_bar_length - filled_bars)
    
    embed = (EmbedBuilder("📊 Your Refining Statistics", color=0x3498DB, timestamp=interaction.created_at)
             .set_thumbnail(interaction.user.display_avatar.url)
             .add_field("🏜️ Sand Deposits", f"**Total Sand:** {user['total_sand']:,}")
             .add_field("✨ Melange Refined", f"**Total Melange:** {user['total_melange']:,}")
             .add_field("⚙️ Conversion Rate", f"{sand_per_melange} sand = 1 melange")
             .add_field("🎯 Progress to Next Melange", f"{progress_bar} {progress_percent}%\n**Sand Needed:** {sand_needed:,}", inline=False)
             .add_field("📅 Last Activity", f"<t:{int(user['last_updated'].timestamp())}:F>", inline=False)
             .set_footer(f"Spice Tracker • {interaction.user.display_name}", interaction.user.display_avatar.url))
    
    await interaction.response.send_message(embed.build())
    
    return {
        'total_sand': user['total_sand'],
        'total_melange': user['total_melange'],
        'sand_per_melange': sand_per_melange
    }

@command_handler("leaderboard", rate_limit=True)
async def leaderboard(interaction: discord.Interaction, limit: int = 10):
    """Display top refiners by melange earned"""
    # Validate limit
    if not 5 <= limit <= 25:
        raise ValueError("Limit must be between 5 and 25.")
    
    leaderboard_data = await database.get_leaderboard(limit)
    
    if not leaderboard_data:
        embed = EmbedBuilder("🏆 Melange Refining Leaderboard", color=0x95A5A6, timestamp=interaction.created_at)
        embed.set_description("🏜️ No refiners found yet! Be the first to start depositing sand with `/logsolo`.")
        await interaction.response.send_message(embed.build())
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
    
    embed = (EmbedBuilder("🏆 Melange Refining Leaderboard", description=leaderboard_text, color=0xF39C12, timestamp=interaction.created_at)
             .add_field("📊 Community Stats", f"**Total Refiners:** {len(leaderboard_data)}\n**Total Melange:** {total_melange:,}\n**Total Sand:** {total_sand:,}")
             .add_field("⚙️ Current Rate", f"{sand_per_melange} sand = 1 melange")
             .set_footer(f"Showing top {len(leaderboard_data)} refiners • Updated", bot.user.display_avatar.url if bot.user else None))
    
    await interaction.response.send_message(embed.build())
    
    return {
        'limit': limit,
        'result_count': len(leaderboard_data),
        'total_melange': total_melange,
        'total_sand': total_sand
    }

@command_handler("setrate", admin_only=True)
async def setrate(interaction: discord.Interaction, sand_per_melange: int):
    """Set the sand to melange conversion rate (Admin only)"""
    # Validate input
    if not 1 <= sand_per_melange <= 1000:
        raise ValueError("Conversion rate must be between 1 and 1,000.")
    
    # Get current rate and update
    current_rate = int(await database.get_setting('sand_per_melange') or 50)
    await database.set_setting('sand_per_melange', str(sand_per_melange))
    
    embed = (EmbedBuilder("⚙️ Conversion Rate Updated", color=0x27AE60, timestamp=interaction.created_at)
             .add_field("📊 Rate Change", f"**Previous Rate:** {current_rate} sand = 1 melange\n**New Rate:** {sand_per_melange} sand = 1 melange", inline=False)
             .add_field("⚠️ Important Note", "This change affects future calculations only. Existing user stats remain unchanged.", inline=False)
             .set_footer(f"Changed by {interaction.user.display_name}", interaction.user.display_avatar.url))
    
    await interaction.response.send_message(embed.build())
    print(f'Conversion rate changed from {current_rate} to {sand_per_melange} by {interaction.user.display_name} ({interaction.user.id})')
    
    return {
        'old_rate': current_rate,
        'new_rate': sand_per_melange
    }

@command_handler("spicesplit", rate_limit=True)
async def spicesplit(interaction: discord.Interaction, total_sand: int, participants: int, harvester_percentage: float = None):
    """Split spice sand among team members"""
    # Use environment variable if no harvester_percentage provided
    if harvester_percentage is None:
        harvester_percentage = float(os.getenv('DEFAULT_HARVESTER_PERCENTAGE', 15.0))
    # Validate inputs
    if total_sand < 1:
        raise ValueError("Total sand must be at least 1.")
    if participants < 1:
        raise ValueError("Number of participants must be at least 1.")
    if not 0 <= harvester_percentage <= 100:
        raise ValueError("Harvester percentage must be between 0 and 100.")
    
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
    
    embed = (EmbedBuilder("🏜️ Spice Split Operation", 
                          description=f"**Total Sand:** {total_sand:,}\n**Participants:** {participants}\n**Harvester Cut:** {harvester_percentage}%",
                          color=0xF39C12, timestamp=interaction.created_at)
             .add_field("🏭 Harvester Share", f"**Sand:** {harvester_sand:,}\n**Melange:** {harvester_melange:,}\n**Leftover Sand:** {harvester_leftover_sand:,}")
             .add_field("👥 Each Team Member Gets", f"**Sand:** {sand_per_participant:,}\n**Melange:** {melange_per_participant:,}\n**Leftover Sand:** {leftover_sand_per_participant:,}")
             .add_field("📊 Split Summary", f"**Team Pool:** {remaining_sand:,} sand\n**Total Distributed:** {total_distributed:,} sand\n**Remainder:** {remainder_sand:,} sand", inline=False)
             .set_footer(f"Split initiated by {interaction.user.display_name} • Conversion: {sand_per_melange} sand = 1 melange", interaction.user.display_avatar.url))
    
    await interaction.response.send_message(embed.build())
    
    return {
        'total_sand': total_sand,
        'participants': participants,
        'harvester_percentage': harvester_percentage,
        'harvester_sand': harvester_sand,
        'harvester_melange': harvester_melange,
        'sand_per_participant': sand_per_participant,
        'melange_per_participant': melange_per_participant
    }

@command_handler("help")
async def help_command(interaction: discord.Interaction):
    """Show all available commands and their descriptions"""
    sand_per_melange = int(await database.get_setting('sand_per_melange') or 50)
    
    embed = (EmbedBuilder("🏜️ Spice Tracker Commands", 
                          description="Track your sand deposits and melange refining progress!",
                          color=0xF39C12, timestamp=interaction.created_at)
             .add_field("📊 User Commands", 
                       "**`/logsolo [amount]`**\nLog sand deposits (1-10,000). Automatically converts to melange.\n\n"
                       "**`/myrefines`**\nView your total sand, melange, and progress to next conversion.\n\n"
                       "**`/leaderboard [limit]`**\nShow top refiners by melange earned (5-25 users).\n\n"
                       "**`/spicesplit [total_sand] [harvester_%]`**\nSplit spice among team members. Harvester % is optional (uses default if not specified).\n\n"
                       "**`/help`**\nDisplay this help message with all commands.", inline=False)
             .add_field("⚙️ Admin Commands", 
                       "**`/setrate [sand_per_melange]`**\nChange conversion rate (1-1,000 sand per melange).\n\n"
                       "**`/resetstats confirm:True`**\nReset all user statistics (requires confirmation).", inline=False)
             .add_field("📋 Current Settings", f"**Conversion Rate:** {sand_per_melange} sand = 1 melange\n**Default Harvester %:** {os.getenv('DEFAULT_HARVESTER_PERCENTAGE', '25.0')}%", inline=False)
             .add_field("💡 Example Usage", 
                       "• `/logsolo 250` - Deposit 250 sand\n"
                       "• `/myrefines` - Check your stats\n"
                       "• `/leaderboard 15` - Show top 15 refiners\n"
                       "• `/spicesplit 1000 30` - Split 1000 sand, 30% to harvester\n"
                       "• `/spicesplit 1000` - Split 1000 sand using default harvester %", inline=False)
             .set_footer("Spice Tracker Bot - Dune-themed resource tracking", bot.user.display_avatar.url if bot.user else None))
    
    await interaction.response.send_message(embed.build())

@command_handler("resetstats", admin_only=True)
async def resetstats(interaction: discord.Interaction, confirm: bool):
    """Reset all user statistics (Admin only - USE WITH CAUTION)"""
    if not confirm:
        embed = (EmbedBuilder("⚠️ Reset Cancelled", color=0xE74C3C)
                 .set_description("You must set the `confirm` parameter to `True` to proceed with the reset.")
                 .add_field("🔄 How to Reset", "Use `/resetstats confirm:True` to confirm the reset.", inline=False))
        await interaction.response.send_message(embed.build(), ephemeral=True)
        return
    
    # Reset all user statistics
    deleted_rows = await database.reset_all_stats()
    
    embed = (EmbedBuilder("🔄 Statistics Reset Complete", 
                          description="⚠️ **All user statistics have been permanently deleted!**",
                          color=0xE74C3C, timestamp=interaction.created_at)
             .add_field("📊 Reset Summary", f"**Users Affected:** {deleted_rows}\n**Data Cleared:** All sand deposits and melange statistics", inline=False)
             .add_field("✅ What Remains", "Conversion rates and bot settings are preserved.", inline=False)
             .set_footer(f"Reset performed by {interaction.user.display_name}", interaction.user.display_avatar.url))
    
    await interaction.response.send_message(embed.build())
    print(f'All user statistics reset by {interaction.user.display_name} ({interaction.user.id}) - {deleted_rows} records deleted')
    
    return {'deleted_rows': deleted_rows}

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