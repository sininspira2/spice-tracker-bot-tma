#!/usr/bin/env python3
"""
Lightweight test framework for Spice Tracker Bot
Tests critical functionality to prevent breaking changes
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.permissions import check_admin_permission, check_admin_role_permission, get_admin_role_ids, get_allowed_role_ids, check_allowed_role_permission
from utils.rate_limiter import RateLimiter
from utils.embed_builder import EmbedBuilder

class TestPermissions(unittest.TestCase):
    """Test permission checking functionality"""
    
    def setUp(self):
        """Set up test mocks"""
        # Mock user
        self.mock_user = Mock()
        self.mock_user.id = 123456789
        
        # Mock guild
        self.mock_guild = Mock()
        self.mock_guild.owner_id = 987654321
        
        # Mock member
        self.mock_member = Mock()
        self.mock_member.id = 123456789
        self.mock_member.guild_permissions = Mock()
        self.mock_member.roles = []
        
        # Mock role
        self.mock_role = Mock()
        self.mock_role.id = 111222333
        self.mock_role.name = "Admin Role"
        
        self.mock_guild.get_member.return_value = self.mock_member
    
    def test_admin_permission_with_discord_admin(self):
        """Test admin permission check with Discord administrator"""
        # Mock interaction
        mock_interaction = Mock()
        mock_interaction.user = self.mock_member
        mock_interaction.guild = self.mock_guild
        
        # Set up Discord administrator permissions
        self.mock_member.guild_permissions.administrator = True
        
        # Test admin permission check
        result = check_admin_permission(self.mock_member)
        self.assertTrue(result)
    
    def test_admin_permission_with_admin_role(self):
        """Test admin permission check with admin role"""
        # Mock interaction
        mock_interaction = Mock()
        mock_interaction.user = self.mock_member
        mock_interaction.guild = self.mock_guild
        
        # Set up admin role
        self.mock_member.guild_permissions.administrator = False
        self.mock_member.roles = [self.mock_role]
        
        # Set environment variable for admin role
        with patch.dict(os.environ, {'ADMIN_ROLE_IDS': '111222333'}):
            result = check_admin_permission(self.mock_member)
            self.assertTrue(result)
    
    def test_admin_permission_without_permissions(self):
        """Test admin permission check without admin permissions or roles"""
        # Mock interaction
        mock_interaction = Mock()
        mock_interaction.user = self.mock_member
        mock_interaction.guild = self.mock_guild
        
        # Set up no permissions
        self.mock_member.guild_permissions.administrator = False
        self.mock_member.roles = []
        
        # Test admin permission check
        result = check_admin_permission(self.mock_member)
        self.assertFalse(result)
    
    def test_admin_role_ids_parsing(self):
        """Test parsing of admin role IDs from environment variable"""
        # Test with single role ID
        with patch.dict(os.environ, {'ADMIN_ROLE_IDS': '123456789'}):
            role_ids = get_admin_role_ids()
            self.assertEqual(role_ids, [123456789])
        
        # Test with multiple role IDs
        with patch.dict(os.environ, {'ADMIN_ROLE_IDS': '123456789,987654321,555666777'}):
            role_ids = get_admin_role_ids()
            self.assertEqual(role_ids, [123456789, 987654321, 555666777])
        
        # Test with empty environment variable
        with patch.dict(os.environ, {'ADMIN_ROLE_IDS': ''}):
            role_ids = get_admin_role_ids()
            self.assertEqual(role_ids, [])
        
        # Test with invalid role IDs
        with patch.dict(os.environ, {'ADMIN_ROLE_IDS': '123456789,invalid,987654321'}):
            role_ids = get_admin_role_ids()
            self.assertEqual(role_ids, [123456789, 987654321])
    
    def test_allowed_role_ids_parsing(self):
        """Test parsing of allowed role IDs from environment variable"""
        # Test with single role ID
        with patch.dict(os.environ, {'ALLOWED_ROLE_IDS': '111222333'}):
            role_ids = get_allowed_role_ids()
            self.assertEqual(role_ids, [111222333])
        
        # Test with multiple role IDs
        with patch.dict(os.environ, {'ALLOWED_ROLE_IDS': '111222333,444555666,777888999'}):
            role_ids = get_allowed_role_ids()
            self.assertEqual(role_ids, [111222333, 444555666, 777888999])
        
        # Test with empty environment variable
        with patch.dict(os.environ, {'ALLOWED_ROLE_IDS': ''}):
            role_ids = get_allowed_role_ids()
            self.assertEqual(role_ids, [])
    
    def test_allowed_role_permission(self):
        """Test allowed role permission checking"""
        # Test with no allowed roles configured (should allow all)
        with patch.dict(os.environ, {'ALLOWED_ROLE_IDS': ''}):
            result = check_allowed_role_permission(self.mock_member)
            self.assertTrue(result)
        
        # Test with user having allowed role
        self.mock_member.roles = [self.mock_role]
        with patch.dict(os.environ, {'ALLOWED_ROLE_IDS': '111222333'}):
            result = check_allowed_role_permission(self.mock_member)
            self.assertTrue(result)
        
        # Test with user not having allowed role
        self.mock_member.roles = []
        with patch.dict(os.environ, {'ALLOWED_ROLE_IDS': '111222333'}):
            result = check_allowed_role_permission(self.mock_member)
            self.assertFalse(result)

class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        """Set up test rate limiter"""
        self.rate_limiter = RateLimiter()
    
    def test_rate_limit_check(self):
        """Test basic rate limit checking"""
        user_id = "12345"
        command = "logsolo"
        
        # First 10 uses should be allowed
        for i in range(10):
            result = self.rate_limiter.check_rate_limit(user_id, command)
            self.assertTrue(result, f"Use {i+1} should be allowed")
        
        # 11th use should be blocked
        result = self.rate_limiter.check_rate_limit(user_id, command)
        self.assertFalse(result, "11th use should be blocked")
    
    def test_rate_limit_reset(self):
        """Test rate limit reset functionality"""
        user_id = "12345"
        command = "logsolo"
        
        # Use up the limit
        for i in range(10):
            self.rate_limiter.check_rate_limit(user_id, command)
        
        # Reset the rate limit
        self.rate_limiter.reset_user_rate_limit(user_id, command)
        
        # Should be able to use again
        result = self.rate_limiter.check_rate_limit(user_id, command)
        self.assertTrue(result)
    
    def test_different_commands(self):
        """Test that different commands have separate rate limits"""
        user_id = "12345"
        
        # Use up logsolo limit
        for i in range(10):
            self.rate_limiter.check_rate_limit(user_id, "logsolo")
        
        # Should still be able to use myrefines
        result = self.rate_limiter.check_rate_limit(user_id, "myrefines")
        self.assertTrue(result)
    
    def test_remaining_uses(self):
        """Test remaining uses calculation"""
        user_id = "12345"
        command = "logsolo"
        
        # Check initial remaining uses
        remaining, reset_time = self.rate_limiter.get_remaining_uses(user_id, command)
        self.assertEqual(remaining, 10)
        self.assertIsNone(reset_time)
        
        # Use the command once
        self.rate_limiter.check_rate_limit(user_id, command)
        
        # Check remaining uses
        remaining, reset_time = self.rate_limiter.get_remaining_uses(user_id, command)
        self.assertEqual(remaining, 9)
        self.assertIsNotNone(reset_time)

class TestEmbedBuilder(unittest.TestCase):
    """Test embed builder functionality"""
    
    def test_embed_creation(self):
        """Test basic embed creation"""
        embed = EmbedBuilder("Test Title", color=0x123456)
        built_embed = embed.build()
        
        self.assertEqual(built_embed.title, "Test Title")
        self.assertEqual(built_embed.color.value, 0x123456)
    
    def test_embed_chaining(self):
        """Test method chaining for embed building"""
        embed = (EmbedBuilder("Test Title")
                 .add_field("Field 1", "Value 1")
                 .add_field("Field 2", "Value 2", inline=False)
                 .set_footer("Test Footer"))
        
        built_embed = embed.build()
        
        self.assertEqual(len(built_embed.fields), 2)
        self.assertEqual(built_embed.fields[0].name, "Field 1")
        self.assertEqual(built_embed.fields[0].value, "Value 1")
        self.assertEqual(built_embed.fields[0].inline, True)
        self.assertEqual(built_embed.fields[1].name, "Field 2")
        self.assertEqual(built_embed.fields[1].value, "Value 2")
        self.assertEqual(built_embed.fields[1].inline, False)
        self.assertEqual(built_embed.footer.text, "Test Footer")
    
    def test_embed_description(self):
        """Test setting embed description"""
        embed = EmbedBuilder("Test Title").set_description("Test Description")
        built_embed = embed.build()
        
        self.assertEqual(built_embed.description, "Test Description")
    
    def test_embed_thumbnail(self):
        """Test setting embed thumbnail"""
        embed = EmbedBuilder("Test Title").set_thumbnail("https://example.com/image.png")
        built_embed = embed.build()
        
        self.assertEqual(built_embed.thumbnail.url, "https://example.com/image.png")

if __name__ == '__main__':
    unittest.main()
