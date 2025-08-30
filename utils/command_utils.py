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
            await cmd_data['function'](interaction)
        return wrapper
    
    # Command with parameters - create based on parameter types
    param_types = {}
    for param_name in cmd_data['params'].keys():
        if param_name == 'amount':
            param_types[param_name] = int
        elif param_name == 'limit':
            param_types[param_name] = int
        elif param_name == 'total_sand':
            param_types[param_name] = int
        elif param_name == 'harvester_percentage':
            param_types[param_name] = float
        elif param_name == 'confirm':
            param_types[param_name] = bool
        elif param_name == 'user':
            param_types[param_name] = discord.Member
        elif param_name == 'expedition_id':
            param_types[param_name] = int
        else:
            param_types[param_name] = str  # Default to string
    
    # Create command with proper parameter types
    @bot.tree.command(name=cmd_name, description=cmd_data['description'])
    async def wrapper(interaction: discord.Interaction, **kwargs):
        # Convert parameters to proper types and call function
        converted_kwargs = {}
        for param_name, param_type in param_types.items():
            if param_name in kwargs:
                try:
                    converted_kwargs[param_name] = param_type(kwargs[param_name])
                except (ValueError, TypeError):
                    # Import send_response here to avoid circular imports
                    from bot import send_response
                    await send_response(interaction, f"❌ Invalid value for {param_name}. Expected {param_type.__name__}.", ephemeral=True)
                    return
        
        await cmd_data['function'](interaction, **converted_kwargs)
    
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
