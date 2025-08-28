const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Database file path
const dbPath = path.join(__dirname, 'spice_tracker.db');

// Create database connection
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error('Error opening database:', err.message);
    } else {
        console.log('Connected to SQLite database.');
    }
});

// Initialize database tables
async function initializeDatabase() {
    return new Promise((resolve, reject) => {
        db.serialize(() => {
            // Create users table
            db.run(`
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_sand INTEGER DEFAULT 0,
                    total_melange INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            `, (err) => {
                if (err) {
                    console.error('Error creating users table:', err);
                    reject(err);
                }
            });

            // Create settings table
            db.run(`
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            `, (err) => {
                if (err) {
                    console.error('Error creating settings table:', err);
                    reject(err);
                }
            });

            // Insert default conversion rate if not exists
            db.run(`
                INSERT OR IGNORE INTO settings (key, value) VALUES ('sand_per_melange', '50')
            `, (err) => {
                if (err) {
                    console.error('Error setting default conversion rate:', err);
                    reject(err);
                } else {
                    resolve();
                }
            });
        });
    });
}

// Get user data
function getUser(userId) {
    return new Promise((resolve, reject) => {
        db.get(
            'SELECT * FROM users WHERE user_id = ?',
            [userId],
            (err, row) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(row);
                }
            }
        );
    });
}

// Create or update user
function upsertUser(userId, username, sandAmount = 0) {
    return new Promise((resolve, reject) => {
        db.run(`
            INSERT INTO users (user_id, username, total_sand, total_melange, last_updated)
            VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                total_sand = total_sand + ?,
                last_updated = CURRENT_TIMESTAMP
        `, [userId, username, sandAmount, sandAmount], function(err) {
            if (err) {
                reject(err);
            } else {
                resolve(this.changes);
            }
        });
    });
}

// Update user melange after conversion
function updateUserMelange(userId, melangeAmount) {
    return new Promise((resolve, reject) => {
        db.run(`
            UPDATE users 
            SET total_melange = total_melange + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ?
        `, [melangeAmount, userId], function(err) {
            if (err) {
                reject(err);
            } else {
                resolve(this.changes);
            }
        });
    });
}

// Get leaderboard
function getLeaderboard(limit = 10) {
    return new Promise((resolve, reject) => {
        db.all(`
            SELECT username, total_sand, total_melange
            FROM users
            ORDER BY total_melange DESC, total_sand DESC
            LIMIT ?
        `, [limit], (err, rows) => {
            if (err) {
                reject(err);
            } else {
                resolve(rows);
            }
        });
    });
}

// Get setting value
function getSetting(key) {
    return new Promise((resolve, reject) => {
        db.get(
            'SELECT value FROM settings WHERE key = ?',
            [key],
            (err, row) => {
                if (err) {
                    reject(err);
                } else {
                    resolve(row ? row.value : null);
                }
            }
        );
    });
}

// Set setting value
function setSetting(key, value) {
    return new Promise((resolve, reject) => {
        db.run(`
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        `, [key, value], function(err) {
            if (err) {
                reject(err);
            } else {
                resolve(this.changes);
            }
        });
    });
}

// Reset all user stats
function resetAllStats() {
    return new Promise((resolve, reject) => {
        db.run('DELETE FROM users', function(err) {
            if (err) {
                reject(err);
            } else {
                resolve(this.changes);
            }
        });
    });
}

// Close database connection
function closeDatabase() {
    return new Promise((resolve, reject) => {
        db.close((err) => {
            if (err) {
                reject(err);
            } else {
                console.log('Database connection closed.');
                resolve();
            }
        });
    });
}

module.exports = {
    initializeDatabase,
    getUser,
    upsertUser,
    updateUserMelange,
    getLeaderboard,
    getSetting,
    setSetting,
    resetAllStats,
    closeDatabase
};
