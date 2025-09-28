"""
Commands package for the Spice Tracker Bot.
Contains all the individual command implementations.
"""

import os
import importlib
import inspect
from typing import Dict, Any, Callable, List, Tuple
from discord import app_commands

# Import base classes that we will check against
from discord.app_commands import Group as AppCommandGroup

# Automatically discover and import all command modules
def discover_commands():
    """
    Automatically discover all command modules in this package, separating them
    into function-based commands and class-based command groups.
    """
    commands: Dict[str, Callable[..., Any]] = {}
    metadata: Dict[str, Any] = {}
    signatures: Dict[str, List[Dict[str, Any]]] = {}
    command_groups: Dict[str, AppCommandGroup] = {}

    current_dir = os.path.dirname(__file__)

    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]

            try:
                module = importlib.import_module(f'.{module_name}', package=__name__)

                # Discover function-based commands
                command_func = None
                if hasattr(module, module_name):
                    command_func = getattr(module, module_name)
                elif hasattr(module, f'{module_name}_command'):
                    command_func = getattr(module, f'{module_name}_command')

                if command_func and inspect.isfunction(command_func):
                    commands[module_name] = command_func

                    original_func = command_func
                    if hasattr(command_func, '__wrapped__'):
                        original_func = command_func.__wrapped__

                    sig = inspect.signature(original_func)
                    params = [
                        {
                            'name': param.name,
                            'annotation': param.annotation,
                            'default': param.default if param.default != inspect.Parameter.empty else None
                        }
                        for param in list(sig.parameters.values())[1:]  # Skip interaction
                        if param.name != 'use_followup'
                    ]
                    signatures[module_name] = params

                # Discover class-based command groups (subclasses of app_commands.Group)
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, AppCommandGroup) and obj is not AppCommandGroup:
                        # Ensure the class name matches the module name convention
                        # e.g., 'guild' module contains 'Guild' class
                        if name.lower() == module_name:
                            command_groups[module_name] = obj

                # Get metadata
                if hasattr(module, 'COMMAND_METADATA'):
                    metadata[module_name] = getattr(module, 'COMMAND_METADATA')

            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")

    # Prioritize command groups over functions in case of name collision
    for group_name in list(command_groups.keys()):
        if group_name in commands:
            del commands[group_name]
            if group_name in signatures:
                del signatures[group_name]

    return commands, metadata, signatures, command_groups

# Auto-discover all commands and groups
COMMANDS, COMMAND_METADATA, COMMAND_SIGNATURES, COMMAND_GROUPS = discover_commands()

# Export all discovered items
__all__ = list(COMMANDS.keys()) + list(COMMAND_GROUPS.keys())

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