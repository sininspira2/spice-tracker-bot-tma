import aiosqlite
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

class Database:
    def __init__(self, db_path='spice_tracker.db'):
        self.db_path = db_path

    @asynccontextmanager
    async def _get_connection(self):
        """Context manager for database connections"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    async def migrate_existing_data(self):
        """Migrate existing users with total_sand to the new deposits system"""
        async with self._get_connection() as db:
            # Check if migration is needed
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in await cursor.fetchall()]
            
            if 'total_sand' not in columns:
                return 0  # No migration needed
            
            # Get users with total_sand > 0
            cursor = await db.execute('''
                SELECT user_id, username, total_sand 
                FROM users 
                WHERE total_sand > 0
            ''')
            users_to_migrate = await cursor.fetchall()
            
            migrated_count = 0
            for user in users_to_migrate:
                user_id, username, total_sand = user
                
                # Create a single deposit record for the existing total_sand
                if total_sand > 0:
                    await db.execute('''
                        INSERT INTO deposits (user_id, username, sand_amount, paid, created_at)
                        VALUES (?, ?, ?, FALSE, CURRENT_TIMESTAMP)
                    ''', (user_id, username, total_sand))
                    migrated_count += 1
            
            # Remove total_sand column from users table
            await db.execute('''
                CREATE TABLE users_new (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_melange INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                INSERT INTO users_new (user_id, username, total_melange, last_updated)
                SELECT user_id, username, total_melange, last_updated FROM users
            ''')
            
            await db.execute('DROP TABLE users')
            await db.execute('ALTER TABLE users_new RENAME TO users')
            
            await db.commit()
            return migrated_count

    async def initialize(self):
        """Initialize database tables"""
        async with self._get_connection() as db:
            # Create tables
            await db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_melange INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    sand_amount INTEGER NOT NULL,
                    paid BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    paid_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                );
                
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits (user_id);
                CREATE INDEX IF NOT EXISTS idx_deposits_created_at ON deposits (created_at);
                CREATE INDEX IF NOT EXISTS idx_deposits_paid ON deposits (paid);
            ''')
            
            # Insert default conversion rate
            await db.execute(
                'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                ('sand_per_melange', '50')
            )
            await db.commit()
            
            # Run migration if needed
            try:
                migrated_count = await self.migrate_existing_data()
                if migrated_count > 0:
                    print(f'Migrated {migrated_count} users to new deposits system')
            except Exception as e:
                print(f'Migration failed: {e}')
                # Continue with initialization even if migration fails

    async def get_user(self, user_id):
        """Get user data by user ID"""
        async with self._get_connection() as db:
            cursor = await db.execute(
                'SELECT * FROM users WHERE user_id = ?',
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'username': row[1], 
                    'total_melange': row[2],
                    'last_updated': datetime.fromisoformat(row[3]) if row[3] else datetime.now()
                }
            return None

    async def upsert_user(self, user_id, username):
        """Create or update user (without sand amount)"""
        async with self._get_connection() as db:
            await db.execute('''
                INSERT INTO users (user_id, username, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    last_updated = CURRENT_TIMESTAMP
            ''', (user_id, username))
            await db.commit()

    async def add_deposit(self, user_id, username, sand_amount):
        """Add a new sand deposit for a user"""
        async with self._get_connection() as db:
            # Ensure user exists
            await self.upsert_user(user_id, username)
            
            # Add deposit record
            await db.execute('''
                INSERT INTO deposits (user_id, username, sand_amount, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, sand_amount))
            await db.commit()

    async def get_user_deposits(self, user_id, include_paid=True):
        """Get all deposits for a user"""
        async with self._get_connection() as db:
            query = '''
                SELECT * FROM deposits 
                WHERE user_id = ?
            '''
            params = [user_id]
            
            if not include_paid:
                query += ' AND paid = FALSE'
            
            query += ' ORDER BY created_at DESC'
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            deposits = []
            for row in rows:
                deposits.append({
                    'id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'sand_amount': row[3],
                    'paid': bool(row[4]),
                    'created_at': datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    'paid_at': datetime.fromisoformat(row[6]) if row[6] else None
                })
            
            return deposits

    async def get_user_total_sand(self, user_id):
        """Get total sand from all deposits for a user"""
        async with self._get_connection() as db:
            cursor = await db.execute('''
                SELECT COALESCE(SUM(sand_amount), 0) as total_sand
                FROM deposits 
                WHERE user_id = ? AND paid = FALSE
            ''', (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_user_paid_sand(self, user_id):
        """Get total sand from paid deposits for a user"""
        async with self._get_connection() as db:
            cursor = await db.execute('''
                SELECT COALESCE(SUM(sand_amount), 0) as total_sand
                FROM deposits 
                WHERE user_id = ? AND paid = TRUE
            ''', (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def mark_deposit_paid(self, deposit_id, user_id):
        """Mark a specific deposit as paid"""
        async with self._get_connection() as db:
            await db.execute('''
                UPDATE deposits 
                SET paid = TRUE, paid_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (deposit_id, user_id))
            await db.commit()

    async def mark_all_user_deposits_paid(self, user_id):
        """Mark all unpaid deposits for a user as paid"""
        async with self._get_connection() as db:
            await db.execute('''
                UPDATE deposits 
                SET paid = TRUE, paid_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND paid = FALSE
            ''', (user_id,))
            await db.commit()

    async def cleanup_old_deposits(self, days=30):
        """Remove deposits older than specified days"""
        async with self._get_connection() as db:
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor = await db.execute('''
                DELETE FROM deposits 
                WHERE created_at < ? AND paid = TRUE
            ''', (cutoff_date.isoformat(),))
            await db.commit()
            return cursor.rowcount

    async def update_user_melange(self, user_id, melange_amount):
        """Update user melange amount"""
        async with self._get_connection() as db:
            await db.execute('''
                UPDATE users 
                SET total_melange = total_melange + ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (melange_amount, user_id))
            await db.commit()

    async def get_leaderboard(self, limit=10):
        """Get leaderboard data based on total sand from deposits"""
        async with self._get_connection() as db:
            cursor = await db.execute('''
                SELECT u.username, 
                       COALESCE(SUM(d.sand_amount), 0) as total_sand,
                       u.total_melange
                FROM users u
                LEFT JOIN deposits d ON u.user_id = d.user_id AND d.paid = FALSE
                GROUP BY u.user_id, u.username, u.total_melange
                ORDER BY u.total_melange DESC, total_sand DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_setting(self, key):
        """Get setting value"""
        async with self._get_connection() as db:
            cursor = await db.execute(
                'SELECT value FROM settings WHERE key = ?',
                (key,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_setting(self, key, value):
        """Set setting value"""
        async with self._get_connection() as db:
            await db.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                (key, value)
            )
            await db.commit()

    async def reset_all_stats(self):
        """Reset all user statistics and deposits"""
        async with self._get_connection() as db:
            cursor1 = await db.execute('DELETE FROM deposits')
            cursor2 = await db.execute('DELETE FROM users')
            await db.commit()
            return cursor1.rowcount + cursor2.rowcount

    async def get_all_unpaid_deposits(self):
        """Get all unpaid deposits across all users"""
        async with self._get_connection() as db:
            cursor = await db.execute('''
                SELECT d.*, u.total_melange
                FROM deposits d
                JOIN users u ON d.user_id = u.user_id
                WHERE d.paid = FALSE
                ORDER BY d.created_at ASC
            ''')
            rows = await cursor.fetchall()
            
            deposits = []
            for row in rows:
                deposits.append({
                    'id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'sand_amount': row[3],
                    'paid': bool(row[4]),
                    'created_at': datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    'paid_at': datetime.fromisoformat(row[6]) if row[6] else None,
                    'total_melange': row[7]
                })
            
            return deposits