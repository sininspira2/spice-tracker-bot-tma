#!/usr/bin/env python3
"""
Database Connection Test Script
Tests the connection to your Supabase database and basic functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from database import Database

# Load environment variables
load_dotenv()

async def test_database_connection():
    """Test basic database connectivity and operations"""
    print("🧪 Testing Supabase Database Connection...")
    
    try:
        # Initialize database
        database = Database()
        print("✅ Database object created successfully")
        
        # Test connection
        async with database._get_connection() as conn:
            print("✅ Database connection successful")
            
            # Test basic query
            result = await conn.fetchrow("SELECT version()")
            print(f"✅ PostgreSQL version: {result[0]}")
            
            # Test settings table
            settings = await database.get_setting('sand_per_melange')
            print(f"✅ Default sand per melange: {settings}")
            
            # Test user creation
            test_user_id = "test_user_123"
            test_username = "TestUser"
            
            await database.upsert_user(test_user_id, test_username)
            print("✅ User creation successful")
            
            # Test user retrieval
            user = await database.get_user(test_user_id)
            if user:
                print(f"✅ User retrieved: {user['username']} (ID: {user['user_id']})")
            else:
                print("❌ User retrieval failed")
            
            # Test deposit creation
            await database.add_deposit(test_user_id, test_username, 1000)
            print("✅ Deposit creation successful")
            
            # Test deposit retrieval
            deposits = await database.get_user_deposits(test_user_id)
            if deposits:
                print(f"✅ Deposits retrieved: {len(deposits)} deposit(s)")
                for deposit in deposits:
                    print(f"   - {deposit['sand_amount']} sand ({'Paid' if deposit['paid'] else 'Unpaid'})")
            else:
                print("❌ Deposit retrieval failed")
            
            # Test leaderboard
            leaderboard = await database.get_leaderboard(5)
            print(f"✅ Leaderboard retrieved: {len(leaderboard)} user(s)")
            
            # Clean up test data
            await database.reset_all_stats()
            print("✅ Test data cleaned up")
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    print("🎉 All database tests passed!")
    return True

async def test_environment_setup():
    """Test environment variable configuration"""
    print("\n🔧 Testing Environment Configuration...")
    
    required_vars = ['DATABASE_URL']
    optional_vars = ['DISCORD_TOKEN', 'CLIENT_ID']
    
    # Check required variables
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Not set (REQUIRED)")
            return False
    
    # Check optional variables
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️  {var}: Not set (optional for bot operation)")
    
    return True

async def main():
    """Main test function"""
    print("🚀 Spice Tracker Bot - Database Test Suite")
    print("=" * 50)
    
    # Test environment setup
    env_ok = await test_environment_setup()
    if not env_ok:
        print("\n❌ Environment setup failed. Please check your configuration.")
        return
    
    print("\n" + "=" * 50)
    
    # Test database connection
    db_ok = await test_database_connection()
    
    print("\n" + "=" * 50)
    
    if db_ok:
        print("🎉 SUCCESS: All tests passed!")
        print("\n✅ Your Supabase database is ready for the bot!")
        print("🔑 Next steps:")
        print("   1. Set your DISCORD_TOKEN and CLIENT_ID")
        print("   2. Deploy to Fly.io")
        print("   3. Test your bot!")
    else:
        print("❌ FAILURE: Some tests failed.")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your DATABASE_URL format")
        print("   2. Verify your Supabase project is active")
        print("   3. Ensure your database password is correct")
        print("   4. Check the Supabase dashboard for any errors")

if __name__ == "__main__":
    # Run the async test
    asyncio.run(main())
