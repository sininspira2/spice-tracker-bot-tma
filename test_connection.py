#!/usr/bin/env python3
"""
Simple Database Connection Test
Tests basic connectivity to Supabase
"""

import asyncio
import os
from dotenv import load_dotenv
import asyncpg

# Load environment variables
load_dotenv()

async def test_basic_connection():
    """Test basic database connectivity"""
    print("🔌 Testing Basic Database Connection...")
    
    try:
        # Get connection string
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment")
            return False
        
        print(f"✅ DATABASE_URL found: {database_url[:50]}...")
        
        # Test connection
        print("🔄 Attempting to connect...")
        conn = await asyncpg.connect(database_url)
        print("✅ Database connection successful!")
        
        # Test basic query
        result = await conn.fetchrow("SELECT version()")
        print(f"✅ PostgreSQL version: {result[0]}")
        
        # Test if tables exist
        tables_result = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        if tables_result:
            print("📋 Tables found:")
            for table in tables_result:
                print(f"   - {table[0]}")
        else:
            print("⚠️  No tables found - you may need to run migrations")
        
        # Close connection
        await conn.close()
        print("✅ Connection closed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        return False

async def main():
    """Main test function"""
    print("🚀 Basic Database Connection Test")
    print("=" * 40)
    
    success = await test_basic_connection()
    
    print("\n" + "=" * 40)
    
    if success:
        print("🎉 SUCCESS: Basic connection works!")
        print("\n🔑 Next steps:")
        print("   1. Run the migration SQL in Supabase dashboard")
        print("   2. Test the full database functionality")
    else:
        print("❌ FAILURE: Connection failed.")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your DATABASE_URL format")
        print("   2. Verify your Supabase project is active")
        print("   3. Ensure your database password is correct")
        print("   4. Check if your project is paused")

if __name__ == "__main__":
    asyncio.run(main())
