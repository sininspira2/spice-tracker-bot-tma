import asyncpg
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

class Database:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

    @asynccontextmanager
    async def _get_connection(self):
        """Context manager for database connections"""
        # Configure connection for Supabase compatibility
        conn = await asyncpg.connect(
            self.database_url,
            statement_cache_size=0,  # Disable prepared statements for pgbouncer compatibility
            command_timeout=60,      # Set command timeout
            server_settings={
                'application_name': 'spice_tracker_bot'
            }
        )
        try:
            yield conn
        finally:
            await conn.close()

    async def migrate_existing_data(self):
        """Migrate existing users with total_sand to the new deposits system"""
        async with self._get_connection() as conn:
            # Check if migration is needed
            columns = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'total_sand'
            """)
            
            if not columns:
                return 0  # No migration needed
            
            # Get users with total_sand > 0
            users_to_migrate = await conn.fetch('''
                SELECT user_id, username, total_sand 
                FROM users 
                WHERE total_sand > 0
            ''')
            
            migrated_count = 0
            for user in users_to_migrate:
                user_id, username, total_sand = user
                
                # Create a single deposit record for the existing total_sand
                await conn.execute('''
                    INSERT INTO deposits (user_id, username, sand_amount, paid, created_at)
                    VALUES ($1, $2, $3, FALSE, CURRENT_TIMESTAMP)
                ''', user_id, username, total_sand)
                migrated_count += 1
            
            # Remove total_sand column from users table
            await conn.execute('''
                CREATE TABLE users_new (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_melange INTEGER DEFAULT 0,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                INSERT INTO users_new (user_id, username, total_melange, last_updated)
                SELECT user_id, username, total_melange, last_updated FROM users
            ''')
            
            await conn.execute('DROP TABLE users')
            await conn.execute('ALTER TABLE users_new RENAME TO users')
            
            return migrated_count

    async def initialize(self):
        """Initialize database tables"""
        async with self._get_connection() as conn:
            # Create tables
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_melange INTEGER DEFAULT 0,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            # Create indexes
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits (user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_deposits_created_at ON deposits (created_at)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_deposits_paid ON deposits (paid)')
            
            # Insert default conversion rate
            await conn.execute(
                'INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING',
                'sand_per_melange', '50'
            )
            
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
        async with self._get_connection() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM users WHERE user_id = $1',
                user_id
            )
            if row:
                return {
                    'user_id': row[0],
                    'username': row[1], 
                    'total_melange': row[2],
                    'last_updated': row[3] if row[3] else datetime.now()
                }
            return None

    async def upsert_user(self, user_id, username):
        """Create or update user (without sand amount)"""
        async with self._get_connection() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username, last_updated)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    last_updated = CURRENT_TIMESTAMP
            ''', user_id, username)

    async def add_deposit(self, user_id, username, sand_amount):
        """Add a new sand deposit for a user"""
        async with self._get_connection() as conn:
            # Ensure user exists
            await self.upsert_user(user_id, username)
            
            # Add deposit record
            await conn.execute('''
                INSERT INTO deposits (user_id, username, sand_amount, created_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            ''', user_id, username, sand_amount)

    async def get_user_deposits(self, user_id, include_paid=True):
        """Get all deposits for a user"""
        async with self._get_connection() as conn:
            query = '''
                SELECT * FROM deposits 
                WHERE user_id = $1
            '''
            params = [user_id]
            
            if not include_paid:
                query += ' AND paid = FALSE'
            
            query += ' ORDER BY created_at DESC'
            
            rows = await conn.fetch(query, *params)
            
            deposits = []
            for row in rows:
                deposits.append({
                    'id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'sand_amount': row[3],
                    'paid': bool(row[4]),
                    'created_at': row[5] if row[5] else datetime.now(),
                    'paid_at': row[6] if row[6] else None
                })
            
            return deposits

    async def get_user_total_sand(self, user_id):
        """Get total sand from all deposits for a user"""
        async with self._get_connection() as conn:
            row = await conn.fetchrow('''
                SELECT COALESCE(SUM(sand_amount), 0) as total_sand
                FROM deposits 
                WHERE user_id = $1 AND paid = FALSE
            ''', user_id)
            return row[0] if row else 0

    async def get_user_paid_sand(self, user_id):
        """Get total sand from paid deposits for a user"""
        async with self._get_connection() as conn:
            row = await conn.fetchrow('''
                SELECT COALESCE(SUM(sand_amount), 0) as total_sand
                FROM deposits 
                WHERE user_id = $1 AND paid = TRUE
            ''', user_id)
            return row[0] if row else 0

    async def mark_deposit_paid(self, deposit_id, user_id):
        """Mark a specific deposit as paid"""
        async with self._get_connection() as conn:
            await conn.execute('''
                UPDATE deposits 
                SET paid = TRUE, paid_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND user_id = $2
            ''', deposit_id, user_id)

    async def mark_all_user_deposits_paid(self, user_id):
        """Mark all unpaid deposits for a user as paid"""
        async with self._get_connection() as conn:
            await conn.execute('''
                UPDATE deposits 
                SET paid = TRUE, paid_at = CURRENT_TIMESTAMP
                WHERE user_id = $1 AND paid = FALSE
            ''', user_id)

    async def cleanup_old_deposits(self, days=30):
        """Remove deposits older than specified days"""
        async with self._get_connection() as conn:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = await conn.execute('''
                DELETE FROM deposits 
                WHERE created_at < $1 AND paid = TRUE
            ''', cutoff_date)
            # Parse the result string to get the count of deleted rows
            if result:
                try:
                    # Result format: "DELETE X" where X is the number of rows deleted
                    count_str = result.split()[-1]
                    return int(count_str)
                except (ValueError, IndexError):
                    return 0
            return 0

    async def update_user_melange(self, user_id, melange_amount):
        """Update user melange amount"""
        async with self._get_connection() as conn:
            await conn.execute('''
                UPDATE users 
                SET total_melange = total_melange + $1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = $2
            ''', melange_amount, user_id)

    async def get_leaderboard(self, limit=10):
        """Get leaderboard data based on total sand from deposits"""
        async with self._get_connection() as conn:
            rows = await conn.fetch('''
                SELECT u.username, 
                       COALESCE(SUM(d.sand_amount), 0) as total_sand,
                       u.total_melange
                FROM users u
                LEFT JOIN deposits d ON u.user_id = d.user_id AND d.paid = FALSE
                GROUP BY u.user_id, u.username, u.total_melange
                ORDER BY u.total_melange DESC, total_sand DESC
                LIMIT $1
            ''', limit)
            return [dict(row) for row in rows]

    async def get_setting(self, key):
        """Get setting value"""
        async with self._get_connection() as conn:
            row = await conn.fetchrow(
                'SELECT value FROM settings WHERE key = $1',
                key
            )
            return row[0] if row else None

    async def set_setting(self, key, value):
        """Set setting value"""
        async with self._get_connection() as conn:
            await conn.execute(
                'INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value',
                key, value
            )

    async def reset_all_stats(self):
        """Reset all user statistics and deposits"""
        async with self._get_connection() as conn:
            result1 = await conn.execute('DELETE FROM deposits')
            result2 = await conn.execute('DELETE FROM users')
            
            # Parse the result strings to get the count of deleted rows
            def parse_delete_result(result):
                if result:
                    try:
                        # Result format: "DELETE X" where X is the number of rows deleted
                        count_str = result.split()[-1]
                        return int(count_str)
                    except (ValueError, IndexError):
                        return 0
                return 0
            
            return parse_delete_result(result1) + parse_delete_result(result2)

    async def get_all_unpaid_deposits(self):
        """Get all unpaid deposits across all users"""
        async with self._get_connection() as conn:
            rows = await conn.fetch('''
                SELECT d.*, u.total_melange
                FROM deposits d
                JOIN users u ON d.user_id = u.user_id
                WHERE d.paid = FALSE
                ORDER BY d.created_at ASC
            ''')
            
            deposits = []
            for row in rows:
                deposits.append({
                    'id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'sand_amount': row[3],
                    'paid': bool(row[4]),
                    'created_at': row[5] if row[5] else datetime.now(),
                    'paid_at': row[6] if row[6] else None,
                    'total_melange': row[7]
                })
            
            return deposits