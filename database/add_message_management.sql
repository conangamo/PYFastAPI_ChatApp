-- Migration: Add message management fields (edit/delete support)
-- Run this to enable message editing and soft deletion

-- Add edited_at and is_deleted columns to messages table
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP WITH TIME ZONE NULL,
ADD COLUMN IF NOT EXISTS is_deleted VARCHAR(10) DEFAULT 'false' NOT NULL;

-- Create index for faster queries on non-deleted messages
CREATE INDEX IF NOT EXISTS idx_messages_is_deleted ON messages(is_deleted);

-- Comment for documentation
COMMENT ON COLUMN messages.edited_at IS 'Timestamp of last edit (NULL if never edited)';
COMMENT ON COLUMN messages.is_deleted IS 'Soft delete flag: "false" or "true"';

-- Display confirmation
SELECT 'Message management fields added successfully!' AS status;

