import discord
from discord.ext import commands
import asyncio
import os
import time
from dotenv import load_dotenv
from database import Database
from utils.rate_limiter import RateLimiter
from utils.permissions import check_admin_permission
from utils.logger import logger

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = False  # Not needed for slash commands
intents.reactions = True  # Enable reaction events
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database and rate limiter
database = Database()
rate_limiter = RateLimiter()

@bot.event
async def on_ready():
    if bot.user:
        logger.bot_event(
            "Bot started",
            bot_name=bot.user.name,
            bot_id=str(bot.user.id),
            guild_count=len(bot.guilds)
        )
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

@bot.tree.command(name="logsolo", description="Log sand deposits and calculate melange conversion")
@discord.app_commands.describe(amount="Amount of sand to deposit")
async def logsolo(interaction: discord.Interaction, amount: int):
    start_time = time.time()
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    guild_id = str(interaction.guild.id) if interaction.guild else None
    guild_name = interaction.guild.name if interaction.guild else None
    
    # Log command execution
    logger.command_executed(
        "logsolo",
        user_id=user_id,
        username=username,
        guild_id=guild_id,
        guild_name=guild_name,
        amount=amount
    )
    
    # Validate amount
    if amount < 1 or amount > 10000:
        logger.command_error(
            "logsolo",
            user_id=user_id,
            username=username,
            error="Invalid amount",
            amount=amount
        )
        await interaction.response.send_message(
            "❌ Amount must be between 1 and 10,000 sand.",
            ephemeral=True
        )
        return
    
    # Check rate limit
    if not rate_limiter.check_rate_limit(str(interaction.user.id), 'logsolo'):
        logger.rate_limit_hit("logsolo", user_id, username)
        await interaction.response.send_message(
            "⏰ Please wait before using this command again.",
            ephemeral=True
        )
        return
    
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    
    try:
        # Get current conversion rate
        sand_per_melange = await database.get_setting('sand_per_melange')
        sand_per_melange = int(sand_per_melange) if sand_per_melange else 50
        
        # Update user sand
        await database.upsert_user(user_id, username, amount)
        
        # Get updated user data
        user = await database.get_user(user_id)
        if not user:
            raise Exception("Failed to get user data after update")
        
        # Calculate melange conversion
        total_melange_earned = user['total_sand'] // sand_per_melange
        current_melange = user['total_melange'] or 0
        new_melange = total_melange_earned - current_melange
        
        # Update melange if new melange earned
        if new_melange > 0:
            await database.update_user_melange(user_id, new_melange)
        
        # Calculate remaining sand after conversion
        remaining_sand = user['total_sand'] % sand_per_melange
        sand_needed_for_next_melange = sand_per_melange - remaining_sand
        
        # Create embed
        embed = discord.Embed(
            title="🏜️ Sand Deposit Logged",
            color=0xE67E22,
            timestamp=interaction.created_at
        )
        
        embed.add_field(
            name="📊 Deposit Summary",
            value=f"**Sand Deposited:** {amount:,}\n**Total Sand:** {user['total_sand']:,}",
            inline=True
        )
        
        embed.add_field(
            name="✨ Melange Status",
            value=f"**Total Melange:** {(current_melange + new_melange):,}\n**Conversion Rate:** {sand_per_melange} sand = 1 melange",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Next Conversion",
            value=f"**Sand Until Next Melange:** {sand_needed_for_next_melange:,}",
            inline=False
        )
        
        # Add melange earned notification if applicable
        if new_melange > 0:
            embed.description = f"🎉 **You earned {new_melange:,} melange from this deposit!**"
        
        embed.set_footer(
            text=f"Requested by {username}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Log successful command completion
        execution_time = time.time() - start_time
        logger.command_success(
            "logsolo",
            user_id=user_id,
            username=username,
            execution_time=execution_time,
            amount=amount,
            total_sand=user['total_sand'],
            total_melange=current_melange + new_melange,
            new_melange=new_melange,
            sand_per_melange=sand_per_melange
        )
        
    except Exception as error:
        execution_time = time.time() - start_time
        logger.command_error(
            "logsolo",
            user_id=user_id,
            username=username,
            error=str(error),
            execution_time=execution_time,
            amount=amount
        )
        print(f'Error in logsolo command: {error}')
        await interaction.response.send_message(
            "❌ An error occurred while processing your sand deposit. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="myrefines", description="Show your total sand and melange statistics")
async def myrefines(interaction: discord.Interaction):
    start_time = time.time()
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    guild_id = str(interaction.guild.id) if interaction.guild else None
    guild_name = interaction.guild.name if interaction.guild else None
    
    # Log command execution
    logger.command_executed(
        "myrefines",
        user_id=user_id,
        username=username,
        guild_id=guild_id,
        guild_name=guild_name
    )
    
    # Check rate limit
    if not rate_limiter.check_rate_limit(str(interaction.user.id), 'myrefines'):
        logger.rate_limit_hit("myrefines", user_id, username)
        await interaction.response.send_message(
            "⏰ Please wait before using this command again.",
            ephemeral=True
        )
        return
    
    try:
        # Get user data
        user = await database.get_user(user_id)
        
        if not user:
            embed = discord.Embed(
                title="📊 Your Refining Statistics",
                description="🏜️ You haven't deposited any sand yet! Use `/logsolo` to start tracking your deposits.",
                color=0x95A5A6,
                timestamp=interaction.created_at
            )
            embed.set_footer(
                text=f"Requested by {username}",
                icon_url=interaction.user.display_avatar.url
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get conversion rate
        sand_per_melange = await database.get_setting('sand_per_melange')
        sand_per_melange = int(sand_per_melange) if sand_per_melange else 50
        
        # Calculate progress to next melange
        remaining_sand = user['total_sand'] % sand_per_melange
        sand_needed_for_next_melange = sand_per_melange - remaining_sand
        progress_percent = int((remaining_sand / sand_per_melange) * 100)
        
        # Create progress bar
        progress_bar_length = 10
        filled_bars = int((remaining_sand / sand_per_melange) * progress_bar_length)
        empty_bars = progress_bar_length - filled_bars
        progress_bar = '▓' * filled_bars + '░' * empty_bars
        
        # Create embed
        embed = discord.Embed(
            title="📊 Your Refining Statistics",
            color=0x3498DB,
            timestamp=interaction.created_at
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        embed.add_field(
            name="🏜️ Sand Deposits",
            value=f"**Total Sand:** {user['total_sand']:,}",
            inline=True
        )
        
        embed.add_field(
            name="✨ Melange Refined",
            value=f"**Total Melange:** {user['total_melange']:,}",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Conversion Rate",
            value=f"{sand_per_melange} sand = 1 melange",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Progress to Next Melange",
            value=f"{progress_bar} {progress_percent}%\n**Sand Needed:** {sand_needed_for_next_melange:,}",
            inline=False
        )
        
        embed.add_field(
            name="📅 Last Activity",
            value=f"<t:{int(user['last_updated'].timestamp())}:F>",
            inline=False
        )
        
        embed.set_footer(
            text=f"Spice Tracker • {username}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Log successful command completion
        execution_time = time.time() - start_time
        logger.command_success(
            "myrefines",
            user_id=user_id,
            username=username,
            execution_time=execution_time,
            total_sand=user['total_sand'],
            total_melange=user['total_melange'],
            sand_per_melange=sand_per_melange
        )
        
    except Exception as error:
        execution_time = time.time() - start_time
        logger.command_error(
            "myrefines",
            user_id=user_id,
            username=username,
            error=str(error),
            execution_time=execution_time
        )
        print(f'Error in myrefines command: {error}')
        await interaction.response.send_message(
            "❌ An error occurred while retrieving your statistics. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="leaderboard", description="Display top refiners by melange earned")
@discord.app_commands.describe(limit="Number of top users to display (default: 10)")
async def leaderboard(interaction: discord.Interaction, limit: int = 10):
    start_time = time.time()
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    guild_id = str(interaction.guild.id) if interaction.guild else None
    guild_name = interaction.guild.name if interaction.guild else None
    
    # Log command execution
    logger.command_executed(
        "leaderboard",
        user_id=user_id,
        username=username,
        guild_id=guild_id,
        guild_name=guild_name,
        limit=limit
    )
    
    # Validate limit
    if limit < 5 or limit > 25:
        logger.command_error(
            "leaderboard",
            user_id=user_id,
            username=username,
            error="Invalid limit",
            limit=limit
        )
        await interaction.response.send_message(
            "❌ Limit must be between 5 and 25.",
            ephemeral=True
        )
        return
    
    # Check rate limit
    if not rate_limiter.check_rate_limit(str(interaction.user.id), 'leaderboard'):
        logger.rate_limit_hit("leaderboard", user_id, username)
        await interaction.response.send_message(
            "⏰ Please wait before using this command again.",
            ephemeral=True
        )
        return
    
    try:
        # Get leaderboard data
        leaderboard_data = await database.get_leaderboard(limit)
        
        if not leaderboard_data:
            embed = discord.Embed(
                title="🏆 Melange Refining Leaderboard",
                description="🏜️ No refiners found yet! Be the first to start depositing sand with `/logsolo`.",
                color=0x95A5A6,
                timestamp=interaction.created_at
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Get conversion rate for display
        sand_per_melange = await database.get_setting('sand_per_melange')
        sand_per_melange = int(sand_per_melange) if sand_per_melange else 50
        
        # Create leaderboard entries
        leaderboard_text = ""
        medals = ['🥇', '🥈', '🥉']
        
        for index, user in enumerate(leaderboard_data):
            position = index + 1
            medal = medals[index] if index < 3 else f"**{position}.**"
            
            leaderboard_text += f"{medal} **{user['username']}**\n"
            leaderboard_text += f"├ Melange: {user['total_melange']:,}\n"
            leaderboard_text += f"└ Sand: {user['total_sand']:,}\n\n"
        
        # Calculate total stats
        total_melange = sum(user['total_melange'] for user in leaderboard_data)
        total_sand = sum(user['total_sand'] for user in leaderboard_data)
        
        embed = discord.Embed(
            title="🏆 Melange Refining Leaderboard",
            description=leaderboard_text,
            color=0xF39C12,
            timestamp=interaction.created_at
        )
        
        embed.add_field(
            name="📊 Community Stats",
            value=f"**Total Refiners:** {len(leaderboard_data)}\n**Total Melange:** {total_melange:,}\n**Total Sand:** {total_sand:,}",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Current Rate",
            value=f"{sand_per_melange} sand = 1 melange",
            inline=True
        )
        
        embed.set_footer(
            text=f"Showing top {len(leaderboard_data)} refiners • Updated",
            icon_url=bot.user.display_avatar.url if bot.user else None
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Log successful command completion
        execution_time = time.time() - start_time
        logger.command_success(
            "leaderboard",
            user_id=user_id,
            username=username,
            execution_time=execution_time,
            limit=limit,
            result_count=len(leaderboard_data),
            total_melange=total_melange,
            total_sand=total_sand
        )
        
    except Exception as error:
        execution_time = time.time() - start_time
        logger.command_error(
            "leaderboard",
            user_id=user_id,
            username=username,
            error=str(error),
            execution_time=execution_time,
            limit=limit
        )
        print(f'Error in leaderboard command: {error}')
        await interaction.response.send_message(
            "❌ An error occurred while retrieving the leaderboard. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="setrate", description="Set the sand to melange conversion rate (Admin only)")
@discord.app_commands.describe(sand_per_melange="Amount of sand required for 1 melange")
async def setrate(interaction: discord.Interaction, sand_per_melange: int):
    start_time = time.time()
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    guild_id = str(interaction.guild.id) if interaction.guild else None
    guild_name = interaction.guild.name if interaction.guild else None
    
    # Log command execution
    logger.command_executed(
        "setrate",
        user_id=user_id,
        username=username,
        guild_id=guild_id,
        guild_name=guild_name,
        new_rate=sand_per_melange
    )
    
    # Validate input
    if sand_per_melange < 1 or sand_per_melange > 1000:
        logger.command_error(
            "setrate",
            user_id=user_id,
            username=username,
            error="Invalid rate",
            new_rate=sand_per_melange
        )
        await interaction.response.send_message(
            "❌ Conversion rate must be between 1 and 1,000.",
            ephemeral=True
        )
        return
    
    # Check admin permissions
    if not interaction.guild or not check_admin_permission(interaction.user, interaction.guild):
        logger.permission_denied("setrate", user_id, username, "Administrator")
        await interaction.response.send_message(
            "❌ You need Administrator permissions to use this command.",
            ephemeral=True
        )
        return
    
    try:
        # Get current rate for comparison
        current_rate = await database.get_setting('sand_per_melange')
        current_rate = int(current_rate) if current_rate else 50
        
        # Update the conversion rate
        await database.set_setting('sand_per_melange', str(sand_per_melange))
        
        embed = discord.Embed(
            title="⚙️ Conversion Rate Updated",
            color=0x27AE60,
            timestamp=interaction.created_at
        )
        
        embed.add_field(
            name="📊 Rate Change",
            value=f"**Previous Rate:** {current_rate} sand = 1 melange\n**New Rate:** {sand_per_melange} sand = 1 melange",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Important Note",
            value="This change affects future calculations only. Existing user stats remain unchanged.",
            inline=False
        )
        
        embed.set_footer(
            text=f"Changed by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Log successful command completion
        execution_time = time.time() - start_time
        logger.command_success(
            "setrate",
            user_id=user_id,
            username=username,
            execution_time=execution_time,
            old_rate=current_rate,
            new_rate=sand_per_melange
        )
        
        # Log the change
        print(f'Conversion rate changed from {current_rate} to {sand_per_melange} by {interaction.user.display_name} ({interaction.user.id})')
        
    except Exception as error:
        execution_time = time.time() - start_time
        logger.command_error(
            "setrate",
            user_id=user_id,
            username=username,
            error=str(error),
            execution_time=execution_time,
            new_rate=sand_per_melange
        )
        print(f'Error in setrate command: {error}')
        await interaction.response.send_message(
            "❌ An error occurred while updating the conversion rate. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="spicesplit", description="Split spice sand among team members")
@discord.app_commands.describe(
    total_sand="Total spice sand collected to split",
    participants="Number of team members participating",
    harvester_percentage="Percentage for harvester (default: 25%)"
)
async def spicesplit(interaction: discord.Interaction, total_sand: int, participants: int, harvester_percentage: float = 25.0):
    start_time = time.time()
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    guild_id = str(interaction.guild.id) if interaction.guild else None
    guild_name = interaction.guild.name if interaction.guild else None
    
    # Log command execution
    logger.command_executed(
        "spicesplit",
        user_id=user_id,
        username=username,
        guild_id=guild_id,
        guild_name=guild_name,
        total_sand=total_sand,
        participants=participants,
        harvester_percentage=harvester_percentage
    )
    
    # Check rate limit
    if not rate_limiter.check_rate_limit(str(interaction.user.id), 'spicesplit'):
        logger.rate_limit_hit("spicesplit", user_id, username)
        await interaction.response.send_message(
            "⏰ Please wait before using this command again.",
            ephemeral=True
        )
        return
    
    # Validate inputs
    if total_sand < 1:
        logger.command_error(
            "spicesplit",
            user_id=user_id,
            username=username,
            error="Invalid total_sand",
            total_sand=total_sand
        )
        await interaction.response.send_message(
            "❌ Total sand must be at least 1.",
            ephemeral=True
        )
        return
    
    if participants < 1:
        logger.command_error(
            "spicesplit",
            user_id=user_id,
            username=username,
            error="Invalid participants",
            participants=participants
        )
        await interaction.response.send_message(
            "❌ Number of participants must be at least 1.",
            ephemeral=True
        )
        return
    
    if harvester_percentage < 0 or harvester_percentage > 100:
        logger.command_error(
            "spicesplit",
            user_id=user_id,
            username=username,
            error="Invalid harvester_percentage",
            harvester_percentage=harvester_percentage
        )
        await interaction.response.send_message(
            "❌ Harvester percentage must be between 0 and 100.",
            ephemeral=True
        )
        return
    
    try:
        # Get conversion rate
        sand_per_melange = await database.get_setting('sand_per_melange')
        sand_per_melange = int(sand_per_melange) if sand_per_melange else 50
        
        # Calculate harvester share
        harvester_sand = int(total_sand * (harvester_percentage / 100))
        remaining_sand = total_sand - harvester_sand
        
        # Convert harvester to melange
        harvester_melange = harvester_sand // sand_per_melange
        harvester_leftover_sand = harvester_sand % sand_per_melange
        
        # Calculate individual team member shares
        sand_per_participant = remaining_sand // participants
        melange_per_participant = sand_per_participant // sand_per_melange
        leftover_sand_per_participant = sand_per_participant % sand_per_melange
        
        # Calculate total distributed and remainder
        total_distributed = sand_per_participant * participants
        remainder_sand = remaining_sand - total_distributed
        
        # Create embed
        embed = discord.Embed(
            title="🏜️ Spice Split Operation",
            description=f"**Total Sand:** {total_sand:,}\n**Participants:** {participants}\n**Harvester Cut:** {harvester_percentage}%",
            color=0xF39C12,
            timestamp=interaction.created_at
        )
        
        embed.add_field(
            name="🏭 Harvester Share",
            value=f"**Sand:** {harvester_sand:,}\n**Melange:** {harvester_melange:,}\n**Leftover Sand:** {harvester_leftover_sand:,}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Each Team Member Gets",
            value=f"**Sand:** {sand_per_participant:,}\n**Melange:** {melange_per_participant:,}\n**Leftover Sand:** {leftover_sand_per_participant:,}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Split Summary",
            value=f"**Team Pool:** {remaining_sand:,} sand\n**Total Distributed:** {total_distributed:,} sand\n**Remainder:** {remainder_sand:,} sand",
            inline=False
        )
        
        embed.set_footer(
            text=f"Split initiated by {interaction.user.display_name} • Conversion: {sand_per_melange} sand = 1 melange",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Send the message
        await interaction.response.send_message(embed=embed)
        
        # Log successful command completion
        execution_time = time.time() - start_time
        logger.command_success(
            "spicesplit",
            user_id=user_id,
            username=username,
            execution_time=execution_time,
            total_sand=total_sand,
            participants=participants,
            harvester_percentage=harvester_percentage,
            harvester_sand=harvester_sand,
            harvester_melange=harvester_melange,
            sand_per_participant=sand_per_participant,
            melange_per_participant=melange_per_participant
        )
        
    except Exception as error:
        execution_time = time.time() - start_time
        logger.command_error(
            "spicesplit",
            user_id=user_id,
            username=username,
            error=str(error),
            execution_time=execution_time,
            total_sand=total_sand,
            participants=participants,
            harvester_percentage=harvester_percentage
        )
        print(f'Error in spicesplit command: {error}')
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An error occurred while creating the spice split. Please try again later.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ An error occurred while processing the spice split.",
                ephemeral=True
            )


async def update_split_message(message, split_data):
    """Update the split message with current participants and their shares"""
    try:
        total_participants = len(split_data['pilots']) + len(split_data['crawlers'])
        
        if total_participants == 0:
            per_person_sand = 0
            per_person_melange = 0
            per_person_leftover = 0
        else:
            per_person_sand = split_data['remaining_sand'] // total_participants
            per_person_melange = per_person_sand // split_data['sand_per_melange']
            per_person_leftover = per_person_sand % split_data['sand_per_melange']
        
        # Create updated embed
        embed = discord.Embed(
            title="🏜️ Spice Split Operation",
            description=f"React with your role to join the split!\n\n**Total Sand:** {split_data['total_sand']:,}\n**Harvester Cut:** {split_data['harvester_percentage']}%",
            color=0xF39C12,
            timestamp=message.created_at
        )
        
        # Harvester share
        harvester_melange = split_data['harvester_sand'] // split_data['sand_per_melange']
        harvester_leftover = split_data['harvester_sand'] % split_data['sand_per_melange']
        
        embed.add_field(
            name="🏭 Harvester Share",
            value=f"**Sand:** {split_data['harvester_sand']:,}\n**Melange:** {harvester_melange:,}\n**Leftover Sand:** {harvester_leftover:,}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Team Share Pool",
            value=f"**Sand to Split:** {split_data['remaining_sand']:,}\n**Participants:** {total_participants}",
            inline=True
        )
        
        if total_participants > 0:
            embed.add_field(
                name="💰 Per Person Share",
                value=f"**Sand:** {per_person_sand:,}\n**Melange:** {per_person_melange:,}\n**Leftover Sand:** {per_person_leftover:,}",
                inline=True
            )
        
        # Build participants list
        participants_text = ""
        
        if split_data['pilots']:
            participants_text += "🛩️ **Ornithopter Pilots:**\n"
            for user_id in split_data['pilots']:
                try:
                    user = await bot.fetch_user(user_id)
                    member = message.guild.get_member(user_id) if message.guild else None
                    display_name = member.display_name if member else user.display_name
                    participants_text += f"• {display_name}\n"
                except:
                    participants_text += f"• Unknown User\n"
            participants_text += "\n"
        
        if split_data['crawlers']:
            participants_text += "🛻 **Sand Crawler Operators:**\n"
            for user_id in split_data['crawlers']:
                try:
                    user = await bot.fetch_user(user_id)
                    member = message.guild.get_member(user_id) if message.guild else None
                    display_name = member.display_name if member else user.display_name
                    participants_text += f"• {display_name}\n"
                except:
                    participants_text += f"• Unknown User\n"
        
        if not participants_text:
            participants_text = "🛩️ **Ornithopter Pilots:** None\n🛻 **Sand Crawler Operators:** None"
        
        embed.add_field(
            name="👥 Current Participants",
            value=participants_text,
            inline=False
        )
        
        embed.set_footer(
            text=f"Split initiated by {split_data['initiator']} • Conversion: {split_data['sand_per_melange']} sand = 1 melange",
            icon_url=None
        )
        
        await message.edit(embed=embed)
        
    except Exception as error:
        print(f'Error updating split message: {error}')

@bot.tree.command(name="help", description="Show all available commands and their descriptions")
async def help_command(interaction: discord.Interaction):
    start_time = time.time()
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    guild_id = str(interaction.guild.id) if interaction.guild else None
    guild_name = interaction.guild.name if interaction.guild else None
    
    # Log command execution
    logger.command_executed(
        "help",
        user_id=user_id,
        username=username,
        guild_id=guild_id,
        guild_name=guild_name
    )
    
    try:
        # Get conversion rate for display
        sand_per_melange = await database.get_setting('sand_per_melange')
        sand_per_melange = int(sand_per_melange) if sand_per_melange else 50
        
        embed = discord.Embed(
            title="🏜️ Spice Tracker Commands",
            description="Track your sand deposits and melange refining progress!",
            color=0xF39C12,
            timestamp=interaction.created_at
        )
        
        # User commands
        embed.add_field(
            name="📊 User Commands",
            value=(
                "**`/logsolo [amount]`**\n"
                "Log sand deposits (1-10,000). Automatically converts to melange.\n\n"
                "**`/myrefines`**\n"
                "View your total sand, melange, and progress to next conversion.\n\n"
                "**`/leaderboard [limit]`**\n"
                "Show top refiners by melange earned (5-25 users).\n\n"
                "**`/spicesplit [total_sand] [harvester_%]`**\n"
                "Split spice among team members. React with 🛩️ (pilots) or 🛻 (crawlers).\n\n"
                "**`/help`**\n"
                "Display this help message with all commands."
            ),
            inline=False
        )
        
        # Admin commands
        embed.add_field(
            name="⚙️ Admin Commands",
            value=(
                "**`/setrate [sand_per_melange]`**\n"
                "Change conversion rate (1-1,000 sand per melange).\n\n"
                "**`/resetstats confirm:True`**\n"
                "Reset all user statistics (requires confirmation)."
            ),
            inline=False
        )
        
        # Current settings
        embed.add_field(
            name="📋 Current Settings",
            value=f"**Conversion Rate:** {sand_per_melange} sand = 1 melange",
            inline=False
        )
        
        # Example usage
        embed.add_field(
            name="💡 Example Usage",
            value=(
                "• `/logsolo 250` - Deposit 250 sand\n"
                "• `/myrefines` - Check your stats\n"
                "• `/leaderboard 15` - Show top 15 refiners\n"
                "• `/spicesplit 1000 30` - Split 1000 sand, 30% to harvester"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="Spice Tracker Bot - Dune-themed resource tracking",
            icon_url=bot.user.display_avatar.url if bot.user else None
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Log successful command completion
        execution_time = time.time() - start_time
        logger.command_success(
            "help",
            user_id=user_id,
            username=username,
            execution_time=execution_time
        )
        
    except Exception as error:
        execution_time = time.time() - start_time
        logger.command_error(
            "help",
            user_id=user_id,
            username=username,
            error=str(error),
            execution_time=execution_time
        )
        print(f'Error in help command: {error}')
        await interaction.response.send_message(
            "❌ An error occurred while displaying help. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="resetstats", description="Reset all user statistics (Admin only - USE WITH CAUTION)")
@discord.app_commands.describe(confirm="Confirm that you want to delete all user data")
async def resetstats(interaction: discord.Interaction, confirm: bool):
    start_time = time.time()
    user_id = str(interaction.user.id)
    username = interaction.user.display_name
    guild_id = str(interaction.guild.id) if interaction.guild else None
    guild_name = interaction.guild.name if interaction.guild else None
    
    # Log command execution
    logger.command_executed(
        "resetstats",
        user_id=user_id,
        username=username,
        guild_id=guild_id,
        guild_name=guild_name,
        confirm=confirm
    )
    
    # Check admin permissions
    if not interaction.guild or not check_admin_permission(interaction.user, interaction.guild):
        logger.permission_denied("resetstats", user_id, username, "Administrator")
        await interaction.response.send_message(
            "❌ You need Administrator permissions to use this command.",
            ephemeral=True
        )
        return
    
    if not confirm:
        embed = discord.Embed(
            title="⚠️ Reset Cancelled",
            description="You must set the `confirm` parameter to `True` to proceed with the reset.",
            color=0xE74C3C
        )
        embed.add_field(
            name="🔄 How to Reset",
            value="Use `/resetstats confirm:True` to confirm the reset.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        # Reset all user statistics
        deleted_rows = await database.reset_all_stats()
        
        embed = discord.Embed(
            title="🔄 Statistics Reset Complete",
            description="⚠️ **All user statistics have been permanently deleted!**",
            color=0xE74C3C,
            timestamp=interaction.created_at
        )
        
        embed.add_field(
            name="📊 Reset Summary",
            value=f"**Users Affected:** {deleted_rows}\n**Data Cleared:** All sand deposits and melange statistics",
            inline=False
        )
        
        embed.add_field(
            name="✅ What Remains",
            value="Conversion rates and bot settings are preserved.",
            inline=False
        )
        
        embed.set_footer(
            text=f"Reset performed by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Log successful command completion
        execution_time = time.time() - start_time
        logger.command_success(
            "resetstats",
            user_id=user_id,
            username=username,
            execution_time=execution_time,
            deleted_rows=deleted_rows
        )
        
        # Log the reset action
        print(f'All user statistics reset by {interaction.user.display_name} ({interaction.user.id}) - {deleted_rows} records deleted')
        
    except Exception as error:
        execution_time = time.time() - start_time
        logger.command_error(
            "resetstats",
            user_id=user_id,
            username=username,
            error=str(error),
            execution_time=execution_time
        )
        print(f'Error in resetstats command: {error}')
        await interaction.response.send_message(
            "❌ An error occurred while resetting statistics. Please try again later.",
            ephemeral=True
        )

# Error handling
@bot.event
async def on_command_error(ctx, error):
    logger.error(
        f"Command error: {error}",
        event_type="command_error",
        command=ctx.command.name if ctx.command else "unknown",
        user_id=str(ctx.author.id) if ctx.author else "unknown",
        username=ctx.author.display_name if ctx.author else "unknown",
        error=str(error)
    )
    print(f'Command error: {error}')

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(
        f"Discord event error: {event}",
        event_type="discord_error",
        event=event,
        args=str(args),
        kwargs=str(kwargs)
    )
    print(f'Discord event error: {event}')

# Railway health check endpoint (optional - for monitoring)
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
            # Suppress HTTP server logs
            pass
    
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