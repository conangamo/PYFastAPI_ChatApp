-- Migration: Add message reactions support
-- Run this to enable emoji reactions on messages

-- Create message_reactions table
CREATE TABLE IF NOT EXISTS message_reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    emoji VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- One user can only react with the same emoji once per message
    UNIQUE(message_id, user_id, emoji)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_reactions_message_id ON message_reactions(message_id);
CREATE INDEX IF NOT EXISTS idx_reactions_user_id ON message_reactions(user_id);
CREATE INDEX IF NOT EXISTS idx_reactions_emoji ON message_reactions(emoji);

-- Comments for documentation
COMMENT ON TABLE message_reactions IS 'Emoji reactions on messages';
COMMENT ON COLUMN message_reactions.emoji IS 'Emoji character (e.g., 👍, ❤️, 😂)';
COMMENT ON COLUMN message_reactions.created_at IS 'When the reaction was added';

-- Display confirmation
SELECT 'Message reactions table created successfully!' AS status;

