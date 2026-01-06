# Database Migrations

## Overview

This directory contains SQL migration scripts for updating the database schema.

## Applied Migrations

### 002_add_all_message_columns.sql
**Date:** 2026-01-06  
**Description:** Adds all missing columns to the `messages` table required by the Message model.

**Columns Added:**
- `edited_at` - Timestamp for when a message was last edited
- `is_deleted` - Soft delete flag ("false" or "true")
- `delivered_at` - Timestamp for message delivery (read receipts)
- `read_at` - Timestamp for when message was read (read receipts)
- `read_by_user_id` - User ID who read the message (read receipts)

**Indexes Created:**
- `idx_messages_edited_at`
- `idx_messages_is_deleted`
- `idx_messages_delivered_at`
- `idx_messages_read_at`
- `idx_messages_read_by_user_id`

## How to Apply Migrations

### Option 1: Using Docker (Recommended)

```bash
# Copy migration file to container
docker cp backend/migrations/002_add_all_message_columns.sql chat_postgres:/tmp/

# Execute migration
docker exec chat_postgres psql -U postgres -d chatapp -f /tmp/002_add_all_message_columns.sql
```

### Option 2: Direct PostgreSQL Connection

```bash
# Connect to PostgreSQL
docker exec -it chat_postgres psql -U postgres -d chatapp

# Run migration
\i /path/to/backend/migrations/002_add_all_message_columns.sql
```

### Option 3: Fresh Database (Development Only)

If you want to start fresh with all columns included:

1. Stop containers:
   ```bash
   docker-compose down
   ```

2. Remove database volume:
   ```bash
   docker volume rm <volume_name>
   ```

3. Restart (will use updated `database/init.sql`):
   ```bash
   docker-compose up -d
   ```

## Verify Migration

Check if all columns exist:

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'messages' 
AND column_name IN ('edited_at', 'is_deleted', 'delivered_at', 'read_at', 'read_by_user_id')
ORDER BY column_name;
```

Expected output:
```
   column_name   |        data_type         | is_nullable 
-----------------+--------------------------+-------------
 delivered_at    | timestamp with time zone | YES
 edited_at       | timestamp with time zone | YES
 is_deleted      | character varying        | NO
 read_at         | timestamp with time zone | YES
 read_by_user_id | uuid                     | YES
```

## Notes

- All migrations use `IF NOT EXISTS` to prevent errors if columns already exist
- Migrations are idempotent - safe to run multiple times
- The `database/init.sql` file has been updated to include all columns for new installations
