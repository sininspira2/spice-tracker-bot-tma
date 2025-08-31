import time
import discord
from functools import wraps
from .logger import logger
from .rate_limiter import RateLimiter
from .permissions import check_admin_permission

# Global rate limiter instance
rate_limiter = RateLimiter()

def command_handler(command_name, rate_limit=True, admin_only=False, description=None):
    """Decorator that handles common command setup, logging, rate limiting, and error handling"""
    def decorator(func):
        # Create a wrapper function that handles the command logic
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            start_time = time.time()
            user_id = str(interaction.user.id)
            username = interaction.user.display_name
            guild_id = str(interaction.guild.id) if interaction.guild else None
            guild_name = interaction.guild.name if interaction.guild else None
            
            # Log command execution
            log_data = {
                'user_id': user_id,
                'username': username,
                'guild_id': guild_id,
                'guild_name': guild_name
            }
            # Add command-specific parameters
            if args:
                log_data['args'] = args
            if kwargs:
                log_data.update(kwargs)
            
            logger.command_executed(command_name, **log_data)
            
            # Check rate limit
            if rate_limit and not rate_limiter.check_rate_limit(user_id, command_name):
                logger.rate_limit_hit(command_name, user_id, username)
                await interaction.response.send_message(
                    "⏰ Please wait before using this command again.",
                    ephemeral=True
                )
                return
            
            # Check admin permissions
            if admin_only and not check_admin_permission(interaction.user):
                logger.permission_denied(command_name, user_id, username, "Administrator")
                await interaction.response.send_message(
                    "❌ You need Administrator permissions to use this command.",
                    ephemeral=True
                )
                return
            
            try:
                # Call the actual command function
                result = await func(interaction, *args, **kwargs)
                
                # Log successful completion
                execution_time = time.time() - start_time
                success_data = {
                    'user_id': user_id,
                    'username': username,
                    'execution_time': execution_time
                }
                if result and isinstance(result, dict):
                    success_data.update(result)
                
                logger.command_success(command_name, **success_data)
                return result
                
            except Exception as error:
                # Log error
                execution_time = time.time() - start_time
                error_data = {
                    'user_id': user_id,
                    'username': username,
                    'error': str(error),
                    'execution_time': execution_time
                }
                # Add command-specific error context
                if args:
                    error_data['args'] = args
                if kwargs:
                    error_data.update(kwargs)
                
                logger.command_error(command_name, **error_data)
                print(f'Error in {command_name} command: {error}')
                
                # Send error message to user
                error_msg = f"❌ An error occurred while processing your request: {error}"
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_msg, ephemeral=True)
                else:
                    await interaction.followup.send(error_msg, ephemeral=True)
        
        # Return the wrapper function - the bot will register it manually
        return wrapper
    return decorator
