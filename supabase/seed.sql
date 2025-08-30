-- Seed data for Spice Tracker Bot
-- This file contains sample data for development and testing

-- Insert sample users
INSERT INTO users (user_id, username, total_melange) VALUES 
    ('123456789012345678', 'SpiceHarvester', 150),
    ('234567890123456789', 'MelangeMaster', 89),
    ('345678901234567890', 'SandCollector', 42),
    ('456789012345678901', 'RefineryRunner', 67),
    ('567890123456789012', 'SpiceTracker', 23)
ON CONFLICT (user_id) DO NOTHING;

-- Insert sample deposits
INSERT INTO deposits (user_id, username, sand_amount, paid, created_at) VALUES 
    ('123456789012345678', 'SpiceHarvester', 2500, TRUE, CURRENT_TIMESTAMP - INTERVAL '5 days'),
    ('123456789012345678', 'SpiceHarvester', 1800, TRUE, CURRENT_TIMESTAMP - INTERVAL '3 days'),
    ('123456789012345678', 'SpiceHarvester', 3200, FALSE, CURRENT_TIMESTAMP - INTERVAL '1 day'),
    ('234567890123456789', 'MelangeMaster', 1900, TRUE, CURRENT_TIMESTAMP - INTERVAL '6 days'),
    ('234567890123456789', 'MelangeMaster', 2100, TRUE, CURRENT_TIMESTAMP - INTERVAL '4 days'),
    ('234567890123456789', 'MelangeMaster', 2800, FALSE, CURRENT_TIMESTAMP - INTERVAL '2 days'),
    ('345678901234567890', 'SandCollector', 1200, TRUE, CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('345678901234567890', 'SandCollector', 1600, TRUE, CURRENT_TIMESTAMP - INTERVAL '5 days'),
    ('345678901234567890', 'SandCollector', 900, FALSE, CURRENT_TIMESTAMP - INTERVAL '1 day'),
    ('456789012345678901', 'RefineryRunner', 3000, TRUE, CURRENT_TIMESTAMP - INTERVAL '8 days'),
    ('456789012345678901', 'RefineryRunner', 2400, TRUE, CURRENT_TIMESTAMP - INTERVAL '6 days'),
    ('456789012345678901', 'RefineryRunner', 1800, FALSE, CURRENT_TIMESTAMP - INTERVAL '2 days'),
    ('567890123456789012', 'SpiceTracker', 800, TRUE, CURRENT_TIMESTAMP - INTERVAL '9 days'),
    ('567890123456789012', 'SpiceTracker', 1200, TRUE, CURRENT_TIMESTAMP - INTERVAL '7 days'),
    ('567890123456789012', 'SpiceTracker', 600, FALSE, CURRENT_TIMESTAMP - INTERVAL '1 day')
ON CONFLICT DO NOTHING;

-- Update user melange totals based on deposits (assuming 50 sand = 1 melange)
UPDATE users SET total_melange = 150 WHERE user_id = '123456789012345678';
UPDATE users SET total_melange = 89 WHERE user_id = '234567890123456789';
UPDATE users SET total_melange = 42 WHERE user_id = '345678901234567890';
UPDATE users SET total_melange = 67 WHERE user_id = '456789012345678901';
UPDATE users SET total_melange = 23 WHERE user_id = '567890123456789012';
