"""
Commands package for the Spice Tracker Bot.
Contains all the individual command implementations.
"""

import os
import importlib
import inspect
from typing import Dict, Any, Callable, List, Tuple

from .settings import Settings

# Automatically discover and import all command modules
def discover_commands():
    """Automatically discover all command modules in this package"""
    commands = {}
    metadata = {}
    signatures = {}  # New: store function signatures

    # Get the directory this file is in
    current_dir = os.path.dirname(__file__)

    # Find all .py files (excluding __init__.py and __pycache__)
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # Remove .py extension

            try:
                # Import the module
                module = importlib.import_module(f'.{module_name}', package=__name__)

                # Get the command function - look for common patterns
                command_func = None
                if hasattr(module, module_name):  # Function same name as module
                    command_func = getattr(module, module_name)
                elif hasattr(module, f'{module_name}_command'):  # Function with _command suffix
                    command_func = getattr(module, f'{module_name}_command')
                elif hasattr(module, f'{module_name}_details'):  # Function with _details suffix
                    command_func = getattr(module, f'{module_name}_details')
                elif hasattr(module, 'help_command') and module_name == 'help':  # Special case for help
                    command_func = getattr(module, 'help_command')
                # No special cases needed - file name matches function name

                if command_func and inspect.isfunction(command_func):
                    commands[module_name] = command_func

                    # Extract function signature for Discord.py registration
                    # Try to get the original function signature if it's been decorated
                    original_func = command_func
                    if hasattr(command_func, '__wrapped__'):
                        original_func = command_func.__wrapped__

                    sig = inspect.signature(original_func)
                    params = list(sig.parameters.values())

                    # Skip the first parameter (interaction) and internal parameters
                    discord_params = []
                    for param in params[1:]:  # Skip interaction parameter
                        if param.name != 'use_followup':  # Skip internal parameter
                            discord_params.append({
                                'name': param.name,
                                'annotation': param.annotation,
                                'default': param.default if param.default != inspect.Parameter.empty else None
                            })

                    signatures[module_name] = discord_params

                # Get the metadata
                command_metadata = getattr(module, 'COMMAND_METADATA', None)
                if command_metadata:
                    metadata[module_name] = command_metadata

            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")

    return commands, metadata, signatures

# Auto-discover commands, metadata, and signatures
COMMANDS, COMMAND_METADATA, COMMAND_SIGNATURES = discover_commands()

# Export all discovered commands and the Settings class
__all__ = list(COMMANDS.keys())
__all__.append('Settings')

# Export all discovered metadata and signatures
COMMAND_METADATA = COMMAND_METADATA
COMMAND_SIGNATURES = COMMAND_SIGNATURES

# Helper function to get commands by permission level
def get_commands_by_permission_level(permission_level: str) -> List[str]:
    """
    Get all command names that require a specific permission level.

    Args:
        permission_level: The permission level to filter by ('admin', 'officer', 'user', 'any')

    Returns:
        List of command names that require the specified permission level
    """
    return [
        cmd_name for cmd_name, metadata in COMMAND_METADATA.items()
        if metadata.get('permission_level', 'user') == permission_level
    ]

# Helper function to get command permission level
def get_command_permission_level(command_name: str) -> str:
    """
    Get the permission level required for a specific command.

    Args:
        command_name: Name of the command

    Returns:
        Permission level required for the command ('admin', 'officer', 'user', 'any')
    """
    metadata = COMMAND_METADATA.get(command_name, {})
    return metadata.get('permission_level', 'user')

# Also export individual command functions for direct import
for cmd_name, cmd_func in COMMANDS.items():
    globals()[cmd_name] = cmd_func