#!/usr/bin/env python3
"""
Fix Database Connection String
Helps encode special characters in the password
"""

import urllib.parse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_connection_string():
    """Fix the database connection string by properly encoding the password"""
    print("🔧 Fixing Database Connection String...")
    
    # Get current connection string
    current_url = os.getenv('DATABASE_URL')
    if not current_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"📋 Current connection string: {current_url[:50]}...")
    
    try:
        # Parse the URL
        from urllib.parse import urlparse, parse_qs
        
        # Extract components
        parsed = urlparse(current_url)
        
        # Get the password from the netloc (username:password@host:port)
        if '@' in parsed.netloc:
            auth, host_port = parsed.netloc.split('@', 1)
            if ':' in auth:
                username, password = auth.split(':', 1)
                
                # Encode the password
                encoded_password = urllib.parse.quote_plus(password)
                
                # Reconstruct the connection string
                fixed_netloc = f"{username}:{encoded_password}@{host_port}"
                fixed_url = f"{parsed.scheme}://{fixed_netloc}{parsed.path}"
                
                if parsed.query:
                    fixed_url += f"?{parsed.query}"
                
                print(f"✅ Fixed connection string: {fixed_url[:50]}...")
                print(f"🔑 Original password: {password}")
                print(f"🔑 Encoded password: {encoded_password}")
                
                # Show what to update in your .env file
                print("\n📝 Update your .env file with:")
                print(f"DATABASE_URL={fixed_url}")
                
                return fixed_url
            else:
                print("❌ Could not parse username:password from connection string")
        else:
            print("❌ Could not parse host from connection string")
            
    except Exception as e:
        print(f"❌ Error parsing connection string: {e}")
    
    return None

def show_manual_fix():
    """Show manual steps to fix the connection string"""
    print("\n🔧 Manual Fix Instructions:")
    print("1. Go to your Supabase dashboard")
    print("2. Navigate to Settings → Database")
    print("3. Copy the connection string from 'Connection string' section")
    print("4. Make sure it looks like this format:")
    print("   postgresql://postgres:[ENCODED-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
    print("5. Update your .env file")
    print("\n💡 The password should be properly URL-encoded automatically in the dashboard")

if __name__ == "__main__":
    print("🚀 Database Connection String Fixer")
    print("=" * 40)
    
    fixed_url = fix_connection_string()
    
    if not fixed_url:
        show_manual_fix()
    
    print("\n" + "=" * 40)
    print("🎯 After fixing the connection string, run:")
    print("   python test_connection.py")
