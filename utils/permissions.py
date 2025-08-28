import discord
import os
from typing import List

def get_admin_role_ids() -> List[int]:
    """Get admin role IDs from environment variable"""
    admin_roles_str = os.getenv('ADMIN_ROLE_IDS', '')
    if not admin_roles_str:
        return []
    
    try:
        # Parse comma-separated role IDs
        role_ids = [int(role_id.strip()) for role_id in admin_roles_str.split(',') if role_id.strip()]
        return role_ids
    except ValueError:
        # If parsing fails, return empty list
        return []

def get_allowed_role_ids() -> List[int]:
    """Get allowed role IDs from environment variable"""
    allowed_roles_str = os.getenv('ALLOWED_ROLE_IDS', '')
    if not allowed_roles_str:
        return []
    
    try:
        # Parse comma-separated role IDs
        role_ids = [int(role_id.strip()) for role_id in allowed_roles_str.split(',') if role_id.strip()]
        return role_ids
    except ValueError:
        # If parsing fails, return empty list
        return []

def has_role(user: discord.User | discord.Member, role_id: int) -> bool:
    """Check if a user has a specific role ID"""
    if not hasattr(user, 'roles'):
        return False
    
    return any(role.id == role_id for role in user.roles)

def check_admin_role_permission(user: discord.User | discord.Member) -> bool:
    """Check if a user has any of the admin role IDs"""
    admin_role_ids = get_admin_role_ids()
    
    # Check if user has any of the admin roles
    for role_id in admin_role_ids:
        if has_role(user, role_id):
            return True
    
    return False

def check_admin_permission(user: discord.User | discord.Member) -> bool:
    """Check if a user has administrator permissions or admin role"""
    # Check if member has administrator permission
    if hasattr(user, 'guild_permissions') and user.guild_permissions.administrator:
        return True
    
    # Check if member has any of the admin roles
    if check_admin_role_permission(user):
        return True
    
    return False

def check_allowed_role_permission(user: discord.User | discord.Member) -> bool:
    """Check if a user has any of the allowed role IDs"""
    allowed_role_ids = get_allowed_role_ids()
    
    # If no allowed roles are configured, allow all users
    if not allowed_role_ids:
        return True
    
    # Check if user has any of the allowed roles
    for role_id in allowed_role_ids:
        if has_role(user, role_id):
            return True
    
    return False

def check_permissions(user: discord.User | discord.Member, permissions: discord.Permissions) -> bool:
    """Check if a user has specific permissions"""
    if not hasattr(user, 'guild_permissions'):
        return False
    
    return user.guild_permissions >= permissions

def check_owner_permission(user: discord.User | discord.Member, guild: discord.Guild) -> bool:
    """Check if a user is the server owner"""
    if not guild:
        return False
    
    return guild.owner_id == user.id

def check_manage_server_permission(user: discord.User | discord.Member) -> bool:
    """Check if a user has manage server permissions"""
    if not hasattr(user, 'guild_permissions'):
        return False
    
    return user.guild_permissions.manage_guild

def get_permission_level(user: discord.User | discord.Member, guild: discord.Guild) -> str:
    """Get permission level description for a user"""
    if not guild:
        return 'Unknown'
    
    if check_owner_permission(user, guild):
        return 'Server Owner'
    
    if check_admin_permission(user):
        # Check if it's from admin roles or Discord permissions
        if check_admin_role_permission(user):
            return 'Admin Role'
        return 'Administrator'
    
    if check_manage_server_permission(user):
        return 'Server Manager'
    
    if check_allowed_role_permission(user):
        return 'Allowed User'
    
    return 'Regular User'