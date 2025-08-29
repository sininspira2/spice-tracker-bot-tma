#!/usr/bin/env python3
"""
Database Setup Script
Creates the basic tables needed for the Spice Tracker Bot
"""

import asyncio
import os
from dotenv import load_dotenv
from database import Database

# Load environment variables
load_dotenv()

async def setup_database():
    """Set up the basic database tables"""
    print("🗄️ Setting up database tables...")
    
    try:
        # Initialize database
        database = Database()
        print("✅ Database object created successfully")
        
        # Create basic tables
        async with database._get_connection() as conn:
            print("🔄 Creating tables...")
            
            # Create users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_melange INTEGER DEFAULT 0,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Users table created")
            
            # Create deposits table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS deposits (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    sand_amount INTEGER NOT NULL,
                    paid BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    paid_at TIMESTAMP WITH TIME ZONE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            print("✅ Deposits table created")
            
            # Create settings table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            print("✅ Settings table created")
            
            # Insert default settings
            await conn.execute('''
                INSERT INTO settings (key, value) VALUES 
                    ('sand_per_melange', '50'),
                    ('default_harvester_percentage', '25.0')
                ON CONFLICT (key) DO NOTHING
            ''')
            print("✅ Default settings inserted")
            
            # Create basic indexes
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits (user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_deposits_created_at ON deposits (created_at)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_total_melange ON users (total_melange DESC)')
            print("✅ Indexes created")
            
        print("🎉 Database setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

async def test_basic_functionality():
    """Test basic database functionality after setup"""
    print("\n🧪 Testing basic functionality...")
    
    try:
        database = Database()
        
        # Test user creation
        test_user_id = "test_user_123"
        test_username = "TestUser"
        
        await database.upsert_user(test_user_id, test_username)
        print("✅ User creation test passed")
        
        # Test deposit creation
        await database.add_deposit(test_user_id, test_username, 1000)
        print("✅ Deposit creation test passed")
        
        # Test user retrieval
        user = await database.get_user(test_user_id)
        if user:
            print(f"✅ User retrieval test passed: {user['username']}")
        else:
            print("❌ User retrieval test failed")
        
        # Test settings retrieval
        setting = await database.get_setting('sand_per_melange')
        if setting:
            print(f"✅ Settings test passed: {setting}")
        else:
            print("❌ Settings test failed")
        
        # Clean up test data
        await database.reset_all_stats()
        print("✅ Test data cleanup passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

async def main():
    """Main setup function"""
    print("🚀 Spice Tracker Bot - Database Setup")
    print("=" * 50)
    
    # Set up database
    setup_success = await setup_database()
    
    if setup_success:
        print("\n" + "=" * 50)
        
        # Test functionality
        test_success = await test_basic_functionality()
        
        print("\n" + "=" * 50)
        
        if test_success:
            print("🎉 SUCCESS: Database is fully set up and working!")
            print("\n✅ Your Supabase database is ready for the bot!")
            print("🔑 Next steps:")
            print("   1. Deploy to Fly.io")
            print("   2. Test your bot commands!")
        else:
            print("⚠️  Database created but some tests failed")
            print("🔧 Check the error messages above")
    else:
        print("❌ Database setup failed")
        print("🔧 Check the error messages above")

if __name__ == "__main__":
    asyncio.run(main())
