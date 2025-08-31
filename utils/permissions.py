import discord
import os
from typing import List

def _parse_role_ids(env_var: str) -> List[int]:
    """Parse comma-separated role IDs from environment variable"""
    if not env_var:
        return []
    
    try:
        role_ids = []
        for role_id in env_var.split(','):
            role_id = role_id.strip()
            if role_id and role_id.isdigit():
                role_ids.append(int(role_id))
        return role_ids
    except ValueError:
        return []

def get_admin_role_ids() -> List[int]:
    """Get admin role IDs from environment variable"""
    return _parse_role_ids(os.getenv('ADMIN_ROLE_IDS', ''))

def get_allowed_role_ids() -> List[int]:
    """Get allowed role IDs from environment variable"""
    return _parse_role_ids(os.getenv('ALLOWED_ROLE_IDS', ''))

def has_role(user: discord.User | discord.Member, role_id: int) -> bool:
    """Check if a user has a specific role ID"""
    return hasattr(user, 'roles') and any(role.id == role_id for role in user.roles)

def check_admin_role_permission(user: discord.User | discord.Member) -> bool:
    """Check if a user has any of the admin role IDs"""
    return any(has_role(user, role_id) for role_id in get_admin_role_ids())

def check_admin_permission(user: discord.User | discord.Member) -> bool:
    """Check if a user has administrator permissions or admin role"""
    return (hasattr(user, 'guild_permissions') and user.guild_permissions.administrator) or \
           check_admin_role_permission(user)

def check_allowed_role_permission(user: discord.User | discord.Member) -> bool:
    """Check if a user has any of the allowed role IDs"""
    allowed_roles = get_allowed_role_ids()
    return not allowed_roles or any(has_role(user, role_id) for role_id in allowed_roles)

def check_permissions(user: discord.User | discord.Member, permissions: discord.Permissions) -> bool:
    """Check if a user has specific permissions"""
    return hasattr(user, 'guild_permissions') and user.guild_permissions >= permissions

def check_owner_permission(user: discord.User | discord.Member, guild: discord.Guild) -> bool:
    """Check if a user is the server owner"""
    return guild and guild.owner_id == user.id

def check_manage_server_permission(user: discord.User | discord.Member) -> bool:
    """Check if a user has manage server permissions"""
    return hasattr(user, 'guild_permissions') and user.guild_permissions.manage_guild

def get_permission_level(user: discord.User | discord.Member, guild: discord.Guild) -> str:
    """Get permission level description for a user"""
    if not guild:
        return 'Unknown'
    
    if check_owner_permission(user, guild):
        return 'Server Owner'
    
    if check_admin_permission(user):
        return 'Admin Role' if check_admin_role_permission(user) else 'Administrator'
    
    if check_manage_server_permission(user):
        return 'Server Manager'
    
    if check_allowed_role_permission(user):
        return 'Allowed User'
    
    return 'Regular User'