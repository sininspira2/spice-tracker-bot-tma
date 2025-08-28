#!/usr/bin/env python3
"""
Simple test runner for Spice Tracker Bot
Run this script to execute all tests
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_bot import run_tests

if __name__ == "__main__":
    print("🚀 Starting Spice Tracker Bot Test Suite...")
    success = run_tests()
    
    if success:
        print("\n🎉 All tests passed! Your bot is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Please check the output above.")
        sys.exit(1)
