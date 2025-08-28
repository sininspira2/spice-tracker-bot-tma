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

            # Create spice split history table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS spice_splits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    initiator_user_id TEXT NOT NULL,
                    initiator_username TEXT NOT NULL,
                    total_sand INTEGER NOT NULL,
                    participants INTEGER NOT NULL,
                    harvester_percentage REAL NOT NULL,
                    sand_per_melange INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create payments tracking table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    sand_amount INTEGER NOT NULL,
                    melange_amount INTEGER NOT NULL,
                    paid_by_user_id TEXT NOT NULL,
                    paid_by_username TEXT NOT NULL,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

    async def record_spice_split(self, initiator_user_id, initiator_username, total_sand, participants, harvester_percentage, sand_per_melange):
        """Record a spice split operation in history"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO spice_splits 
                (initiator_user_id, initiator_username, total_sand, participants, harvester_percentage, sand_per_melange)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (initiator_user_id, initiator_username, total_sand, participants, harvester_percentage, sand_per_melange))
            await db.commit()

    async def get_spice_split_history(self, limit=20):
        """Get recent spice split history"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT id, initiator_username, total_sand, participants, harvester_percentage, 
                       sand_per_melange, created_at
                FROM spice_splits 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            
            splits = []
            for row in rows:
                splits.append({
                    'id': row[0],
                    'initiator_username': row[1],
                    'total_sand': row[2],
                    'participants': row[3],
                    'harvester_percentage': row[4],
                    'sand_per_melange': row[5],
                    'created_at': row[6]
                })
            return splits

    async def get_spice_split_stats(self):
        """Get summary statistics for spice splits"""
        async with aiosqlite.connect(self.db_path) as db:
            # Total splits count
            cursor = await db.execute('SELECT COUNT(*) FROM spice_splits')
            total_splits = (await cursor.fetchone())[0]
            
            # Total sand processed
            cursor = await db.execute('SELECT SUM(total_sand) FROM spice_splits')
            total_sand_result = await cursor.fetchone()
            total_sand = total_sand_result[0] if total_sand_result[0] else 0
            
            # Average participants
            cursor = await db.execute('SELECT AVG(participants) FROM spice_splits')
            avg_participants_result = await cursor.fetchone()
            avg_participants = round(avg_participants_result[0], 1) if avg_participants_result[0] else 0
            
            return {
                'total_splits': total_splits,
                'total_sand_processed': total_sand,
                'average_participants': avg_participants
            }

    async def record_payment(self, user_id, username, sand_amount, melange_amount, paid_by_user_id, paid_by_username, notes=None):
        """Record a payment made to a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO payments 
                (user_id, username, sand_amount, melange_amount, paid_by_user_id, paid_by_username, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, sand_amount, melange_amount, paid_by_user_id, paid_by_username, notes))
            await db.commit()

    async def get_payment_history(self, user_id=None, limit=20):
        """Get payment history, optionally filtered by user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if user_id:
                cursor = await db.execute('''
                    SELECT id, username, sand_amount, melange_amount, paid_by_username, notes, created_at
                    FROM payments 
                    WHERE user_id = ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (user_id, limit))
            else:
                cursor = await db.execute('''
                    SELECT id, username, sand_amount, melange_amount, paid_by_username, notes, created_at
                    FROM payments 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
            rows = await cursor.fetchall()
            
            payments = []
            for row in rows:
                payments.append({
                    'id': row[0],
                    'username': row[1],
                    'sand_amount': row[2],
                    'melange_amount': row[3],
                    'paid_by_username': row[4],
                    'notes': row[5],
                    'created_at': row[6]
                })
            return payments

    async def get_payment_stats(self):
        """Get payment statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            # Total payments count
            cursor = await db.execute('SELECT COUNT(*) FROM payments')
            total_payments = (await cursor.fetchone())[0]
            
            # Total melange paid out
            cursor = await db.execute('SELECT SUM(melange_amount) FROM payments')
            total_melange_result = await cursor.fetchone()
            total_melange_paid = total_melange_result[0] if total_melange_result[0] else 0
            
            # Total sand paid out
            cursor = await db.execute('SELECT SUM(sand_amount) FROM payments')
            total_sand_result = await cursor.fetchone()
            total_sand_paid = total_sand_result[0] if total_sand_result[0] else 0
            
            return {
                'total_payments': total_payments,
                'total_melange_paid': total_melange_paid,
                'total_sand_paid': total_sand_paid
            }