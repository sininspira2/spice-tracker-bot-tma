#!/usr/bin/env python3
"""
Simple test runner for Spice Tracker Bot
Run this script to execute all tests
"""

import sys
import os
import subprocess

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting Spice Tracker Bot Test Suite...")
    print("=" * 50)
    
    try:
        # Run the tests using the test_bot.py file
        result = subprocess.run([sys.executable, "test_bot.py"], 
                              capture_output=True, text=True, cwd=os.getcwd())
        
        # Print the test output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n🎉 All tests passed! Your bot is working correctly.")
            sys.exit(0)
        else:
            print(f"\n💥 Tests failed with exit code {result.returncode}.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)
