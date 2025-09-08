-- Performance index for leaderboard command
CREATE INDEX idx_users_leaderboard ON users (total_melange DESC, username ASC);
