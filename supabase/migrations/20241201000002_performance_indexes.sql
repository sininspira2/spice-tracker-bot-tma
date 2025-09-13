-- Performance Index Migration for Spice Tracker Bot
-- Add composite indexes for improved query performance

-- Index for leaderboard queries - optimizes ordering by total_melange DESC, username ASC
CREATE INDEX idx_users_leaderboard ON users (total_melange DESC, username ASC);

-- Index for user deposit history queries - optimizes filtering by user_id and ordering by created_at DESC
CREATE INDEX idx_deposits_user_id_created_at ON deposits (user_id, created_at DESC);
