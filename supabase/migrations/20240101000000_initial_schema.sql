-- Initial schema for Spice Tracker Bot
-- This migration creates the core tables for tracking spice sand harvests and melange production

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    total_melange INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create deposits table for tracking individual harvests
CREATE TABLE IF NOT EXISTS deposits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    sand_amount INTEGER NOT NULL CHECK (sand_amount > 0),
    paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Create settings table for bot configuration
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create audit log table for tracking important changes
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id TEXT,
    old_values JSONB,
    new_values JSONB,
    user_id TEXT,
    username TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits (user_id);
CREATE INDEX IF NOT EXISTS idx_deposits_created_at ON deposits (created_at);
CREATE INDEX IF NOT EXISTS idx_deposits_paid ON deposits (paid);
CREATE INDEX IF NOT EXISTS idx_deposits_sand_amount ON deposits (sand_amount);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_total_melange ON users (total_melange DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);

-- Insert default settings
INSERT INTO settings (key, value, description) VALUES 
    ('sand_per_melange', '50', 'Amount of spice sand required for 1 melange'),
    ('default_harvester_percentage', '25.0', 'Default percentage for primary harvester in team splits'),
    ('max_sand_per_harvest', '10000', 'Maximum spice sand allowed per harvest'),
    ('min_sand_per_harvest', '1', 'Minimum spice sand required per harvest')
ON CONFLICT (key) DO NOTHING;

-- Create functions for common operations

-- Function to update user's last_updated timestamp
CREATE OR REPLACE FUNCTION update_user_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to log audit events
CREATE OR REPLACE FUNCTION log_audit_event()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (action, table_name, record_id, new_values, user_id, username)
        VALUES (TG_OP, TG_TABLE_NAME, NEW.user_id, to_jsonb(NEW), NEW.user_id, NEW.username);
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (action, table_name, record_id, old_values, new_values, user_id, username)
        VALUES (TG_OP, TG_TABLE_NAME, NEW.user_id, to_jsonb(OLD), to_jsonb(NEW), NEW.user_id, NEW.username);
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (action, table_name, record_id, old_values, user_id, username)
        VALUES (TG_OP, TG_TABLE_NAME, OLD.user_id, to_jsonb(OLD), OLD.user_id, OLD.username);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_user_timestamp();

CREATE TRIGGER audit_users_changes
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_deposits_changes
    AFTER INSERT OR UPDATE OR DELETE ON deposits
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_event();

-- Create views for common queries

-- View for user statistics
CREATE OR REPLACE VIEW user_stats AS
SELECT 
    u.user_id,
    u.username,
    u.total_melange,
    u.last_updated,
    u.created_at,
    COALESCE(SUM(CASE WHEN d.paid = FALSE THEN d.sand_amount ELSE 0 END), 0) as unpaid_sand,
    COALESCE(SUM(CASE WHEN d.paid = TRUE THEN d.sand_amount ELSE 0 END), 0) as paid_sand,
    COALESCE(SUM(d.sand_amount), 0) as total_sand,
    COUNT(d.id) as total_deposits,
    COUNT(CASE WHEN d.paid = FALSE THEN 1 END) as unpaid_deposits,
    COUNT(CASE WHEN d.paid = TRUE THEN 1 END) as paid_deposits
FROM users u
LEFT JOIN deposits d ON u.user_id = d.user_id
GROUP BY u.user_id, u.username, u.total_melange, u.last_updated, u.created_at;

-- View for leaderboard
CREATE OR REPLACE VIEW leaderboard AS
SELECT 
    u.user_id,
    u.username,
    u.total_melange,
    COALESCE(SUM(CASE WHEN d.paid = FALSE THEN d.sand_amount ELSE 0 END), 0) as unpaid_sand,
    COALESCE(SUM(CASE WHEN d.paid = TRUE THEN d.sand_amount ELSE 0 END), 0) as paid_sand,
    COUNT(d.id) as total_deposits,
    u.last_updated
FROM users u
LEFT JOIN deposits d ON u.user_id = d.user_id
GROUP BY u.user_id, u.username, u.total_melange, u.last_updated
ORDER BY u.total_melange DESC, unpaid_sand DESC;

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE deposits ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policies

-- Users table policies
CREATE POLICY "Users are viewable by everyone" ON users FOR SELECT USING (true);
CREATE POLICY "Users can insert their own data" ON users FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update their own data" ON users FOR UPDATE USING (true);

-- Deposits table policies
CREATE POLICY "Deposits are viewable by everyone" ON deposits FOR SELECT USING (true);
CREATE POLICY "Users can insert their own deposits" ON deposits FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update their own deposits" ON deposits FOR UPDATE USING (true);

-- Settings table policies
CREATE POLICY "Settings are viewable by everyone" ON settings FOR SELECT USING (true);
CREATE POLICY "Settings can be updated by authenticated users" ON settings FOR UPDATE USING (true);

-- Audit log policies
CREATE POLICY "Audit log is viewable by everyone" ON audit_log FOR SELECT USING (true);
CREATE POLICY "Audit log can be inserted by system" ON audit_log FOR INSERT WITH CHECK (true);

-- Create comments for documentation
COMMENT ON TABLE users IS 'Stores user information and melange totals';
COMMENT ON TABLE deposits IS 'Tracks individual spice sand deposits with payment status';
COMMENT ON TABLE settings IS 'Bot configuration settings';
COMMENT ON TABLE audit_log IS 'Audit trail for all data changes';
COMMENT ON VIEW user_stats IS 'Comprehensive user statistics view';
COMMENT ON VIEW leaderboard IS 'User rankings by melange production';

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO anon, authenticated;
