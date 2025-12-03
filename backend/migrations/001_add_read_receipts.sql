-- Migration: Add Read Receipts columns to messages table
-- Date: 2025-11-20
-- Description: Adds delivered_at, read_at, and read_by_user_id columns for read receipts functionality

-- Add new columns
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS read_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS read_by_user_id UUID;

-- Add foreign key constraint
ALTER TABLE messages
ADD CONSTRAINT fk_messages_read_by_user 
FOREIGN KEY (read_by_user_id) 
REFERENCES users(id) 
ON DELETE SET NULL;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_messages_delivered_at ON messages(delivered_at);
CREATE INDEX IF NOT EXISTS idx_messages_read_at ON messages(read_at);
CREATE INDEX IF NOT EXISTS idx_messages_read_by_user_id ON messages(read_by_user_id);

-- Verify migration
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'messages' 
AND column_name IN ('delivered_at', 'read_at', 'read_by_user_id');

