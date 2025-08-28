import discord

def check_admin_permission(user: discord.User | discord.Member, guild: discord.Guild) -> bool:
    """Check if a user has administrator permissions"""
    if not guild:
        return False
    
    member = guild.get_member(user.id)
    if not member:
        return False
    
    # Check if member has administrator permission
    return member.guild_permissions.administrator

def check_permissions(user: discord.User, guild: discord.Guild, permissions: discord.Permissions) -> bool:
    """Check if a user has specific permissions"""
    if not guild:
        return False
    
    member = guild.get_member(user.id)
    if not member:
        return False
    
    return member.guild_permissions >= permissions

def check_owner_permission(user: discord.User, guild: discord.Guild) -> bool:
    """Check if a user is the server owner"""
    if not guild:
        return False
    
    return guild.owner_id == user.id

def check_manage_server_permission(user: discord.User, guild: discord.Guild) -> bool:
    """Check if a user has manage server permissions"""
    if not guild:
        return False
    
    member = guild.get_member(user.id)
    if not member:
        return False
    
    return member.guild_permissions.manage_guild

def get_permission_level(user: discord.User, guild: discord.Guild) -> str:
    """Get permission level description for a user"""
    if not guild:
        return 'Unknown'
    
    if check_owner_permission(user, guild):
        return 'Server Owner'
    
    if check_admin_permission(user, guild):
        return 'Administrator'
    
    if check_manage_server_permission(user, guild):
        return 'Server Manager'
    
    return 'Regular User'