-- Add a composite index to the deposits table to improve query performance for the ledger command.
CREATE INDEX idx_deposits_user_id_created_at ON deposits (user_id, created_at DESC);
