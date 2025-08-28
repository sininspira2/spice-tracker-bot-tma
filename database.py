import aiosqlite
import os
from datetime import datetime

class Database:
    def __init__(self, db_path='spice_tracker.db'):
        self.db_path = db_path

    async def initialize(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_sand INTEGER DEFAULT 0,
                    total_melange INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            # Insert default conversion rate if not exists
            await db.execute(
                'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                ('sand_per_melange', '50')
            )

            await db.commit()

    async def get_user(self, user_id):
        """Get user data by user ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT user_id, username, total_sand, total_melange, last_updated FROM users WHERE user_id = ?',
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                # Convert the row to a dictionary with proper datetime parsing
                return {
                    'user_id': row[0],
                    'username': row[1], 
                    'total_sand': row[2],
                    'total_melange': row[3],
                    'last_updated': datetime.fromisoformat(row[4]) if row[4] else datetime.now()
                }
            return None

    async def upsert_user(self, user_id, username, sand_amount=0):
        """Create or update user with sand amount"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO users (user_id, username, total_sand, total_melange, last_updated)
                VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    total_sand = total_sand + ?,
                    last_updated = CURRENT_TIMESTAMP
            ''', (user_id, username, sand_amount, sand_amount))
            await db.commit()

    async def update_user_melange(self, user_id, melange_amount):
        """Update user melange amount"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users 
                SET total_melange = total_melange + ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (melange_amount, user_id))
            await db.commit()

    async def get_leaderboard(self, limit=10):
        """Get leaderboard data"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT username, total_sand, total_melange
                FROM users
                ORDER BY total_melange DESC, total_sand DESC
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_setting(self, key):
        """Get setting value"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT value FROM settings WHERE key = ?',
                (key,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_setting(self, key, value):
        """Set setting value"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                (key, value)
            )
            await db.commit()

    async def reset_all_stats(self):
        """Reset all user statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('DELETE FROM users')
            await db.commit()
            return cursor.rowcount