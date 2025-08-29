#!/usr/bin/env python3
"""
Debug Database Connection String
Helps identify issues with the connection string format
"""

import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def debug_connection_string():
    """Debug the database connection string"""
    print("🔍 Debugging Database Connection String...")
    
    # Get current connection string
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"📋 Full connection string: {database_url}")
    
    try:
        # Parse the URL
        parsed = urlparse(database_url)
        
        print(f"\n🔍 Parsed Components:")
        print(f"   Scheme: {parsed.scheme}")
        print(f"   Username: {parsed.username}")
        print(f"   Password: {'*' * len(parsed.password) if parsed.password else 'None'}")
        print(f"   Hostname: {parsed.hostname}")
        print(f"   Port: {parsed.port}")
        print(f"   Path: {parsed.path}")
        print(f"   Query: {parsed.query}")
        
        # Check for common issues
        print(f"\n🔍 Analysis:")
        
        if not parsed.hostname:
            print("   ❌ No hostname found")
        else:
            print(f"   ✅ Hostname: {parsed.hostname}")
            
            # Check if it looks like a Supabase hostname
            if 'supabase.co' in parsed.hostname:
                print("   ✅ Hostname contains 'supabase.co'")
            else:
                print("   ⚠️  Hostname doesn't contain 'supabase.co'")
        
        if not parsed.port:
            print("   ⚠️  No port specified (defaults to 5432)")
        elif parsed.port == 5432:
            print("   ✅ Port is 5432 (correct for PostgreSQL)")
        else:
            print(f"   ⚠️  Port is {parsed.port} (unusual for PostgreSQL)")
        
        if parsed.scheme != 'postgresql':
            print(f"   ⚠️  Scheme is '{parsed.scheme}' (should be 'postgresql')")
        else:
            print("   ✅ Scheme is 'postgresql'")
        
        # Show what the connection string should look like
        print(f"\n📝 Expected Format:")
        print("   postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
        
        # Show your current format
        print(f"\n📋 Your Current Format:")
        print(f"   {parsed.scheme}://{parsed.username}:[PASSWORD]@{parsed.hostname}:{parsed.port}{parsed.path}")
        
    except Exception as e:
        print(f"❌ Error parsing connection string: {e}")

def show_troubleshooting():
    """Show troubleshooting steps"""
    print(f"\n🔧 Troubleshooting Steps:")
    print("1. Go to your Supabase dashboard")
    print("2. Navigate to Settings → Database")
    print("3. Copy the connection string from 'Connection string' section")
    print("4. Make sure it starts with: postgresql://postgres:")
    print("5. Make sure it contains: @db.[PROJECT-REF].supabase.co:5432/postgres")
    print("6. Check if your project is active (not paused)")
    print("7. Verify the project reference in your dashboard URL")

if __name__ == "__main__":
    print("🚀 Database Connection String Debugger")
    print("=" * 50)
    
    debug_connection_string()
    show_troubleshooting()
    
    print("\n" + "=" * 50)
    print("🎯 After fixing any issues, run:")
    print("   python test_connection.py")
