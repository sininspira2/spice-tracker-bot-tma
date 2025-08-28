#!/usr/bin/env python3
"""
Lightweight test framework for Spice Tracker Bot
Tests critical functionality to prevent breaking changes
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, AsyncMock
import sys
import traceback
import aiosqlite

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from utils.rate_limiter import RateLimiter
from utils.permissions import check_admin_permission


class TestDatabase(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        """Set up test database"""
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.database = Database(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
    
    async def asyncSetUp(self):
        """Async setup"""
        await self.database.initialize()
    
    async def asyncTearDown(self):
        """Async cleanup"""
        pass
    
    def test_database_initialization(self):
        """Test database tables are created correctly"""
        async def test():
            await self.database.initialize()
            
            # Test that users table exists and has correct structure
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("PRAGMA table_info(users)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                expected_columns = ['user_id', 'username', 'total_sand', 'total_melange', 'last_updated']
                for expected in expected_columns:
                    self.assertIn(expected, column_names)
                
                # Test that settings table exists
                cursor = await db.execute("PRAGMA table_info(settings)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                expected_columns = ['key', 'value']
                for expected in expected_columns:
                    self.assertIn(expected, column_names)
        
        asyncio.run(test())
    
    def test_user_operations(self):
        """Test user creation, update, and retrieval"""
        async def test():
            await self.database.initialize()
            
            # Test user creation
            user_id = "test_user_123"
            username = "TestUser"
            sand_amount = 100
            
            await self.database.upsert_user(user_id, username, sand_amount)
            
            # Test user retrieval
            user = await self.database.get_user(user_id)
            self.assertIsNotNone(user)
            self.assertEqual(user['user_id'], user_id)
            self.assertEqual(user['username'], username)
            self.assertEqual(user['total_sand'], sand_amount)
            self.assertEqual(user['total_melange'], 0)
            
            # Test user update
            await self.database.upsert_user(user_id, username, 50)
            user = await self.database.get_user(user_id)
            self.assertEqual(user['total_sand'], 150)  # 100 + 50
        
        asyncio.run(test())
    
    def test_melange_conversion(self):
        """Test melange conversion logic"""
        async def test():
            await self.database.initialize()
            
            user_id = "test_user_456"
            username = "TestUser2"
            
            # Set conversion rate to 50 sand = 1 melange
            await self.database.set_setting('sand_per_melange', '50')
            
            # Add 125 sand (should give 2 melange with 25 remaining)
            await self.database.upsert_user(user_id, username, 125)
            
            # Update melange
            await self.database.update_user_melange(user_id, 2)
            
            user = await self.database.get_user(user_id)
            self.assertEqual(user['total_sand'], 125)
            self.assertEqual(user['total_melange'], 2)
            
            # Verify conversion rate
            rate = await self.database.get_setting('sand_per_melange')
            self.assertEqual(rate, '50')
        
        asyncio.run(test())
    
    def test_leaderboard(self):
        """Test leaderboard functionality"""
        async def test():
            await self.database.initialize()
            
            # Create test users with different amounts
            users = [
                ("user1", "User1", 1000, 20),
                ("user2", "User2", 500, 10),
                ("user3", "User3", 2000, 40)
            ]
            
            for user_id, username, sand, melange in users:
                await self.database.upsert_user(user_id, username, sand)
                await self.database.update_user_melange(user_id, melange)
            
            # Test leaderboard
            leaderboard = await self.database.get_leaderboard(limit=3)
            self.assertEqual(len(leaderboard), 3)
            
            # Should be ordered by melange (descending)
            self.assertEqual(leaderboard[0]['username'], 'User3')  # 40 melange
            self.assertEqual(leaderboard[1]['username'], 'User1')  # 20 melange
            self.assertEqual(leaderboard[2]['username'], 'User2')  # 10 melange
        
        asyncio.run(test())


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        """Set up rate limiter"""
        self.rate_limiter = RateLimiter()
    
    def test_basic_rate_limiting(self):
        """Test basic rate limit functionality"""
        user_id = "test_user"
        command = "logsolo"
        
        # Should allow first 10 uses within 60 seconds
        for i in range(10):
            self.assertTrue(self.rate_limiter.check_rate_limit(user_id, command))
        
        # 11th use should be blocked
        self.assertFalse(self.rate_limiter.check_rate_limit(user_id, command))
    
    def test_rate_limit_reset(self):
        """Test rate limit reset functionality"""
        user_id = "test_user"
        command = "logsolo"
        
        # Use up the limit
        for i in range(10):
            self.rate_limiter.check_rate_limit(user_id, command)
        
        # Reset the limit
        self.rate_limiter.reset_user_rate_limit(user_id, command)
        
        # Should be able to use again
        self.assertTrue(self.rate_limiter.check_rate_limit(user_id, command))
    
    def test_different_commands(self):
        """Test different commands have different rate limits"""
        user_id = "test_user"
        
        # logsolo: 10 per minute
        for i in range(10):
            self.assertTrue(self.rate_limiter.check_rate_limit(user_id, "logsolo"))
        self.assertFalse(self.rate_limiter.check_rate_limit(user_id, "logsolo"))
        
        # myrefines: 5 per 30 seconds (should still work)
        for i in range(5):
            self.assertTrue(self.rate_limiter.check_rate_limit(user_id, "myrefines"))
        self.assertFalse(self.rate_limiter.check_rate_limit(user_id, "myrefines"))
    
    def test_remaining_uses(self):
        """Test remaining uses calculation"""
        user_id = "test_user"
        command = "logsolo"
        
        # Check initial remaining uses (should be max_uses and None for reset_time)
        remaining, reset_time = self.rate_limiter.get_remaining_uses(user_id, command)
        self.assertEqual(remaining, 10)
        self.assertIsNone(reset_time)  # No reset time until first use
        
        # Use the command once
        self.rate_limiter.check_rate_limit(user_id, command)
        remaining, reset_time = self.rate_limiter.get_remaining_uses(user_id, command)
        self.assertEqual(remaining, 9)
        self.assertIsNotNone(reset_time)  # Now should have a reset time
        
        # Use it a few more times
        for i in range(3):
            self.rate_limiter.check_rate_limit(user_id, command)
        
        remaining, reset_time = self.rate_limiter.get_remaining_uses(user_id, command)
        self.assertEqual(remaining, 6)  # 10 - 4 = 6
        self.assertIsNotNone(reset_time)


class TestPermissions(unittest.TestCase):
    """Test permission checking"""
    
    def test_admin_permission_check(self):
        """Test admin permission checking"""
        # Mock interaction with admin permissions
        mock_user = Mock()
        mock_guild = Mock()
        mock_member = Mock()
        mock_member.guild_permissions.administrator = True
        mock_guild.get_member.return_value = mock_member
        
        result = check_admin_permission(mock_user, mock_guild)
        self.assertTrue(result)
        
        # Mock interaction without admin permissions
        mock_member.guild_permissions.administrator = False
        
        result = check_admin_permission(mock_user, mock_guild)
        self.assertFalse(result)


class TestBotLogic(unittest.TestCase):
    """Test core bot logic without Discord dependencies"""
    
    def test_sand_validation(self):
        """Test sand amount validation logic"""
        # Valid amounts
        valid_amounts = [1, 100, 5000, 10000]
        for amount in valid_amounts:
            self.assertTrue(1 <= amount <= 10000)
        
        # Invalid amounts
        invalid_amounts = [0, -1, 10001, 99999]
        for amount in invalid_amounts:
            self.assertFalse(1 <= amount <= 10000)
    
    def test_melange_calculation(self):
        """Test melange calculation logic"""
        # Test conversion rate of 50 sand = 1 melange
        sand_per_melange = 50
        
        test_cases = [
            (25, 0),      # 25 sand = 0 melange
            (50, 1),      # 50 sand = 1 melange
            (75, 1),      # 75 sand = 1 melange
            (100, 2),     # 100 sand = 2 melange
            (125, 2),     # 125 sand = 2 melange
            (2500, 50),   # 2500 sand = 50 melange
        ]
        
        for sand, expected_melange in test_cases:
            calculated_melange = sand // sand_per_melange
            self.assertEqual(calculated_melange, expected_melange)
            
            # Test remaining sand calculation
            remaining_sand = sand % sand_per_melange
            self.assertLess(remaining_sand, sand_per_melange)
            self.assertGreaterEqual(remaining_sand, 0)
    
    def test_harvester_split_calculation(self):
        """Test harvester split calculation logic"""
        total_sand = 10000
        participants = 4
        harvester_percent = 25
        
        # Calculate harvester cut
        harvester_cut = (total_sand * harvester_percent) // 100
        self.assertEqual(harvester_cut, 2500)
        
        # Calculate remaining for team
        remaining_for_team = total_sand - harvester_cut
        self.assertEqual(remaining_for_team, 7500)
        
        # Calculate per-participant amount
        per_participant = remaining_for_team // participants
        self.assertEqual(per_participant, 1875)
        
        # Verify total adds up
        total_distributed = harvester_cut + (per_participant * participants)
        self.assertEqual(total_distributed, 10000)


def run_tests():
    """Run all tests and report results"""
    print("🧪 Running Spice Tracker Bot Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestDatabase,
        TestRateLimiter,
        TestPermissions,
        TestBotLogic
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
