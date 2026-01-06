-- Migration: Add all missing columns to messages table
-- This migration adds all columns required by the Message model
-- Date: 2026-01-06

-- Add edited_at column (for message editing)
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP WITH TIME ZONE NULL;

-- Add is_deleted column (for soft deletion)
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS is_deleted VARCHAR(10) DEFAULT 'false' NOT NULL;

-- Add delivered_at column (for read receipts)
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP WITH TIME ZONE NULL;

-- Add read_at column (for read receipts)
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS read_at TIMESTAMP WITH TIME ZONE NULL;

-- Add read_by_user_id column (for read receipts)
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS read_by_user_id UUID NULL;

-- Add foreign key constraint for read_by_user_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_messages_read_by_user_id'
    ) THEN
        ALTER TABLE messages
        ADD CONSTRAINT fk_messages_read_by_user_id
        FOREIGN KEY (read_by_user_id) 
        REFERENCES users(id) 
        ON DELETE SET NULL;
    END IF;
END $$;

-- Update created_at to use timezone (if needed)
-- Note: This might fail if there's existing data, so we'll skip if column already has timezone
DO $$
BEGIN
    -- Check if created_at is timestamp without time zone
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' 
        AND column_name = 'created_at'
        AND data_type = 'timestamp without time zone'
    ) THEN
        -- Convert to timestamp with time zone
        ALTER TABLE messages 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'UTC';
    END IF;
END $$;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_messages_edited_at ON messages(edited_at);
CREATE INDEX IF NOT EXISTS idx_messages_is_deleted ON messages(is_deleted);
CREATE INDEX IF NOT EXISTS idx_messages_delivered_at ON messages(delivered_at);
CREATE INDEX IF NOT EXISTS idx_messages_read_at ON messages(read_at);
CREATE INDEX IF NOT EXISTS idx_messages_read_by_user_id ON messages(read_by_user_id);

-- Verify migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'messages' 
AND column_name IN ('edited_at', 'is_deleted', 'delivered_at', 'read_at', 'read_by_user_id', 'created_at')
ORDER BY column_name;

-- Display confirmation
SELECT 'All message columns added successfully!' AS status;

