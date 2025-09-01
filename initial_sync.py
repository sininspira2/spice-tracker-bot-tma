#!/usr/bin/env python3
"""
One-time sync script to bootstrap all slash commands including /sync
Run this once, then you can use /sync command in Discord
"""

import asyncio
import discord
from discord.ext import commands
import os

async def bootstrap_sync():
    print("🚀 Bootstrap Sync - One-Time Command Registration")
    print("=" * 50)
    
    # Get bot token
    token = input("Enter your Discord bot token: ").strip()
    if not token:
        print("❌ No token provided!")
        return
    
    # Get your Discord user ID (for owner check)
    owner_id = input("Enter your Discord user ID (for /sync permissions): ").strip()
    if owner_id:
        os.environ['BOT_OWNER_ID'] = owner_id
    
    # Create minimal bot
    intents = discord.Intents.default()
    intents.message_content = False
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'✅ Connected as {bot.user}')
        
        try:
            # Import and register ALL commands (including the new /sync command)
            import bot as bot_module
            bot_module.bot = bot  # Override bot instance
            
            print("🔧 Registering all commands...")
            bot_module.register_commands()
            
            print("🔄 Syncing to Discord...")
            synced = await bot.tree.sync()
            
            print(f"✅ Successfully synced {len(synced)} commands!")
            print("\n📋 Available commands:")
            for i, cmd in enumerate(synced, 1):
                print(f"  {i:2d}. /{cmd.name}")
                if cmd.name == 'sync':
                    print(f"      👆 You can now use this to sync future changes!")
            
            print(f"\n🎉 Bootstrap complete!")
            print(f"💡 Next time, just use /sync in Discord (owner only)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await bot.close()
    
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(bootstrap_sync())
