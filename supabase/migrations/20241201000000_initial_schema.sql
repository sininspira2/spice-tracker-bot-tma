-- Initial Schema Migration for Spice Tracker Bot
-- Complete database schema for fresh deployment

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table - stores Discord user information and melange tracking
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    total_melange INTEGER DEFAULT 0,
    paid_melange INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Deposits table - tracks spice sand deposits for users (sand accumulates toward melange)
CREATE TABLE deposits (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    sand_amount INTEGER NOT NULL,
    type TEXT DEFAULT 'solo' CHECK (type IN ('solo', 'expedition')),
    expedition_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- Expeditions table - tracks group expeditions with guild cuts
CREATE TABLE expeditions (
    id SERIAL PRIMARY KEY,
    initiator_id TEXT NOT NULL,
    initiator_username TEXT NOT NULL,
    total_sand INTEGER NOT NULL,
    sand_per_melange INTEGER NOT NULL,
    guild_cut_percentage FLOAT DEFAULT 10.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (initiator_id) REFERENCES users (user_id)
);

-- Expedition participants table - tracks individual participation in expeditions
CREATE TABLE expedition_participants (
    id SERIAL PRIMARY KEY,
    expedition_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    sand_amount INTEGER NOT NULL,
    melange_amount INTEGER NOT NULL,
    leftover_sand INTEGER NOT NULL,
    is_harvester BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (expedition_id) REFERENCES expeditions (id),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- Settings table - stores bot configuration
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Guild treasury table - tracks this guild's accumulated resources
CREATE TABLE guild_treasury (
    id SERIAL PRIMARY KEY,
    total_sand INTEGER DEFAULT 0,
    total_melange INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Guild transactions table - audit trail for guild treasury operations
CREATE TABLE guild_transactions (
    id SERIAL PRIMARY KEY,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('deposit', 'withdrawal')),
    sand_amount INTEGER NOT NULL,
    melange_amount INTEGER DEFAULT 0,
    expedition_id INTEGER,
    admin_user_id TEXT,
    admin_username TEXT,
    target_user_id TEXT,
    target_username TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (expedition_id) REFERENCES expeditions (id)
);

-- Melange payments table - tracks when melange is paid out to users
CREATE TABLE melange_payments (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    melange_amount INTEGER NOT NULL,
    admin_user_id TEXT,
    admin_username TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- Performance indexes
CREATE INDEX idx_deposits_user_id ON deposits (user_id);
CREATE INDEX idx_deposits_created_at ON deposits (created_at);
CREATE INDEX idx_deposits_type ON deposits (type);
CREATE INDEX idx_deposits_expedition_id ON deposits (expedition_id);

CREATE INDEX idx_expeditions_initiator_id ON expeditions (initiator_id);
CREATE INDEX idx_expeditions_created_at ON expeditions (created_at);

CREATE INDEX idx_expedition_participants_expedition_id ON expedition_participants (expedition_id);
CREATE INDEX idx_expedition_participants_user_id ON expedition_participants (user_id);

CREATE INDEX idx_guild_transactions_type ON guild_transactions (transaction_type);
CREATE INDEX idx_guild_transactions_created_at ON guild_transactions (created_at);
CREATE INDEX idx_guild_transactions_expedition_id ON guild_transactions (expedition_id);

CREATE INDEX idx_melange_payments_user_id ON melange_payments (user_id);
CREATE INDEX idx_melange_payments_created_at ON melange_payments (created_at);

-- Default configuration
INSERT INTO settings (key, value) VALUES ('sand_per_melange', '50');

-- Initial guild treasury record
INSERT INTO guild_treasury (total_sand, total_melange) 
VALUES (0, 0);

-- Useful views for common queries



-- Leaderboard view
CREATE VIEW leaderboard AS
SELECT 
    u.user_id,
    u.username,
    u.total_melange,
    u.paid_melange,
    (u.total_melange - u.paid_melange) as pending_melange,
    COALESCE(SUM(d.sand_amount), 0) as total_sand,
    COUNT(d.id) as total_deposits,
    u.last_updated
FROM users u
LEFT JOIN deposits d ON u.user_id = d.user_id
GROUP BY u.user_id, u.username, u.total_melange, u.paid_melange, u.last_updated
ORDER BY u.total_melange DESC, pending_melange DESC;

-- Expedition summary view
CREATE VIEW expedition_summary AS
SELECT 
    e.id,
    e.initiator_username,
    e.total_sand,
    e.guild_cut_percentage,
    e.created_at,
    COUNT(ep.id) as participant_count,
    SUM(ep.sand_amount) as distributed_sand,
    SUM(ep.melange_amount) as distributed_melange
FROM expeditions e
LEFT JOIN expedition_participants ep ON e.id = ep.expedition_id
GROUP BY e.id, e.initiator_username, e.total_sand, e.guild_cut_percentage, e.created_at
ORDER BY e.created_at DESC;

-- Function to update user's last_updated timestamp
CREATE OR REPLACE FUNCTION update_user_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for user timestamp updates
CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_timestamp();

-- Comments for documentation
COMMENT ON TABLE users IS 'Discord user information with melange totals and payment tracking';
COMMENT ON TABLE deposits IS 'Spice sand deposits that accumulate toward melange production';
COMMENT ON TABLE expeditions IS 'Group expeditions with guild cuts';
COMMENT ON TABLE expedition_participants IS 'Individual participation in expeditions';
COMMENT ON TABLE settings IS 'Bot configuration settings';
COMMENT ON TABLE guild_treasury IS 'This guild''s resource accumulation (per-guild database)';
COMMENT ON TABLE guild_transactions IS 'Audit trail for guild treasury operations';
COMMENT ON TABLE melange_payments IS 'Records of melange payments made to users';

COMMENT ON VIEW leaderboard IS 'User rankings by melange production and pending amounts';
COMMENT ON VIEW expedition_summary IS 'Summary statistics for expeditions';
