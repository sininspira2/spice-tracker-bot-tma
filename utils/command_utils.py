"""
Utility functions for Discord bot commands to eliminate code duplication.
"""
import time
from typing import Dict, Any, Callable, Optional
from discord.ext import commands
import discord
from .logger import logger


def create_command_function(cmd_data: Dict[str, Any], cmd_name: str, bot: commands.Bot):
    """Generic command factory that handles all parameter types"""
    if 'params' not in cmd_data:
        # Command without parameters
        @bot.tree.command(name=cmd_name, description=cmd_data['description'])
        async def wrapper(interaction: discord.Interaction):
            # The decorator will add use_followup parameter automatically
            await cmd_data['function'](interaction)
        return wrapper
    
    # Create command with proper parameter types based on the specific command
    if cmd_name == 'harvest':
        @bot.tree.command(name=cmd_name, description=cmd_data['description'])
        async def wrapper(interaction: discord.Interaction, amount: int):
            # The decorator will add use_followup parameter automatically
            await cmd_data['function'](interaction, amount)
    elif cmd_name == 'leaderboard':
        @bot.tree.command(name=cmd_name, description=cmd_data['description'])
        async def wrapper(interaction: discord.Interaction, limit: int = 10):
            # The decorator will add use_followup parameter automatically
            await cmd_data['function'](interaction, limit)
    elif cmd_name == 'split':
        @bot.tree.command(name=cmd_name, description=cmd_data['description'])
        async def wrapper(interaction: discord.Interaction, total_sand: int, harvester_percentage: float = None):
            # The decorator will add use_followup parameter automatically
            await cmd_data['function'](interaction, total_sand, harvester_percentage)
    elif cmd_name == 'reset':
        @bot.tree.command(name=cmd_name, description=cmd_data['description'])
        async def wrapper(interaction: discord.Interaction, confirm: bool):
            # The decorator will add use_followup parameter automatically
            await cmd_data['function'](interaction, confirm)
    elif cmd_name == 'payment':
        @bot.tree.command(name=cmd_name, description=cmd_data['description'])
        async def wrapper(interaction: discord.Interaction, user: discord.Member):
            # The decorator will add use_followup parameter automatically
            await cmd_data['function'](interaction, user)
    elif cmd_name == 'expedition':
        @bot.tree.command(name=cmd_name, description=cmd_data['description'])
        async def wrapper(interaction: discord.Interaction, expedition_id: int):
            # The decorator will add use_followup parameter automatically
            await cmd_data['function'](interaction, expedition_id)
    else:
        # Generic fallback for other commands
        @bot.tree.command(name=cmd_name, description=cmd_data['description'])
        async def wrapper(interaction: discord.Interaction):
            # The decorator will add use_followup parameter automatically
            await cmd_data['function'](interaction)
    
    # Add parameter descriptions
    for param_name, param_desc in cmd_data['params'].items():
        wrapper = discord.app_commands.describe(**{param_name: param_desc})(wrapper)
    
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


def build_command_embed(title: str, description: str = None, color: int = 0x3498DB, 
                       fields: Optional[Dict[str, str]] = None, footer: str = None, 
                       thumbnail: str = None, timestamp=None) -> discord.Embed:
    """Build a standardized embed for commands to eliminate repetitive embed creation code"""
    from .embed_builder import EmbedBuilder
    
    embed = EmbedBuilder(title, description=description, color=color, timestamp=timestamp)
    
    if fields:
        for field_name, field_value in fields.items():
            embed.add_field(field_name, field_value)
    
    if footer:
        embed.set_footer(footer)
    
    if thumbnail:
        embed.set_thumbnail(thumbnail)
    
    return embed


def log_command_metrics(command_name: str, user_id: str, username: str, 
                       total_time: float, **additional_metrics):
    """Centralized logging for command metrics to eliminate repetitive logging code"""
    logger.info(f"{command_name} command completed", 
               user_id=user_id,
               username=username,
               total_time=f"{total_time:.3f}s",
               **additional_metrics)
